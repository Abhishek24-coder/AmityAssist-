# UniAssist Task List: Active Priority Execution Bundle

This task list tracks the active 4-phase execution milestone:
**Phase 21 $\longrightarrow$ Phase 22 $\longrightarrow$ Phase 26 $\longrightarrow$ Phase 29**

---

### Phase 21: Multi-Department "No-Dues" Clearance & Itemized Vouchers [COMPLETED ✅]
- `[x]` **Backend Models & State Progression:**
  - `[x]` Define 4-department clearance gates in `backend/models/schemas.py` and `backend/services/withdrawal_workflow.py` (`LIBRARY`, `HOSTEL`, `ACCOUNTS`, `REGISTRAR`).
  - `[x]` Implement standardized clearance voucher generation with immutable reference ID and official ordinance citations.
  - `[x]` Add department clearance endpoint: `POST /api/withdrawal/{ref}/clear/{department}` with officer notes and timestamps.
  - `[x]` Return sequential clearance status in `GET /api/withdrawal/status/{student_id}` and `GET /api/status/{student_id}`.
- `[x]` **Frontend Kiosk & Student UI:**
  - `[x]` Update `frontend_flutter/lib/src/features/withdrawal/presentation/withdrawal_home_screen.dart` with an interactive visual timeline stepper and clearance guidance.
  - `[x]` Display real-time status checkmarks (`[✅ Library]` $\rightarrow$ `[✅ Hostel]` $\rightarrow$ `[⏳ Accounts]` $\rightarrow$ `[⚪ Registrar]`) and voucher cards in `request_status_screen.dart`.
  - `[x]` Add role-specific clearance buttons and sign-off dialog to `frontend_flutter/lib/src/features/staff/presentation/staff_withdrawal_screen.dart`.
- `[x]` **Verification & Testing:**
  - `[x]` Write automated tests in `backend/tests/test_clearance_pipeline.py`.
  - `[x]` Verify all 119 backend tests pass with zero regressions (`pytest -q`).
  - `[x]` Verify Flutter tests pass with `flutter test` and `flutter analyze` has 0 issues.

---

### Phase 22: Smart Financial Offsetting (The ₹200 Lost ID Card Solution) [COMPLETED ✅]
- `[x]` Add `offset_from_caution_deposit` logic in `backend/services/withdrawal_workflow.py`.
- `[x]` Auto-deduct asset replacement fines ($\le$ ₹2,000) from refundable security deposit (`caution_deposit_ledger`).
- `[x]` Add 1-tap "Deduct from Security Deposit" checkbox to Flutter kiosk and staff clearance cards.
- `[x]` Automated test verification for deposit ledger re-balancing (`backend/tests/test_smart_deposit_offset.py`).
- `[x]` Verify all 122 backend tests pass with zero regressions (`pytest -q`).
- `[x]` Verify Flutter `flutter analyze` has 0 issues and all tests pass.

---

### Phase 26: Printable QR Token Slip & Mobile Tracking Handshake [COMPLETED ✅]
- `[x]` Implement `backend/services/token_pdf_service.py` to generate branded 1-page PDF slips with dynamic 2D QR codes.
- `[x]` Add endpoint `GET /api/withdrawal/{ref}/slip` returning the PDF stream.
- `[x]` Add public tracking endpoint `GET /api/withdrawal/track/{ref}` returning sanitized clearance progress.
- `[x]` Add "Download / Print QR Token Slip" button to Flutter `_ClearanceVoucherCard` in `request_status_screen.dart`.
- `[x]` Build responsive public token tracking banner and modal dialog in `guest_services_screen.dart` with live 4-gate handshake and slip download.
- `[x]` Automated test suite: `backend/tests/test_token_slip_and_tracking.py` (all 3/3 passing).
- `[x]` Verification: All 125 backend tests pass with 100% success; Flutter analyze has 0 issues and all tests pass.

---

### Phase 29: Intelligent Search & Policy Guidance (SQLite FTS5 / Hybrid RAG & Voice) [COMPLETED ✅]
- `[x]` Create SQLite `FTS5` virtual table indexing university handbooks, ordinances, and refund policies (`backend/services/policy_search_service.py`).
- `[x]` Add endpoint `GET /api/policy/search?q=...` with sub-5ms BM25 keyword ranking and `<mark>` snippet generation.
- `[x]` Add hybrid RAG endpoint `POST /api/policy/guide` cross-referencing live student profile (attendance condonation, withdrawal refund slabs, caution deposit offset).
- `[x]` Add voice endpoint `POST /api/voice/query` with speech synthesis parameters and natural cadence text.
- `[x]` Build Policy & Voice AI tab in `frontend_flutter/.../digital_counselor_modal.dart` with push-to-talk mic, TTS playback, quick query chips, and 1-tap action navigation.
- `[x]` Comprehensive test suite: `backend/tests/test_policy_fts_and_voice.py` (8/8 passing).
- `[x]` Verification: All backend tests pass; Flutter analyze has 0 issues and all tests pass.

---

### Phase 23: Collaborative Digital "Notesheet" Workflow [COMPLETED ✅]
- `[x]` **Backend Models & Hierarchical State Engine:**
  - `[x]` Create `notesheets`, `notesheet_signatures`, and `notesheet_edits` tables in database schema.
  - `[x]` Implement 5-tier hierarchical approval engine in `backend/services/notesheet_service.py` (`SUPERVISOR` ➔ `HOD` ➔ `HOI` ➔ `PRO_VC` ➔ `VC` ➔ `APPROVED`).
  - `[x]` Implement **In-Flight Collaborative Editing** (`edit_notesheet_field`): senior officers can correct course code typos and dates in-flight with mandatory audit notes without rejecting the document.
  - `[x]` Add endpoints in `backend/routes/notesheet.py`: create, list with filters, detail with audit trail, action (forward/approve/reject), and in-flight field editing.
- `[x]` **Frontend Staff Cockpit:**
  - `[x]` Build `frontend_flutter/.../staff_notesheet_screen.dart` with stage filter, 5-stage progress indicator, in-flight edit modal dialog, and forwarding/approval action toolbar.
  - `[x]` Add "Digital Notesheets" quick action card in `staff_dashboard_screen.dart`.
- `[x]` **Verification & Testing:**
  - `[x]` Comprehensive automated test suite: `backend/tests/test_notesheet_workflow.py` (5/5 tests passing).

---

### Phase 24: Centralized Real-Time Student Status Registry [COMPLETED ✅]
- `[x]` **Backend State Machine & Access Enforcement:**
  - `[x]` Add operational status columns (`status`, `status_reason`, `status_updated_at`, `status_updated_by`) to students table and create `student_status_history` audit table.
  - `[x]` Implement `backend/services/registry_service.py` managing transitions across `ACTIVE`, `UNDER_CLEARANCE`, `WITHDRAWN`, `SUSPENDED`, `DEBARRED` and enforcing entry/attendance locks.
  - `[x]` Add endpoints in `backend/routes/registry.py`: status lookup, Proctorial update, audit history, course roster warning matrix, and SSE real-time event streaming (`/api/registry/events`).
  - `[x]` Integrate with auth verification (`/api/auth/verify`) to flag kiosk restrictions and lock warnings.
- `[x]` **Frontend Faculty & Kiosk UI:**
  - `[x]` Build `frontend_flutter/.../staff_registry_screen.dart` displaying live roster, warning counts, red locked alert cards, update status dialog, and audit history inspector.
  - `[x]` Add "Status Registry & Entry Locks" quick action card in `staff_dashboard_screen.dart`.
- `[x]` **Verification & Testing:**
  - `[x]` Comprehensive automated test suite: `backend/tests/test_student_registry.py` (5/5 tests passing).
  - `[x]` Full regression test run: All 143 tests passing with 100% success.

