import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_admin_policy_list():
    res = client.get("/api/policy/admin/list")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["count"] >= 12
    assert len(data["policies"]) >= 12

def test_admin_policy_upsert_and_fts_retrieval():
    payload = {
        "doc_id": "POL-TEST-WIFI-01",
        "category": "Campus IT",
        "title": "Campus High-Speed 5G WiFi Policy",
        "clause_code": "ORD-IT-55.2",
        "content": "All registered students and faculty get unlimited high-speed 5G Wi-Fi across campus hostels and libraries with student credentials.",
        "action_url": "/forms",
        "action_label": "Register MAC Address"
    }
    save_res = client.post("/api/policy/admin/save", json=payload)
    assert save_res.status_code == 200
    assert save_res.json()["status"] == "success"

    # FTS5 search verification
    search_res = client.get("/api/policy/search?q=5G+WiFi")
    assert search_res.status_code == 200
    results = search_res.json()["results"]
    assert any(r["doc_id"] == "POL-TEST-WIFI-01" for r in results)

    # Hybrid Guidance citation verification
    guide_res = client.post("/api/policy/guide", json={"query": "how to connect 5G wifi", "language": "en-IN"})
    assert guide_res.status_code == 200
    citations = [c["clause_code"] for c in guide_res.json().get("citations", [])]
    assert "ORD-IT-55.2" in citations

    # Clean up
    del_res = client.delete("/api/policy/admin/POL-TEST-WIFI-01")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"
