from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.logging import logger
from app.schemas.outreach import CampaignCreate, EmailUpdate, OutcomeUpdate, ReplyDraftUpdate
from app.services.outreach_service import outreach_service

router = APIRouter(prefix="/outreach", tags=["outreach"])


class SendRequest(BaseModel):
    campaign_id: Optional[int] = None
    email_ids: Optional[List[int]] = None


class SimulateReplyRequest(BaseModel):
    email_id: int
    decline: bool = False


class SendRepliesRequest(BaseModel):
    reply_ids: Optional[List[int]] = None


class DemoIncomingReplyRequest(BaseModel):
    email_id: int
    subject: Optional[str] = None
    body: str = Field(..., min_length=1, max_length=10000)


@router.get("/tracking")
def tracking(db: Session = Depends(get_db)):
    return outreach_service.tracking_summary(db)


@router.get("/analytics")
def analytics(campaign_id: Optional[int] = None, db: Session = Depends(get_db)):
    return outreach_service.campaign_analytics(db, campaign_id)


@router.get("/campaigns")
def list_campaigns(db: Session = Depends(get_db)):
    return {"campaigns": outreach_service.list_campaigns(db)}


@router.post("/campaigns")
async def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    try:
        return await outreach_service.create_campaign(db, payload)
    except Exception as e:
        db.rollback()
        logger.error(f"Outreach draft generation failed: {e}")
        raise HTTPException(status_code=502, detail="Email draft generation failed. Check Claude configuration and backend logs.") from e


@router.get("/emails")
def list_emails(
    campaign_id: Optional[int] = None,
    influencer_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return {"emails": outreach_service.list_emails(db, campaign_id, influencer_id, status)}


@router.get("/replies")
def list_replies(
    campaign_id: Optional[int] = None,
    influencer_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return {"replies": outreach_service.list_replies(db, campaign_id, influencer_id, status)}


@router.get("/conversations/{influencer_id}")
def conversation(influencer_id: int, db: Session = Depends(get_db)):
    try:
        return outreach_service.conversation_history(db, influencer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/replies/{reply_id}")
def update_reply_draft(reply_id: int, payload: ReplyDraftUpdate, db: Session = Depends(get_db)):
    try:
        reply = outreach_service.update_reply_draft(db, reply_id, payload.subject, payload.body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    return reply


@router.post("/replies/{reply_id}/approve")
def approve_reply(reply_id: int, db: Session = Depends(get_db)):
    try:
        reply = outreach_service.approve_reply(db, reply_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    return reply


@router.post("/replies/{reply_id}/reject")
def reject_reply(reply_id: int, db: Session = Depends(get_db)):
    try:
        reply = outreach_service.reject_reply(db, reply_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    return reply


@router.post("/send-replies")
async def send_approved_replies(payload: SendRepliesRequest, db: Session = Depends(get_db)):
    return await outreach_service.send_approved_replies(db, payload.reply_ids)


@router.patch("/emails/{email_id}")
def update_email(email_id: int, payload: EmailUpdate, db: Session = Depends(get_db)):
    try:
        updated = outreach_service.update_email(db, email_id, payload.subject, payload.body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="Email not found")
    return updated


@router.post("/emails/{email_id}/approve")
def approve_email(email_id: int, db: Session = Depends(get_db)):
    try:
        updated = outreach_service.approve_email(db, email_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="Email not found")
    return updated


@router.post("/emails/{email_id}/reject")
def reject_email(email_id: int, db: Session = Depends(get_db)):
    try:
        updated = outreach_service.reject_email(db, email_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="Email not found")
    return updated


@router.post("/send")
async def send_approved(payload: SendRequest, db: Session = Depends(get_db)):
    try:
        return await outreach_service.send_approved(db, payload.campaign_id, payload.email_ids)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/emails/{email_id}/outcome")
def record_outcome(email_id: int, payload: OutcomeUpdate, db: Session = Depends(get_db)):
    try:
        return outreach_service.apply_outcome(db, email_id, payload.outcome)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/events")
def list_events(
    campaign_id: Optional[int] = Query(None),
    influencer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    events = outreach_service.list_events(db, campaign_id, influencer_id)
    return {
        "events": [
            {
                "id": e.id,
                "email_id": e.email_id,
                "campaign_id": e.campaign_id,
                "influencer_id": e.influencer_id,
                "event_type": e.event_type,
                "detail": e.detail,
                "created_at": e.created_at,
            }
            for e in events
        ]
    }


@router.post("/jobs/process-due")
async def process_due(force: bool = False, db: Session = Depends(get_db)):
    """Create follow-up drafts that are due. force=true ignores the 3–7 day wait (demo/testing)."""
    try:
        return await outreach_service.process_due_followups(db, force=force)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/jobs/poll-replies")
async def poll_replies(db: Session = Depends(get_db)):
    try:
        return await outreach_service.poll_replies(db)
    except Exception as e:
        logger.error(f"Gmail reply polling failed: {e}")
        raise HTTPException(status_code=502, detail="Gmail reply polling failed. Check the Gmail connection and backend logs.") from e


@router.post("/demo/simulate-reply")
async def simulate_reply(payload: SimulateReplyRequest, db: Session = Depends(get_db)):
    try:
        return await outreach_service.simulate_reply(db, payload.email_id, payload.decline)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/demo/incoming-reply")
async def demo_incoming_reply(payload: DemoIncomingReplyRequest, db: Session = Depends(get_db)):
    try:
        return await outreach_service.record_simulated_reply(
            db,
            payload.email_id,
            payload.body,
            payload.subject,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/opt-out/{token}", response_class=HTMLResponse)
def public_opt_out(token: str, db: Session = Depends(get_db)):
    try:
        outreach_service.opt_out_by_token(db, token)
    except ValueError:
        return HTMLResponse("<h2>Invalid opt-out link</h2>", status_code=404)
    return HTMLResponse(
        "<h2>You have been unsubscribed.</h2><p>No further follow-up emails will be sent.</p>"
    )
