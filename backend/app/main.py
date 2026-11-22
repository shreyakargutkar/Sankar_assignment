import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.core.database import engine, Base, SessionLocal, migrate_schema
from app.api.routes import influencers, discovery, sheets, outreach, gmail
from app.services.influencer_service import influencer_service
from app.services.discovery_service import PUBLIC_SAMPLE_CREATORS
from app.services.followup_scheduler import start_scheduler, stop_scheduler
from app.schemas.influencer import InfluencerCreate
from app.models.influencer import Influencer
from app.models.outreach import (  # noqa: F401 — register tables
    OutreachCampaign,
    OutreachEmail,
    OutreachEvent,
    InfluencerReply,
    GmailOAuthToken,
    GmailOAuthState,
    OutreachRecipientClaim,
    DailySendQuota,
)

# Create DB Tables
Base.metadata.create_all(bind=engine)
migrate_schema()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    db = SessionLocal()
    try:
        count = db.query(Influencer).count()
        if count == 0:
            logger.info("Database is empty. Seeding initial public creator samples...")
            initial_creators = []
            for item in PUBLIC_SAMPLE_CREATORS[:8]:
                u = item["username"].lstrip("@")
                initial_creators.append(InfluencerCreate(
                    name=item["name"],
                    instagram_username=u,
                    profile_url=f"https://instagram.com/{u}",
                    niche=item["niche"],
                    followers_count=item["followers"],
                    email=item.get("email"),
                    location=item["location"],
                    status="Email Available" if item.get("email") else "New Lead"
                ))
            influencer_service.batch_create_influencers(db, initial_creators)
            logger.info(f"Seeded {len(initial_creators)} initial influencers.")
    except Exception as e:
        logger.error(f"Error during startup seeding: {e}")
    finally:
        db.close()

    start_scheduler()
    yield
    stop_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for influencer research, approval-gated Gmail outreach, reply management, and campaign analytics.",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled exception on {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please check server logs."}
    )

# Include Routers
app.include_router(influencers.router, prefix=settings.API_V1_STR)
app.include_router(discovery.router, prefix=settings.API_V1_STR)
app.include_router(sheets.router, prefix=settings.API_V1_STR)
app.include_router(outreach.router, prefix=settings.API_V1_STR)
app.include_router(gmail.router, prefix=settings.API_V1_STR)

@app.get("/health")
@app.get(f"{settings.API_V1_STR}/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "3.0.0",
        "demo_mode": settings.DEMO_MODE,
        "phase": 3
    }
