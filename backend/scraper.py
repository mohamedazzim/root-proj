import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime, date
from sqlalchemy.orm import Session
import re
import pdfplumber
import os
import tempfile

from models import Cause, ScraperLog, ScraperStatus

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://www.mhc.tn.gov.in/judis/clists/clists-madras"
DATE_API_URL = f"{BASE_URL}/api/getDate.php?toc=1"
PDF_BASE_URL = f"{BASE_URL}/causelists/pdf"

HRCE_KEYWORDS = [
    "HRCE",
    "Hindu Religious",
    "Charitable Endowments",
    "Temple",
    "Devasthanam",
    "Devaswom",
    "Mutt",
    "Religious Trust",
    "Dharmada",
    "Arulmigu"
]


# Global state for scraper control
SCRAPER_STATE = {
    "is_running": False,
    "stop_requested": False,
    "current_action": "Idle",
    "logs": []
}

def add_log(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    SCRAPER_STATE["logs"].insert(0, log_entry)
    # Keep only last 50 logs
    if len(SCRAPER_STATE["logs"]) > 50:
        SCRAPER_STATE["logs"].pop()
    SCRAPER_STATE["current_action"] = message

def stop_scraper():
    if SCRAPER_STATE["is_running"]:
        SCRAPER_STATE["stop_requested"] = True
        add_log("Stop requested by user...")
        return True
    return False

def get_scraper_progress():
    return SCRAPER_STATE

def detect_hrce_case(text: str) -> bool:
    if not text:
        return False
    text_upper = text.upper()
    return any(keyword.upper() in text_upper for keyword in HRCE_KEYWORDS)

def fetch_available_dates():
    try:
        response = requests.get(DATE_API_URL, verify=False, timeout=30)
        response.raise_for_status()
        data = response.json()
        # data is list of dicts: [{"doc":"2025-11-24"}, ...]
        return [item['doc'] for item in data]
    except Exception as e:
        print(f"Error fetching dates: {e}")
        return []

def download_pdf(date_str):
    # date_str is YYYY-MM-DD
    # PDF filename format: cause_DDMMYYYY.pdf
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        filename = f"cause_{dt.strftime('%d%m%Y')}.pdf"
        url = f"{PDF_BASE_URL}/{filename}"
        
        response = requests.get(url, verify=False, timeout=60)
        if response.status_code == 200:
            fd, path = tempfile.mkstemp(suffix=".pdf")
            with os.fdopen(fd, 'wb') as tmp:
                tmp.write(response.content)
            return path
        else:
            print(f"Failed to download PDF for {date_str}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        return None

def parse_pdf_content(pdf_path, hearing_date):
    causes = []
    current_court = None
    
    # Regex patterns
    court_pattern = re.compile(r"COURT\s+NO\.\s+(\d+\s*[a-zA-Z]?)")
    # Main case pattern: SrNo CaseNo Rest
    main_case_pattern = re.compile(r"^(\d+)\s+([A-Z]+(?:/[A-Za-z0-9]+)?/\d+/\d+)\s+(.*)")
    # Connected case pattern: (AND)? CaseNo Rest
    # Matches lines starting with AND or just whitespace, then a case number
    connected_case_pattern = re.compile(r"^\s*(?:AND)?\s*([A-Z]+(?:/[A-Za-z0-9]+)?/\d+/\d+)\s+(.*)")
    # Pattern for just "AND" on a line, implying next line has case info
    and_only_pattern = re.compile(r"^\s*AND\s*$")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                    
                lines = text.split('\n')
                
                # Try to find court number
                for line in lines:
                    match = court_pattern.search(line)
                    if match:
                        current_court = f"COURT NO. {match.group(1)}"
                
                i = 0
                current_sr_no = None
                
                while i < len(lines):
                    line = lines[i].strip()
                    if not line:
                        i += 1
                        continue

                    # Check for Main Case
                    main_match = main_case_pattern.match(line)
                    connected_match = connected_case_pattern.match(line)
                    and_only_match = and_only_pattern.match(line)
                    
                    is_main = bool(main_match)
                    is_connected = bool(connected_match) and not is_main
                    is_and_only = bool(and_only_match)
                    
                    if is_main:
                        current_sr_no = main_match.group(1)
                        case_no = main_match.group(2)
                        rest_of_line = main_match.group(3)
                    elif is_connected and current_sr_no:
                        # It's a connected case under the current Sr No
                        case_no = connected_match.group(1)
                        rest_of_line = connected_match.group(2)
                    elif is_and_only and current_sr_no:
                        # "AND" is on this line, check next line for case no
                        if i + 1 < len(lines):
                            next_line = lines[i+1].strip()
                            # Try to match case pattern on next line
                            # It might not have "AND" prefix since "AND" was on previous line
                            # But we can reuse connected_case_pattern or just look for case no
                            next_match = re.match(r"^\s*([A-Z]+(?:/[A-Za-z0-9]+)?/\d+/\d+)\s+(.*)", next_line)
                            if next_match:
                                case_no = next_match.group(1)
                                rest_of_line = next_match.group(2)
                                i += 1 # Skip the next line since we consumed it
                            else:
                                i += 1
                                continue
                        else:
                            i += 1
                            continue
                    else:
                        # Not a case line, move on
                        i += 1
                        continue
                        
                    # Common parsing logic for both main and connected cases
                    # Improved Petitioner/Advocate separation
                    # Look for common advocate prefixes
                    adv_split = re.split(r'\s+(M/S\.|Mr\.|Ms\.|Mrs\.|Dr\.|Adv\.)', rest_of_line, 1)
                    
                    if len(adv_split) >= 3:
                        petitioner = adv_split[0].strip()
                        advocate = (adv_split[1] + adv_split[2]).strip()
                    else:
                        # Fallback to double space split
                        parts = re.split(r'\s{2,}', rest_of_line)
                        petitioner = parts[0] if len(parts) > 0 else ""
                        advocate = parts[1] if len(parts) > 1 else ""
                    
                    case_type = ""
                    respondent = ""
                    
                    # Look ahead for next lines to find VS and Respondent
                    # The structure is usually:
                    # Line 1: Seq CaseNo Petitioner Advocate
                    # Line 2: (CaseType) VS
                    # Line 3: Respondent Location
                    
                    # Check next few lines
                    j = 1
                    found_vs = False
                    
                    # We need to be careful not to consume the next case's line
                    while i + j < len(lines) and j <= 5: # Increased lookahead slightly
                        next_line = lines[i+j].strip()
                        
                        # Stop if next line looks like a new case
                        if main_case_pattern.match(next_line) or connected_case_pattern.match(next_line) or and_only_pattern.match(next_line):
                            break
                        
                        # Check for Case Type
                        if not case_type and "(" in next_line:
                                case_type_match = re.search(r"\((.*?)\)", next_line)
                                if case_type_match:
                                    case_type = case_type_match.group(1)
                        
                        # Check for VS
                        if "VS" in next_line or "vs" in next_line.lower():
                            found_vs = True
                            # Sometimes VS is on the same line as Respondent
                            # or Respondent is on the next line
                            
                            # If there is text after VS, it might be respondent
                            vs_parts = re.split(r'VS|vs', next_line, flags=re.IGNORECASE)
                            if len(vs_parts) > 1 and len(vs_parts[1].strip()) > 3:
                                    # Likely respondent is here
                                    respondent = vs_parts[1].strip()
                                    # Clean up dashes
                                    respondent = re.sub(r'^-+\s*', '', respondent)
                            
                        elif found_vs and not respondent:
                            # This line is likely the respondent
                            respondent = next_line.split('   ')[0].strip()
                            # Don't break immediately, might find more info or clean up
                            break
                        
                        j += 1
                        
                    cause_data = {
                        "sr_no": current_sr_no,
                        "court_no": current_court,
                        "case_no": case_no,
                        "petitioner": petitioner,
                        "respondent": respondent,
                        "advocate": advocate,
                        "hearing_date": hearing_date,
                        "case_type": case_type,
                        "raw_text": line,
                        "is_hrce": detect_hrce_case(petitioner) or detect_hrce_case(respondent) or detect_hrce_case(line)
                    }
                    causes.append(cause_data)
                    i += 1
                    
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        
    return causes

def scrape_cause_list(db: Session, target_date: date = None) -> int:
    SCRAPER_STATE["is_running"] = True
    SCRAPER_STATE["stop_requested"] = False
    SCRAPER_STATE["logs"] = []
    total_extracted = 0
    
    add_log(f"Starting scraper run. Target date: {target_date if target_date else 'All available'}")
    
    try:
        if target_date:
            dates = [target_date.strftime("%Y-%m-%d")]
        else:
            add_log("Fetching available dates from server...")
            dates = fetch_available_dates()
            
        add_log(f"Found {len(dates)} dates to process: {dates}")
        
        for date_str in dates:
            if SCRAPER_STATE["stop_requested"]:
                add_log("Scraper stopped by user request.")
                break
                
            add_log(f"Processing date: {date_str}")
            pdf_path = download_pdf(date_str)
            if not pdf_path:
                add_log(f"Skipping {date_str} - PDF download failed")
                continue
                
            try:
                hearing_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                add_log(f"Parsing PDF for {date_str}...")
                
                # Delete existing records for this date to avoid duplicates
                db.query(Cause).filter(Cause.hearing_date == hearing_date).delete()
                db.commit()
                
                causes_data = parse_pdf_content(pdf_path, hearing_date)
                
                if causes_data:
                    cause_objects = [Cause(**data) for data in causes_data]
                    db.bulk_save_objects(cause_objects)
                    db.commit()
                    total_extracted += len(cause_objects)
                    add_log(f"Successfully extracted {len(cause_objects)} causes for {date_str}")
                else:
                    add_log(f"No causes found in PDF for {date_str}")
            except Exception as e:
                add_log(f"Error processing {date_str}: {str(e)}")
            finally:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
        
        status = ScraperStatus.SUCCESS if not SCRAPER_STATE["stop_requested"] else ScraperStatus.ERROR
        log = ScraperLog(
            status=status,
            records_extracted=total_extracted,
            run_date=date.today(),
            error_message="Stopped by user" if SCRAPER_STATE["stop_requested"] else None
        )
        db.add(log)
        db.commit()
        
        add_log(f"Scraper finished. Total records: {total_extracted}")
        return total_extracted
    
    except Exception as e:
        add_log(f"Critical scraper error: {str(e)}")
        log = ScraperLog(
            status=ScraperStatus.ERROR,
            records_extracted=total_extracted,
            error_message=str(e),
            run_date=date.today()
        )
        db.add(log)
        db.commit()
        raise
    finally:
        SCRAPER_STATE["is_running"] = False
        SCRAPER_STATE["stop_requested"] = False


def run_scraper(db: Session, target_date: date = None) -> int:
    return scrape_cause_list(db, target_date)

