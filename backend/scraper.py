import requests
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime, date
from sqlalchemy.orm import Session
import re

from models import Cause, ScraperLog, ScraperStatus

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CAUSE_LIST_URL = "https://mhc.tn.gov.in/judis/clists/clists-madras/index.php"

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


def detect_hrce_case(text: str) -> bool:
    if not text:
        return False
    text_upper = text.upper()
    return any(keyword.upper() in text_upper for keyword in HRCE_KEYWORDS)


def parse_cause_entry(entry_text: str) -> dict:
    data = {
        "court_no": None,
        "case_no": None,
        "petitioner": None,
        "respondent": None,
        "advocate": None,
        "hearing_date": None,
        "hearing_time": None,
        "case_type": None,
        "raw_text": entry_text,
        "is_hrce": detect_hrce_case(entry_text)
    }
    
    case_no_match = re.search(r'(W\.P\.|WP|O\.S\.A\.|OSA|CRL\.A\.|CRLA|W\.A\.|WA|C\.M\.A\.|CMA)[\s\.]*(No\.|NO\.)?[\s]*(\d+)[\s]*(of|OF)?[\s]*(\d{4})', entry_text, re.IGNORECASE)
    if case_no_match:
        data["case_no"] = case_no_match.group(0).strip()
    
    court_match = re.search(r'Court[\s]*(?:No\.?|Number)?[\s]*:?[\s]*(\d+)', entry_text, re.IGNORECASE)
    if court_match:
        data["court_no"] = court_match.group(1)
    
    vs_match = re.search(r'(.+?)\s+(?:v\.|vs\.?|versus)\s+(.+?)(?:\n|Adv)', entry_text, re.IGNORECASE)
    if vs_match:
        data["petitioner"] = vs_match.group(1).strip()
        data["respondent"] = vs_match.group(2).strip()
    
    adv_match = re.search(r'(?:Adv|Advocate|For|Counsel)[\s:]+(.+?)(?:\n|$)', entry_text, re.IGNORECASE)
    if adv_match:
        data["advocate"] = adv_match.group(1).strip()
    
    return data


def scrape_cause_list(db: Session) -> int:
    try:
        response = requests.get(CAUSE_LIST_URL, timeout=30, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        causes = []
        entries = soup.find_all('div', class_='cause-entry')
        
        if not entries:
            entries = soup.find_all('tr')
        
        if not entries:
            text_blocks = soup.get_text().split('\n\n')
            entries = [block for block in text_blocks if len(block.strip()) > 50]
        
        for entry in entries:
            if isinstance(entry, str):
                entry_text = entry
            else:
                entry_text = entry.get_text(separator=' ', strip=True)
            
            if len(entry_text.strip()) < 20:
                continue
            
            cause_data = parse_cause_entry(entry_text)
            
            cause = Cause(**cause_data)
            causes.append(cause)
        
        if causes:
            db.bulk_save_objects(causes)
            db.commit()
        
        log = ScraperLog(
            status=ScraperStatus.SUCCESS,
            records_extracted=len(causes),
            run_date=date.today()
        )
        db.add(log)
        db.commit()
        
        return len(causes)
    
    except Exception as e:
        log = ScraperLog(
            status=ScraperStatus.ERROR,
            records_extracted=0,
            error_message=str(e),
            run_date=date.today()
        )
        db.add(log)
        db.commit()
        raise


def run_scraper(db: Session) -> int:
    return scrape_cause_list(db)
