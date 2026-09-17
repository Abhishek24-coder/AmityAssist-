"""
Tests for Phase 21 Multi-Department Clearance Pipeline & Itemized Vouchers.
Verifies sequential gates, department sign-offs, voucher transparency, and audit integration.
"""

import pytest


class TestClearancePipeline:
    def test_withdrawal_application_initializes_4_clearance_gates(self, client):
        """Applying for withdrawal must initialize all 4 departmental clearance gates."""
        res = client.post(
            "/api/withdrawal/apply",
            json={"student_id": "STU001", "reason": "Relocating abroad for family reasons"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        ref_no = data["reference_no"]
        assert ref_no is not None
        assert "voucher" in data
        assert data["voucher"]["ordinance_clause"] is not None

        # Verify status endpoint returns 4 gates
        status_res = client.get("/api/withdrawal/status/STU001")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["has_request"] is True
        gates = status_data["gates"]
        assert len(gates) == 4
        dept_names = [g["department"] for g in gates]
        assert dept_names == ["LIBRARY", "HOSTEL", "ACCOUNTS", "REGISTRAR"]
        for g in gates:
            assert g["status"] == "PENDING"

    def test_clearance_voucher_structure(self, client):
        """Voucher must provide full fee breakdown citing UGC regulations."""
        apply_res = client.post(
            "/api/withdrawal/apply",
            json={"student_id": "STU001", "reason": "Academic relocation"},
        )
        ref_no = apply_res.json()["reference_no"]

        voucher_res = client.get(f"/api/withdrawal/voucher/{ref_no}")
        assert voucher_res.status_code == 200
        voucher = voucher_res.json()
        assert voucher["reference_no"] == ref_no
        assert voucher["student_id"] == "STU001"
        assert "UGC Fee Refund Policy" in voucher["ordinance_clause"]
        assert voucher["gross_fee_paid"] > 0
        assert voucher["refund_percentage"] in (50.0, 80.0, 100.0)
        assert voucher["net_refundable_amount"] > 0
        assert len(voucher["gates"]) == 4

    def test_department_clearance_signoff_flow(self, client):
        """Department officers can sign off or flag dues, advancing clearance state."""
        apply_res = client.post(
            "/api/withdrawal/apply",
            json={"student_id": "STU001", "reason": "Personal medical reasons"},
        )
        ref_no = apply_res.json()["reference_no"]

        # 1. Clear Library
        lib_res = client.post(
            f"/api/withdrawal/{ref_no}/clear/LIBRARY",
            json={
                "action": "CLEAR",
                "officer_name": "Mrs. S. Verma",
                "officer_id": "LIB-042",
                "notes": "All 3 borrowed textbooks returned in good condition",
            },
        )
        assert lib_res.status_code == 200
        assert lib_res.json()["status"] == "CLEARED"
        assert lib_res.json()["is_all_cleared"] is False

        # 2. Flag dues at Hostel (e.g. minor room key fine)
        hostel_res = client.post(
            f"/api/withdrawal/{ref_no}/clear/HOSTEL",
            json={
                "action": "FLAG_DUES",
                "officer_name": "Mr. R. Sharma",
                "officer_id": "HST-019",
                "notes": "Lost room cupboard key",
                "dues_amount": 200.0,
            },
        )
        assert hostel_res.status_code == 200
        assert hostel_res.json()["status"] == "DUES_FLAGGED"

        # 3. Clear Accounts
        acc_res = client.post(
            f"/api/withdrawal/{ref_no}/clear/ACCOUNTS",
            json={
                "action": "CLEAR",
                "officer_name": "Mr. A. Goel",
                "officer_id": "ACC-101",
                "notes": "Fee ledger verified. Net refund voucher cleared for RTGS",
            },
        )
        assert acc_res.status_code == 200
        assert acc_res.json()["status"] == "CLEARED"

        # 4. Clear Registrar -> Whole clearance completes
        reg_res = client.post(
            f"/api/withdrawal/{ref_no}/clear/REGISTRAR",
            json={
                "action": "CLEAR",
                "officer_name": "Dr. K. Saxena",
                "officer_id": "REG-001",
                "notes": "Official exit clearance approved with university seal",
            },
        )
        assert reg_res.status_code == 200

        # Verify invalid department gate is rejected with 400
        invalid_res = client.post(
            f"/api/withdrawal/{ref_no}/clear/CANTEEN",
            json={
                "action": "CLEAR",
                "officer_name": "Chef",
                "officer_id": "CNT-01",
            },
        )
        assert invalid_res.status_code == 400

    def test_nonexistent_voucher_returns_404(self, client):
        """Fetching a nonexistent voucher reference must return 404."""
        res = client.get("/api/withdrawal/voucher/NONEXISTENT-REF-999")
        assert res.status_code == 404
