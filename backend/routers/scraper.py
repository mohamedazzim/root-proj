from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from database import get_db
from models import User, UserRole, ScraperLog, Cause
from schemas import ScraperLogResponse, ScraperTriggerResponse
from routers.auth import get_current_user
from scraper import run_scraper

router = APIRouter()


def check_admin_or_superadmin(current_user: User):
    if current_user.role not in [UserRole.COURT_ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized. Admin access required.")


@router.post("/trigger", response_model=ScraperTriggerResponse)
async def trigger_scraper(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin_or_superadmin(current_user)
    
    try:
        records_count = run_scraper(db)
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
        "status": latest_log.status,
        "last_run": latest_log.run_date,
        "last_status": latest_log.status,
        "total_records": total_causes,
        "last_extraction_count": latest_log.records_extracted
    }
