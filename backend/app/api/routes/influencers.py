from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.api.dependencies import get_db
from app.schemas.influencer import (
    InfluencerCreate,
    InfluencerUpdate,
    InfluencerResponse,
    InfluencerStatusUpdate,
    AIAnalysisRequest
)
from app.services.influencer_service import influencer_service
from app.services.ai_analyzer import claude_analyzer
from app.core.logging import logger

router = APIRouter(prefix="/influencers", tags=["influencers"])

@router.get("", response_model=dict)
def list_influencers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    niche: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    min_followers: Optional[int] = None,
    max_followers: Optional[int] = None,
    min_score: Optional[int] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    db: Session = Depends(get_db)
):
    """
    List influencers with filtering, search, sorting, and pagination.
    """
    items, total = influencer_service.get_influencers(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        niche=niche,
        status=status,
        location=location,
        min_followers=min_followers,
        max_followers=max_followers,
        min_score=min_score,
        sort_by=sort_by,
        sort_order=sort_order
    )

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": [InfluencerResponse.model_validate(item) for item in items]
    }

@router.get("/stats", response_model=dict)
def get_stats(db: Session = Depends(get_db)):
    """
    Get dashboard pipeline statistics.
    """
    return influencer_service.get_dashboard_stats(db)

@router.get("/{influencer_id}", response_model=InfluencerResponse)
def get_influencer(influencer_id: int, db: Session = Depends(get_db)):
    influencer = influencer_service.get_influencer(db, influencer_id)
    if not influencer:
        raise HTTPException(status_code=404, detail="Influencer not found")
    return InfluencerResponse.model_validate(influencer)

@router.post("", response_model=InfluencerResponse, status_code=status.HTTP_201_CREATED)
def create_influencer(payload: InfluencerCreate, db: Session = Depends(get_db)):
    """
    Add a single influencer record with automatic deduplication.
    """
    influencer, is_created = influencer_service.create_influencer(db, payload)
    if not is_created:
        raise HTTPException(
            status_code=409,
            detail=f"Influencer with handle '@{influencer.instagram_username}' or profile URL already exists."
        )
    return InfluencerResponse.model_validate(influencer)

@router.patch("/{influencer_id}", response_model=InfluencerResponse)
def update_influencer(influencer_id: int, payload: InfluencerUpdate, db: Session = Depends(get_db)):
    updated = influencer_service.update_influencer(db, influencer_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Influencer not found")
    return InfluencerResponse.model_validate(updated)

@router.put("/{influencer_id}/status", response_model=InfluencerResponse)
def update_lead_status(influencer_id: int, payload: InfluencerStatusUpdate, db: Session = Depends(get_db)):
    """
    Update lead lifecycle status.
    """
    updated = influencer_service.update_status(db, influencer_id, payload.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Influencer not found")
    return InfluencerResponse.model_validate(updated)

@router.delete("/{influencer_id}", status_code=status.HTTP_200_OK)
def delete_influencer(influencer_id: int, db: Session = Depends(get_db)):
    deleted = influencer_service.delete_influencer(db, influencer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Influencer not found")
    return {"message": "Influencer removed successfully", "id": influencer_id}

@router.post("/batch-analyze-ai", response_model=dict)
async def analyze_influencers_with_claude(payload: AIAnalysisRequest, db: Session = Depends(get_db)):
    """
    Run Claude AI analysis on selected influencers:
    - Calculates suitability score (0-100)
    - Generates profile summary
    - Categorizes influencer
    - Explains campaign match rationale
    """
    results = []
    for inf_id in payload.influencer_ids:
        inf = influencer_service.get_influencer(db, inf_id)
        if not inf:
            continue

        try:
            analysis = await claude_analyzer.analyze_influencer(
                influencer=inf,
                brand_name=payload.brand_name,
                campaign_description=payload.campaign_description,
                relevant_keywords=payload.relevant_keywords or ""
            )

            # Update DB record
            inf.suitability_score = analysis["suitability_score"]
            inf.category = analysis["category"]
            inf.profile_summary = analysis["profile_summary"]
            inf.match_reason = analysis["match_reason"]
            inf.campaign_name = payload.brand_name

            db.commit()
            db.refresh(inf)

            results.append({
                "influencer_id": inf.id,
                "name": inf.name,
                "username": inf.instagram_username,
                "analysis": analysis
            })
        except Exception as e:
            logger.error(f"Error analyzing influencer {inf_id}: {e}")

    return {
        "processed": len(results),
        "results": results
    }

