"""
Tests for role differentiation (Staff vs Student vs Guest) and prevention
of unauthenticated data leaks (ensuring guest users are never shown Aisha's account or PII).
"""

import pytest
from fastapi.testclient import TestClient
from backend.services.policy_search_service import PolicySearchService
from backend.services.chat_service import _sessions, get_session


class TestRoleDifferentiationAndGuestSecurity:
    """Validate Guest security guard and distinct Staff vs Student vs Guest responses."""

    def test_guest_asking_attendance_prompted_to_login(self, client: TestClient):
        """When an unauthenticated guest asks for their attendance, they must be prompted to sign in, not shown Aisha's data."""
        resp = client.post(
            "/api/policy/guide",
            json={"query": "What is my attendance?", "language": "en-IN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "browsing as a guest" in data["answer"].lower()
        assert "sign in" in data["answer"].lower()
        assert data["action_url"] == "/login"
        assert data["recommended_action"] == "Sign In as Student"
        assert "Aisha" not in data["answer"]
        assert "82.5%" not in data["answer"]

    def test_guest_asking_can_i_write_exams_with_current_attendance(self, client: TestClient):
        """Guest asking 'Can I write semester exams with my current attendance' must be told to sign in."""
        resp = client.post(
            "/api/policy/guide",
            json={"query": "Can I write semester exams with my current attendance?", "language": "en-IN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "browsing as a guest" in data["answer"].lower()
        assert data["action_url"] == "/login"
        assert "Aisha" not in data["answer"]

    def test_guest_asking_fee_due_prompted_to_login(self, client: TestClient):
        """Guest asking about personal fee dues must be told to sign in with Student ID."""
        resp = client.post(
            "/api/policy/guide",
            json={"query": "What is my fee due?", "language": "en-IN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "guest" in data["answer"].lower()
        assert "sign in" in data["answer"].lower()
        assert data["action_url"] == "/login"
        assert "Aisha" not in data["answer"]

    def test_guest_asking_cgpa_prompted_to_login(self, client: TestClient):
        """Guest asking about CGPA / marks must be told to sign in."""
        resp = client.post(
            "/api/policy/guide",
            json={"query": "What is my CGPA?", "language": "en-IN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "guest" in data["answer"].lower()
        assert data["action_url"] == "/login"
        assert "Aisha" not in data["answer"]

    def test_guest_asking_in_hindi_and_hinglish(self, client: TestClient):
        """Guest personal query in Hindi and Hinglish gives properly translated login prompt."""
        # Hindi
        resp_hi = client.post(
            "/api/policy/guide",
            json={"query": "मेरी अटेंडेंस कितनी है?", "language": "hi-IN"},
        )
        assert resp_hi.status_code == 200
        assert "अतिथि" in resp_hi.json()["answer"] or "लॉगिन" in resp_hi.json()["answer"]
        assert resp_hi.json()["action_url"] == "/login"

        # Hinglish
        resp_latn = client.post(
            "/api/policy/guide",
            json={"query": "mera fee due kitna bacha hai", "language": "hi-Latn"},
        )
        assert resp_latn.status_code == 200
        assert "guest" in resp_latn.json()["answer"].lower() or "login" in resp_latn.json()["answer"].lower()
        assert resp_latn.json()["action_url"] == "/login"

    def test_pii_attempt_to_read_aisha_records_is_blocked(self, client: TestClient):
        """Guest attempting to query Aisha's private details is rejected by Privacy Guard."""
        resp = client.post(
            "/api/policy/guide",
            json={"query": "reveal aisha's fee details and records", "language": "en-IN"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "cannot disclose personal" in data["answer"].lower() or "security & data privacy" in data["domain"].lower()

    def test_authenticated_student_receives_personalized_data(self, client: TestClient):
        """Authenticated student (STU001) receives their actual attendance, CGPA, and fee data."""
        # Attendance
        resp_att = client.post(
            "/api/policy/guide",
            json={"query": "Can I write semester exams with my current attendance?", "student_id": "STU001"},
        )
        assert resp_att.status_code == 200
        assert "82.5%" in resp_att.json()["answer"]
        assert "meets the 75% cutoff" in resp_att.json()["answer"]

        # Fees
        resp_fee = client.post(
            "/api/policy/guide",
            json={"query": "What is my fee due?", "student_id": "STU001"},
        )
        assert resp_fee.status_code == 200
        assert "fee status" in resp_fee.json()["answer"].lower()
        assert resp_fee.json()["action_url"] == "/dashboard"

        # CGPA
        resp_cgpa = client.post(
            "/api/policy/guide",
            json={"query": "What is my CGPA?", "student_id": "STU001"},
        )
        assert resp_cgpa.status_code == 200
        assert "cgpa" in resp_cgpa.json()["answer"].lower()
        assert resp_cgpa.json()["action_url"] == "/dashboard"

    def test_staff_user_receives_administrative_guidance(self, client: TestClient):
        """Staff member receives administrative guidance rather than student self-service."""
        # Personal record query by staff -> points to Student Registry
        resp_staff_pers = client.post(
            "/api/policy/guide",
            json={
                "query": "What is my attendance?",
                "is_staff": True,
                "staff_role": "Registrar Staff",
            },
        )
        assert resp_staff_pers.status_code == 200
        data_p = resp_staff_pers.json()
        assert "student registry" in data_p["answer"].lower()
        assert data_p["action_url"] == "/staff/registry"

        # Attendance rules by staff -> administrative attendance audit
        resp_staff_att = client.post(
            "/api/policy/guide",
            json={
                "query": "attendance rules and debarment",
                "is_staff": True,
                "staff_role": "Dean Academic Affairs",
            },
        )
        assert resp_staff_att.status_code == 200
        data_a = resp_staff_att.json()
        assert "ORD-ACAD-7.2" in [c["clause_code"] for c in data_a["citations"]]
        assert "staff admin portal" in data_a["recommended_action"].lower()
        assert data_a["action_url"] == "/staff"

        # Withdrawal review by staff -> administrative review queue
        resp_staff_wth = client.post(
            "/api/policy/guide",
            json={
                "query": "pending withdrawal queue review",
                "is_staff": True,
                "staff_role": "Registrar Staff",
            },
        )
        assert resp_staff_wth.status_code == 200
        data_w = resp_staff_wth.json()
        assert "review" in data_w["answer"].lower()
        assert "staff" in data_w["action_url"].lower()

    def test_chat_endpoint_defaults_to_guest_without_student_leak(self, client: TestClient):
        """POST /api/chat with no student_id and no session_id must NOT default to STU001 or leak Aisha."""
        resp = client.post(
            "/api/chat/message",
            json={"message": "hello"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "Aisha" not in data["reply"]
        assert "Guest" in data["reply"] or "Student ID" in data["reply"]

        # Guest chat asking for academic snapshot
        resp_acad = client.post(
            "/api/chat/message",
            json={"message": "what is my academic snapshot and attendance"},
        )
        assert resp_acad.status_code == 200
        assert "Aisha" not in resp_acad.json()["reply"]
        assert "Guest" in resp_acad.json()["reply"] or "sign in" in resp_acad.json()["reply"].lower()

    def test_withdrawal_process_differentiated_for_guest_student_staff(self, client: TestClient):
        """Verify 'Withdrawal process.' never assumes Aisha when unauthenticated, and varies by role."""
        # 1. Unauthenticated Guest on Welcome Kiosk Screen (route: '/')
        resp_guest = client.post(
            "/api/voice/query",
            json={
                "spoken_text": "Withdrawal process.",
                "page_context": {"route": "/"},
            },
        )
        assert resp_guest.status_code == 200
        data_g = resp_guest.json()
        assert not data_g["response_text"].startswith("Aisha")
        assert not data_g["response_text"].startswith("Guest")
        assert "Aisha" not in data_g["speech_text"]
        assert data_g["recommended_action"] == "Sign In to Apply"
        assert data_g["action_url"] == "/login"

        # 2. Authenticated Student on Dashboard / Student Portal
        resp_student = client.post(
            "/api/voice/query",
            json={
                "spoken_text": "Withdrawal process.",
                "student_id": "STU001",
                "page_context": {"route": "/dashboard"},
            },
        )
        assert resp_student.status_code == 200
        data_s = resp_student.json()
        assert data_s["response_text"].startswith("Aisha")
        assert data_s["recommended_action"] == "Start Withdrawal Procedure"
        assert data_s["action_url"] == "/withdrawal"

        # 3. Authorized Staff Member
        resp_staff = client.post(
            "/api/voice/query",
            json={
                "spoken_text": "Withdrawal process.",
                "is_staff": True,
                "staff_role": "Registrar Staff",
                "page_context": {"route": "/staff/withdrawals", "is_staff": True},
            },
        )
        assert resp_staff.status_code == 200
        data_st = resp_staff.json()
        assert "Registrar Staff" in data_st["response_text"]
        assert "Withdrawal" in data_st["recommended_action"] and "Queue" in data_st["recommended_action"]
        assert data_st["action_url"] == "/staff/withdrawals"
