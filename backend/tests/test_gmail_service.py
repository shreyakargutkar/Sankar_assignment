import json
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet

from app.core.config import settings
from app.models.outreach import GmailOAuthState
from app.services.gmail_service import GmailService


def test_oauth_tokens_are_encrypted_at_rest(monkeypatch):
    monkeypatch.setattr(
        settings,
        "GMAIL_TOKEN_ENCRYPTION_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    service = GmailService()
    token = json.dumps({"refresh_token": "private-refresh-token"})

    encrypted = service._encrypt_token(token)

    assert encrypted.startswith("enc:v1:")
    assert "private-refresh-token" not in encrypted
    assert service._decrypt_token(encrypted) == token


def test_gmail_oauth_rejects_unissued_state(db_session):
    with pytest.raises(ValueError, match="Invalid or expired OAuth state"):
        GmailService().exchange_code(db_session, "not-a-real-code", "unissued-state")


def test_gmail_auth_url_uses_persisted_random_state(db_session, monkeypatch):
    monkeypatch.setattr(settings, "GMAIL_CLIENT_ID", "test-client.apps.googleusercontent.com")
    monkeypatch.setattr(settings, "GMAIL_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(settings, "GMAIL_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.setattr(
        settings,
        "GMAIL_REDIRECT_URI",
        "http://127.0.0.1:8000/api/v1/gmail/callback",
    )

    auth_url = GmailService().build_auth_url(db_session)
    state = parse_qs(urlparse(auth_url).query)["state"][0]

    assert urlparse(auth_url).hostname == "accounts.google.com"
    assert db_session.query(GmailOAuthState).filter_by(state=state).first() is not None
