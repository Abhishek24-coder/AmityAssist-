"""
Phase 2 lifecycle endpoint tests.

These cover the student/staff API surface added on top of the original
withdrawal chatbot: profiles, notices, exams, scholarships, grievances,
back-paper registration, and document audit verification.
"""

from backend.database.connection import get_connection


class TestStudentLifecycleRoutes:
    @staticmethod
    def _student_headers(client, student_id: str = "STU001"):
        login = client.post("/api/auth/login", json={"student_id": student_id})
        return {"Authorization": f"Bearer {login.json()['token']}"}

    def test_profile_query_route_returns_expanded_profile(self, client):
        response = client.get(
            "/api/student/profile",
            params={"student_id": "STU001"},
            headers=self._student_headers(client, "STU001"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "STU001"
        assert data["branch"] == "CSE"
        assert data["semester"] == 6
        assert data["cgpa"] in (8.75, 8.85)

    def test_notices_are_personalized_by_branch_and_semester(self, client):
        response = client.get(
            "/api/student/notices",
            params={"student_id": "STU001"},
            headers=self._student_headers(client, "STU001"),
        )

        assert response.status_code == 200
        titles = {item["title"] for item in response.json()}
        assert "Mid-Semester Examinations Datesheet" in titles
        assert "Wipro Campus Placement Internship Drive 2026" in titles
        assert "ECE Electronics Lab Practical Datesheet" not in titles

    def test_exams_and_backpaper_registration(self, client):
        exams_response = client.get(
            "/api/student/exams",
            params={"student_id": "STU002"},
            headers=self._student_headers(client, "STU002"),
        )
        assert exams_response.status_code == 200
        failed_exam = next(item for item in exams_response.json() if item["grade"] == "F")

        register_response = client.post(
            "/api/student/backpaper",
            json={"student_id": "STU002", "exam_id": failed_exam["id"]},
            headers=self._student_headers(client, "STU002"),
        )

        assert register_response.status_code == 200
        assert "registered" in register_response.json()["message"].lower()

    def test_scholarship_discovery_and_application(self, client):
        discovery = client.get(
            "/api/student/scholarships",
            params={"student_id": "STU003"},
            headers=self._student_headers(client, "STU003"),
        )
        assert discovery.status_code == 200
        eligible = [item for item in discovery.json() if item["eligible"]]
        assert eligible

        application = client.post(
            "/api/student/scholarships/apply",
            json={"student_id": "STU003", "scholarship_id": eligible[0]["id"]},
            headers=self._student_headers(client, "STU003"),
        )

        assert application.status_code == 200
        assert "submitted" in application.json()["message"].lower()

    def test_grievance_create_and_student_list(self, client):
        create = client.post(
            "/api/student/grievances",
            json={
                "student_id": "STU004",
                "category": "academic",
                "description": "Need help resolving a course registration issue.",
            },
            headers=self._student_headers(client, "STU004"),
        )
        assert create.status_code == 200

        listing = client.get(
            "/api/student/grievances",
            params={"student_id": "STU004"},
            headers=self._student_headers(client, "STU004"),
        )
        assert listing.status_code == 200
        assert any(item["category"] == "academic" for item in listing.json())


class TestStaffLifecycleRoutes:
    @staticmethod
    def _staff_headers(client):
        login = client.post("/api/auth/staff/login", json={"username": "registrar_staff"})
        return {"Authorization": f"Bearer {login.json()['token']}"}

    def test_admin_can_resolve_grievance(self, client):
        client.post(
            "/api/student/grievances",
            json={
                "student_id": "STU005",
                "category": "hostel",
                "description": "Hostel allocation needs review.",
            },
        )
        conn = get_connection()
        grievance = conn.execute(
            "SELECT id FROM grievances WHERE student_id = ? ORDER BY id DESC LIMIT 1",
            ("STU005",),
        ).fetchone()

        response = client.post(
            f"/api/admin/grievances/{grievance['id']}/resolve",
            json={"resolution": "Allocation reviewed and forwarded to hostel office."},
            headers=self._staff_headers(client),
        )

        assert response.status_code == 200
        assert response.json()["notification_sent"] is True

    def test_document_upload_audit_and_admin_verification(self, client):
        upload = client.post(
            "/api/documents/upload",
            data={"student_id": "STU001"},
            files={"file": ("id_card.png", b"fake image bytes", "image/png")},
        )
        assert upload.status_code == 200
        assert "ocr_data" in upload.json()

        headers = self._staff_headers(client)
        audit = client.get("/api/admin/documents", headers=headers)
        assert audit.status_code == 200
        document = next(item for item in audit.json() if item["file_name"] == "id_card.png")
        assert document["ocr_data"]["extracted_student_id"] == "STU001"

        verification = client.post(
            f"/api/admin/documents/{document['id']}/verify",
            json={"status": "verified", "notes": "OCR fields match student record."},
            headers=headers,
        )
        assert verification.status_code == 200
        assert "verified" in verification.json()["message"]
