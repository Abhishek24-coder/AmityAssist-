"""
End-to-End Institutional Integration Test Suite.
Verifies cross-phase interaction across:
- Phase 21 (Clearance Chain)
- Phase 22 (Smart Caution Deposit Offsetting)
- Phase 23 (Digital Notesheets with in-flight edits)
- Phase 24 (Student Status Registry & Entry Locks)
- Phase 25 (Document OCR Verification & Cross-Check)
- Phase 26 (Printable QR Token Slip & Tracking)
- Phase 27 (Accreditation CO/PO Attainment Matrix)
- Phase 28 (Multi-University Institutional Configuration)
- Phase 29 (FTS5 Policy Search & Voice Assistance)
"""

import io
import pytest


class TestInstitutionalIntegration:

    def test_institution_config_and_clearance_chain_flow(self, client):
        """Phase 28 + Phase 21: Custom clearance chain is configured and queried."""
        # 1. Fetch institution config
        cfg_res = client.get("/api/institution/config")
        assert cfg_res.status_code == 200
        assert "institution_name" in cfg_res.json()

        # 2. Fetch clearance chain desks
        chain_res = client.get("/api/institution/clearance-chain")
        assert chain_res.status_code == 200
        desks = chain_res.json()["chain"]
        assert len(desks) >= 3

        # 3. Check refund slabs
        slabs_res = client.get("/api/institution/refund-slabs")
        assert slabs_res.status_code == 200
        assert len(slabs_res.json()["slabs"]) >= 3

    def test_ocr_and_document_verification_integration(self, client):
        """Phase 25 + Phase 2: Document upload triggers OCR with student ID cross-matching."""
        # Authenticate as student
        login = client.post("/api/auth/login", json={"student_id": "STU001"})
        assert login.status_code == 200
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Upload a dummy PNG file
        file_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        res = client.post(
            "/api/documents/upload",
            data={
                "student_id": "STU001",
                "document_type": "Identity Card",
            },
            files={"file": ("id_card.png", io.BytesIO(file_content), "image/png")},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert "ocr_identity_match" in data
        assert data["ocr_identity_match"] in ["MATCH", "MISMATCH", "NOT_FOUND"]

    def test_notesheet_and_registry_interlock(self, client):
        """Phase 23 + Phase 24: Notesheet action aligns with proctorial registry status."""
        # 1. Check student registry status
        status_res = client.get("/api/registry/status/STU001")
        assert status_res.status_code == 200
        assert status_res.json()["status"] in ["ACTIVE", "UNDER_CLEARANCE", "SUSPENDED", "DEBARRED", "WITHDRAWN"]

        # 2. Create and advance a notesheet
        ns_res = client.post("/api/notesheets", json={
            "title": "Proctorial Board Inquiry - STU001",
            "category": "DISCIPLINARY",
            "created_by": "STAFF001",
            "student_id": "STU001",
            "content": {"reason": "Formal inquiry regarding laboratory attendance."}
        })
        assert ns_res.status_code == 200
        ref = ns_res.json()["notesheet"]["reference_no"]

        # 3. In-flight edit by authorized officer
        edit_res = client.post(f"/api/notesheets/{ref}/edit-field", json={
            "officer_id": "STAFF002",
            "officer_role": "HOD",
            "field_name": "reason",
            "new_value": "Formal inquiry regarding laboratory attendance - corrected room 302.",
            "reason": "Corrected lab venue"
        })
        assert edit_res.status_code == 200
        updated = edit_res.json()["notesheet"]
        assert updated["content"]["reason"] == "Formal inquiry regarding laboratory attendance - corrected room 302."
        assert len(updated["edits"]) == 1

    def test_accreditation_and_policy_guidance(self, client):
        """Phase 27 + Phase 29: Accreditation metrics match and policy search answers inquiries."""
        # 1. CO Attainment calculation
        co_res = client.get("/api/accreditation/co-attainment", params={"branch": "CSE", "semester": 6})
        assert co_res.status_code == 200
        assert "courses" in co_res.json()

        # 2. PO Attainment matrix
        po_res = client.get("/api/accreditation/po-attainment", params={"branch": "CSE"})
        assert po_res.status_code == 200
        assert "po_matrix" in po_res.json()

        # 3. Policy search (FTS5)
        search_res = client.get("/api/policy/search", params={"q": "attendance"})
        assert search_res.status_code == 200
        assert len(search_res.json()["results"]) > 0
