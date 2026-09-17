import pytest
from starlette.testclient import TestClient


class TestTokenSlipAndTracking:
    def test_token_slip_pdf_generation_and_headers(self, client: TestClient):
        # 1. Submit withdrawal request
        res = client.post(
            "/api/withdrawal/apply",
            json={"student_id": "STU001", "reason": "Relocating abroad to Canada"},
        )
        assert res.status_code == 200
        ref_no = res.json()["reference_no"]

        # 2. Download token slip PDF
        slip_res = client.get(f"/api/withdrawal/{ref_no}/slip")
        assert slip_res.status_code == 200
        assert slip_res.headers["content-type"] == "application/pdf"
        assert f'filename="TOKEN-{ref_no}.pdf"' in slip_res.headers["content-disposition"]

        # 3. Verify PDF binary format and vector content
        content = slip_res.content
        assert content.startswith(b"%PDF-1.4")
        assert content.endswith(b"%%EOF\n")
        assert b"AMITY UNIVERSITY" in content
        assert ref_no.encode("latin-1") in content
        assert b"SCAN TO TRACK ONLINE" in content

    def test_public_tracking_endpoint_without_auth(self, client: TestClient):
        # 1. Submit request
        res = client.post(
            "/api/withdrawal/apply",
            json={"student_id": "STU002", "reason": "Family relocation"},
        )
        ref_no = res.json()["reference_no"]

        # 2. Call public tracking without any headers or authentication
        track_res = client.get(f"/api/withdrawal/track/{ref_no}")
        assert track_res.status_code == 200
        data = track_res.json()

        assert data["reference_no"] == ref_no
        assert data["student_id"] == "STU002"
        assert len(data["gates"]) == 4
        assert "net_refundable_amount" in data
        assert "caution_deposit_balance" in data
        assert f"ref={ref_no}" in data["tracking_url"]

    def test_nonexistent_reference_returns_404(self, client: TestClient):
        slip_res = client.get("/api/withdrawal/NONEXISTENT-REF-9999/slip")
        assert slip_res.status_code == 404

        track_res = client.get("/api/withdrawal/track/NONEXISTENT-REF-9999")
        assert track_res.status_code == 404
