from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from database import get_db
from models import User, UserRole, ScraperLog, Cause
from schemas import ScraperLogResponse, ScraperTriggerResponse
from routers.auth import get_current_user
from scraper import run_scraper, stop_scraper, get_scraper_progress

router = APIRouter()


def check_admin_or_superadmin(current_user: User):
    if current_user.role not in [UserRole.COURT_ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized. Admin access required.")


@router.post("/trigger", response_model=ScraperTriggerResponse)
def trigger_scraper(
    target_date: date = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin_or_superadmin(current_user)
    
    print(f"Triggering scraper with target_date: {target_date}")
    
    try:
        records_count = run_scraper(db, target_date)
        return ScraperTriggerResponse(
            message="Scraper completed successfully",
            status="success",
            records_extracted=records_count
        )
    except Exception as e:
        return ScraperTriggerResponse(
            message=f"Scraper failed: {str(e)}",
            status="error",
            records_extracted=0
        )


@router.get("/logs", response_model=List[ScraperLogResponse])
async def get_scraper_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin_or_superadmin(current_user)
    
    logs = db.query(ScraperLog).order_by(ScraperLog.created_at.desc()).limit(limit).all()
    return logs


@router.get("/status")
async def get_scraper_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin_or_superadmin(current_user)
    
    latest_log = db.query(ScraperLog).order_by(ScraperLog.created_at.desc()).first()
    
    if not latest_log:
        return {
            "status": "never_run",
            "last_run": None,
            "last_status": None,
            "total_records": 0
        }
    
    total_causes = db.query(Cause).count()
    
    return {
        "status": str(latest_log.status.value) if hasattr(latest_log.status, 'value') else str(latest_log.status),
        "last_run": latest_log.created_at,
        "last_status": str(latest_log.status.value) if hasattr(latest_log.status, 'value') else str(latest_log.status),
        "total_records": total_causes,
        "last_extraction_count": latest_log.records_extracted
    }


@router.post("/stop")
async def stop_scraper_endpoint(
    current_user: User = Depends(get_current_user)
):
    check_admin_or_superadmin(current_user)
    stop_scraper()
    return {"message": "Scraper stop requested"}


@router.get("/progress")
async def get_progress(
    current_user: User = Depends(get_current_user)
):
    check_admin_or_superadmin(current_user)
    return get_scraper_progress()
