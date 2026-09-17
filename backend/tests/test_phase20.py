"""
Phase 20 tests: System Parity, Diagnostic Readiness, and End-to-End Polish.
"""


def test_system_parity_check_healthy(client):
    """Parity check endpoint confirms health and active status of all 20 phases."""
    res = client.get("/api/system/parity-check")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "HEALTHY"
    assert data["cache_operational"] is True
    assert data["total_managed_tables"] >= 20
    assert data["completed_phases_count"] >= 29
    assert data["total_managed_tables"] >= 30

    matrix = data["phase_parity_matrix"]
    assert matrix["phase_0_hygiene"]["status"] == "ACTIVE"
    assert matrix["phase_1_withdrawal_mvp"]["status"] == "ACTIVE"
    assert matrix["phase_2_core_apis"]["status"] == "ACTIVE"
    assert matrix["phase_3_nlp_router"]["status"] == "ACTIVE"
    assert matrix["phase_6_jwt_rbac"]["status"] == "ACTIVE"
    assert matrix["phase_9_workflow_engine"]["status"] == "ACTIVE"
    assert matrix["phase_10_notifications"]["status"] == "ACTIVE"
    assert matrix["phase_11_analytics"]["status"] == "ACTIVE"
    assert matrix["phase_12_multi_campus"]["status"] == "ACTIVE"
    assert matrix["phase_18_advanced_ai"]["status"] == "ACTIVE"
    assert matrix["phase_19_compliance"]["status"] == "ACTIVE"
    assert matrix["phase_20_parity_polish"]["status"] == "ACTIVE"
    assert matrix["phase_21_clearance_gates"]["status"] == "ACTIVE"
    assert matrix["phase_22_deposit_offset"]["status"] == "ACTIVE"
    assert matrix["phase_23_notesheets"]["status"] == "ACTIVE"
    assert matrix["phase_24_status_registry"]["status"] == "ACTIVE"
    assert matrix["phase_25_ocr_verification"]["status"] == "ACTIVE"
    assert matrix["phase_26_qr_token_slip"]["status"] == "ACTIVE"
    assert matrix["phase_27_accreditation"]["status"] == "ACTIVE"
    assert matrix["phase_28_institution_config"]["status"] == "ACTIVE"
    assert matrix["phase_29_search_voice"]["status"] == "ACTIVE"


def test_end_to_end_student_lifecycle_journey(client):
    """Verify that auth, student profile, chat, and compliance flow smoothly together."""
    # 1. Login
    login_res = client.post("/api/auth/login", json={"student_id": "STU001"})
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Profile
    profile_res = client.get("/api/student/profile", params={"student_id": "STU001"}, headers=headers)
    assert profile_res.status_code == 200
    assert profile_res.json()["id"] == "STU001"

    # 3. Chat with contextual AI
    chat_res = client.post("/api/chat/message", json={
        "student_id": "STU001",
        "message": "What is my current CGPA and scholarship status?"
    }, headers=headers)
    assert chat_res.status_code == 200
    assert len(chat_res.json()["reply"]) > 0

    # 4. Check GDPR data export
    export_res = client.get("/api/compliance/export/STU001", headers=headers)
    assert export_res.status_code == 200
    assert export_res.json()["student_profile"]["id"] == "STU001"
