"""
Tests for Phase 28: Multi-University White-Label Institutional Configurator.
Verifies institution branding configuration, dynamic clearance chain CRUD,
and custom refund slab management.
"""

import pytest


class TestInstitutionConfig:
    def test_default_institution_config_seeded(self, client):
        """Default Amity University configuration is seeded on startup."""
        res = client.get("/api/institution/config")
        assert res.status_code == 200
        data = res.json()
        assert data["institution_name"] == "Amity University"
        assert data["primary_color"] == "#003366"
        assert data["secondary_color"] == "#FFB800"
        assert "contact_email" in data

    def test_update_institution_branding(self, client):
        """Institution branding can be updated via PUT."""
        res = client.put(
            "/api/institution/config",
            json={"updates": {
                "institution_name": "Galgotias University",
                "primary_color": "#1A5276",
                "institution_motto": "Transforming Lives",
            }},
        )
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert res.json()["total_updated"] == 3

        # Verify changes persisted
        verify_res = client.get("/api/institution/config")
        assert verify_res.json()["institution_name"] == "Galgotias University"
        assert verify_res.json()["primary_color"] == "#1A5276"

    def test_default_clearance_chain_seeded(self, client):
        """Default 4-desk clearance chain is seeded."""
        res = client.get("/api/institution/clearance-chain")
        assert res.status_code == 200
        data = res.json()
        assert data["total_desks"] == 4
        desks = data["chain"]
        assert desks[0]["desk_code"] == "LIBRARY"
        assert desks[1]["desk_code"] == "HOSTEL"
        assert desks[2]["desk_code"] == "ACCOUNTS"
        assert desks[3]["desk_code"] == "REGISTRAR"

    def test_add_clearance_desk(self, client):
        """A new clearance desk can be added to the chain."""
        res = client.post(
            "/api/institution/clearance-chain/add",
            json={
                "desk_code": "SPORTS",
                "desk_name": "Sports Clearance Desk",
                "description": "Verify return of sports equipment.",
                "position": 3,
            },
        )
        assert res.status_code == 200
        assert res.json()["success"] is True
        chain = res.json()["chain"]
        sports_desk = next(d for d in chain if d["desk_code"] == "SPORTS")
        assert sports_desk["sequence_order"] == 3

    def test_remove_clearance_desk(self, client):
        """A clearance desk can be removed from the chain."""
        # First add a desk to remove
        client.post(
            "/api/institution/clearance-chain/add",
            json={"desk_code": "TEMP_DESK", "desk_name": "Temporary Desk"},
        )
        res = client.post(
            "/api/institution/clearance-chain/remove",
            json={"desk_code": "TEMP_DESK"},
        )
        assert res.status_code == 200
        assert res.json()["removed"] == "TEMP_DESK"

    def test_duplicate_desk_rejected(self, client):
        """Adding a desk with an existing code is rejected."""
        res = client.post(
            "/api/institution/clearance-chain/add",
            json={"desk_code": "LIBRARY", "desk_name": "Duplicate Library"},
        )
        assert res.status_code == 400
        assert "already exists" in res.json()["detail"]

    def test_default_refund_slabs_seeded(self, client):
        """Default refund slabs are seeded and queryable."""
        res = client.get("/api/institution/refund-slabs")
        assert res.status_code == 200
        data = res.json()
        assert data["total_slabs"] >= 1
        slabs = data["slabs"]
        # Verify slabs are ordered by min_days
        for i in range(1, len(slabs)):
            assert slabs[i]["min_days"] >= slabs[i - 1]["min_days"]

    def test_update_refund_slabs(self, client):
        """Refund slabs can be replaced with custom configuration."""
        res = client.put(
            "/api/institution/refund-slabs",
            json={"slabs": [
                {"slab_label": "Within 7 days", "min_days": 0, "max_days": 7, "refund_percent": 100.0, "policy_note": "Full refund within first week."},
                {"slab_label": "8-30 days", "min_days": 8, "max_days": 30, "refund_percent": 50.0, "policy_note": "50% refund."},
                {"slab_label": "After 30 days", "min_days": 31, "max_days": 9999, "refund_percent": 0.0, "policy_note": "No refund."},
            ]},
        )
        assert res.status_code == 200
        assert res.json()["total_slabs"] == 3

    def test_replace_clearance_chain(self, client):
        """Entire clearance chain can be replaced with new desks."""
        res = client.put(
            "/api/institution/clearance-chain",
            json={"desks": [
                {"desk_code": "LAB", "desk_name": "Laboratory Clearance", "description": "Lab equipment return"},
                {"desk_code": "LIBRARY", "desk_name": "Library Clearance", "description": "Book returns"},
                {"desk_code": "FINANCE", "desk_name": "Finance Office", "description": "Fee settlement"},
            ]},
        )
        assert res.status_code == 200
        assert res.json()["total_desks"] == 3
        chain = res.json()["chain"]
        assert chain[0]["desk_code"] == "LAB"
        assert chain[0]["sequence_order"] == 1

    def test_empty_config_update_rejected(self, client):
        """Empty config update payload is rejected."""
        res = client.put(
            "/api/institution/config",
            json={"updates": {}},
        )
        assert res.status_code == 400
