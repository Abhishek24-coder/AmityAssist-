"""
End-to-end chat conversation tests and withdrawal flow tests.

Double-validation:
  Round 1 — Full happy path: verify → reason → suggestion → confirm → DONE
  Round 2 — Cancel flow + invalid session handling + CONFIRM/CANCEL guard
"""

import pytest


def _verify_student(client, student_id="STU003"):
    """Helper: verify a student and return the session_id."""
    resp = client.post("/api/auth/verify", json={"student_id": student_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is True
    return data["session_id"]


class TestFullWithdrawalFlow:
    """Round 1 — Happy path: reason → suggest → confirm → DONE."""

    def test_step1_ask_reason_state(self, client):
        """After sending the withdrawal reason, state should advance to SUGGEST."""
        session_id = _verify_student(client, "STU004")
        resp = client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "I cannot afford my tuition fees this semester"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "SUGGEST"
        assert data["intent"] == "financial"
        assert data["sentiment"] is not None
        # Bot must offer financial alternatives
        assert "bursary" in data["reply"].lower() or "payment" in data["reply"].lower()

    def test_step2_decline_alternatives_moves_to_confirm(self, client):
        """Saying 'no' to alternatives should move state to CONFIRM."""
        session_id = _verify_student(client, "STU005")
        # Step 1: send reason
        client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "I am failing all my exams and cannot keep up"},
        )
        # Step 2: decline suggestion
        resp = client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "No, I have decided to withdraw"},
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "CONFIRM"

    def test_step3_confirm_submits_withdrawal(self, client):
        """Typing CONFIRM should create a withdrawal record and return state=DONE."""
        session_id = _verify_student(client, "STU006")
        client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "family emergency, need to go home"},
        )
        client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "no thanks"},
        )
        resp = client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "CONFIRM"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "DONE"
        assert data["withdrawal_submitted"] is True
        assert ("AMITY-WTH-" in data["reply"] or "WD-" in data["reply"])

    def test_withdrawal_record_stored_in_db(self, client):
        """After CONFIRM the withdrawal_requests table must contain the record."""
        from backend.database.connection import get_connection

        session_id = _verify_student(client, "STU007")
        client.post("/api/chat/message", json={"session_id": session_id, "message": "I got a good job offer"})
        client.post("/api/chat/message", json={"session_id": session_id, "message": "no"})
        client.post("/api/chat/message", json={"session_id": session_id, "message": "CONFIRM"})

        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM withdrawal_requests WHERE student_id = ? ORDER BY id DESC LIMIT 1",
            ("STU007",),
        ).fetchone()
        assert row is not None
        assert row["status"] == "pending"
        assert row["detected_intent"] == "career"


class TestCancelAndGuardFlows:
    """Round 2 — Cancel flow, invalid session, and input resilience."""

    def test_cancel_at_confirm_stage_resets_to_ask_reason(self, client):
        """Typing CANCEL must abort withdrawal and reset to ASK_REASON."""
        session_id = _verify_student(client, "STU008")
        client.post("/api/chat/message", json={"session_id": session_id, "message": "cannot afford fees"})
        client.post("/api/chat/message", json={"session_id": session_id, "message": "nope"})
        resp = client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "CANCEL"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "ASK_REASON"
        assert "cancelled" in data["reply"].lower()

    def test_invalid_session_returns_401(self, client):
        """A fabricated / expired session_id must return HTTP 401."""
        resp = client.post(
            "/api/chat/message",
            json={"session_id": "x" * 32, "message": "hello"},
        )
        assert resp.status_code == 401

    def test_invalid_confirm_keyword_stays_at_confirm(self, client):
        """Any message other than CONFIRM or CANCEL must keep state at CONFIRM."""
        session_id = _verify_student(client, "STU009")
        client.post("/api/chat/message", json={"session_id": session_id, "message": "sick, hospital"})
        client.post("/api/chat/message", json={"session_id": session_id, "message": "no"})
        resp = client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "maybe"},
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "CONFIRM"

    def test_accept_alternatives_resolves_session(self, client):
        """Saying 'yes' to alternatives should mark the session as RESOLVED."""
        session_id = _verify_student(client, "STU010")
        client.post("/api/chat/message", json={"session_id": session_id, "message": "struggling financially"})
        resp = client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "yes please, I would like to try that"},
        )
        assert resp.status_code == 200
        assert resp.json()["state"] == "RESOLVED"

    def test_empty_message_rejected_by_schema(self, client):
        """An empty or whitespace-only message must fail schema validation."""
        session_id = _verify_student(client, "STU001")
        resp = client.post(
            "/api/chat/message",
            json={"session_id": session_id, "message": "   "},
        )
        assert resp.status_code == 422
