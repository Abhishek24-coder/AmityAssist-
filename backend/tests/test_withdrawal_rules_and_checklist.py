"""
Tests for single-active withdrawal constraint and staff dossier checklist interactivity.
"""

import pytest
from backend.database.connection import get_connection
from backend.security.jwt import create_access_token


def _admin_headers(client=None):
    token = create_access_token(subject="REG001", role="Registrar")
    return {"Authorization": f"Bearer {token}"}


class TestWithdrawalRulesAndChecklist:
    def test_guest_withdrawal_application_is_rejected(self, client):
        """Guest, anonymous or empty student ID cannot apply for withdrawal."""
        res = client.post(
            "/api/withdrawal/apply",
            json={"student_id": "GUEST", "reason": "Attempting as guest"},
        )
        assert res.status_code == 401

        res2 = client.post(
            "/api/withdrawal/apply",
            json={"student_id": "NON_EXISTENT_999", "reason": "Invalid student"},
        )
        assert res2.status_code == 404

    def test_single_active_withdrawal_request_enforced(self, client):
        """Student cannot submit a second withdrawal request while one is active."""
        # Use STU004 for this test
        conn = get_connection()
        conn.execute("DELETE FROM withdrawal_requests WHERE UPPER(student_id) = 'STU004'")
        conn.commit()

        # First request succeeds
        res1 = client.post(
            "/api/withdrawal/apply",
            json={"student_id": "STU004", "reason": "First application"},
        )
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["success"] is True
        ref1 = data1["reference_no"]

        # Second request must be rejected with 400
        res2 = client.post(
            "/api/withdrawal/apply",
            json={"student_id": "STU004", "reason": "Second application while active"},
        )
        assert res2.status_code == 400
        assert "already in progress" in res2.json()["detail"].lower()

    def test_staff_checklist_toggle_and_verify_all(self, client):
        """Staff can interactively toggle checklist items and verify all."""
        # Find STU004's active request id
        conn = get_connection()
        row = conn.execute(
            "SELECT id FROM withdrawal_requests WHERE UPPER(student_id) = 'STU004' ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        assert row is not None
        req_id = row["id"]

        headers = _admin_headers(client)

        # Fetch review details
        details_res = client.get(f"/api/admin/requests/{req_id}/review-details", headers=headers)
        assert details_res.status_code == 200
        details = details_res.json()
        checklist = details["checklist"]
        assert len(checklist) > 0
        first_item = checklist[0]
        item_id = first_item["id"]

        # Staff checks item -> completed
        update_res = client.post(
            f"/api/admin/requests/{req_id}/checklist/{item_id}",
            json={"status": "completed"},
            headers=headers,
        )
        assert update_res.status_code == 200
        assert update_res.json()["status"] == "verified"

        # Verify DB updated
        c_row = conn.execute("SELECT status FROM withdrawal_checklist_items WHERE id = ?", (item_id,)).fetchone()
        assert c_row["status"] == "verified"

        # Staff unchecks item -> pending
        uncheck_res = client.post(
            f"/api/admin/requests/{req_id}/checklist/{item_id}",
            json={"status": "pending"},
            headers=headers,
        )
        assert uncheck_res.status_code == 200
        assert uncheck_res.json()["status"] == "pending"

        # Staff clicks Verify All
        verify_all_res = client.post(
            f"/api/admin/requests/{req_id}/checklist/verify-all",
            headers=headers,
        )
        assert verify_all_res.status_code == 200

        all_items = conn.execute("SELECT status FROM withdrawal_checklist_items WHERE request_id = ?", (req_id,)).fetchall()
        for item in all_items:
            assert item["status"] == "verified"
