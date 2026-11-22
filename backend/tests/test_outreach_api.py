import csv
from datetime import datetime

import pytest

from app.core.config import settings
from app.models.influencer import LeadStatus
from app.models.outreach import OutreachEmail
from app.services.gmail_service import gmail_service


def _create_lead(client, username="maya_skincare", email="maya@creators.test"):
    payload = {
        "name": "Maya Chen",
        "instagram_username": username,
        "niche": "Fashion",
        "followers_count": 42000,
        "email": email,
        "location": "Los Angeles, USA",
    }
    res = client.post("/api/v1/influencers", json=payload)
    assert res.status_code == 201
    return res.json()


def _campaign(client, influencer_ids):
    return client.post(
        "/api/v1/outreach/campaigns",
        json={
            "brand_name": "Lumen Skin",
            "campaign_description": "Clean skincare launch with honest creator reviews.",
            "collaboration_offer": "Paid reel + story sequence",
            "call_to_action": "Reply with your rate card if interested.",
            "sender_name": "Jordan Lee, Partnerships",
            "relevant_keywords": "skincare, clean beauty",
            "influencer_ids": influencer_ids,
        },
    )


def test_generate_requires_approval_before_send(client):
    lead = _create_lead(client)
    created = _campaign(client, [lead["id"]])
    assert created.status_code == 200
    data = created.json()
    assert data["created_count"] == 1
    email = data["emails"][0]
    assert email["status"] == "pending_approval"
    assert "Lumen Skin" in email["body"]
    assert "selected because" in email["body"]
    assert "Reply with your rate card" in email["body"]
    assert "Sender: Jordan Lee, Partnerships" in email["body"]
    assert "/api/v1/outreach/opt-out/" in email["body"]

    send_early = client.post("/api/v1/outreach/send", json={"campaign_id": data["campaign"]["id"]})
    assert send_early.status_code == 200
    assert send_early.json()["sent"] == []

    approve = client.post(f"/api/v1/outreach/emails/{email['id']}/approve")
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"
    assert approve.json()["human_approved"] is True

    sent = client.post("/api/v1/outreach/send", json={"campaign_id": data["campaign"]["id"]})
    assert sent.status_code == 200
    payload = sent.json()
    assert len(payload["sent"]) == 1
    assert payload["sent"][0]["send_mode"] == "simulated"
    assert payload["sent"][0]["status"] == "sent"

    inf = client.get(f"/api/v1/influencers/{lead['id']}").json()
    assert inf["status"] == LeadStatus.EMAIL_SENT.value


def test_duplicate_sequence_is_skipped(client):
    lead = _create_lead(client, "dup_creator", "dup@creators.test")
    first = _campaign(client, [lead["id"]])
    assert first.json()["created_count"] == 1
    email_id = first.json()["emails"][0]["id"]
    client.post(f"/api/v1/outreach/emails/{email_id}/approve")
    client.post("/api/v1/outreach/send", json={"campaign_id": first.json()["campaign"]["id"]})

    second = _campaign(client, [lead["id"]])
    assert second.status_code == 200
    assert second.json()["created_count"] == 0
    assert second.json()["skipped"][0]["reason"] == "already_contacted_this_address"


def test_followup_requires_approval_and_stops_on_reply(client):
    lead = _create_lead(client, "follow_creator", "follow@creators.test")
    created = _campaign(client, [lead["id"]]).json()
    email_id = created["emails"][0]["id"]
    client.post(f"/api/v1/outreach/emails/{email_id}/approve")
    initial_send = client.post(
        "/api/v1/outreach/send",
        json={"campaign_id": created["campaign"]["id"]},
    ).json()["sent"][0]
    first_due_days = (
        datetime.fromisoformat(initial_send["follow_up_due_at"])
        - datetime.fromisoformat(initial_send["sent_at"])
    ).total_seconds() / 86400
    assert 3 <= first_due_days <= 5

    due = client.post("/api/v1/outreach/jobs/process-due?force=true")
    assert due.status_code == 200
    assert len(due.json()["created"]) == 1
    follow = due.json()["created"][0]
    assert follow["sequence_number"] == 1
    assert follow["status"] == "pending_approval"
    assert "fashion content" in follow["body"].lower()

    send_unapproved = client.post("/api/v1/outreach/send", json={"email_ids": [follow["id"]]})
    assert send_unapproved.json()["sent"] == []

    client.post(f"/api/v1/outreach/emails/{follow['id']}/approve")
    followup_send = client.post(
        "/api/v1/outreach/send",
        json={"email_ids": [follow["id"]]},
    ).json()["sent"][0]
    second_due_days = (
        datetime.fromisoformat(followup_send["follow_up_due_at"])
        - datetime.fromisoformat(followup_send["sent_at"])
    ).total_seconds() / 86400
    assert 5 <= second_due_days <= 7
    second_followup = client.post("/api/v1/outreach/jobs/process-due?force=true")
    final_drafts = second_followup.json()["created"]
    assert any(email["sequence_number"] == 2 for email in final_drafts)
    assert any("fashion content" in email["body"].lower() for email in final_drafts)

    reply = client.post("/api/v1/outreach/demo/simulate-reply", json={"email_id": email_id, "decline": False})
    assert reply.status_code == 200
    inf = client.get(f"/api/v1/influencers/{lead['id']}").json()
    assert inf["status"] == LeadStatus.INTERESTED.value
    assert reply.json()["reply"]["classification"] == "Interested"

    due_again = client.post("/api/v1/outreach/jobs/process-due?force=true")
    extra = [e for e in due_again.json()["created"] if e["influencer_id"] == lead["id"]]
    assert extra == []


def test_opt_out_cancels_followups(client, db_session):
    lead = _create_lead(client, "opt_creator", "opt@creators.test")
    created = _campaign(client, [lead["id"]]).json()
    email_id = created["emails"][0]["id"]
    client.post(f"/api/v1/outreach/emails/{email_id}/approve")
    client.post("/api/v1/outreach/send", json={"campaign_id": created["campaign"]["id"]})

    token = db_session.query(OutreachEmail).filter(OutreachEmail.id == email_id).first().opt_out_token
    page = client.get(f"/api/v1/outreach/opt-out/{token}")
    assert page.status_code == 200
    inf = client.get(f"/api/v1/influencers/{lead['id']}").json()
    assert inf["opted_out"] is True
    assert inf["status"] == LeadStatus.NOT_INTERESTED.value


def test_editing_approved_email_requires_new_approval(client):
    lead = _create_lead(client, "reapprove_creator", "reapprove@creators.test")
    email = _campaign(client, [lead["id"]]).json()["emails"][0]
    email_id = email["id"]

    approved = client.post(f"/api/v1/outreach/emails/{email_id}/approve")
    assert approved.json()["status"] == "approved"
    edited = client.patch(
        f"/api/v1/outreach/emails/{email_id}",
        json={"body": email["body"] + "\nUpdated copy."},
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "pending_approval"
    assert edited.json()["human_approved"] is False

    response = client.post("/api/v1/outreach/send", json={"email_ids": [email_id]})
    assert response.json()["sent"] == []


def test_decline_stops_campaign_without_global_opt_out(client):
    lead = _create_lead(client, "decline_creator", "decline@creators.test")
    created = _campaign(client, [lead["id"]]).json()
    email_id = created["emails"][0]["id"]
    client.post(f"/api/v1/outreach/emails/{email_id}/approve")
    client.post("/api/v1/outreach/send", json={"email_ids": [email_id]})

    outcome = client.post(
        f"/api/v1/outreach/emails/{email_id}/outcome",
        json={"outcome": "not_interested"},
    )
    assert outcome.status_code == 200
    influencer = client.get(f"/api/v1/influencers/{lead['id']}").json()
    assert influencer["status"] == LeadStatus.NOT_INTERESTED.value
    assert influencer["opted_out"] is False


@pytest.mark.parametrize("send_mode", ["simulated", "live_gmail"])
def test_daily_send_limit_counts_live_and_simulated_sends(client, monkeypatch, send_mode):
    monkeypatch.setattr(settings, "DAILY_SEND_LIMIT", 1)
    monkeypatch.setattr(settings, "MIN_SECONDS_BETWEEN_SENDS", 0)
    monkeypatch.setattr(
        gmail_service,
        "send_email",
        lambda *args: (send_mode, {"gmail_message_id": "mock-message"}),
    )
    first = _create_lead(client, "limit_creator_1", "limit1@creators.test")
    second = _create_lead(client, "limit_creator_2", "limit2@creators.test")
    created = _campaign(client, [first["id"], second["id"]]).json()
    email_ids = [email["id"] for email in created["emails"]]
    for email_id in email_ids:
        client.post(f"/api/v1/outreach/emails/{email_id}/approve")

    sent = client.post("/api/v1/outreach/send", json={"email_ids": email_ids}).json()
    assert len(sent["sent"]) == 1
    assert sent["sent"][0]["send_mode"] == send_mode
    assert sent["quota"]["used"] == 1
    assert sent["quota"]["remaining"] == 0
    assert any("Daily sending limit reached" in item["error"] for item in sent["failed"])


def test_reply_poll_updates_status_and_stops_followups(client, monkeypatch):
    lead = _create_lead(client, "reply_poll_creator", "replypoll@creators.test")
    created = _campaign(client, [lead["id"]]).json()
    email_id = created["emails"][0]["id"]
    client.post(f"/api/v1/outreach/emails/{email_id}/approve")
    client.post("/api/v1/outreach/send", json={"email_ids": [email_id]})

    monkeypatch.setattr(
        gmail_service,
        "connection_status",
        lambda db: {"connected": True, "send_mode": "live_gmail"},
    )
    queries = []

    def inbox_reply(db, query, max_results=20):
        queries.append(query)
        return [{
            "id": "reply-poll-message",
            "from": lead["email"],
            "snippet": "Thanks, I am interested in learning more.",
            "body": "Thanks, I am interested in learning more.",
            "subject": "Re: partnership",
            "internal_date": str(int(datetime.now().timestamp() * 1000)),
        }]

    monkeypatch.setattr(gmail_service, "list_recent_inbox", inbox_reply)
    result = client.post("/api/v1/outreach/jobs/poll-replies")
    assert result.status_code == 200
    assert len(result.json()["detected"]) == 1
    assert result.json()["detected"][0]["classification"] == "Interested"
    assert queries and "after:" in queries[0]
    influencer = client.get(f"/api/v1/influencers/{lead['id']}").json()
    assert influencer["status"] == LeadStatus.INTERESTED.value


def test_manual_sheet_sync_preserves_latest_outreach_metadata(client, tmp_path):
    lead = _create_lead(client, "sheets_outreach_creator", "sheetsoutreach@creators.test")
    created = _campaign(client, [lead["id"]]).json()
    email = created["emails"][0]
    client.post(f"/api/v1/outreach/emails/{email['id']}/approve")
    client.post("/api/v1/outreach/send", json={"email_ids": [email["id"]]})

    sync = client.post(
        "/api/v1/sheets/sync",
        json={"influencer_ids": [lead["id"]]},
    )
    assert sync.status_code == 200
    with open(tmp_path / "google_sheets_synced_export.csv", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1
    assert rows[0]["Latest Outreach Campaign"] == "Lumen Skin outreach"
    assert rows[0]["Latest Email Subject"] == email["subject"]
    assert rows[0]["Latest Email Status"] == "Email Sent"
    assert rows[0]["Latest Email Sent At"] != "N/A"


def test_gmail_status_is_simulated_without_oauth(client):
    res = client.get("/api/v1/gmail/status")
    assert res.status_code == 200
    data = res.json()
    assert data["connected"] is False
    assert data["send_mode"] == "simulated"


def test_forced_followup_timing_is_demo_only(client, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    response = client.post("/api/v1/outreach/jobs/process-due?force=true")
    assert response.status_code == 400
