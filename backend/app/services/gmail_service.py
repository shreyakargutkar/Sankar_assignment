import base64
import re
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.utils import parseaddr
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.core.config import settings
from app.core.logging import logger
from app.models.outreach import GmailOAuthState, GmailOAuthToken

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class GmailService:
    def is_oauth_configured(self) -> bool:
        return bool(
            settings.GMAIL_CLIENT_ID
            and settings.GMAIL_CLIENT_SECRET
            and settings.GMAIL_TOKEN_ENCRYPTION_KEY
        )

    def _fernet(self):
        from cryptography.fernet import Fernet

        key = settings.GMAIL_TOKEN_ENCRYPTION_KEY
        if not key:
            raise RuntimeError(
                "GMAIL_TOKEN_ENCRYPTION_KEY is required to store Gmail OAuth tokens securely."
            )
        try:
            return Fernet(key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as e:
            raise RuntimeError(
                "GMAIL_TOKEN_ENCRYPTION_KEY must be a valid Fernet key."
            ) from e

    def _encrypt_token(self, token_json: str) -> str:
        encrypted = self._fernet().encrypt(token_json.encode("utf-8")).decode("ascii")
        return f"enc:v1:{encrypted}"

    def _decrypt_token(self, token_json: str) -> str:
        if not token_json.startswith("enc:v1:"):
            # Migrate tokens persisted by older versions on their next read.
            return token_json
        try:
            return self._fernet().decrypt(token_json[7:].encode("ascii")).decode("utf-8")
        except Exception as e:
            raise RuntimeError(
                "Stored Gmail OAuth token could not be decrypted. Check GMAIL_TOKEN_ENCRYPTION_KEY."
            ) from e

    def _client_config(self) -> dict:
        return {
            "web": {
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GMAIL_REDIRECT_URI],
            }
        }

    def _configure_redirect_transport(self) -> None:
        redirect = urlparse(settings.GMAIL_REDIRECT_URI)
        if redirect.scheme == "https":
            return
        if redirect.scheme == "http" and redirect.hostname in {"localhost", "127.0.0.1", "::1"}:
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
            return
        raise RuntimeError("GMAIL_REDIRECT_URI must use HTTPS except for a localhost development callback.")

    def build_auth_url(self, db) -> str:
        if not self.is_oauth_configured():
            raise RuntimeError(
                "Gmail OAuth requires GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, and "
                "GMAIL_TOKEN_ENCRYPTION_KEY."
            )
        self._fernet()
        self._configure_redirect_transport()
        from google_auth_oauthlib.flow import Flow

        db.query(GmailOAuthState).filter(
            GmailOAuthState.created_at < _utcnow_naive() - timedelta(minutes=10)
        ).delete(synchronize_session=False)
        state = secrets.token_urlsafe(32)
        db.add(GmailOAuthState(state=state))
        db.commit()
        flow = Flow.from_client_config(
            self._client_config(),
            scopes=GMAIL_SCOPES,
            redirect_uri=settings.GMAIL_REDIRECT_URI,
        )
        url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )
        return url

    def exchange_code(self, db, code: str, state: str) -> GmailOAuthToken:
        if not state:
            raise ValueError("Missing OAuth state. Start the Gmail connection flow again.")
        stored_state = db.query(GmailOAuthState).filter(GmailOAuthState.state == state).first()
        if not stored_state:
            raise ValueError("Invalid or expired OAuth state. Start the Gmail connection flow again.")
        if stored_state.created_at < _utcnow_naive() - timedelta(minutes=10):
            db.delete(stored_state)
            db.commit()
            raise ValueError("OAuth state expired. Start the Gmail connection flow again.")
        db.delete(stored_state)
        db.commit()

        self._configure_redirect_transport()
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build

        flow = Flow.from_client_config(
            self._client_config(),
            scopes=GMAIL_SCOPES,
            redirect_uri=settings.GMAIL_REDIRECT_URI,
        )
        flow.state = state
        flow.fetch_token(code=code)
        creds = flow.credentials
        email_address = None
        try:
            gmail = build("gmail", "v1", credentials=creds)
            profile = gmail.users().getProfile(userId="me").execute()
            email_address = profile.get("emailAddress")
        except Exception as e:
            logger.warning(f"Could not fetch Gmail profile email: {e}")

        db.query(GmailOAuthToken).update({GmailOAuthToken.is_active: False})
        token = GmailOAuthToken(
            email_address=email_address,
            token_json=self._encrypt_token(creds.to_json()),
            scopes=" ".join(creds.scopes or GMAIL_SCOPES),
            is_active=True,
        )
        db.add(token)
        db.commit()
        db.refresh(token)
        return token

    def get_active_token(self, db) -> Optional[GmailOAuthToken]:
        return db.query(GmailOAuthToken).filter(GmailOAuthToken.is_active.is_(True)).first()

    def _credentials_from_token(self, token: GmailOAuthToken):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        info = json.loads(self._decrypt_token(token.token_json))
        creds = Credentials.from_authorized_user_info(info, GMAIL_SCOPES)
        if not token.token_json.startswith("enc:v1:"):
            token.token_json = self._encrypt_token(token.token_json)
        if creds.expired:
            if not creds.refresh_token:
                raise RuntimeError("Gmail access token expired without a refresh token. Reconnect Gmail.")
            creds.refresh(Request())
            token.token_json = self._encrypt_token(creds.to_json())
            token.last_error = None
        return creds

    def refresh_and_persist(self, db, token: GmailOAuthToken):
        creds = self._credentials_from_token(token)
        token.token_json = creds.to_json()
        db.commit()
        return creds

    def connection_status(self, db) -> Dict[str, Any]:
        oauth_ready = self.is_oauth_configured()
        token = self.get_active_token(db)
        live = False
        email_address = None
        needs_reauth = False
        last_error = None
        if token:
            email_address = token.email_address
            last_error = token.last_error
            try:
                self.refresh_and_persist(db, token)
                live = True
            except Exception as e:
                needs_reauth = True
                last_error = str(e)
                token.last_error = last_error
                db.commit()
        mode = "live_gmail" if live else ("reauth_required" if needs_reauth else "simulated")
        return {
            "oauth_client_configured": oauth_ready,
            "token_encryption_configured": bool(settings.GMAIL_TOKEN_ENCRYPTION_KEY),
            "connected": live,
            "email_address": email_address,
            "needs_reauth": needs_reauth,
            "last_error": last_error,
            "send_mode": mode,
            "status_label": "Gmail Connected (Live)" if live else "Simulated Gmail (no live send)",
        }

    def send_email(
        self,
        db,
        to_email: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Returns (send_mode, metadata).
        send_mode is live_gmail or simulated.
        """
        parsed_to = parseaddr(to_email)[1]
        if not parsed_to or parsed_to != to_email or any(c in to_email + subject for c in "\r\n"):
            raise ValueError("Recipient email and subject must be valid single-line values.")
        token = self.get_active_token(db)
        if token:
            try:
                creds = self.refresh_and_persist(db, token)
                from googleapiclient.discovery import build

                message = MIMEText(body)
                message["to"] = to_email
                message["subject"] = subject
                if token.email_address:
                    message["from"] = token.email_address
                if reply_to_message_id:
                    message["In-Reply-To"] = reply_to_message_id
                    message["References"] = reply_to_message_id
                raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
                service = build("gmail", "v1", credentials=creds)
                request_body = {"raw": raw}
                if thread_id:
                    request_body["threadId"] = thread_id
                sent = service.users().messages().send(userId="me", body=request_body).execute()
                return "live_gmail", {
                    "gmail_message_id": sent.get("id"),
                    "gmail_thread_id": sent.get("threadId"),
                    "simulated": False,
                }
            except Exception as e:
                logger.error(f"Gmail send failed: {e}")
                token.last_error = str(e)
                db.commit()
                # Do not silently simulate a live-connected mailbox failure
                raise RuntimeError(f"Gmail API error (token may be expired): {e}") from e

        archive = self._archive_simulated(to_email, subject, body)
        return "simulated", {
            "gmail_message_id": archive["id"],
            "gmail_thread_id": None,
            "simulated": True,
            "archive_path": archive["path"],
        }

    def _archive_simulated(self, to_email: str, subject: str, body: str) -> Dict[str, str]:
        path = self._simulated_outbox_file()
        data_dir = os.path.dirname(path)
        os.makedirs(data_dir, exist_ok=True)
        record_id = f"sim_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        record = {
            "id": record_id,
            "to": to_email,
            "subject": subject,
            "body": body,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "mode": "simulated",
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return {"id": record_id, "path": path}

    @staticmethod
    def _simulated_outbox_file() -> str:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        return os.path.join(data_dir, "simulated_gmail_outbox.jsonl")

    def list_recent_inbox(self, db, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        token = self.get_active_token(db)
        if not token:
            return []
        try:
            creds = self.refresh_and_persist(db, token)
            from googleapiclient.discovery import build

            service = build("gmail", "v1", credentials=creds)
            listed = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
            messages = []
            for item in listed.get("messages", []):
                msg = service.users().messages().get(
                    userId="me",
                    id=item["id"],
                    format="full",
                ).execute()
                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                messages.append({
                    "id": msg.get("id"),
                    "threadId": msg.get("threadId"),
                    "from": headers.get("From"),
                    "subject": headers.get("Subject"),
                    "rfc822_message_id": headers.get("Message-ID"),
                    "in_reply_to": headers.get("In-Reply-To"),
                    "snippet": msg.get("snippet"),
                    "body": self._extract_message_body(msg.get("payload", {})),
                    "internal_date": msg.get("internalDate"),
                    "label_ids": msg.get("labelIds", []),
                })
            return messages
        except Exception as e:
            logger.error(f"Gmail inbox poll failed: {e}")
            token.last_error = str(e)
            db.commit()
            raise RuntimeError(f"Gmail inbox polling failed: {e}") from e

    @classmethod
    def _extract_message_body(cls, payload: Dict[str, Any]) -> str:
        plain_parts = []
        html_parts = []

        def visit(part: Dict[str, Any]) -> None:
            body_data = part.get("body", {}).get("data")
            mime_type = part.get("mimeType", "")
            if body_data and mime_type in {"text/plain", "text/html"}:
                try:
                    decoded = base64.urlsafe_b64decode(body_data + "===")
                    text = decoded.decode("utf-8", errors="replace")
                    (plain_parts if mime_type == "text/plain" else html_parts).append(text)
                except (ValueError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not decode Gmail MIME body part: {e}")
            for child in part.get("parts", []):
                visit(child)

        visit(payload)
        if plain_parts:
            return "\n".join(plain_parts).strip()
        if html_parts:
            html = "\n".join(html_parts)
            html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", html)
            html = re.sub(r"(?s)<[^>]+>", " ", html)
            return re.sub(r"\s+", " ", html).strip()
        return ""


gmail_service = GmailService()
