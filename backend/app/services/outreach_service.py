import asyncio
import secrets
from collections import Counter
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
from random import randint
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.logging import logger
from app.models.influencer import Influencer, LeadStatus
from app.models.outreach import (
    DailySendQuota,
    OutreachCampaign,
    OutreachEmail,
    OutreachEvent,
    OutreachRecipientClaim,
    InfluencerReply,
)
from app.services.email_generator import email_generator
from app.services.gmail_service import gmail_service
from app.services.google_sheets import google_sheets_service

STOP_STATUSES = {
    LeadStatus.REPLIED.value,
    LeadStatus.INTERESTED.value,
    LeadStatus.NOT_INTERESTED.value,
    LeadStatus.COLLABORATION_CONFIRMED.value,
    LeadStatus.PRICING_ENQUIRY.value,
    LeadStatus.COLLABORATION_REQUEST.value,
    LeadStatus.GENERAL_QUERY.value,
}

TERMINAL_EMAIL_STATUSES = {"sent", "rejected", "cancelled"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


class OutreachService:
    def add_event(
        self,
        db: Session,
        event_type: str,
        detail: str = "",
        email_id: Optional[int] = None,
        campaign_id: Optional[int] = None,
        influencer_id: Optional[int] = None,
    ):
        db.add(
            OutreachEvent(
                event_type=event_type,
                detail=detail,
                email_id=email_id,
                campaign_id=campaign_id,
                influencer_id=influencer_id,
            )
        )

    def _opt_out_url(self, token: str) -> str:
        return f"{settings.PUBLIC_BASE_URL}{settings.API_V1_STR}/outreach/opt-out/{token}"

    def _serialize_email(self, email: OutreachEmail) -> Dict[str, Any]:
        inf = email.influencer
        return {
            "id": email.id,
            "campaign_id": email.campaign_id,
            "influencer_id": email.influencer_id,
            "influencer_name": inf.name if inf else None,
            "instagram_username": inf.instagram_username if inf else None,
            "sequence_number": email.sequence_number,
            "email_type": email.email_type,
            "to_email": email.to_email,
            "subject": email.subject,
            "body": email.body,
            "status": email.status,
            "human_approved": email.human_approved,
            "approved_at": email.approved_at,
            "rejected_at": email.rejected_at,
            "sent_at": email.sent_at,
            "follow_up_due_at": email.follow_up_due_at,
            "send_mode": email.send_mode,
            "gmail_message_id": email.gmail_message_id,
            "error_message": email.error_message,
            "stop_followups": email.stop_followups,
            "created_at": email.created_at,
            "updated_at": email.updated_at,
        }

    def _serialize_reply(self, reply: InfluencerReply) -> Dict[str, Any]:
        influencer = reply.influencer
        campaign = reply.campaign
        return {
            "id": reply.id,
            "gmail_message_id": reply.gmail_message_id,
            "gmail_thread_id": reply.gmail_thread_id,
            "influencer_id": reply.influencer_id,
            "influencer_name": influencer.name if influencer else None,
            "instagram_username": influencer.instagram_username if influencer else None,
            "from_email": reply.from_email,
            "campaign_id": reply.campaign_id,
            "campaign_name": campaign.name if campaign else None,
            "original_email_id": reply.original_email_id,
            "subject": reply.subject,
            "body": reply.body,
            "classification": reply.classification,
            "confidence": reply.confidence,
            "classification_reason": reply.classification_reason,
            "draft_subject": reply.draft_subject,
            "draft_body": reply.draft_body,
            "status": reply.status,
            "human_approved": reply.human_approved,
            "approved_at": reply.approved_at,
            "rejected_at": reply.rejected_at,
            "sent_at": reply.sent_at,
            "reply_gmail_message_id": reply.reply_gmail_message_id,
            "send_mode": reply.send_mode,
            "error_message": reply.error_message,
            "received_at": reply.received_at,
            "created_at": reply.created_at,
        }

    def campaign_counts(self, db: Session, campaign_id: int) -> dict:
        emails = db.query(OutreachEmail).filter(OutreachEmail.campaign_id == campaign_id).all()
        return dict(Counter(e.status for e in emails))

    def list_campaigns(self, db: Session) -> List[Dict[str, Any]]:
        campaigns = db.query(OutreachCampaign).order_by(OutreachCampaign.created_at.desc()).all()
        out = []
        for c in campaigns:
            out.append({
                "id": c.id,
                "name": c.name,
                "brand_name": c.brand_name,
                "campaign_description": c.campaign_description,
                "collaboration_offer": c.collaboration_offer,
                "call_to_action": c.call_to_action,
                "sender_name": c.sender_name,
                "relevant_keywords": c.relevant_keywords,
                "status": c.status,
                "created_at": c.created_at,
                "email_counts": self.campaign_counts(db, c.id),
            })
        return out

    async def create_campaign(self, db: Session, payload) -> Dict[str, Any]:
        name = payload.name or f"{payload.brand_name} outreach"
        campaign = OutreachCampaign(
            name=name,
            brand_name=payload.brand_name,
            campaign_description=payload.campaign_description,
            collaboration_offer=payload.collaboration_offer,
            call_to_action=payload.call_to_action,
            sender_name=payload.sender_name or settings.SENDER_NAME,
            relevant_keywords=payload.relevant_keywords or "",
            status="drafting",
        )
        db.add(campaign)
        db.flush()

        sender_email = ""
        token = gmail_service.get_active_token(db)
        if token and token.email_address:
            sender_email = token.email_address

        created = []
        skipped = []
        influencers = db.query(Influencer).filter(Influencer.id.in_(payload.influencer_ids)).all()
        found_ids = {i.id for i in influencers}
        for requested in payload.influencer_ids:
            if requested not in found_ids:
                skipped.append({"influencer_id": requested, "reason": "not_found"})

        for inf in influencers:
            reason = self._skip_reason(db, campaign.id, inf, sequence_number=0)
            if reason:
                skipped.append({
                    "influencer_id": inf.id,
                    "username": inf.instagram_username,
                    "reason": reason,
                })
                continue
            opt_token = secrets.token_urlsafe(16)
            try:
                draft = await email_generator.generate_email(
                    influencer=inf,
                    campaign=campaign,
                    sequence_number=0,
                    opt_out_url=self._opt_out_url(opt_token),
                    sender_email=sender_email,
                )
            except Exception:
                db.rollback()
                raise
            email = OutreachEmail(
                campaign_id=campaign.id,
                influencer_id=inf.id,
                sequence_number=0,
                email_type="initial",
                to_email=inf.email,
                subject=draft["subject"],
                body=draft["body"],
                status="pending_approval",
                human_approved=False,
                opt_out_token=opt_token,
            )
            db.add(email)
            db.flush()
            self.add_event(
                db,
                "draft_generated",
                f"Initial AI draft for @{inf.instagram_username}",
                email_id=email.id,
                campaign_id=campaign.id,
                influencer_id=inf.id,
            )
            created.append(email)

        campaign.status = "pending_approval" if created else "empty"
        db.commit()
        for e in created:
            db.refresh(e)

        return {
            "campaign": {
                "id": campaign.id,
                "name": campaign.name,
                "brand_name": campaign.brand_name,
                "status": campaign.status,
                "email_counts": self.campaign_counts(db, campaign.id),
            },
            "created_count": len(created),
            "skipped": skipped,
            "emails": [self._serialize_email(e) for e in created],
            "generation_mode": "live_claude" if (email_generator.is_api_configured() and not settings.DEMO_MODE) else "simulated_claude",
        }

    def _skip_reason(self, db: Session, campaign_id: int, inf: Influencer, sequence_number: int) -> Optional[str]:
        if not inf.email:
            return "no_email"
        if inf.opted_out:
            return "opted_out"
        if inf.status == LeadStatus.NOT_INTERESTED.value:
            return "not_interested"
        existing = (
            db.query(OutreachEmail)
            .filter(
                OutreachEmail.campaign_id == campaign_id,
                OutreachEmail.influencer_id == inf.id,
                OutreachEmail.sequence_number == sequence_number,
            )
            .first()
        )
        if existing:
            return "duplicate_sequence"
        duplicate_initial = (
            db.query(OutreachEmail)
            .filter(
                OutreachEmail.to_email.ilike(inf.email),
                OutreachEmail.sequence_number == 0,
                OutreachEmail.status.in_(("pending_approval", "approved", "sending", "sent")),
            )
            .first()
        )
        if duplicate_initial and sequence_number == 0:
            return "already_contacted_this_address"
        return None

    def list_emails(
        self,
        db: Session,
        campaign_id: Optional[int] = None,
        influencer_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        q = db.query(OutreachEmail).options(joinedload(OutreachEmail.influencer)).order_by(
            OutreachEmail.campaign_id.desc(),
            OutreachEmail.sequence_number.asc(),
            OutreachEmail.id.asc(),
        )
        if campaign_id:
            q = q.filter(OutreachEmail.campaign_id == campaign_id)
        if influencer_id:
            q = q.filter(OutreachEmail.influencer_id == influencer_id)
        if status:
            q = q.filter(OutreachEmail.status == status)
        return [self._serialize_email(e) for e in q.all()]

    def get_email(self, db: Session, email_id: int) -> Optional[OutreachEmail]:
        return (
            db.query(OutreachEmail)
            .options(joinedload(OutreachEmail.influencer), joinedload(OutreachEmail.campaign))
            .filter(OutreachEmail.id == email_id)
            .first()
        )

    def update_email(self, db: Session, email_id: int, subject: Optional[str], body: Optional[str]):
        email = self.get_email(db, email_id)
        if not email:
            return None
        if email.status == "sent":
            raise ValueError("Sent emails cannot be edited.")
        if email.status in {"rejected", "cancelled", "sending"}:
            raise ValueError(f"Emails with status '{email.status}' cannot be edited.")
        changed = False
        if subject is not None:
            if not subject.strip():
                raise ValueError("Email subject cannot be empty.")
            changed = changed or subject != email.subject
            email.subject = subject
        if body is not None:
            if not body.strip():
                raise ValueError("Email body cannot be empty.")
            changed = changed or body != email.body
            email.body = body
        if changed and email.status == "approved":
            email.status = "pending_approval"
            email.human_approved = False
            email.approved_at = None
            self.add_event(
                db,
                "approval_revoked",
                "Email content changed after approval; renewed approval is required",
                email_id=email.id,
                campaign_id=email.campaign_id,
                influencer_id=email.influencer_id,
            )
        self.add_event(db, "edited", "Subject/body updated by operator", email_id=email.id, campaign_id=email.campaign_id, influencer_id=email.influencer_id)
        db.commit()
        db.refresh(email)
        return self._serialize_email(email)

    def approve_email(self, db: Session, email_id: int):
        email = self.get_email(db, email_id)
        if not email:
            return None
        if email.status == "sent":
            raise ValueError("Already sent.")
        if email.status == "rejected":
            raise ValueError("Rejected emails cannot be approved. Generate a new draft.")
        if email.status not in {"pending_approval", "approved", "failed"}:
            raise ValueError("This email is not available for approval.")
        inf = email.influencer
        if inf and (inf.opted_out or inf.status in STOP_STATUSES):
            raise ValueError("Follow-ups are stopped for this influencer.")
        email.status = "approved"
        email.human_approved = True
        email.approved_at = _naive(_utcnow())
        self.add_event(db, "approved", "Human approved send", email_id=email.id, campaign_id=email.campaign_id, influencer_id=email.influencer_id)
        db.commit()
        db.refresh(email)
        return self._serialize_email(email)

    def reject_email(self, db: Session, email_id: int):
        email = self.get_email(db, email_id)
        if not email:
            return None
        if email.status == "sent":
            raise ValueError("Already sent.")
        email.status = "rejected"
        email.human_approved = False
        email.rejected_at = _naive(_utcnow())
        self.add_event(db, "rejected", "Human rejected send", email_id=email.id, campaign_id=email.campaign_id, influencer_id=email.influencer_id)
        db.commit()
        db.refresh(email)
        return self._serialize_email(email)

    def _quota(self, db: Session) -> DailySendQuota:
        day = _utcnow().strftime("%Y-%m-%d")
        row = db.query(DailySendQuota).filter(DailySendQuota.day == day).first()
        if not row:
            row = DailySendQuota(day=day, live_sent=0, simulated_sent=0, reserved=0)
            db.add(row)
            db.commit()
            db.refresh(row)
        return row

    def quota_status(self, db: Session) -> Dict[str, Any]:
        row = self._quota(db)
        db.refresh(row)
        used = row.live_sent + row.simulated_sent
        return {
            "day": row.day,
            "daily_limit": settings.DAILY_SEND_LIMIT,
            "live_sent": row.live_sent,
            "simulated_sent": row.simulated_sent,
            "reserved": row.reserved,
            "used": used,
            "remaining": max(0, settings.DAILY_SEND_LIMIT - used - row.reserved),
            "min_seconds_between_sends": settings.MIN_SECONDS_BETWEEN_SENDS,
            "last_send_at": row.last_send_at,
        }

    async def _reserve_send_quota(self, db: Session) -> DailySendQuota:
        quota = self._quota(db)
        while True:
            db.refresh(quota)
            used = quota.live_sent + quota.simulated_sent + quota.reserved
            if used >= settings.DAILY_SEND_LIMIT:
                raise ValueError(f"Daily sending limit reached ({settings.DAILY_SEND_LIMIT}).")

            now = _utcnow()
            last = quota.last_send_at
            if last and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if last and settings.MIN_SECONDS_BETWEEN_SENDS > 0:
                wait = settings.MIN_SECONDS_BETWEEN_SENDS - (now - last).total_seconds()
                if wait > 0:
                    await asyncio.sleep(wait)
                    continue

            reserved_at = _naive(_utcnow())
            claim = db.query(DailySendQuota).filter(
                DailySendQuota.id == quota.id,
                DailySendQuota.live_sent
                + DailySendQuota.simulated_sent
                + DailySendQuota.reserved
                < settings.DAILY_SEND_LIMIT,
            )
            if settings.MIN_SECONDS_BETWEEN_SENDS > 0:
                earliest_allowed = _naive(
                    _utcnow() - timedelta(seconds=settings.MIN_SECONDS_BETWEEN_SENDS)
                )
                claim = claim.filter(
                    or_(
                        DailySendQuota.last_send_at.is_(None),
                        DailySendQuota.last_send_at <= earliest_allowed,
                    )
                )
            claimed = claim.update(
                {
                    DailySendQuota.reserved: DailySendQuota.reserved + 1,
                    DailySendQuota.last_send_at: reserved_at,
                },
                synchronize_session=False,
            )
            db.commit()
            if claimed:
                db.refresh(quota)
                return quota

    @staticmethod
    def _finish_send_reservation(
        db: Session, quota: DailySendQuota, send_mode: Optional[str] = None
    ) -> None:
        values = {DailySendQuota.reserved: DailySendQuota.reserved - 1}
        if send_mode == "live_gmail":
            values[DailySendQuota.live_sent] = DailySendQuota.live_sent + 1
        elif send_mode == "simulated":
            values[DailySendQuota.simulated_sent] = DailySendQuota.simulated_sent + 1
        db.query(DailySendQuota).filter(
            DailySendQuota.id == quota.id,
            DailySendQuota.reserved > 0,
        ).update(values, synchronize_session=False)

    async def send_approved(
        self,
        db: Session,
        campaign_id: Optional[int] = None,
        email_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        q = db.query(OutreachEmail).options(joinedload(OutreachEmail.influencer), joinedload(OutreachEmail.campaign)).filter(
            OutreachEmail.status == "approved",
            OutreachEmail.human_approved.is_(True),
        )
        if campaign_id:
            q = q.filter(OutreachEmail.campaign_id == campaign_id)
        if email_ids:
            q = q.filter(OutreachEmail.id.in_(email_ids))
        emails = q.all()
        if not emails:
            return {"sent": [], "failed": [], "skipped": [], "message": "No approved emails waiting to send."}

        sent, failed, skipped = [], [], []
        synced_influencers = {}
        outreach_metadata = {}

        for email in emails:
            inf = email.influencer
            if not inf or not email.to_email:
                skipped.append({"id": email.id, "reason": "missing_influencer_or_email"})
                continue
            if inf.opted_out:
                email.status = "cancelled"
                email.stop_followups = True
                skipped.append({"id": email.id, "reason": "opted_out"})
                continue
            if inf.status in STOP_STATUSES:
                email.status = "cancelled"
                email.stop_followups = True
                skipped.append({"id": email.id, "reason": f"stopped:{inf.status}"})
                continue
            duplicate_sent = (
                db.query(OutreachEmail)
                .filter(
                    OutreachEmail.id != email.id,
                    OutreachEmail.to_email.ilike(email.to_email),
                    OutreachEmail.sequence_number == email.sequence_number,
                    OutreachEmail.status == "sent",
                )
                .first()
            )
            if duplicate_sent:
                email.status = "cancelled"
                skipped.append({"id": email.id, "reason": "duplicate_already_sent"})
                continue

            recipient_claim = None
            if email.sequence_number == 0:
                address = email.to_email.strip().lower()
                recipient_claim = (
                    db.query(OutreachRecipientClaim)
                    .filter(OutreachRecipientClaim.email_address == address)
                    .first()
                )
                if recipient_claim:
                    skipped.append({"id": email.id, "reason": "initial_email_already_claimed"})
                    continue
                recipient_claim = OutreachRecipientClaim(
                    email_address=address,
                    email_id=email.id,
                    status="sending",
                )
                db.add(recipient_claim)
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    skipped.append({"id": email.id, "reason": "initial_email_already_claimed"})
                    continue

            try:
                quota = await self._reserve_send_quota(db)
            except ValueError as e:
                if recipient_claim:
                    db.delete(recipient_claim)
                    db.commit()
                failed.append({"id": email.id, "error": str(e)})
                break

            claimed = (
                db.query(OutreachEmail)
                .filter(
                    OutreachEmail.id == email.id,
                    OutreachEmail.status == "approved",
                    OutreachEmail.human_approved.is_(True),
                )
                .update({OutreachEmail.status: "sending"}, synchronize_session=False)
            )
            db.commit()
            if not claimed:
                self._finish_send_reservation(db, quota)
                if recipient_claim:
                    db.delete(recipient_claim)
                db.commit()
                skipped.append({"id": email.id, "reason": "approval_no_longer_valid_or_already_claimed"})
                continue
            email.status = "sending"
            db.refresh(inf)
            if inf.opted_out or inf.status in STOP_STATUSES or email.stop_followups:
                self._finish_send_reservation(db, quota)
                if recipient_claim:
                    db.delete(recipient_claim)
                email.status = "cancelled"
                email.stop_followups = True
                db.commit()
                skipped.append({"id": email.id, "reason": "stopped_before_send"})
                continue

            try:
                mode, meta = gmail_service.send_email(db, email.to_email, email.subject, email.body)
            except Exception as e:
                self._finish_send_reservation(db, quota)
                if recipient_claim:
                    db.delete(recipient_claim)
                email.status = "failed"
                email.error_message = str(e)
                self.add_event(db, "send_failed", str(e), email_id=email.id, campaign_id=email.campaign_id, influencer_id=inf.id)
                failed.append({"id": email.id, "error": str(e)})
                db.commit()
                continue

            now = _naive(_utcnow())
            email.status = "sent"
            email.sent_at = now
            email.send_mode = mode
            email.gmail_message_id = meta.get("gmail_message_id")
            email.gmail_thread_id = meta.get("gmail_thread_id")
            email.error_message = None
            inf.last_contacted_at = now
            inf.synced_to_sheets = False
            email.campaign.status = "active"
            if email.sequence_number == 0:
                inf.status = LeadStatus.EMAIL_SENT.value
                days = randint(settings.FOLLOWUP_1_MIN_DAYS, settings.FOLLOWUP_1_MAX_DAYS)
                email.follow_up_due_at = now + timedelta(days=days)
            elif email.sequence_number == 1:
                inf.status = LeadStatus.EMAIL_SENT.value
                days = randint(settings.FOLLOWUP_2_MIN_DAYS, settings.FOLLOWUP_2_MAX_DAYS)
                email.follow_up_due_at = now + timedelta(days=days)
            else:
                inf.status = LeadStatus.EMAIL_SENT.value
                email.follow_up_due_at = None

            self._finish_send_reservation(db, quota, mode)
            if recipient_claim:
                recipient_claim.status = "sent"

            self.add_event(
                db,
                "sent",
                f"Sent via {mode} to {email.to_email}",
                email_id=email.id,
                campaign_id=email.campaign_id,
                influencer_id=inf.id,
            )
            sent.append(self._serialize_email(email))
            synced_influencers[inf.id] = inf
            outreach_metadata[inf.id] = {
                "campaign_name": email.campaign.name,
                "subject": email.subject,
                "status": "Email Sent",
                "sent_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            }
            db.commit()

        sheets_result = None
        if synced_influencers:
            try:
                sheets_result = await google_sheets_service.sync_influencers(
                    list(synced_influencers.values()),
                    outreach_metadata=outreach_metadata,
                )
                stamp = _naive(_utcnow())
                if sheets_result.get("success"):
                    for inf in synced_influencers.values():
                        inf.synced_to_sheets = True
                        inf.last_synced_at = stamp
                db.commit()
            except Exception as e:
                logger.warning(f"Sheets sync after send failed: {e}")
                sheets_result = {"success": False, "error": str(e)}

        if sent:
            db.commit()

        return {
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
            "quota": self.quota_status(db),
            "sheets_sync": sheets_result,
            "message": f"Sent {len(sent)} email(s). {len(failed)} failed. {len(skipped)} skipped.",
        }

    async def create_followup_draft(self, db: Session, parent: OutreachEmail) -> Optional[OutreachEmail]:
        next_seq = parent.sequence_number + 1
        if next_seq > 2:
            return None
        inf = parent.influencer or db.query(Influencer).filter(Influencer.id == parent.influencer_id).first()
        campaign = parent.campaign or db.query(OutreachCampaign).filter(OutreachCampaign.id == parent.campaign_id).first()
        if not inf or not campaign:
            return None
        if inf.opted_out or inf.status in STOP_STATUSES or parent.stop_followups:
            return None
        reason = self._skip_reason(db, campaign.id, inf, sequence_number=next_seq)
        if reason:
            return None

        sender_email = ""
        token = gmail_service.get_active_token(db)
        if token and token.email_address:
            sender_email = token.email_address
        opt_token = secrets.token_urlsafe(16)
        draft = await email_generator.generate_email(
            influencer=inf,
            campaign=campaign,
            sequence_number=next_seq,
            opt_out_url=self._opt_out_url(opt_token),
            sender_email=sender_email,
        )
        email_type = "follow_up_1" if next_seq == 1 else "follow_up_2"
        email = OutreachEmail(
            campaign_id=campaign.id,
            influencer_id=inf.id,
            sequence_number=next_seq,
            email_type=email_type,
            to_email=inf.email,
            subject=draft["subject"],
            body=draft["body"],
            status="pending_approval",
            human_approved=False,
            opt_out_token=opt_token,
        )
        db.add(email)
        inf.status = LeadStatus.FOLLOW_UP_DUE.value
        db.flush()
        self.add_event(
            db,
            "followup_drafted",
            f"{email_type} queued for human approval",
            email_id=email.id,
            campaign_id=campaign.id,
            influencer_id=inf.id,
        )
        db.commit()
        db.refresh(email)
        return email

    async def process_due_followups(self, db: Session, force: bool = False) -> Dict[str, Any]:
        if force and not settings.DEMO_MODE:
            raise ValueError("Forcing follow-up timing is available only in demo mode.")
        now = _naive(_utcnow())
        q = db.query(OutreachEmail).options(
            joinedload(OutreachEmail.influencer),
            joinedload(OutreachEmail.campaign),
        ).filter(
            OutreachEmail.status == "sent",
            OutreachEmail.sequence_number < 2,
            OutreachEmail.stop_followups.is_(False),
        )
        due = []
        for parent in q.all():
            if not parent.follow_up_due_at and not force:
                continue
            due_at = parent.follow_up_due_at
            if due_at and due_at.tzinfo is not None:
                due_at = due_at.replace(tzinfo=None)
            if force or (due_at and due_at <= now):
                due.append(parent)

        created = []
        skipped = []
        for parent in due:
            inf = parent.influencer
            if not inf or inf.opted_out or inf.status in STOP_STATUSES:
                skipped.append({"parent_id": parent.id, "reason": "stopped"})
                continue
            email = await self.create_followup_draft(db, parent)
            if email:
                created.append(self._serialize_email(email))
            else:
                skipped.append({"parent_id": parent.id, "reason": "already_exists_or_ineligible"})
        return {"created": created, "skipped": skipped, "processed": len(due)}

    def stop_influencer_followups(
        self,
        db: Session,
        influencer_id: int,
        status: str,
        detail: str,
        campaign_id: Optional[int] = None,
    ):
        inf = db.query(Influencer).filter(Influencer.id == influencer_id).first()
        if not inf:
            return None
        inf.status = status
        q = db.query(OutreachEmail).filter(OutreachEmail.influencer_id == influencer_id)
        if campaign_id:
            q = q.filter(OutreachEmail.campaign_id == campaign_id)
        for email in q.all():
            email.stop_followups = True
            if email.status in ("pending_approval", "approved"):
                email.status = "cancelled"
        self.add_event(db, "followups_stopped", detail, influencer_id=influencer_id, campaign_id=campaign_id)
        db.commit()
        return inf

    def apply_outcome(self, db: Session, email_id: int, outcome: str) -> Dict[str, Any]:
        email = self.get_email(db, email_id)
        if not email:
            raise ValueError("Email not found")
        if email.status != "sent":
            raise ValueError("Only sent emails can be marked as replied or declined.")
        mapping = {
            "replied": LeadStatus.REPLIED.value,
            "interested": LeadStatus.INTERESTED.value,
            "not_interested": LeadStatus.NOT_INTERESTED.value,
            "opt_out": LeadStatus.NOT_INTERESTED.value,
        }
        if outcome not in mapping:
            raise ValueError("Outcome must be replied, interested, not_interested, or opt_out")
        if outcome == "opt_out":
            inf = email.influencer
            if inf:
                inf.opted_out = True
        inf = self.stop_influencer_followups(
            db,
            email.influencer_id,
            mapping[outcome],
            f"Outcome recorded: {outcome}",
            campaign_id=None,
        )
        self.add_event(
            db,
            f"outcome_{outcome}",
            f"Campaign tracking set to {mapping[outcome]}",
            email_id=email.id,
            campaign_id=email.campaign_id,
            influencer_id=email.influencer_id,
        )
        db.commit()
        return {"influencer_id": email.influencer_id, "status": inf.status if inf else mapping[outcome], "outcome": outcome}

    def opt_out_by_token(self, db: Session, token: str) -> Dict[str, Any]:
        email = db.query(OutreachEmail).filter(OutreachEmail.opt_out_token == token).first()
        if not email:
            raise ValueError("Invalid opt-out token")
        inf = self.stop_influencer_followups(
            db, email.influencer_id, LeadStatus.NOT_INTERESTED.value, "Opt-out link used"
        )
        if inf:
            inf.opted_out = True
            db.commit()
        return {"ok": True, "influencer_id": email.influencer_id}

    def list_events(self, db: Session, campaign_id: Optional[int] = None, influencer_id: Optional[int] = None):
        q = db.query(OutreachEvent).order_by(OutreachEvent.created_at.desc())
        if campaign_id:
            q = q.filter(OutreachEvent.campaign_id == campaign_id)
        if influencer_id:
            q = q.filter(OutreachEvent.influencer_id == influencer_id)
        return q.limit(200).all()

    def tracking_summary(self, db: Session) -> Dict[str, Any]:
        from app.services.reply_manager import reply_manager

        emails = db.query(OutreachEmail).all()
        influencers = db.query(Influencer).all()
        replies = db.query(InfluencerReply).all()
        return {
            "demo_mode": settings.DEMO_MODE,
            "reply_ai_mode": "live_claude" if reply_manager.is_api_configured() else "simulated_classifier",
            "emails_by_status": dict(Counter(e.status for e in emails)),
            "emails_by_type": dict(Counter(e.email_type for e in emails)),
            "replies_by_classification": dict(Counter(r.classification for r in replies)),
            "pending_reply_approvals": sum(1 for r in replies if r.status == "pending_approval"),
            "pipeline": dict(Counter(i.status for i in influencers)),
            "opted_out": sum(1 for i in influencers if i.opted_out),
            "analytics": self.campaign_analytics(db),
            "quota": self.quota_status(db),
            "gmail": gmail_service.connection_status(db),
        }

    def campaign_analytics(self, db: Session, campaign_id: Optional[int] = None) -> Dict[str, Any]:
        influencers_query = db.query(Influencer)
        emails_query = db.query(OutreachEmail)
        replies_query = db.query(InfluencerReply)
        if campaign_id:
            emails_query = emails_query.filter(OutreachEmail.campaign_id == campaign_id)
            replies_query = replies_query.filter(InfluencerReply.campaign_id == campaign_id)
            influencer_ids = db.query(OutreachEmail.influencer_id).filter(
                OutreachEmail.campaign_id == campaign_id
            ).distinct()
            influencers_query = influencers_query.filter(Influencer.id.in_(influencer_ids))

        influencers = influencers_query.all()
        emails = emails_query.all()
        replies = replies_query.all()
        reply_count = len({r.gmail_message_id for r in replies})
        sent_count = sum(1 for e in emails if e.status == "sent")
        initial_sent_influencers = {
            email.influencer_id
            for email in emails
            if email.sequence_number == 0 and email.status == "sent"
        }
        replied_influencers = {
            reply.influencer_id
            for reply in replies
            if reply.influencer_id in initial_sent_influencers
        }
        return {
            "campaign_id": campaign_id,
            "total_influencers_researched": influencers_query.count(),
            "qualified_influencers": sum(
                1 for inf in influencers if inf.suitability_score is not None and inf.suitability_score >= 70
            ),
            "emails_sent": sent_count,
            "emails_delivered": None,
            "delivery_information_available": False,
            "replies_received": reply_count,
            "interested_influencers": len({
                r.influencer_id for r in replies if r.classification == "Interested"
            }),
            "not_interested_influencers": len({
                r.influencer_id for r in replies if r.classification == "Not Interested"
            }),
            "collaboration_confirmations": sum(
                1 for inf in influencers if inf.status == LeadStatus.COLLABORATION_CONFIRMED.value
            ),
            "reply_rate": round(
                len(replied_influencers) / len(initial_sent_influencers), 4
            ) if initial_sent_influencers else 0,
        }

    def list_replies(
        self,
        db: Session,
        campaign_id: Optional[int] = None,
        influencer_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = db.query(InfluencerReply).options(
            joinedload(InfluencerReply.influencer),
            joinedload(InfluencerReply.campaign),
        ).order_by(InfluencerReply.received_at.desc(), InfluencerReply.id.desc())
        if campaign_id:
            query = query.filter(InfluencerReply.campaign_id == campaign_id)
        if influencer_id:
            query = query.filter(InfluencerReply.influencer_id == influencer_id)
        if status:
            query = query.filter(InfluencerReply.status == status)
        return [self._serialize_reply(reply) for reply in query.all()]

    def update_reply_draft(
        self,
        db: Session,
        reply_id: int,
        subject: Optional[str],
        body: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        reply = db.query(InfluencerReply).options(
            joinedload(InfluencerReply.influencer),
            joinedload(InfluencerReply.campaign),
        ).filter(InfluencerReply.id == reply_id).first()
        if not reply:
            return None
        if reply.status not in {"pending_approval", "approved", "failed"}:
            raise ValueError(f"Reply drafts with status '{reply.status}' cannot be edited.")
        changed = False
        if subject is not None:
            if not subject.strip():
                raise ValueError("Reply subject cannot be empty.")
            changed = changed or subject != reply.draft_subject
            reply.draft_subject = subject
        if body is not None:
            if not body.strip():
                raise ValueError("Reply body cannot be empty.")
            changed = changed or body != reply.draft_body
            reply.draft_body = body
        if changed and reply.status == "approved":
            reply.status = "pending_approval"
            reply.human_approved = False
            reply.approved_at = None
            self.add_event(
                db,
                "reply_approval_revoked",
                "Reply draft changed after approval; renewed approval is required",
                campaign_id=reply.campaign_id,
                influencer_id=reply.influencer_id,
            )
        self.add_event(
            db,
            "reply_draft_edited",
            "Human edited the AI-generated reply",
            campaign_id=reply.campaign_id,
            influencer_id=reply.influencer_id,
        )
        db.commit()
        db.refresh(reply)
        return self._serialize_reply(reply)

    def approve_reply(self, db: Session, reply_id: int) -> Optional[Dict[str, Any]]:
        reply = db.query(InfluencerReply).options(
            joinedload(InfluencerReply.influencer),
            joinedload(InfluencerReply.campaign),
        ).filter(InfluencerReply.id == reply_id).first()
        if not reply:
            return None
        if reply.status not in {"pending_approval", "failed"}:
            raise ValueError("This reply is not available for approval.")
        if not reply.draft_subject or not reply.draft_body:
            raise ValueError("Reply has no sendable draft.")
        if reply.classification == "Opt-out" or reply.influencer.opted_out:
            raise ValueError("Opt-outs cannot receive a reply.")
        reply.status = "approved"
        reply.human_approved = True
        reply.approved_at = _naive(_utcnow())
        self.add_event(
            db,
            "reply_approved",
            "Human approved the AI reply",
            campaign_id=reply.campaign_id,
            influencer_id=reply.influencer_id,
        )
        db.commit()
        db.refresh(reply)
        return self._serialize_reply(reply)

    def reject_reply(self, db: Session, reply_id: int) -> Optional[Dict[str, Any]]:
        reply = db.query(InfluencerReply).options(
            joinedload(InfluencerReply.influencer),
            joinedload(InfluencerReply.campaign),
        ).filter(InfluencerReply.id == reply_id).first()
        if not reply:
            return None
        if reply.status in {"sent", "no_reply_required"}:
            raise ValueError("This reply cannot be rejected.")
        reply.status = "rejected"
        reply.human_approved = False
        reply.rejected_at = _naive(_utcnow())
        self.add_event(
            db,
            "reply_rejected",
            "Human rejected the AI reply",
            campaign_id=reply.campaign_id,
            influencer_id=reply.influencer_id,
        )
        db.commit()
        db.refresh(reply)
        return self._serialize_reply(reply)

    async def send_approved_replies(
        self,
        db: Session,
        reply_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        query = db.query(InfluencerReply).options(
            joinedload(InfluencerReply.influencer),
            joinedload(InfluencerReply.campaign),
        ).filter(
            InfluencerReply.status == "approved",
            InfluencerReply.human_approved.is_(True),
        )
        if reply_ids:
            query = query.filter(InfluencerReply.id.in_(reply_ids))
        replies = query.all()
        sent, failed, skipped = [], [], []
        sheets_by_id: Dict[int, Influencer] = {}
        for reply in replies:
            if reply.classification == "Opt-out" or reply.influencer.opted_out:
                reply.status = "no_reply_required"
                reply.human_approved = False
                skipped.append({"reply_id": reply.id, "reason": "influencer_opted_out"})
                db.commit()
                continue
            claimed = db.query(InfluencerReply).filter(
                InfluencerReply.id == reply.id,
                InfluencerReply.status == "approved",
                InfluencerReply.human_approved.is_(True),
            ).update({InfluencerReply.status: "sending"}, synchronize_session=False)
            db.commit()
            if not claimed:
                continue
            quota = None
            try:
                quota = await self._reserve_send_quota(db)
                mode, metadata = gmail_service.send_email(
                    db,
                    reply.from_email,
                    reply.draft_subject,
                    reply.draft_body,
                    thread_id=reply.gmail_thread_id,
                    reply_to_message_id=reply.gmail_rfc822_message_id,
                )
            except Exception as e:
                if quota:
                    self._finish_send_reservation(db, quota)
                reply.status = "failed"
                reply.human_approved = False
                reply.error_message = str(e)
                failed.append({"reply_id": reply.id, "error": str(e)})
                db.commit()
                continue
            self._finish_send_reservation(db, quota, mode)
            reply.status = "sent"
            reply.sent_at = _naive(_utcnow())
            reply.send_mode = mode
            reply.reply_gmail_message_id = metadata.get("gmail_message_id")
            reply.error_message = None
            self.add_event(
                db,
                "ai_reply_sent",
                f"Approved reply sent via {mode}",
                campaign_id=reply.campaign_id,
                influencer_id=reply.influencer_id,
            )
            sent.append(self._serialize_reply(reply))
            sheets_by_id[reply.influencer_id] = reply.influencer
            db.commit()

        sheets_results = []
        for influencer_id, inf in sheets_by_id.items():
            latest = db.query(InfluencerReply).filter(
                InfluencerReply.influencer_id == influencer_id
            ).order_by(InfluencerReply.received_at.desc()).first()
            result = await self._sync_reply_status(db, inf, latest) if latest else None
            if result:
                sheets_results.append(result)
        return {
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
            "quota": self.quota_status(db),
            "sheets_sync": sheets_results,
            "message": f"Sent {len(sent)} approved reply/replies; {len(failed)} failed.",
        }

    def conversation_history(self, db: Session, influencer_id: int) -> Dict[str, Any]:
        influencer = db.query(Influencer).filter(Influencer.id == influencer_id).first()
        if not influencer:
            raise ValueError("Influencer not found")
        outbound = db.query(OutreachEmail).filter(
            OutreachEmail.influencer_id == influencer_id,
            OutreachEmail.status == "sent",
        ).all()
        inbound = db.query(InfluencerReply).filter(
            InfluencerReply.influencer_id == influencer_id,
        ).all()
        messages = [
            {
                "id": f"outbound-{email.id}",
                "direction": "outbound",
                "subject": email.subject,
                "body": email.body,
                "status": email.status,
                "send_mode": email.send_mode,
                "timestamp": email.sent_at,
                "campaign_id": email.campaign_id,
            }
            for email in outbound
        ]
        for reply in inbound:
            messages.append({
                "id": f"inbound-{reply.id}",
                "direction": "inbound",
                "subject": reply.subject,
                "body": reply.body,
                "classification": reply.classification,
                "status": reply.status,
                "timestamp": reply.received_at,
                "campaign_id": reply.campaign_id,
            })
            if reply.sent_at and reply.draft_body:
                messages.append({
                    "id": f"reply-{reply.id}",
                    "direction": "outbound",
                    "subject": reply.draft_subject,
                    "body": reply.draft_body,
                    "status": reply.status,
                    "send_mode": reply.send_mode,
                    "timestamp": reply.sent_at,
                    "campaign_id": reply.campaign_id,
                })
        messages.sort(key=lambda message: message["timestamp"] or datetime.min)
        return {
            "influencer_id": influencer.id,
            "influencer_name": influencer.name,
            "messages": messages,
        }

    async def poll_replies(self, db: Session) -> Dict[str, Any]:
        gmail_status = gmail_service.connection_status(db)
        if not gmail_status["connected"]:
            return {"detected": [], "mode": gmail_status["send_mode"], "message": "Connect Gmail to monitor replies."}

        sent_emails = db.query(OutreachEmail).options(
            joinedload(OutreachEmail.influencer),
            joinedload(OutreachEmail.campaign),
        ).filter(OutreachEmail.status == "sent").order_by(OutreachEmail.sent_at.asc()).all()
        by_influencer: Dict[int, List[OutreachEmail]] = {}
        for email in sent_emails:
            if email.influencer and email.influencer.email:
                by_influencer.setdefault(email.influencer_id, []).append(email)

        detected = []
        for influencer_id, outreach in by_influencer.items():
            inf = outreach[0].influencer
            first_sent_at = next((email.sent_at for email in outreach if email.sent_at), None)
            if not inf or not first_sent_at:
                continue
            if first_sent_at.tzinfo is None:
                first_sent_at = first_sent_at.replace(tzinfo=timezone.utc)
            after = max(0, int(first_sent_at.timestamp()) - 1)
            inbox_messages = gmail_service.list_recent_inbox(
                db,
                query=f"from:{inf.email} after:{after}",
                max_results=100,
            )
            for message in inbox_messages:
                message_id = message.get("id")
                sender_address = parseaddr(message.get("from", ""))[1].lower()
                if not message_id or sender_address != inf.email.lower():
                    continue
                if db.query(InfluencerReply.id).filter(
                    InfluencerReply.gmail_message_id == message_id
                ).first():
                    continue
                received_at = self._message_received_at(message)
                original = self._match_original_email(outreach, message, received_at)
                if not original:
                    continue
                reply_body = (message.get("body") or message.get("snippet") or "").strip()
                if not reply_body:
                    logger.warning("Skipping Gmail message %s because it has no readable body.", message_id)
                    continue
                result = await self._record_incoming_reply(
                    db,
                    original,
                    message.get("subject") or "",
                    reply_body,
                    message_id,
                    received_at=received_at,
                    thread_id=message.get("threadId"),
                    rfc822_message_id=message.get("rfc822_message_id"),
                    source="Gmail",
                )
                detected.append({
                    **result["reply"],
                    "sheets_sync": result["sheets_sync"],
                    "classification_mode": result["classification_mode"],
                })
        return {"detected": detected, "mode": "live_gmail"}

    async def simulate_reply(self, db: Session, email_id: int, decline: bool = False) -> Dict[str, Any]:
        email = self.get_email(db, email_id)
        if not email or email.status != "sent":
            raise ValueError("Only sent emails can receive a simulated reply.")
        if not settings.DEMO_MODE:
            raise ValueError("Simulated inbox replies are available only in demo mode.")
        outcome = (
            "Thanks for reaching out, but I'm not interested in this collaboration."
            if decline
            else "Thanks for your note. I'm interested in learning more about the collaboration details."
        )
        return await self.record_simulated_reply(
            db,
            email_id,
            outcome,
            f"Re: {email.subject}",
        )

    async def record_simulated_reply(
        self,
        db: Session,
        email_id: int,
        body: str,
        subject: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not settings.DEMO_MODE:
            raise ValueError("Simulated inbox replies are available only in demo mode.")
        if not body.strip() or len(body) > 10000:
            raise ValueError("Demo reply must contain 1 to 10000 characters.")
        original = self.get_email(db, email_id)
        if not original or original.status != "sent":
            raise ValueError("Only sent emails can receive a simulated reply.")
        return await self._record_incoming_reply(
            db,
            original,
            (subject or f"Re: {original.subject}")[:500],
            body.strip(),
            f"sim_reply_{secrets.token_urlsafe(16)}",
        )

    @staticmethod
    def _message_received_at(message: Dict[str, Any]) -> datetime:
        try:
            received = datetime.fromtimestamp(int(message["internal_date"]) / 1000, tz=timezone.utc)
        except (KeyError, TypeError, ValueError, OSError):
            received = _utcnow()
        return _naive(received)

    @staticmethod
    def _match_original_email(
        outreach: List[OutreachEmail],
        message: Dict[str, Any],
        received_at: datetime,
    ) -> Optional[OutreachEmail]:
        thread_id = message.get("threadId")
        thread_matches = [email for email in outreach if thread_id and email.gmail_thread_id == thread_id]
        candidates = thread_matches or outreach
        candidates = [
            email for email in candidates
            if email.sent_at and _naive(email.sent_at) <= received_at
        ]
        return max(candidates, key=lambda email: email.sent_at) if candidates else None

    async def _record_incoming_reply(
        self,
        db: Session,
        original: OutreachEmail,
        subject: str,
        body: str,
        message_id: str,
        classification_override: Optional[str] = None,
        received_at: Optional[datetime] = None,
        thread_id: Optional[str] = None,
        rfc822_message_id: Optional[str] = None,
        source: str = "Demo",
    ) -> Dict[str, Any]:
        from app.services.reply_manager import reply_manager

        inf = original.influencer
        campaign = original.campaign
        reply = InfluencerReply(
            gmail_message_id=message_id,
            gmail_thread_id=thread_id or original.gmail_thread_id,
            gmail_rfc822_message_id=rfc822_message_id,
            influencer_id=inf.id,
            campaign_id=original.campaign_id,
            original_email_id=original.id,
            from_email=inf.email or "",
            subject=subject,
            body=body,
            classification="Unclassified",
            confidence=0,
            classification_reason="Classification is in progress.",
            received_at=_naive(received_at or _utcnow()),
            status="processing",
        )
        db.add(reply)
        db.flush()
        self.stop_influencer_followups(
            db,
            inf.id,
            LeadStatus.REPLIED.value,
            f"{source} reply received; follow-ups stopped before AI processing",
        )
        self.add_event(
            db,
            "influencer_reply_received",
            f"{source} message received; AI classification pending",
            email_id=original.id,
            campaign_id=original.campaign_id,
            influencer_id=inf.id,
        )
        db.commit()
        db.refresh(reply)

        classification_mode = "unavailable"
        try:
            classification = (
                {
                    "classification": classification_override,
                    "confidence": 100,
                    "reason": "Selected in the demo inbox.",
                    "mode": "simulated_classifier",
                }
                if classification_override
                else await reply_manager.classify(inf, original, subject, body)
            )
            label = str(classification["classification"])
            crm_status = {
                "Interested": LeadStatus.INTERESTED.value,
                "Not Interested": LeadStatus.NOT_INTERESTED.value,
                "Pricing Enquiry": LeadStatus.PRICING_ENQUIRY.value,
                "Collaboration Request": LeadStatus.COLLABORATION_REQUEST.value,
                "General Query": LeadStatus.GENERAL_QUERY.value,
                "Opt-out": LeadStatus.NOT_INTERESTED.value,
            }[label]
            reply.classification = label
            reply.confidence = int(classification["confidence"])
            reply.classification_reason = str(classification["reason"])
            classification_mode = str(classification["mode"])
            if label == "Opt-out":
                inf.opted_out = True
                reply.status = "no_reply_required"
            else:
                reply.status = "pending_approval"
            self.stop_influencer_followups(
                db,
                inf.id,
                crm_status,
                f"{source} reply classified as {label}",
            )
            if label != "Opt-out":
                draft = await reply_manager.generate_draft(
                    inf,
                    campaign,
                    original,
                    subject,
                    body,
                    label,
                )
                reply.draft_subject = draft["subject"]
                reply.draft_body = draft["body"]
            self.add_event(
                db,
                "opt_out_detected" if label == "Opt-out" else "reply_draft_generated",
                "No reply generated; contact suppressed globally" if label == "Opt-out"
                else "Reply draft requires human approval",
                email_id=original.id,
                campaign_id=original.campaign_id,
                influencer_id=inf.id,
            )
        except Exception as e:
            logger.exception("%s reply processing failed for message %s", source, message_id)
            reply.status = "failed"
            reply.error_message = str(e)
            reply.classification_reason = "AI processing failed; review the reply and create a draft manually."
        db.commit()
        db.refresh(reply)

        sheets_result = await self._sync_reply_status(db, inf, reply)
        return {
            "reply": self._serialize_reply(reply),
            "status": inf.status,
            "outcome": reply.classification,
            "simulated": source == "Demo",
            "sheets_sync": sheets_result,
            "classification_mode": classification_mode,
        }

    async def _sync_reply_status(
        self,
        db: Session,
        inf: Influencer,
        reply: InfluencerReply,
    ) -> Dict[str, Any]:
        original = reply.original_email
        metadata = {
            inf.id: {
                "campaign_name": reply.campaign.name if reply.campaign else "N/A",
                "subject": original.subject if original else reply.subject,
                "status": inf.status,
                "sent_at": (
                    original.sent_at.strftime("%Y-%m-%d %H:%M:%S")
                    if original and original.sent_at
                    else "N/A"
                ),
                "reply_classification": reply.classification,
                "reply_received_at": (
                    reply.received_at.strftime("%Y-%m-%d %H:%M:%S")
                    if reply.received_at
                    else "N/A"
                ),
            }
        }
        try:
            result = await google_sheets_service.sync_influencers(
                [inf],
                outreach_metadata=metadata,
            )
            if result.get("success"):
                inf.synced_to_sheets = True
                inf.last_synced_at = _naive(_utcnow())
                db.commit()
            return result
        except Exception as e:
            logger.error("Google Sheets sync after reply classification failed: %s", e)
            return {"success": False, "error": str(e)}


outreach_service = OutreachService()
