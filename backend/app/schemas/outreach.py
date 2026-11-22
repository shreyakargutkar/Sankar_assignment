from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class CampaignCreate(BaseModel):
    name: Optional[str] = None
    brand_name: str = Field(..., min_length=1)
    campaign_description: str = Field(..., min_length=5)
    collaboration_offer: Optional[str] = "Paid/gifted collaboration with creative freedom and a clear brief."
    call_to_action: Optional[str] = "Reply to this email if you would like to collaborate, and we will share the full brief."
    sender_name: Optional[str] = None
    relevant_keywords: Optional[str] = ""
    influencer_ids: List[int] = Field(..., min_length=1)


class EmailUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None


class OutcomeUpdate(BaseModel):
    outcome: str = Field(..., description="replied | interested | not_interested | opt_out")


class ReplyDraftUpdate(BaseModel):
    subject: Optional[str] = Field(None, max_length=998)
    body: Optional[str] = Field(None, max_length=20000)


class OutreachEmailResponse(BaseModel):
    id: int
    campaign_id: int
    influencer_id: int
    influencer_name: Optional[str] = None
    instagram_username: Optional[str] = None
    sequence_number: int
    email_type: str
    to_email: str
    subject: str
    body: str
    status: str
    human_approved: bool
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    follow_up_due_at: Optional[datetime] = None
    send_mode: Optional[str] = None
    gmail_message_id: Optional[str] = None
    error_message: Optional[str] = None
    stop_followups: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CampaignResponse(BaseModel):
    id: int
    name: str
    brand_name: str
    campaign_description: str
    collaboration_offer: Optional[str] = None
    call_to_action: Optional[str] = None
    sender_name: str
    relevant_keywords: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    email_counts: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class OutreachEventResponse(BaseModel):
    id: int
    email_id: Optional[int] = None
    campaign_id: Optional[int] = None
    influencer_id: Optional[int] = None
    event_type: str
    detail: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
