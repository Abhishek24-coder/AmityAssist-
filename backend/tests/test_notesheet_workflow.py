"""
Tests for Phase 23: Collaborative Digital Notesheet Workflow.
Verifies multi-tier hierarchical approvals (Supervisor -> HOD -> HOI -> Pro-VC -> VC),
In-Flight Collaborative Editing, and audit annotations.
"""

import pytest


class TestNotesheetWorkflow:
    def test_create_notesheet_and_initial_stage(self, client):
        """Creating a notesheet initializes stage at SUPERVISOR with reference number."""
        payload = {
            "title": "Course Exemption Request for Transfer Student",
            "category": "Academic",
            "created_by": "FAC_002",
            "creator_name": "Prof. S. Sen",
            "creator_role": "Supervisor",
            "student_id": "STU001",
            "content": {
                "course_code": "CSE201",
                "semester": "3",
                "reason": "Equivalent credits completed at previous university",
                "recommended_credits": 4,
            },
            "comments": "Verified previous transcript. Recommending exemption.",
        }

        res = client.post("/api/notesheets", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        ns = data["notesheet"]
        assert ns["reference_no"].startswith("NS-")
        assert ns["title"] == payload["title"]
        assert ns["current_stage"] == "SUPERVISOR"
        assert ns["status"] == "IN_REVIEW"
        assert len(ns["signatures"]) == 1
        assert ns["signatures"][0]["stage"] == "SUPERVISOR"
        assert ns["next_stage"] == "HOD"

    def test_in_flight_collaborative_editing_with_audit_log(self, client):
        """Senior officer can edit course code/typo in-flight with mandatory justification."""
        create_res = client.post(
            "/api/notesheets",
            json={
                "title": "Special Fee Waiver Notesheet",
                "category": "Fee Concession",
                "created_by": "FAC_003",
                "content": {"course_code": "CS101", "waiver_amount": 5000},
                "student_id": "STU002",
            },
        )
        assert create_res.status_code == 200
        ref_no = create_res.json()["notesheet"]["reference_no"]

        # HOD performs an in-flight correction: CS101 -> CSE101
        edit_payload = {
            "officer_id": "HOD_CSE",
            "officer_role": "HOD",
            "field_name": "course_code",
            "new_value": "CSE101",
            "reason": "Corrected outdated course code typo from CS101 to standard CSE101",
        }
        edit_res = client.post(f"/api/notesheets/{ref_no}/edit-field", json=edit_payload)
        assert edit_res.status_code == 200
        updated = edit_res.json()["notesheet"]
        assert updated["content"]["course_code"] == "CSE101"
        assert updated["status"] == "IN_REVIEW"  # NOT rejected or reset!
        assert len(updated["edits"]) == 1
        audit = updated["edits"][0]
        assert audit["field_name"] == "course_code"
        assert audit["old_value"] == "CS101"
        assert audit["new_value"] == "CSE101"
        assert "Corrected outdated course code" in audit["reason"]

    def test_five_tier_sequential_approval_chain(self, client):
        """Notesheet advances Supervisor -> HOD -> HOI -> Pro-VC -> VC -> APPROVED."""
        create_res = client.post(
            "/api/notesheets",
            json={
                "title": "Semester Grade Review File",
                "category": "Academic",
                "created_by": "FAC_004",
                "content": {"student_id": "STU003", "proposed_grade": "A"},
            },
        )
        ref_no = create_res.json()["notesheet"]["reference_no"]

        # 1. Forward from SUPERVISOR to HOD
        fwd1 = client.post(
            f"/api/notesheets/{ref_no}/action",
            json={"officer_id": "FAC_004", "officer_name": "Supervisor", "role": "Supervisor", "action": "FORWARD"},
        )
        assert fwd1.status_code == 200
        assert fwd1.json()["notesheet"]["current_stage"] == "HOD"

        # 2. Forward from HOD to HOI
        fwd2 = client.post(
            f"/api/notesheets/{ref_no}/action",
            json={"officer_id": "HOD_001", "officer_name": "Dr. Verma", "role": "HOD", "action": "FORWARD"},
        )
        assert fwd2.status_code == 200
        assert fwd2.json()["notesheet"]["current_stage"] == "HOI"

        # 3. Forward from HOI to PRO_VC
        fwd3 = client.post(
            f"/api/notesheets/{ref_no}/action",
            json={"officer_id": "HOI_001", "officer_name": "Director Singh", "role": "HOI", "action": "FORWARD"},
        )
        assert fwd3.status_code == 200
        assert fwd3.json()["notesheet"]["current_stage"] == "PRO_VC"

        # 4. Forward from PRO_VC to VC
        fwd4 = client.post(
            f"/api/notesheets/{ref_no}/action",
            json={"officer_id": "PVC_001", "officer_name": "Prof. Rao", "role": "Pro-VC", "action": "FORWARD"},
        )
        assert fwd4.status_code == 200
        assert fwd4.json()["notesheet"]["current_stage"] == "VC"

        # 5. Final Approval at VC
        fwd5 = client.post(
            f"/api/notesheets/{ref_no}/action",
            json={"officer_id": "VC_001", "officer_name": "Hon. Vice Chancellor", "role": "VC", "action": "APPROVE", "comments": "Approved as per Academic Ordinance."},
        )
        assert fwd5.status_code == 200
        final_ns = fwd5.json()["notesheet"]
        assert final_ns["status"] == "APPROVED"
        assert final_ns["current_stage"] == "APPROVED"
        assert len(final_ns["signatures"]) == 6

    def test_rejection_halts_approval_chain(self, client):
        """Rejection at any stage sets status to REJECTED."""
        create_res = client.post(
            "/api/notesheets",
            json={
                "title": "Unauthorized Hostel Extension",
                "category": "Disciplinary",
                "created_by": "FAC_005",
                "content": {"violation": "Noise after hours"},
            },
        )
        ref_no = create_res.json()["notesheet"]["reference_no"]

        rej_res = client.post(
            f"/api/notesheets/{ref_no}/action",
            json={"officer_id": "HOD_002", "officer_name": "HOD Sharma", "role": "HOD", "action": "REJECT", "comments": "Request rejected due to repeated offenses."},
        )
        assert rej_res.status_code == 200
        assert rej_res.json()["notesheet"]["status"] == "REJECTED"

    def test_list_and_filter_notesheets(self, client):
        """Querying notesheets supports stage and status filtering."""
        res = client.get("/api/notesheets?status=IN_REVIEW")
        assert res.status_code == 200
        body = res.json()
        assert "notesheets" in body
        assert "stages" in body
        assert all(n["status"] == "IN_REVIEW" for n in body["notesheets"])
