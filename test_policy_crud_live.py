import os
import sys
from fastapi.testclient import TestClient

# Ensure backend can be imported
sys.path.insert(0, os.path.abspath("."))
from backend.main import app

client = TestClient(app)

def test_policy_crud():
    print("--- 1. Testing GET /api/policy/admin/list ---")
    res = client.get("/api/policy/admin/list")
    assert res.status_code == 200, f"Failed: {res.text}"
    data = res.json()
    print(f"Total seeded policies: {data['count']}")
    assert data["count"] >= 12, "Should have at least 12 policies"

    print("\n--- 2. Creating a brand new custom policy via POST /api/policy/admin/save ---")
    custom_policy = {
        "doc_id": "POL-CUSTOM-AI-01",
        "category": "Artificial Intelligence",
        "title": "Student AI Lab & Robotics Access Ordinance",
        "clause_code": "ORD-AI-99.1",
        "content": "Students registered in computer science and robotics courses have 24/7 biometric access to High Performance AI Computing Cluster. GPU allocation requires faculty approval.",
        "action_url": "/forms",
        "action_label": "Apply AI Lab Access"
    }
    save_res = client.post("/api/policy/admin/save", json=custom_policy)
    assert save_res.status_code == 200, f"Save failed: {save_res.text}"
    print(f"Custom policy saved: {save_res.json()['message']}")

    print("\n--- 3. Testing FTS5 BM25 search for the newly added custom policy ---")
    search_res = client.get("/api/policy/search?q=robotics+GPU+allocation")
    assert search_res.status_code == 200
    search_data = search_res.json()
    print(f"Search results found: {search_data['count']}")
    assert search_data["count"] > 0, "FTS5 should immediately find the new policy!"
    found_doc = search_data["results"][0]
    print(f"Found doc_id: {found_doc['doc_id']}, title: {found_doc['title']}")
    assert found_doc["doc_id"] == "POL-CUSTOM-AI-01"

    print("\n--- 4. Testing AI Hybrid Guidance retrieval for the new policy ---")
    guide_res = client.post("/api/policy/guide", json={"query": "how can i get access to AI robotics GPU lab", "language": "en-IN"})
    assert guide_res.status_code == 200
    guide_data = guide_res.json()
    print("AI Retrieved citations:", [c["clause_code"] for c in guide_data.get("citations", [])])
    assert any(c.get("clause_code") == "ORD-AI-99.1" for c in guide_data.get("citations", [])), "AI must automatically cite ORD-AI-99.1!"
    print(f"AI Recommended action: {guide_data.get('recommended_action')}")

    print("\n--- 5. Testing DELETE /api/policy/admin/POL-CUSTOM-AI-01 ---")
    del_res = client.delete("/api/policy/admin/POL-CUSTOM-AI-01")
    assert del_res.status_code == 200
    print(f"Delete response: {del_res.json()}")

    # Verify search no longer returns it
    post_del_search = client.get("/api/policy/search?q=robotics+GPU+allocation")
    assert post_del_search.json()["count"] == 0, "Policy should be deleted from FTS5 index"

    print("\nALL POLICY CRUD & REAL-TIME AI RETRIEVAL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_policy_crud()
