from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List
from rapidfuzz import fuzz
from datetime import date

from database import get_db
from models import Cause, User
from schemas import CauseResponse, CauseSearchParams, RelatedCase
from routers.auth import get_current_user

router = APIRouter()


def calculate_similarity(text1: str, text2: str) -> float:
    if not text1 or not text2:
        return 0.0
    return fuzz.ratio(text1.lower(), text2.lower()) / 100.0


@router.get("/search", response_model=List[CauseResponse])
async def search_causes(
    query: str = None,
    case_no: str = None,
    petitioner: str = None,
    respondent: str = None,
    advocate: str = None,
    court_no: str = None,
    hearing_date_from: date = None,
    hearing_date_to: date = None,
    case_type: str = None,
    is_hrce: bool = None,
    fuzzy: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query_obj = db.query(Cause)
    
    if fuzzy and (case_no or petitioner or respondent or advocate):
        all_causes = query_obj.all()
        results = []
        
        for cause in all_causes:
            score = 0
            matches = 0
            
            if case_no and cause.case_no:
                s = calculate_similarity(case_no, cause.case_no)
                if s > 0.6:
                    score += s
                    matches += 1
            
            if petitioner and cause.petitioner:
                s = calculate_similarity(petitioner, cause.petitioner)
                if s > 0.7:
                    score += s
                    matches += 1
            
            if respondent and cause.respondent:
                s = calculate_similarity(respondent, cause.respondent)
                if s > 0.7:
                    score += s
                    matches += 1
            
            if advocate and cause.advocate:
                s = calculate_similarity(advocate, cause.advocate)
                if s > 0.7:
                    score += s
                    matches += 1
            
            if matches > 0 and (score / matches) > 0.7:
                results.append(cause)
        
        if court_no:
            results = [c for c in results if c.court_no == court_no]
        if hearing_date_from:
            results = [c for c in results if c.hearing_date and c.hearing_date >= hearing_date_from]
        if hearing_date_to:
            results = [c for c in results if c.hearing_date and c.hearing_date <= hearing_date_to]
        if case_type:
            results = [c for c in results if c.case_type == case_type]
        if is_hrce is not None:
            results = [c for c in results if c.is_hrce == is_hrce]
        
        return results[offset:offset+limit]
    
    else:
        if query:
            query_obj = query_obj.filter(
                or_(
                    Cause.case_no.ilike(f"%{query}%"),
                    Cause.petitioner.ilike(f"%{query}%"),
                    Cause.respondent.ilike(f"%{query}%"),
                    Cause.advocate.ilike(f"%{query}%"),
                    Cause.raw_text.ilike(f"%{query}%")
                )
            )
        
        if case_no:
            query_obj = query_obj.filter(Cause.case_no.ilike(f"%{case_no}%"))
        if petitioner:
            query_obj = query_obj.filter(Cause.petitioner.ilike(f"%{petitioner}%"))
        if respondent:
            query_obj = query_obj.filter(Cause.respondent.ilike(f"%{respondent}%"))
        if advocate:
            query_obj = query_obj.filter(Cause.advocate.ilike(f"%{advocate}%"))
        if court_no:
            query_obj = query_obj.filter(Cause.court_no == court_no)
        if hearing_date_from:
            query_obj = query_obj.filter(Cause.hearing_date >= hearing_date_from)
        if hearing_date_to:
            query_obj = query_obj.filter(Cause.hearing_date <= hearing_date_to)
        if case_type:
            query_obj = query_obj.filter(Cause.case_type.ilike(f"%{case_type}%"))
        if is_hrce is not None:
            query_obj = query_obj.filter(Cause.is_hrce == is_hrce)
        
        results = query_obj.offset(offset).limit(limit).all()
        return results


@router.get("/{cause_id}", response_model=CauseResponse)
async def get_cause(
    cause_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cause = db.query(Cause).filter(Cause.id == cause_id).first()
    if not cause:
        raise HTTPException(status_code=404, detail="Cause not found")
    return cause


@router.get("/{cause_id}/related", response_model=List[RelatedCase])
async def get_related_causes(
    cause_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cause = db.query(Cause).filter(Cause.id == cause_id).first()
    if not cause:
        raise HTTPException(status_code=404, detail="Cause not found")
    
    all_causes = db.query(Cause).filter(Cause.id != cause_id).all()
    related = []
    
    for other_cause in all_causes:
        max_score = 0
        reason = ""
        
        if cause.petitioner and other_cause.petitioner:
            pet_score = calculate_similarity(cause.petitioner, other_cause.petitioner)
            if pet_score > max_score and pet_score > 0.75:
                max_score = pet_score
                reason = "Similar petitioner name"
        
        if cause.respondent and other_cause.respondent:
            res_score = calculate_similarity(cause.respondent, other_cause.respondent)
            if res_score > max_score and res_score > 0.75:
                max_score = res_score
                reason = "Similar respondent name"
        
        if cause.advocate and other_cause.advocate:
            adv_score = calculate_similarity(cause.advocate, other_cause.advocate)
            if adv_score > max_score and adv_score > 0.8:
                max_score = adv_score
                reason = "Same advocate"
        
        if max_score > 0.75:
            related.append(RelatedCase(
                cause=other_cause,
                similarity_score=max_score,
                match_reason=reason
            ))
    
    related.sort(key=lambda x: x.similarity_score, reverse=True)
    return related[:10]
