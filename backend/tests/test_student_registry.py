"""
Tests for Phase 24: Centralized Real-Time Student Status Registry.
Verifies operational statuses (ACTIVE, SUSPENDED, DEBARRED),
entry & kiosk access locks, tamper-evident status audit trails, and faculty roster warning flags.
"""

import pytest


class TestStudentRegistry:
    def test_default_student_status_is_active_and_permitted(self, client):
        """Active student has entry permitted and kiosk access unhindered."""
        res = client.get("/api/registry/status/STU001")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == "STU001"
        assert data["status"] == "ACTIVE"
        assert data["entry_permitted"] is True
        assert data["attendance_permitted"] is True
        assert data["kiosk_restricted"] is False
        assert data["lock_reason"] is None

    def test_update_status_to_suspended_locks_access(self, client):
        """Updating status to SUSPENDED records audit entry and locks campus access."""
        update_payload = {
            "student_id": "STU002",
            "new_status": "SUSPENDED",
            "reason": "14-day disciplinary suspension for examination malpractice in Mid-Terms",
            "updated_by": "PROCTOR_BOARD_OFFICER_01",
        }
        update_res = client.post("/api/registry/status/update", json=update_payload)
        assert update_res.status_code == 200
        data = update_res.json()["student"]
        assert data["status"] == "SUSPENDED"
        assert data["entry_permitted"] is False
        assert data["attendance_permitted"] is False
        assert data["kiosk_restricted"] is True
        assert "malpractice" in data["lock_reason"]
        assert "Proctorial Board Office" in data["alert_action"]

        # Cross-check auth endpoint reflects the lock
        verify_res = client.post("/api/auth/verify", json={"student_id": "STU002"})
        assert verify_res.status_code == 200
        auth_data = verify_res.json()
        assert auth_data["status"] == "SUSPENDED"
        assert auth_data["kiosk_restricted"] is True
        assert "malpractice" in auth_data["lock_reason"]

    def test_status_audit_history_recorded(self, client):
        """Status modifications create tamper-evident history entries."""
        # STU002 was updated in previous test; verify history exists
        hist_res = client.get("/api/registry/history/STU002")
        assert hist_res.status_code == 200
        hist_data = hist_res.json()
        assert hist_data["total"] >= 1
        entry = hist_data["history"][0]
        assert entry["previous_status"] == "ACTIVE"
        assert entry["new_status"] == "SUSPENDED"
        assert entry["updated_by"] == "PROCTOR_BOARD_OFFICER_01"

    def test_faculty_roster_highlights_suspended_students(self, client):
        """Faculty roster highlights suspended students with attendance_locked=True and RED badge."""
        roster_res = client.get("/api/registry/roster/ECE")
        assert roster_res.status_code == 200
        roster_data = roster_res.json()
        assert roster_data["total_enrolled"] >= 1
        assert roster_data["suspended_count"] >= 1

        stu002_entry = next((s for s in roster_data["roster"] if s["id"] == "STU002"), None)
        assert stu002_entry is not None
        assert stu002_entry["attendance_locked"] is True
        assert stu002_entry["badge_color"] == "RED"
        assert stu002_entry["status"] == "SUSPENDED"

    def test_invalid_status_rejected(self, client):
        """Reject undefined status codes."""
        res = client.post(
            "/api/registry/status/update",
            json={
                "student_id": "STU001",
                "new_status": "EXPELLED_TEMPORARY",  # Invalid
                "reason": "Test reason",
                "updated_by": "ADMIN",
            },
        )
        assert res.status_code == 400
        assert "Invalid status" in res.json()["detail"]
