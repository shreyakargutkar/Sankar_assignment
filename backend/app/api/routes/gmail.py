from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import settings
from app.models.outreach import GmailOAuthState, GmailOAuthToken
from app.services.gmail_service import gmail_service

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.get("/status")
def gmail_status(db: Session = Depends(get_db)):
    return gmail_service.connection_status(db)


@router.get("/auth-url")
def gmail_auth_url(db: Session = Depends(get_db)):
    if not gmail_service.is_oauth_configured():
        raise HTTPException(
            status_code=400,
            detail=(
                "Set GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, and "
                "GMAIL_TOKEN_ENCRYPTION_KEY to connect Gmail, or use simulated sending."
            ),
        )
    try:
        return {"auth_url": gmail_service.build_auth_url(db)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
def gmail_callback(code: str = "", error: str = "", state: str = "", db: Session = Depends(get_db)):
    frontend = settings.FRONTEND_URL.rstrip("/")
    if error:
        if state:
            db.query(GmailOAuthState).filter(GmailOAuthState.state == state).delete()
            db.commit()
        return RedirectResponse(f"{frontend}/?{urlencode({'gmail': 'error', 'reason': 'authorization_denied'})}")
    if not code:
        return RedirectResponse(f"{frontend}/?{urlencode({'gmail': 'error', 'reason': 'missing_code'})}")
    try:
        gmail_service.exchange_code(db, code, state)
        return RedirectResponse(f"{frontend}/?gmail=connected")
    except Exception as e:
        db.rollback()
        from app.core.logging import logger

        logger.error(f"Gmail OAuth callback failed: {e}")
        return RedirectResponse(f"{frontend}/?gmail=error&reason=token_exchange_failed")


@router.post("/disconnect")
def gmail_disconnect(db: Session = Depends(get_db)):
    db.query(GmailOAuthToken).update({GmailOAuthToken.is_active: False})
    db.commit()
    return {"disconnected": True, "send_mode": "simulated"}
