import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from app.api.dependencies import get_db
from app.schemas.influencer import CampaignResearchRequest, InfluencerResponse
from app.services.discovery_service import discovery_service
from app.services.influencer_service import influencer_service
from app.services.ai_analyzer import claude_analyzer
from app.core.logging import logger

router = APIRouter(prefix="/discovery", tags=["discovery"])

@router.post("/search", response_model=dict)
async def discover_influencers(
    criteria: CampaignResearchRequest,
    db: Session = Depends(get_db)
):
    """
    Influencer Research Module:
    - Filters/identifies influencers by brand, niche, location, follower range, and keywords.
    - Saves to database with deduplication.
    - Automatically runs Claude AI analysis if auto_analyze_with_ai is enabled.
    """
    logger.info(f"Running influencer discovery for brand '{criteria.brand_name}', niche '{criteria.influencer_niche}'")
    
    # 1. Discover matching candidate leads
    candidates = discovery_service.discover_influencers(criteria)

    # 2. Batch save into database with deduplication
    batch_result = influencer_service.batch_create_influencers(db, candidates)
    saved_influencers = batch_result["created_influencers"]

    # 3. If auto-analyze is requested, run Claude AI analysis on new leads
    analyzed_results = []
    if criteria.auto_analyze_with_ai and saved_influencers:
        for inf in saved_influencers:
            try:
                analysis = await claude_analyzer.analyze_influencer(
                    influencer=inf,
                    brand_name=criteria.brand_name,
                    campaign_description=criteria.campaign_description,
                    relevant_keywords=criteria.relevant_keywords
                )
                inf.suitability_score = analysis["suitability_score"]
                inf.category = analysis["category"]
                inf.profile_summary = analysis["profile_summary"]
                inf.match_reason = analysis["match_reason"]
                inf.campaign_name = criteria.brand_name
                db.commit()
                db.refresh(inf)
                analyzed_results.append(inf)
            except Exception as e:
                logger.error(f"AI analysis failed for @{inf.instagram_username}: {e}")

    # Return comprehensive response
    return {
        "status": "success",
        "criteria": criteria.model_dump(),
        "total_discovered": len(candidates),
        "newly_added": batch_result["created_count"],
        "duplicates_skipped": batch_result["skipped_count"],
        "skipped_handles": batch_result["skipped_usernames"],
        "influencers": [InfluencerResponse.model_validate(inf) for inf in (analyzed_results if analyzed_results else saved_influencers)]
    }

@router.post("/upload-csv", response_model=dict)
async def upload_csv_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload CSV file of influencers, parse with header mapping, and store with deduplication.
    """
    if not file.filename.endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    contents = await file.read()
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError:
        decoded = contents.decode("latin-1")

    parsed_items = discovery_service.parse_csv_upload(decoded)
    if not parsed_items:
        raise HTTPException(status_code=400, detail="No valid influencer rows found in the CSV.")

    batch_result = influencer_service.batch_create_influencers(db, parsed_items)

    return {
        "filename": file.filename,
        "rows_detected": len(parsed_items),
        "imported": batch_result["created_count"],
        "duplicates_skipped": batch_result["skipped_count"],
        "skipped_usernames": batch_result["skipped_usernames"]
    }

@router.get("/sample-csv")
def download_sample_csv():
    """
    Download a sample CSV template for influencer upload.
    """
    sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "sample_influencers.csv")
    if os.path.exists(sample_path):
        return FileResponse(
            sample_path,
            media_type="text/csv",
            filename="sample_influencers_template.csv"
        )
    raise HTTPException(status_code=404, detail="Sample template not found")

