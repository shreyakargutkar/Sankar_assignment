from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.influencer import LeadStatus

class InfluencerBase(BaseModel):
    name: str = Field(..., min_length=1, description="Influencer full or display name")
    instagram_username: str = Field(..., min_length=1, description="Instagram username e.g. @tech_sarah or tech_sarah")
    profile_url: Optional[str] = Field(None, description="Instagram profile URL")
    niche: str = Field(..., min_length=1, description="Influencer primary niche")
    followers_count: int = Field(..., ge=0, description="Follower count")
    email: Optional[str] = Field(None, description="Public business email")
    location: str = Field("Global", description="Target location or creator location")

    @field_validator("instagram_username")
    def clean_username(cls, v: str) -> str:
        cleaned = v.strip().lstrip("@").strip()
        if not cleaned:
            raise ValueError("Instagram username cannot be empty")
        return cleaned

    @field_validator("profile_url", mode="before")
    def generate_profile_url(cls, v, values):
        if v and str(v).strip():
            url = str(v).strip()
            if not url.startswith("http"):
                url = f"https://{url}"
            return url.rstrip("/")
        # Auto-generate if not provided
        username = values.data.get("instagram_username", "") if hasattr(values, "data") else ""
        if username:
            clean_u = str(username).strip().lstrip("@")
            return f"https://instagram.com/{clean_u}"
        return v

class InfluencerCreate(InfluencerBase):
    status: Optional[str] = LeadStatus.NEW_LEAD.value

class InfluencerUpdate(BaseModel):
    name: Optional[str] = None
    niche: Optional[str] = None
    followers_count: Optional[int] = None
    email: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    suitability_score: Optional[int] = None
    category: Optional[str] = None
    profile_summary: Optional[str] = None
    match_reason: Optional[str] = None
    campaign_name: Optional[str] = None

class InfluencerStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    def validate_status(cls, v: str) -> str:
        allowed = [s.value for s in LeadStatus]
        if v not in allowed:
            raise ValueError(f"Status must be one of: {allowed}")
        return v

class InfluencerResponse(InfluencerBase):
    id: int
    status: str
    suitability_score: Optional[int] = None
    category: Optional[str] = None
    profile_summary: Optional[str] = None
    match_reason: Optional[str] = None
    campaign_name: Optional[str] = None
    synced_to_sheets: bool
    last_synced_at: Optional[datetime] = None
    opted_out: Optional[bool] = False
    last_contacted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Campaign Research Criteria
class CampaignResearchRequest(BaseModel):
    brand_name: str = Field(..., min_length=1, description="Brand or company name")
    campaign_description: str = Field(..., min_length=5, description="Brief description of the marketing campaign")
    influencer_niche: str = Field(..., min_length=1, description="Niche category")
    target_location: str = Field("Global", description="Target region or country")
    min_followers: int = Field(5000, ge=0, description="Minimum follower threshold")
    max_followers: int = Field(1000000, ge=1000, description="Maximum follower threshold")
    relevant_keywords: str = Field(..., description="Keywords comma separated")
    auto_analyze_with_ai: bool = Field(True, description="Immediately run Claude AI analysis on discovered creators")
    limit: int = Field(10, ge=1, le=50, description="Number of influencers to discover")

class AIAnalysisRequest(BaseModel):
    influencer_ids: List[int]
    brand_name: str
    campaign_description: str
    relevant_keywords: Optional[str] = None

class AIAnalysisResult(BaseModel):
    influencer_id: int
    suitability_score: int
    category: str
    profile_summary: str
    match_reason: str

class GoogleSheetsSyncRequest(BaseModel):
    spreadsheet_id: Optional[str] = None
    influencer_ids: Optional[List[int]] = None # If None, sync all unsynced or all
