from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    UniqueConstraint,
    ForeignKey,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class OutreachCampaign(Base):
    __tablename__ = "outreach_campaigns"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    brand_name = Column(String(255), nullable=False)
    campaign_description = Column(Text, nullable=False)
    collaboration_offer = Column(Text, nullable=True)
    call_to_action = Column(Text, nullable=True)
    sender_name = Column(String(255), nullable=False, default="Partnerships Team")
    relevant_keywords = Column(String(512), nullable=True)
    status = Column(String(50), nullable=False, default="draft", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    emails = relationship("OutreachEmail", back_populates="campaign", cascade="all, delete-orphan")


class OutreachEmail(Base):
    __tablename__ = "outreach_emails"
    __table_args__ = (
        UniqueConstraint("campaign_id", "influencer_id", "sequence_number", name="uq_campaign_influencer_sequence"),
        Index("ix_outreach_due", "follow_up_due_at"),
        Index("ix_outreach_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("outreach_campaigns.id"), nullable=False, index=True)
    influencer_id = Column(Integer, ForeignKey("influencers.id"), nullable=False, index=True)

    sequence_number = Column(Integer, nullable=False, default=0)  # 0 initial, 1 first follow-up, 2 second
    email_type = Column(String(40), nullable=False, default="initial")  # initial | follow_up_1 | follow_up_2

    to_email = Column(String(255), nullable=False)
    subject = Column(Text, nullable=False)
    body = Column(Text, nullable=False)

    status = Column(String(50), nullable=False, default="pending_approval")
    # pending_approval | approved | rejected | sent | failed | cancelled

    human_approved = Column(Boolean, default=False, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    follow_up_due_at = Column(DateTime(timezone=True), nullable=True)

    send_mode = Column(String(30), nullable=True)  # live_gmail | simulated
    gmail_message_id = Column(String(255), nullable=True)
    gmail_thread_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)

    opt_out_token = Column(String(64), unique=True, index=True, nullable=True)
    stop_followups = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    campaign = relationship("OutreachCampaign", back_populates="emails")
    influencer = relationship("Influencer")
    events = relationship("OutreachEvent", back_populates="email", cascade="all, delete-orphan")


class OutreachEvent(Base):
    __tablename__ = "outreach_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("outreach_emails.id"), nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("outreach_campaigns.id"), nullable=True, index=True)
    influencer_id = Column(Integer, ForeignKey("influencers.id"), nullable=True, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    email = relationship("OutreachEmail", back_populates="events")


class InfluencerReply(Base):
    __tablename__ = "influencer_replies"
    __table_args__ = (
        Index("ix_influencer_replies_received_at", "received_at"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    gmail_message_id = Column(String(255), unique=True, nullable=False, index=True)
    gmail_thread_id = Column(String(255), nullable=True, index=True)
    gmail_rfc822_message_id = Column(String(512), nullable=True)
    influencer_id = Column(Integer, ForeignKey("influencers.id"), nullable=False, index=True)
    campaign_id = Column(Integer, ForeignKey("outreach_campaigns.id"), nullable=True, index=True)
    original_email_id = Column(Integer, ForeignKey("outreach_emails.id"), nullable=True, index=True)

    from_email = Column(String(255), nullable=False)
    subject = Column(Text, nullable=False, default="")
    body = Column(Text, nullable=False)
    classification = Column(String(40), nullable=False, default="General Query")
    confidence = Column(Integer, nullable=False, default=0)
    classification_reason = Column(Text, nullable=True)

    draft_subject = Column(Text, nullable=True)
    draft_body = Column(Text, nullable=True)
    status = Column(String(40), nullable=False, default="pending_approval", index=True)
    # pending_approval | approved | rejected | sent | no_reply_required
    human_approved = Column(Boolean, default=False, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    reply_gmail_message_id = Column(String(255), nullable=True)
    send_mode = Column(String(30), nullable=True)
    error_message = Column(Text, nullable=True)

    received_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    influencer = relationship("Influencer")
    campaign = relationship("OutreachCampaign")
    original_email = relationship("OutreachEmail")


class GmailOAuthToken(Base):
    __tablename__ = "gmail_oauth_tokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email_address = Column(String(255), nullable=True)
    token_json = Column(Text, nullable=False)
    scopes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GmailOAuthState(Base):
    __tablename__ = "gmail_oauth_states"

    state = Column(String(128), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OutreachRecipientClaim(Base):
    __tablename__ = "outreach_recipient_claims"

    email_address = Column(String(255), primary_key=True)
    email_id = Column(Integer, ForeignKey("outreach_emails.id"), unique=True, nullable=False)
    status = Column(String(20), nullable=False, default="sending")
    claimed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DailySendQuota(Base):
    __tablename__ = "daily_send_quotas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    day = Column(String(10), unique=True, nullable=False, index=True)  # YYYY-MM-DD
    live_sent = Column(Integer, default=0, nullable=False)
    simulated_sent = Column(Integer, default=0, nullable=False)
    reserved = Column(Integer, default=0, nullable=False)
    last_send_at = Column(DateTime(timezone=True), nullable=True)
