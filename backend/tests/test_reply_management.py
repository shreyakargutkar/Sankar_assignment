import csv
from datetime import datetime, timezone

from app.models.influencer import LeadStatus
from app.services.gmail_service import gmail_service
from app.services.reply_manager import ReplyManager


def _create_lead(client, username):
    response = client.post(
        "/api/v1/influencers",
        json={
            "name": "Maya Chen",
            "instagram_username": username,
            "niche": "Fashion",
            "followers_count": 42000,
            "email": f"{username}@creators.test",
            "location": "Los Angeles",
        },
    )
    assert response.status_code == 201
    return response.json()


def _send_initial(client, username):
    lead = _create_lead(client, username)
    campaign = client.post(
        "/api/v1/outreach/campaigns",
        json={
            "brand_name": "Lumen Skin",
            "campaign_description": "Clean skincare launch with honest creator reviews.",
            "collaboration_offer": "Paid reel and story collaboration",
            "call_to_action": "Reply to discuss a brief.",
            "sender_name": "Jordan Lee, Partnerships",
            "influencer_ids": [lead["id"]],
        },
    ).json()
    initial = campaign["emails"][0]
    client.post(f"/api/v1/outreach/emails/{initial['id']}/approve")
    sent = client.post(
        "/api/v1/outreach/send",
        json={"email_ids": [initial["id"]]},
    ).json()["sent"][0]
    return lead, campaign, initial, sent


def test_demo_classifier_covers_all_required_reply_categories():
    cases = {
        "I am interested in learning more": "Interested",
        "Thanks, but I am not interested": "Not Interested",
        "Could you send your budget and pricing?": "Pricing Enquiry",
        "Please send the collaboration brief and deliverables": "Collaboration Request",
        "What is the campaign about?": "General Query",
        "Please unsubscribe and stop emailing me": "Opt-out",
    }
    for text, expected in cases.items():
        assert ReplyManager._classify_demo("", text)["classification"] == expected


def test_reply_requires_approval_and_records_complete_conversation(client, tmp_path):
    lead, campaign, initial, sent = _send_initial(client, "phase3_pricing")
    incoming = client.post(
        "/api/v1/outreach/demo/incoming-reply",
        json={
            "email_id": initial["id"],
            "body": "Could you share the budget and pricing for this collaboration?",
        },
    )
    assert incoming.status_code == 200
    reply = incoming.json()["reply"]
    assert reply["classification"] == "Pricing Enquiry"
    assert reply["status"] == "pending_approval"
    assert reply["draft_subject"]
    assert "budget" in reply["draft_body"].lower()

    influencer = client.get(f"/api/v1/influencers/{lead['id']}").json()
    assert influencer["status"] == LeadStatus.PRICING_ENQUIRY.value
    assert influencer["opted_out"] is False
    due = client.post("/api/v1/outreach/jobs/process-due?force=true").json()
    assert all(email["influencer_id"] != lead["id"] for email in due["created"])

    unapproved = client.post(
        "/api/v1/outreach/send-replies",
        json={"reply_ids": [reply["id"]]},
    ).json()
    assert unapproved["sent"] == []

    approved = client.post(f"/api/v1/outreach/replies/{reply['id']}/approve")
    assert approved.status_code == 200
    edited = client.patch(
        f"/api/v1/outreach/replies/{reply['id']}",
        json={"body": reply["draft_body"] + "\nOne more question."},
    )
    assert edited.json()["status"] == "pending_approval"
    assert edited.json()["human_approved"] is False
    assert client.post(
        "/api/v1/outreach/send-replies",
        json={"reply_ids": [reply["id"]]},
    ).json()["sent"] == []

    client.post(f"/api/v1/outreach/replies/{reply['id']}/approve")
    sent_reply = client.post(
        "/api/v1/outreach/send-replies",
        json={"reply_ids": [reply["id"]]},
    )
    assert sent_reply.status_code == 200
    assert sent_reply.json()["sent"][0]["send_mode"] == "simulated"

    history = client.get(f"/api/v1/outreach/conversations/{lead['id']}").json()["messages"]
    assert [message["direction"] for message in history] == ["outbound", "inbound", "outbound"]
    assert history[0]["body"] == initial["body"]
    assert history[-1]["body"].endswith("One more question.")

    analytics = client.get(
        f"/api/v1/outreach/analytics?campaign_id={campaign['campaign']['id']}"
    ).json()
    assert analytics["total_influencers_researched"] == 1
    assert analytics["emails_sent"] == 1
    assert analytics["replies_received"] == 1
    assert analytics["reply_rate"] == 1
    assert analytics["emails_delivered"] is None
    assert analytics["delivery_information_available"] is False

    with open(tmp_path / "google_sheets_synced_export.csv", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1
    assert rows[0]["Latest Reply Classification"] == "Pricing Enquiry"


def test_opt_out_reply_suppresses_contact_without_reply_draft(client):
    lead, _campaign, initial, _sent = _send_initial(client, "phase3_optout")
    incoming = client.post(
        "/api/v1/outreach/demo/incoming-reply",
        json={
            "email_id": initial["id"],
            "body": "Please unsubscribe me and stop emailing me.",
        },
    )
    assert incoming.status_code == 200
    reply = incoming.json()["reply"]
    assert reply["classification"] == "Opt-out"
    assert reply["status"] == "no_reply_required"
    assert reply["draft_body"] is None

    influencer = client.get(f"/api/v1/influencers/{lead['id']}").json()
    assert influencer["opted_out"] is True
    assert influencer["status"] == LeadStatus.NOT_INTERESTED.value
    assert client.post(
        f"/api/v1/outreach/replies/{reply['id']}/approve"
    ).status_code == 400


def test_opt_out_blocks_previously_approved_ai_reply(client):
    lead, _campaign, initial, _sent = _send_initial(client, "phase3_approved_then_optout")
    first_reply = client.post(
        "/api/v1/outreach/demo/incoming-reply",
        json={"email_id": initial["id"], "body": "I am interested in learning more."},
    ).json()["reply"]
    assert client.post(f"/api/v1/outreach/replies/{first_reply['id']}/approve").status_code == 200

    opt_out = client.post(
        "/api/v1/outreach/demo/incoming-reply",
        json={
            "email_id": initial["id"],
            "body": "Please unsubscribe me and stop emailing me.",
        },
    )
    assert opt_out.json()["reply"]["classification"] == "Opt-out"

    result = client.post(
        "/api/v1/outreach/send-replies",
        json={"reply_ids": [first_reply["id"]]},
    )
    assert result.status_code == 200
    assert result.json()["sent"] == []
    assert result.json()["skipped"] == [{
        "reply_id": first_reply["id"],
        "reason": "influencer_opted_out",
    }]
    stored = client.get("/api/v1/outreach/replies").json()["replies"]
    assert next(reply for reply in stored if reply["id"] == first_reply["id"])["status"] == "no_reply_required"


def test_gmail_poll_detects_and_deduplicates_influencer_replies(client, monkeypatch):
    lead, _campaign, initial, _sent = _send_initial(client, "phase3_gmail_poll")
    monkeypatch.setattr(
        gmail_service,
        "connection_status",
        lambda db: {"connected": True, "send_mode": "live_gmail"},
    )
    received = int(datetime.now(timezone.utc).timestamp() * 1000)
    calls = []

    def list_inbox(db, query, max_results=20):
        calls.append(query)
        return [{
            "id": "gmail-inbound-001",
            "threadId": "thread-demo",
            "from": lead["email"],
            "subject": f"Re: {initial['subject']}",
            "body": "Please share your rate card and campaign budget.",
            "snippet": "Please share your rate card",
            "internal_date": str(received),
            "rfc822_message_id": "<inbound-001@example.test>",
        }]

    monkeypatch.setattr(gmail_service, "list_recent_inbox", list_inbox)
    first = client.post("/api/v1/outreach/jobs/poll-replies")
    assert first.status_code == 200
    assert len(first.json()["detected"]) == 1
    assert first.json()["detected"][0]["classification"] == "Pricing Enquiry"
    assert calls and "from:phase3_gmail_poll@creators.test" in calls[0]

    second = client.post("/api/v1/outreach/jobs/poll-replies")
    assert second.status_code == 200
    assert second.json()["detected"] == []
    assert client.get("/api/v1/outreach/replies").json()["replies"] and len(
        client.get("/api/v1/outreach/replies").json()["replies"]
    ) == 1


def test_inbox_stopping_conditions_cancel_already_queued_followups(client):
    lead, _campaign, initial, _sent = _send_initial(client, "phase3_followup_stop")
    queued = client.post("/api/v1/outreach/jobs/process-due?force=true").json()["created"]
    followup = next(email for email in queued if email["sequence_number"] == 1)

    incoming = client.post(
        "/api/v1/outreach/demo/incoming-reply",
        json={"email_id": initial["id"], "body": "Thanks, this sounds interesting."},
    )
    assert incoming.status_code == 200
    follow = client.get("/api/v1/outreach/emails").json()["emails"]
    assert next(email for email in follow if email["id"] == followup["id"])["status"] == "cancelled"
    assert client.post(
        f"/api/v1/outreach/emails/{followup['id']}/approve"
    ).status_code == 400


def test_gmail_reply_is_saved_and_followups_stop_when_ai_fails(client, monkeypatch):
    lead, _campaign, initial, _sent = _send_initial(client, "phase3_ai_failure")
    followup = client.post("/api/v1/outreach/jobs/process-due?force=true").json()["created"][0]
    monkeypatch.setattr(
        gmail_service,
        "connection_status",
        lambda db: {"connected": True, "send_mode": "live_gmail"},
    )
    monkeypatch.setattr(
        gmail_service,
        "list_recent_inbox",
        lambda db, query, max_results=20: [{
            "id": "ai-failure-inbound",
            "from": lead["email"],
            "subject": "Re: collaboration",
            "body": "I have a question about the proposed scope.",
            "internal_date": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
        }],
    )

    async def fail_classification(*args, **kwargs):
        raise RuntimeError("Claude unavailable")

    from app.services.reply_manager import reply_manager

    monkeypatch.setattr(reply_manager, "classify", fail_classification)
    polled = client.post("/api/v1/outreach/jobs/poll-replies")
    assert polled.status_code == 200
    saved_reply = polled.json()["detected"][0]
    assert saved_reply["status"] == "failed"
    assert "Claude unavailable" in saved_reply["error_message"]
    assert saved_reply["body"] == "I have a question about the proposed scope."
    assert client.get(f"/api/v1/influencers/{lead['id']}").json()["status"] == LeadStatus.REPLIED.value

    emails = client.get("/api/v1/outreach/emails").json()["emails"]
    assert next(email for email in emails if email["id"] == followup["id"])["status"] == "cancelled"
