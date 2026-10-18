"""
Phase 19 tests: GDPR Compliance, Privacy Controls, and Audit Trail Management.
"""

import pytest


def _staff_headers(client, username="registrar_staff"):
    response = client.post("/api/auth/staff/login", json={"username": username})
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _student_headers(client, student_id="STU001"):
    response = client.post("/api/auth/login", json={"student_id": student_id})
    return {"Authorization": f"Bearer {response.json()['token']}"}


class TestPhase19Compliance:
    def test_export_student_data_structure(self, client):
        """Export must return complete portable JSON bundle for a valid student."""
        res = client.get("/api/compliance/export/STU001", headers=_student_headers(client, "STU001"))
        assert res.status_code == 200
        data = res.json()
        assert "export_metadata" in data
        assert data["export_metadata"]["student_id"] == "STU001"
        assert "student_profile" in data
        assert data["student_profile"]["id"] == "STU001"
        assert "conversations" in data
        assert "grievances" in data
        assert "scholarship_applications" in data
        assert "examinations" in data
        assert "workflows" in data
        assert "notifications" in data

    def test_export_nonexistent_student_returns_404(self, client):
        """Exporting unknown student returns 404."""
        # Nonexistent student token attempting to export non-existent record
        from backend.security.jwt import create_access_token
        token = create_access_token("NONEXISTENT999", "Student")
        res = client.get("/api/compliance/export/NONEXISTENT999", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 404

    def test_export_respects_student_token_isolation(self, client):
        """Student token cannot export another student's data."""
        stu1_headers = _student_headers(client, "STU001")
        # STU001 trying to access STU002's export
        res = client.get("/api/compliance/export/STU002", headers=stu1_headers)
        assert res.status_code == 403

        # STU001 accessing their own export succeeds
        res_own = client.get("/api/compliance/export/STU001", headers=stu1_headers)
        assert res_own.status_code == 200

    def test_right_to_erasure_anonymization(self, client):
        """Right to erasure anonymizes student PII and logs audit event."""
        # Test on STU012
        res = client.post("/api/compliance/erasure", json={
            "student_id": "STU012",
            "reason": "Graduated and requested GDPR erasure"
        }, headers=_student_headers(client, "STU012"))
        assert res.status_code == 200
        assert res.json()["status"] == "completed"

        # Verify profile was scrubbed/anonymized in DB
        profile_res = client.get(
            "/api/student/profile",
            params={"student_id": "STU012"},
            headers=_student_headers(client, "STU012"),
        )
        assert profile_res.status_code == 200
        profile = profile_res.json()
        assert "Anonymized Student" in profile["name"]
        assert "@privacy.uniassist.local" in profile["email"]
        assert profile["interests"] is None

    def test_audit_logs_require_staff_auth(self, client):
        """Audit log query is staff protected."""
        unauth_res = client.get("/api/compliance/audit-logs")
        assert unauth_res.status_code == 401

        staff_headers = _staff_headers(client)
        auth_res = client.get("/api/compliance/audit-logs", headers=staff_headers)
        assert auth_res.status_code == 200
        assert "audit_logs" in auth_res.json()
        assert isinstance(auth_res.json()["audit_logs"], list)

    def test_retention_policies_and_cleanup(self, client):
        """Staff can view retention schedules and trigger automated cleanup."""
        staff_headers = _staff_headers(client)

        # View policies
        policies_res = client.get("/api/compliance/retention-policies", headers=staff_headers)
        assert policies_res.status_code == 200
        assert "policies" in policies_res.json()
        policy_entities = [p["entity_name"] for p in policies_res.json()["policies"]]
        assert "conversations" in policy_entities
        assert "audit_logs" in policy_entities

        # Execute cleanup
        cleanup_res = client.post("/api/compliance/retention-cleanup", headers=staff_headers)
        assert cleanup_res.status_code == 200
        assert cleanup_res.json()["status"] == "success"
        assert "conversations" in cleanup_res.json()["summary"]
