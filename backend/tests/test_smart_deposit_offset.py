import pytest
from starlette.testclient import TestClient


class TestSmartDepositOffset:
    def test_smart_offset_200_lost_id_fine_clears_gate_instantly(self, client: TestClient):
        # 1. Apply for withdrawal
        apply_res = client.post(
            "/api/withdrawal/apply",
            json={"student_id": "STU001", "reason": "Relocating abroad", "course": "B.Tech CSE"},
        )
        assert apply_res.status_code == 200
        ref_no = apply_res.json()["reference_no"]

        # 2. Registrar flags ₹200 lost ID fine
        flag_res = client.post(
            f"/api/withdrawal/{ref_no}/clear/REGISTRAR",
            json={
                "action": "FLAG_DUES",
                "officer_name": "Registrar Proctor",
                "officer_id": "REG-01",
                "notes": "Missing physical identity card",
                "dues_amount": 200.0,
            },
        )
        assert flag_res.status_code == 200
        data = flag_res.json()
        assert data["status"] == "DUES_FLAGGED"

        # 3. Verify ledger starts at 10,000.0
        ledger_res = client.get(f"/api/withdrawal/{ref_no}/deposit-ledger")
        assert ledger_res.status_code == 200
        ledger_data = ledger_res.json()
        assert ledger_data["original_deposit"] == 10000.0
        assert ledger_data["remaining_balance"] == 10000.0

        # 4. Perform Smart Caution Deposit Offset of ₹200
        offset_res = client.post(
            f"/api/withdrawal/{ref_no}/offset-dues",
            json={
                "department": "REGISTRAR",
                "amount": 200.0,
                "reason": "Lost ID Card replacement fine",
                "student_consent": True,
                "authorized_by": "Finance Bursar",
            },
        )
        assert offset_res.status_code == 200
        offset_data = offset_res.json()
        assert offset_data["status"] == "CLEARED"
        assert offset_data["remaining_balance"] == 9800.0

        # 5. Check voucher reflects updated caution deposit balance of 9800
        voucher_res = client.get(f"/api/withdrawal/voucher/{ref_no}")
        assert voucher_res.status_code == 200
        v_data = voucher_res.json()
        assert v_data["caution_deposit_balance"] == 9800.0

        # Verify Registrar gate in voucher is CLEARED
        reg_gate = next(g for g in v_data["gates"] if g["department"] == "REGISTRAR")
        assert reg_gate["status"] == "CLEARED"
        assert reg_gate["dues_amount"] == 0.0
        assert "Caution Deposit offset" in reg_gate["notes"]

        # 6. Verify ledger transaction history
        ledger_updated = client.get(f"/api/withdrawal/{ref_no}/deposit-ledger").json()
        assert ledger_updated["total_offset"] == 200.0
        assert ledger_updated["remaining_balance"] == 9800.0
        assert len(ledger_updated["transactions"]) == 1
        assert ledger_updated["transactions"][0]["amount"] == 200.0
        assert ledger_updated["transactions"][0]["department"] == "REGISTRAR"

    def test_offset_exceeding_balance_rejected(self, client: TestClient):
        apply_res = client.post(
            "/api/withdrawal/apply",
            json={"student_id": "STU002", "reason": "Program transfer"},
        )
        ref_no = apply_res.json()["reference_no"]

        # Try offsetting 15,000 when deposit is 10,000
        resp = client.post(
            f"/api/withdrawal/{ref_no}/offset-dues",
            json={
                "department": "HOSTEL",
                "amount": 15000.0,
                "reason": "Hostel major damage charges",
            },
        )
        assert resp.status_code == 400
        assert "exceeds available caution deposit balance" in resp.json()["detail"]

    def test_all_gates_cleared_via_offset_completes_workflow(self, client: TestClient):
        apply_res = client.post(
            "/api/withdrawal/apply",
            json={"student_id": "STU003", "reason": "Moving out"},
        )
        ref_no = apply_res.json()["reference_no"]

        # Clear first 3 gates normally
        for dept in ["LIBRARY", "HOSTEL", "ACCOUNTS"]:
            client.post(
                f"/api/withdrawal/{ref_no}/clear/{dept}",
                json={"action": "CLEAR", "officer_name": "Auditor", "officer_id": "AUD-1"},
            )

        # Flag Registrar with ₹100 fine
        client.post(
            f"/api/withdrawal/{ref_no}/clear/REGISTRAR",
            json={"action": "FLAG_DUES", "officer_name": "Registrar", "officer_id": "REG-1", "dues_amount": 100.0},
        )

        # Offset the ₹100 fine
        client.post(
            f"/api/withdrawal/{ref_no}/offset-dues",
            json={"department": "REGISTRAR", "amount": 100.0, "reason": "Duplicate badge fine"},
        )

        # Check status endpoint shows request completed
        status_res = client.get("/api/withdrawal/status/STU003")
        assert status_res.status_code == 200
        assert status_res.json()["request"]["status"] == "completed"
