"""Tests for Phase 29: Intelligent Search & Policy Guidance (SQLite FTS5 / Hybrid RAG & Voice)."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.policy_search_service import PolicySearchService


class TestPolicyFTSAndGuidance:
    """Test suite verifying FTS5 indexing, BM25 ranking, and personalized hybrid RAG advice."""

    def test_fts5_index_and_bm25_search(self, client: TestClient):
        """Verify FTS5 virtual table queries return ranked results with highlighted snippets."""
        results = PolicySearchService.search_policies("attendance condonation", limit=5)
        assert len(results) > 0
        top = results[0]
        assert "ORD-ACAD-7.2" == top["clause_code"]
        assert top["score"] is not None
        assert "snippet" in top
        assert "attendance" in top["snippet"].lower()

    def test_search_endpoint_returns_valid_json(self, client: TestClient):
        """Verify GET /api/policy/search returns sub-5ms BM25 matches."""
        resp = client.get("/api/policy/search?q=withdrawal+refund")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] > 0
        clauses = [r["clause_code"] for r in data["results"]]
        assert "ORD-WTH-14.1" in clauses

    def test_search_offset_policy(self, client: TestClient):
        """Verify searching for lost ID or offset yields the smart offset ordinance."""
        resp = client.get("/api/policy/search?q=offset+caution+deposit")
        assert resp.status_code == 200
        data = resp.json()
        assert any("ORD-FIN-14.4" == r["clause_code"] for r in data["results"])

    def test_category_filter(self, client: TestClient):
        """Verify filtering by category works as expected."""
        resp = client.get("/api/policy/search?q=examination&category=Examinations")
        assert resp.status_code == 200
        data = resp.json()
        assert all(r["category"] == "Examinations" for r in data["results"])

    def test_categories_and_clause_lookup(self, client: TestClient):
        """Verify listing categories and looking up an exact clause code."""
        cat_resp = client.get("/api/policy/categories")
        assert cat_resp.status_code == 200
        assert "Academics" in cat_resp.json()["categories"]

        clause_resp = client.get("/api/policy/ORD-ACAD-7.2")
        assert clause_resp.status_code == 200
        assert clause_resp.json()["clause_code"] == "ORD-ACAD-7.2"

        notFound = client.get("/api/policy/ORD-NONEXISTENT")
        assert notFound.status_code == 404

    def test_personalized_attendance_guidance_for_shortfall_student(self, client: TestClient):
        """Verify hybrid RAG personalizes advice based on student's attendance."""
        # STU001 has 82.5% attendance -> meets cutoff
        resp1 = client.post(
            "/api/policy/guide",
            json={"query": "Can I write semester exams with my current attendance?", "student_id": "STU001"},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert "ORD-ACAD-7.2" in [c["clause_code"] for c in data1["citations"]]
        assert "82.5%" in data1["answer"]
        assert "meets the 75% cutoff" in data1["answer"]

        # STU002 has 68.0% attendance -> eligible for Dean Condonation with Form AC-04
        resp2 = client.post(
            "/api/policy/guide",
            json={"query": "Can I write semester exams with my current attendance?", "student_id": "STU002"},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert "ORD-ACAD-7.2" in [c["clause_code"] for c in data2["citations"]]
        assert "68.0%" in data2["answer"]
        assert "Form AC-04" in data2["answer"] or "Condonation" in data2["answer"]

    def test_personalized_withdrawal_and_offset_guidance(self, client: TestClient):
        """Verify hybrid RAG provides exact ordinance answers for withdrawal and offset questions."""
        payload = {
            "query": "Can I offset my lost ID card 200 rupee fine from caution deposit?",
            "student_id": "STU001",
        }
        resp = client.post("/api/policy/guide", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "ORD-FIN-14.4" in [c["clause_code"] for c in data["citations"]]
        assert "200" in data["answer"]
        assert "caution deposit" in data["answer"].lower()

    def test_voice_query_endpoint(self, client: TestClient):
        """Verify POST /api/voice/query delivers voice speech text and audio parameters."""
        payload = {
            "spoken_text": "How do I apply for dean condonation for attendance shortage?",
            "student_id": "STU001",
            "language": "en-IN",
        }
        resp = client.post("/api/voice/query", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["transcription"] == payload["spoken_text"]
        assert "speech_text" in data
        assert "speech_params" in data
        assert data["speech_params"]["lang"] == "en-IN"
        assert len(data["citations"]) > 0
