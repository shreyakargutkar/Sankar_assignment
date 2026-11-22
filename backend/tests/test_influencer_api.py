import csv

from app.models.influencer import LeadStatus


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_create_and_deduplicate_influencer(client):
    payload = {
        "name": "Sarah Connor",
        "instagram_username": "sarah_tech24",
        "profile_url": "https://instagram.com/sarah_tech24",
        "niche": "Tech & AI",
        "followers_count": 50000,
        "email": "sarah@futuretech.com",
        "location": "San Francisco, USA"
    }

    response = client.post("/api/v1/influencers", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["instagram_username"] == "sarah_tech24"
    assert created["status"] == LeadStatus.EMAIL_AVAILABLE.value

    duplicate_payload = {
        "name": "Sarah Connor Duplicate",
        "instagram_username": "@sarah_tech24",
        "profile_url": "https://instagram.com/sarah_tech24/",
        "niche": "Tech & AI",
        "followers_count": 55000,
        "email": "sarah2@futuretech.com",
        "location": "San Francisco, USA"
    }
    dup_res = client.post("/api/v1/influencers", json=duplicate_payload)
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"]


def test_update_lead_status(client):
    payload = {
        "name": "Marcus Kane",
        "instagram_username": "marcus_kane",
        "niche": "Fitness",
        "followers_count": 25000,
        "email": "marcus@fitness.io",
        "location": "Austin, USA"
    }
    res = client.post("/api/v1/influencers", json=payload)
    assert res.status_code == 201
    inf_id = res.json()["id"]

    update_res = client.put(f"/api/v1/influencers/{inf_id}/status", json={"status": "Collaboration Confirmed"})
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "Collaboration Confirmed"


def test_campaign_discovery_and_ai_analysis(client):
    search_payload = {
        "brand_name": "NovaFlow SaaS",
        "campaign_description": "Launch of our new generative workflow tool targeting developers and tech enthusiasts.",
        "influencer_niche": "Tech & AI",
        "target_location": "United States",
        "min_followers": 10000,
        "max_followers": 250000,
        "relevant_keywords": "saas, productivity, ai tools",
        "auto_analyze_with_ai": True,
        "limit": 4
    }

    res = client.post("/api/v1/discovery/search", json=search_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["influencers"]) > 0

    first = data["influencers"][0]
    assert first["suitability_score"] is not None
    assert 0 <= first["suitability_score"] <= 100
    assert len(first["profile_summary"]) > 0
    assert len(first["match_reason"]) > 0


def test_google_sheets_sync_fallback(client, tmp_path):
    payload = {
        "name": "Chloe Vogue",
        "instagram_username": "chloevogue_chic",
        "niche": "Fashion",
        "followers_count": 75000,
        "email": "collabs@chloevogue.com",
        "location": "Paris, France"
    }
    client.post("/api/v1/influencers", json=payload)

    sync_res = client.post("/api/v1/sheets/sync", json={})
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["success"] is True
    assert sync_data["synced_count"] >= 1

    client.post("/api/v1/sheets/sync", json={})
    with open(tmp_path / "google_sheets_synced_export.csv", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1
