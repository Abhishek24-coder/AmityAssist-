"""
Tests for Phase 25: Real Local Document OCR Verification.
Verifies OCR service initialization, identity cross-check logic,
fallback behavior, and upload endpoint integration.
"""

import pytest


class TestOcrVerification:
    def test_ocr_service_fallback_available(self, client):
        """OCR service initializes successfully with either real or mock engine."""
        from backend.services.ocr_service import OcrService
        # Should return True or False without error
        result = OcrService.is_real_ocr_available()
        assert isinstance(result, bool)

    def test_identity_cross_check_match(self, client):
        """Extracted enrollment ID matching student ID returns MATCH."""
        from backend.services.ocr_service import OcrService
        assert OcrService._cross_check_identity("STU001", "STU001") == "MATCH"
        assert OcrService._cross_check_identity("stu001", "STU001") == "MATCH"

    def test_identity_cross_check_mismatch(self, client):
        """Extracted enrollment ID different from student ID returns MISMATCH."""
        from backend.services.ocr_service import OcrService
        assert OcrService._cross_check_identity("STU999", "STU001") == "MISMATCH"

    def test_identity_cross_check_not_found(self, client):
        """Missing extracted enrollment ID returns NOT_FOUND."""
        from backend.services.ocr_service import OcrService
        assert OcrService._cross_check_identity(None, "STU001") == "NOT_FOUND"
        assert OcrService._cross_check_identity("", "STU001") == "NOT_FOUND"

    def test_mock_ocr_analysis_returns_correct_shape(self, client):
        """Mock OCR analysis returns all required fields including identity match."""
        from backend.services.ocr_service import OcrService
        result = OcrService._mock_ocr_analysis(
            file_bytes=b"fake image data",
            filename="student_id_card.jpg",
            student_id="STU001",
        )
        assert "ocr_data" in result
        assert "fraud_flags" in result
        assert "overall_status" in result
        assert "ocr_identity_match" in result
        assert "ocr_engine" in result
        assert result["ocr_engine"] == "mock_fallback"
        assert result["ocr_identity_match"] == "MATCH"
        assert result["ocr_data"]["document_type"] == "ID Card"
        assert result["ocr_data"]["extracted_student_id"] == "STU001"

    def test_document_type_detection(self, client):
        """Document type detection classifies filenames correctly."""
        from backend.services.ocr_service import OcrService
        assert OcrService._detect_document_type("student_id_card.jpg") == "ID Card"
        assert OcrService._detect_document_type("marksheet_sem6.pdf") == "Marksheet"
        assert OcrService._detect_document_type("medical_certificate.png") == "Medical Certificate"
        assert OcrService._detect_document_type("bank_deposit_slip.jpg") == "Bank Deposit Slip"
        assert OcrService._detect_document_type("random_file.pdf") == "Other Document"

    def test_upload_endpoint_returns_ocr_identity_match(self, client):
        """Upload endpoint includes ocr_identity_match and ocr_engine in response."""
        import io
        # Create a minimal valid PNG (1x1 pixel)
        png_header = (
            b'\x89PNG\r\n\x1a\n'  # PNG signature
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'  # IHDR
            b'\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N'  # IDAT
            b'\x00\x00\x00\x00IEND\xaeB`\x82'  # IEND
        )
        res = client.post(
            "/api/documents/upload",
            data={"student_id": "STU001"},
            files={"file": ("student_id_card.png", io.BytesIO(png_header), "image/png")},
        )
        assert res.status_code == 200
        data = res.json()
        assert "ocr_identity_match" in data
        assert data["ocr_identity_match"] in ("MATCH", "MISMATCH", "NOT_FOUND")
        assert "ocr_engine" in data
        assert data["ocr_engine"] in ("tesseract", "mock_fallback")
        assert "verification_status" in data

    def test_name_extraction_regex(self, client):
        """Name extraction regex captures common patterns."""
        from backend.services.ocr_service import OcrService
        text1 = "Student Name: Aisha Malik\nEnrollment No: STU001"
        assert OcrService._extract_name(text1) == "Aisha Malik"
        text2 = "Name of Student: Rahul Sharma\nDate: 2024-05-15"
        assert OcrService._extract_name(text2) == "Rahul Sharma"

    def test_enrollment_extraction_regex(self, client):
        """Enrollment number extraction captures STU format."""
        from backend.services.ocr_service import OcrService
        text = "Student ID: STU001\nName: Test Student"
        assert OcrService._extract_enrollment_number(text) == "STU001"

    def test_date_extraction_regex(self, client):
        """Date extraction captures common date formats."""
        from backend.services.ocr_service import OcrService
        text = "Issued on 15/06/2024 by the Registrar"
        assert OcrService._extract_date(text) == "15/06/2024"
