"""
Tests for Phase 27: Academic Accreditation & CO/PO Reporting Engine.
Verifies CO attainment calculation, PO attainment matrix generation,
cohort summaries, and CSV export format compliance.
"""

import pytest


class TestAccreditation:
    def test_co_attainment_for_cse_branch(self, client):
        """CO attainment endpoint returns structured data for CSE branch."""
        res = client.get("/api/accreditation/co-attainment?branch=CSE")
        assert res.status_code == 200
        data = res.json()
        assert data["branch"] == "CSE"
        assert "courses" in data
        assert data["total_courses"] >= 1
        # Each course should have COs
        for course in data["courses"]:
            assert "course_code" in course
            assert "course_name" in course
            assert "cos" in course
            for co in course["cos"]:
                assert "co_code" in co
                assert "attainment_percentage" in co
                assert "is_attained" in co
                assert "status" in co
                assert co["status"] in ("ATTAINED", "NOT_ATTAINED")

    def test_co_attainment_with_semester_filter(self, client):
        """CO attainment can be filtered by semester."""
        res = client.get("/api/accreditation/co-attainment?branch=CSE&semester=6")
        assert res.status_code == 200
        data = res.json()
        assert data["semester"] == 6
        for course in data["courses"]:
            assert course["semester"] == 6

    def test_po_attainment_matrix(self, client):
        """PO attainment endpoint returns 12 PO entries with attainment levels."""
        res = client.get("/api/accreditation/po-attainment?branch=CSE")
        assert res.status_code == 200
        data = res.json()
        assert data["branch"] == "CSE"
        assert data["total_pos"] == 12
        assert len(data["po_matrix"]) == 12
        for po in data["po_matrix"]:
            assert po["po_code"].startswith("PO")
            assert "average_correlation_weight" in po
            assert "attainment_level" in po
            assert po["attainment_level"] in ("HIGH", "MEDIUM", "LOW", "NONE")

    def test_cohort_summary(self, client):
        """Cohort summary provides combined CO/PO metrics."""
        res = client.get("/api/accreditation/cohort-summary?branch=CSE&year=2025")
        assert res.status_code == 200
        data = res.json()
        assert data["branch"] == "CSE"
        assert data["academic_year"] == 2025
        assert "co_attainment_rate" in data
        assert "po_summary" in data
        assert "co_report" in data
        assert "po_report" in data

    def test_csv_export(self, client):
        """CSV export returns valid CSV content with correct headers."""
        res = client.get("/api/accreditation/export?branch=CSE&format=csv")
        assert res.status_code == 200
        assert "text/csv" in res.headers.get("content-type", "")
        csv_text = res.text
        lines = csv_text.strip().split("\n")
        assert len(lines) >= 2  # Header + at least 1 data row
        header = lines[0]
        assert "Course Code" in header
        assert "CO Code" in header
        assert "Attainment %" in header

    def test_pdf_export(self, client):
        """PDF export returns valid PDF content."""
        res = client.get("/api/accreditation/export?branch=CSE&format=pdf")
        assert res.status_code == 200
        assert "application/pdf" in res.headers.get("content-type", "")
        assert res.content.startswith(b"%PDF")

    def test_invalid_export_format_rejected(self, client):
        """Invalid export format returns 400 error."""
        res = client.get("/api/accreditation/export?branch=CSE&format=xlsx")
        assert res.status_code == 400

    def test_empty_branch_returns_empty_courses(self, client):
        """Non-existent branch returns empty course list without error."""
        res = client.get("/api/accreditation/co-attainment?branch=NONEXISTENT")
        assert res.status_code == 200
        data = res.json()
        assert data["courses"] == []

    def test_grade_to_numeric_mapping(self, client):
        """Grade-to-numeric conversion is correct for all standard grades."""
        from backend.services.accreditation_service import AccreditationService
        assert AccreditationService.grade_to_numeric("O") == 10
        assert AccreditationService.grade_to_numeric("A+") == 9
        assert AccreditationService.grade_to_numeric("A") == 8
        assert AccreditationService.grade_to_numeric("B+") == 7
        assert AccreditationService.grade_to_numeric("F") == 0
        assert AccreditationService.grade_to_numeric(None) == 0
