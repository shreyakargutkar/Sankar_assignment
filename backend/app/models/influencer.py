from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class LeadStatus(str, enum.Enum):
    NEW_LEAD = "New Lead"
    EMAIL_AVAILABLE = "Email Available"
    EMAIL_SENT = "Email Sent"
    FOLLOW_UP_DUE = "Follow-up Due"
    REPLIED = "Replied"
    INTERESTED = "Interested"
    NOT_INTERESTED = "Not Interested"
    COLLABORATION_CONFIRMED = "Collaboration Confirmed"
    PRICING_ENQUIRY = "Pricing Enquiry"
    COLLABORATION_REQUEST = "Collaboration Request"
    GENERAL_QUERY = "General Query"

class Influencer(Base):
    __tablename__ = "influencers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    instagram_username = Column(String(255), unique=True, index=True, nullable=False)
    profile_url = Column(String(512), unique=True, index=True, nullable=False)
    niche = Column(String(100), nullable=False, index=True)
    followers_count = Column(Integer, nullable=False, default=0, index=True)
    email = Column(String(255), nullable=True, index=True)
    location = Column(String(255), nullable=False, default="Global", index=True)
    
    # Lead Status
    status = Column(String(50), nullable=False, default=LeadStatus.NEW_LEAD.value, index=True)
    
    # Claude AI Analysis Fields
    suitability_score = Column(Integer, nullable=True) # 0-100
    category = Column(String(100), nullable=True) # e.g. "Micro-Influencer (Tech/AI)"
    profile_summary = Column(Text, nullable=True)
    match_reason = Column(Text, nullable=True)
    campaign_name = Column(String(255), nullable=True)
    
    # Google Sheets Sync Status
    synced_to_sheets = Column(Boolean, default=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    # Outreach controls
    opted_out = Column(Boolean, default=False, nullable=False)
    last_contacted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
