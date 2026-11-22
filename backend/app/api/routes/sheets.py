from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from typing import List, Optional

from app.api.dependencies import get_db
from app.schemas.influencer import GoogleSheetsSyncRequest
from app.models.influencer import Influencer
from app.models.outreach import InfluencerReply, OutreachEmail
from app.services.google_sheets import google_sheets_service
from app.services.ai_analyzer import claude_analyzer
from app.services.gmail_service import gmail_service
from app.core.config import settings
from app.core.logging import logger

router = APIRouter(prefix="/sheets", tags=["google-sheets"])

@router.post("/sync", response_model=dict)
async def sync_to_google_sheets(
    payload: GoogleSheetsSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Sync influencer records to Google Sheets.
    If credentials are not yet configured, cleanly syncs to local export file.
    """
    query = db.query(Influencer)
    if payload.influencer_ids:
        query = query.filter(Influencer.id.in_(payload.influencer_ids))

    influencers = query.all()
    if not influencers:
        raise HTTPException(status_code=400, detail="No influencers found to sync.")

    outreach_metadata = {}
    latest_emails = (
        db.query(OutreachEmail)
        .options(joinedload(OutreachEmail.campaign))
        .filter(OutreachEmail.influencer_id.in_([inf.id for inf in influencers]))
        .order_by(OutreachEmail.id.desc())
        .all()
    )
    for email in latest_emails:
        outreach_metadata.setdefault(
            email.influencer_id,
            {
                "campaign_name": email.campaign.name if email.campaign else "N/A",
                "subject": email.subject,
                "status": "Email Sent" if email.status == "sent" else email.status.replace("_", " ").title(),
                "sent_at": (
                    email.sent_at.strftime("%Y-%m-%d %H:%M:%S")
                    if email.sent_at
                    else "N/A"
                ),
            },
        )
    latest_replies = (
        db.query(InfluencerReply)
        .filter(InfluencerReply.influencer_id.in_([inf.id for inf in influencers]))
        .order_by(InfluencerReply.received_at.desc(), InfluencerReply.id.desc())
        .all()
    )
    for reply in latest_replies:
        metadata = outreach_metadata.setdefault(reply.influencer_id, {})
        metadata["reply_classification"] = reply.classification
        metadata["reply_received_at"] = (
            reply.received_at.strftime("%Y-%m-%d %H:%M:%S") if reply.received_at else "N/A"
        )
        metadata.setdefault(
            "campaign_name",
            reply.campaign.name if reply.campaign else "N/A",
        )

    sync_result = await google_sheets_service.sync_influencers(
        influencers=influencers,
        spreadsheet_id=payload.spreadsheet_id,
        outreach_metadata=outreach_metadata,
    )

    if sync_result.get("success"):
        now = datetime.now()
        for inf in influencers:
            inf.synced_to_sheets = True
            inf.last_synced_at = now
        db.commit()

    return sync_result

@router.get("/status", response_model=dict)
def get_integrations_status(db: Session = Depends(get_db)):
    """
    Returns live connectivity status of Claude AI, Google Sheets, and Gmail.
    """
    return {
        "claude_ai": {
            "configured": claude_analyzer.is_api_configured(),
            "model": settings.CLAUDE_MODEL,
            "demo_mode": settings.DEMO_MODE,
            "status_label": "Live API Active" if (claude_analyzer.is_api_configured() and not settings.DEMO_MODE) else "Demo AI Engine (Active)"
        },
        "google_sheets": {
            "configured": google_sheets_service.is_configured(),
            "spreadsheet_id": settings.GOOGLE_SPREADSHEET_ID or None,
            "status_label": "Live Google Sheets" if google_sheets_service.is_configured() else "Local CSV Sync Archive (Active)"
        },
        "gmail": gmail_service.connection_status(db)
    }
