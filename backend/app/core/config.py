import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Instagram Influencer Outreach Automation"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./influencers.db"
    
    # Claude AI (Anthropic)
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # Google Sheets API
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = "google_credentials.json"
    GOOGLE_SPREADSHEET_ID: str = ""
    
    # Gmail OAuth 2.0
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/gmail/callback"
    GMAIL_TOKEN_ENCRYPTION_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:5173"

    # Outreach / anti-spam
    DAILY_SEND_LIMIT: int = 40
    MIN_SECONDS_BETWEEN_SENDS: float = 0.25
    FOLLOWUP_1_MIN_DAYS: int = 3
    FOLLOWUP_1_MAX_DAYS: int = 5
    FOLLOWUP_2_MIN_DAYS: int = 5
    FOLLOWUP_2_MAX_DAYS: int = 7
    SENDER_NAME: str = "Partnerships Team"
    PUBLIC_BASE_URL: str = "http://127.0.0.1:8000"

    # Environment & Demo Mode
    DEMO_MODE: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

settings = Settings()
