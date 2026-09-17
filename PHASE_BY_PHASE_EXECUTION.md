# UniAssist: Full Phase-by-Phase Execution Specification

This document provides the exhaustive, detailed execution breakdown for **every single development phase** of UniAssist (Phases 0 through 29). It details the phase objective, the technical stack used, all features included, the exact working mechanisms, real-world examples, and the verification status.

---

## Part 1: Completed Baseline Phases (Phases 0 to 20)

---

### Phase 0: Project Hygiene, Foundation & Runtime Setup
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Python 3.11+, Virtualenv (`.venv`), Git, Docker Compose, PowerShell.
* **Features Included:**
  * Root repository architecture and directory hygiene.
  * Comprehensive `.gitignore` filtering temporary SQLite WAL files, uploads, and Flutter outputs.
  * Docker Compose specification for API, PostgreSQL, Redis, and MinIO storage.
* **Working Mechanism:** Sets up the foundational virtual environment, installs dependencies, and verifies that the local environment is completely reproducible across machines.
* **Verification:** `pytest` executable and virtual environment successfully activated.

---

### Phase 1: Withdrawal Intelligence Workflow Baseline
* **Status:** `[x] COMPLETED`
* **Technical Stack:** FastAPI, SQLite, Pydantic v2, Python `uuid`.
* **Features Included:**
  * Official university procedure guidance endpoint (`GET /api/withdrawal/guide`).
  * Required documents discovery endpoint (`GET /api/withdrawal/documents`).
  * Dynamic clearance checklist generation keyed to withdrawal reasons (Academic, Medical, Financial).
  * Unique reference generation (e.g., `WD-8A2F10B3`).
* **Working Mechanism:** Queries seeded procedure steps and documents from the database, matching the student's stated reason with mandatory versus optional documentation.
* **Verification:** Validated via automated tests in `backend/tests/test_withdrawal.py`.

---

### Phase 2: Core Student & Staff Lifecycle APIs
* **Status:** `[x] COMPLETED`
* **Technical Stack:** FastAPI, SQLite, Pydantic, Starlette.
* **Features Included:**
  * Student profile retrieval (`GET /api/student/profile`).
  * Academic notices feed (`GET /api/student/notices`).
  * Exam schedules and results (`GET /api/student/exams`).
  * Backpaper registration endpoint (`POST /api/student/backpaper`).
  * Scholarship discovery and application (`/api/student/scholarships`).
  * Student grievance submission and admin resolution endpoints (`/api/student/grievances`, `/api/admin/grievances`).
* **Working Mechanism:** Parameterized SQL queries fetch and mutate student records across courses, grades, notices, and grievances.
* **Verification:** Verified with 13 automated tests across student and admin routers.

---

### Phase 3: Conversational AI Router & FSM Baseline
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Python `re` (regex), Deterministic State Machine (FSM), Pydantic.
* **Features Included:**
  * Intent classification service (`backend/services/nlp_service.py`).
  * Multilingual intent markers (English, Hindi, Hinglish).
  * State-machine session registry managing transitions across conversation turns.
  * Deterministic refund calculation formula embedded in conversation states.
* **Working Mechanism:** Evaluates incoming chat messages against intent token sets, transitioning student session state (`ASK_REASON` $\rightarrow$ `SUGGEST` $\rightarrow$ `CONFIRM` $\rightarrow$ `DONE`).
* **Verification:** Tested conversation state transitions in `backend/tests/test_chat.py`.

---

### Phase 4: Modern Design System & Kiosk UI Scaffolding
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Flutter 3.x, Dart, `flutter_animate`, Google Fonts.
* **Features Included:**
  * High-contrast design tokens in `kiosk_theme.dart` (Navy `#0A192F`, Gold `#F5A623`, Emerald `#2ECC71`).
  * Accessible minimum touch targets of 48x48 dp.
  * Responsive adaptive layouts for tablet kiosks, desktop browsers, and mobile screens.
* **Working Mechanism:** Centralized `ThemeData` tokens provide cohesive typography, elevation, and tactile button feedback across all widgets.
* **Verification:** Visual verification on Flutter Web and responsive layout tests.

---

### Phase 5: Student Lifecycle Presentation Views
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Flutter, Dart, `flutter_riverpod`, HTML5 Blob Download Bridge.
* **Features Included:**
  * Academic screen with circular attendance progress rings.
  * Scholarship Hub displaying eligibility criteria and one-tap application dialogs.
  * Grievance Desk with status tracking badges.
  * Universal `DownloadService` supporting in-browser PDF downloads and modal previews.
* **Working Mechanism:** Riverpod `FutureProvider` instances watch backend REST endpoints and bind async data to reactive UI widgets.
* **Verification:** Verified student profile, notices, and forms rendering on Flutter web server.

---

### Phase 6: JWT Authentication & Role-Based Access Control (RBAC)
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Python `jose` (JWT), `passlib` (bcrypt), FastAPI Security (`HTTPBearer`).
* **Features Included:**
  * Stateless JWT token issuance and cryptographic signature verification.
  * Student login (`POST /api/auth/login`) with Enrollment ID and PIN.
  * Staff login (`POST /api/auth/staff-login`) with role claims.
  * RBAC decorators guarding admin and staff routes.
* **Working Mechanism:** Decodes incoming `Authorization: Bearer <token>` headers, extracts identity and role claims, and enforces route permissions before handler execution.
* **Verification:** Verified with 13 automated tests in `backend/tests/test_auth.py`.

---

### Phase 7: Production Runtime Abstraction & Fallback
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Python `os`, SQLite3, `psycopg2` (optional), Redis (optional), MinIO (optional).
* **Features Included:**
  * Auto-detection of active database engine (`backend/database/connection.py`).
  * In-memory cache fallback when Redis is absent.
  * Local filesystem storage fallback (`uploads/`) when MinIO/S3 is absent.
* **Working Mechanism:** Inspects environment variables (`DATABASE_URL`, `REDIS_URL`, `S3_ENDPOINT`) and seamlessly toggles between local zero-dependency tools and enterprise cluster drivers.
* **Verification:** Verified zero-crash initialization in local development environments.

---

### Phase 8: Document Intelligence Baseline & Duplicate Detection
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Python `hashlib` (SHA-256), `mimetypes`, FastAPI `UploadFile`.
* **Features Included:**
  * Multipart document upload endpoint (`POST /api/documents/upload`).
  * Cryptographic SHA-256 hash generation for duplicate file detection.
  * Rejection of empty files and unwhitelisted file extensions.
  * Document metadata capture (file size, extension, SHA-256, timestamp).
* **Working Mechanism:** Computes the SHA-256 hash of the uploaded byte stream and queries prior student records. If an identical hash is found, flags the file as an existing duplicate.
* **Verification:** Verified with automated tests in `backend/tests/test_documents.py`.

---

### Phase 9: Generic Workflow Engine
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Python, SQLite/PostgreSQL, Pydantic.
* **Features Included:**
  * Generic workflow service (`backend/services/workflow_service.py`).
  * State progression lifecycle (`SUBMITTED` $\rightarrow$ `UNDER_REVIEW` $\rightarrow$ `APPROVED` $\rightarrow$ `COMPLETED`).
  * Automatic department assignment based on request type.
* **Working Mechanism:** Persists workflow instances and events, providing audit-proof status transition checks.
* **Verification:** Verified workflow creation and transition tests.

---

### Phase 10: Multi-Role Staff Portal Scaffolding
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Flutter, Dart, Riverpod.
* **Features Included:**
  * Staff operational dashboard (`staff_dashboard_screen.dart`).
  * Pending withdrawal request queues (`staff_withdrawal_screen.dart`).
  * Grievance response interface (`staff_grievance_screen.dart`).
  * Document inspection review panel (`staff_document_screen.dart`).
* **Working Mechanism:** Authenticated staff view pulls pending department queues, allowing 1-tap review actions.
* **Verification:** Verified staff tab navigation and action dialogs.

---

### Phase 11: Analytics & Institutional Reports
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Python, Pandas/CSV, ReportLab (PDF generation).
* **Features Included:**
  * Administrative statistics API (`GET /api/admin/stats`).
  * Lifecycle funnel metrics and bottleneck detection.
  * PDF and CSV report export foundation.
* **Working Mechanism:** Aggregates database records across request types, calculating average processing hours and department backlog sizes.
* **Verification:** Verified stats endpoints return valid JSON metrics.

---

### Phase 12: Multi-Campus Scaffolding
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Python, SQLite/PostgreSQL.
* **Features Included:**
  * Campus registry models and endpoints (`GET /api/campuses`).
  * Campus-scoped procedure and student lookups.
* **Working Mechanism:** Attaches a `campus_id` foreign key to student records and procedure definitions.
* **Verification:** Verified multi-campus endpoint queries.

---

### Phase 13–14: Deployment Hardening & Security Middleware
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Starlette Middleware, Docker Compose Production, Security Headers.
* **Features Included:**
  * Rate limiting and payload size guards.
  * Security headers middleware enforcing `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, and CSP.
  * Production Docker Compose configuration.
* **Working Mechanism:** Intercepts incoming HTTP requests, inspecting request rates, sizes, and setting strict response security headers.
* **Verification:** Verified headers returned in HTTP response envelopes.

---

### Phase 15: Full Student Kiosk Touch Journey
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Flutter, Dart, Riverpod, HTML5 Window Timer.
* **Features Included:**
  * Kiosk Welcome screen with Student Login vs Guest Mode (`kiosk_welcome_screen.dart`).
  * 45-second auto-expiring ambient privacy timer with countdown overlay.
  * Interactive tap-based Advisor Wizard modal (`digital_counselor_modal.dart`).
  * Complete Forms Catalog screen with category filters and instant download (`forms_catalog_screen.dart`).
* **Working Mechanism:** Kiosk touch events reset an ambient timer. If 45s passes without input, memory and auth state are purged, returning to the Welcome screen.
* **Verification:** Verified touch flows and auto-logout countdown on Flutter Web.

---

### Phase 16: Staff Operations Frontend Expansion
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Flutter, Dart, Riverpod.
* **Features Included:**
  * Staff withdrawal status toggling (Approve / Reject / Pending Dues).
  * Staff grievance resolution forms with resolution comments.
  * Staff document inspection with verification status flags.
* **Working Mechanism:** Dispatches authenticated PUT/POST requests to admin endpoints, updating UI state optimistically upon success.
* **Verification:** Verified staff status updates reflect in student views.

---

### Phase 17: CORS & Navigation Stability Fixes
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Starlette / FastAPI Middleware, Flutter `go_router` / Navigator.
* **Features Included:**
  * Outermost `CORSMiddleware` ordering resolving browser preflight `OPTIONS` blocks.
  * Flutter back-button routing fixed by replacing `context.go()` with `context.push()` to preserve navigation stacks.
  * Fallback route hardening preventing anonymous users from being pushed to the student dashboard.
* **Working Mechanism:** Reversed middleware registration order so CORS executes first. Preserved Flutter route history so `context.canPop()` remains functional.
* **Verification:** Verified seamless back-button navigation and zero browser console CORS errors.

---

### Phase 18: Advanced Conversational AI Foundation
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Python, HTTPX, Google Gemini API, Textwrap.
* **Features Included:**
  * Conversational memory summarizer (`backend/services/advanced_ai_service.py`).
  * Domain guardrail filter restricting queries to university lifecycle topics.
  * Google Gemini API configuration (`settings.llm_enabled`, `gemini_api_key`).
  * Safe local fallback reply builder when no external LLM is configured.
* **Working Mechanism:** Retains rolling 8-turn conversation memory, scoring sentiment and extracting topic intents before issuing LLM prompts.
* **Verification:** Verified fallback replies and sentiment scoring in test suite.

---

### Phase 19: Compliance & Audit Systems
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Python, SQLite/PostgreSQL, JSON.
* **Features Included:**
  * Tamper-evident audit logging service (`backend/services/audit_service.py`).
  * GDPR / DPDP personal data export endpoint (`GET /api/compliance/export/{student_id}`).
  * Right-to-be-forgotten anonymization endpoint (`POST /api/compliance/anonymize/{student_id}`).
* **Working Mechanism:** Generates structured JSON exports of all student records and sanitizes PII while preserving statistical aggregates.
* **Verification:** Verified compliance endpoints in test suite.

---

### Phase 20: System Parity & Verification Baseline
* **Status:** `[x] COMPLETED`
* **Technical Stack:** Pytest, FastAPI TestClient.
* **Features Included:**
  * System diagnostics health matrix endpoint: `GET /api/system/parity-check`.
  * 110 automated tests passing with zero failures.
* **Working Mechanism:** Runs automated unit and integration tests across auth, database, documents, workflows, and compliance.
* **Verification:** 100% passing test suite (`110 passed in 2.14s`).

---

## Part 2: Pending Roadmap Phases (The Institutional Expansion)

---

### Phase 21: Multi-Department "No-Dues" Clearance & Itemized Vouchers
* **Status:** `[x] COMPLETED`
* **Objective:** Eliminate the 5-building physical campus runaround and clerk confusion by creating a sequential digital clearance chain and standardized pre-itemized fee vouchers.
* **Technical Stack:** FastAPI, SQLite/PostgreSQL, Pydantic v2, Flutter Riverpod.
* **Features Included:**
  * 4 sequential departmental clearance gates: `LIBRARY`, `HOSTEL`, `ACCOUNTS`, `REGISTRAR`.
  * Department sign-off endpoint: `POST /api/withdrawal/{ref}/clear/{department}` with officer ID, notes, and timestamps.
  * Standardized clearance voucher citing the exact university ordinance code so no clerk can ask *"What is this fee for?"*.
  * Interactive visual clearance timeline stepper in `withdrawal_home_screen.dart` with real-time checkmarks.
  * Role-specific clearance buttons in the Staff Portal.
* **Working Mechanism:** When a student applies, a clearance instance is created with 4 pending gates. Each department officer can only approve their designated gate. The request advances sequentially until the Registrar applies the final digital seal.
* **Example:** Rohan Verma (in Canada) tracks his clearance online. Library clears his books at 10:15 AM, Hostel clears his room at 11:30 AM, Accounts reconciles his fee ledger, and the Registrar signs off—all visible in real time on Rohan's phone.

---

### Phase 22: Smart Financial Offsetting (The ₹200 Lost ID Card Solution)
* **Status:** `[x] COMPLETED`
* **Objective:** Prevent a ₹1,00,000 withdrawal refund from being halted for days over a minor ₹200 lost plastic card or library fine.
* **Technical Stack:** Python, SQLite/PostgreSQL, Flutter Riverpod.
* **Features Included:**
  * Caution deposit offsetting logic in `backend/services/withdrawal_workflow.py`.
  * Automated ledger adjustment re-calculating net refundable deposit balance.
  * **"Deduct from Security Deposit"** 1-tap checkbox on the student kiosk screen and staff clearance card.
  * Instant status update to `CLEARED_VIA_OFFSET` without requiring bank visits.
* **Working Mechanism:** When an officer flags an asset fine $\le$ ₹2,000, the student is prompted with a checkbox. Checking the box deducts the fee directly from their refundable caution deposit, immediately clearing the department gate.
* **Example:** Aman lost his plastic ID card. The guard flags a ₹200 replacement fee. Aman taps "Deduct ₹200 from my ₹10,000 Security Deposit". The guard's screen turns green instantly, and the clearance finishes in 10 seconds.

---

### Phase 23: Collaborative Digital "Notesheet" Workflow
* **Status:** `[ ] PENDING`
* **Objective:** Replace physical office peons carrying paper folders across campus with a digital approval document featuring in-flight collaborative editing.
* **Technical Stack:** FastAPI, SQLite/PostgreSQL, Flutter Riverpod, Digital Signatures.
* **Features Included:**
  * Multi-tier administrative approval hierarchy: `Supervisor` $\rightarrow$ `HOD` $\rightarrow$ `HOI (Director)` $\rightarrow$ `Pro-VC` $\rightarrow$ `Vice Chancellor`.
  * **In-Flight Collaborative Editing:** Senior officers can modify typos, course codes, or dates directly without rejecting the file.
  * Immutable digital audit annotation log recording every edit with the officer's Employee ID and timestamp.
  * Digital Notesheet viewer and signature interface in the Staff Portal.
* **Working Mechanism:** Notesheets are stored as structured JSON documents. Authorized officers can append digital signatures or edit specific fields. Edits create versioned audit records rather than rejecting the file down the chain.
* **Example:** A suspension notesheet contains a typo ("Semester 4" instead of "Semester 3"). The Pro-VC clicks "Edit Field", corrects it to Semester 3, adds a 1-sentence note, and approves it. The file reaches the Vice Chancellor in seconds rather than losing two weeks to physical peon couriers.

---

### Phase 24: Centralized Real-Time Student Status Registry
* **Status:** `[ ] PENDING`
* **Objective:** Eliminate the communication black hole where faculty miss emails and suspended students continue attending classes or exams.
* **Technical Stack:** FastAPI, WebSockets / SSE, Flutter Riverpod.
* **Features Included:**
  * Real-time student status state machine: `ACTIVE`, `UNDER_CLEARANCE`, `WITHDRAWN`, `SUSPENDED`, `DEBARRED`.
  * Real-time status broadcast updating all connected clients upon Proctorial Board action.
  * Faculty attendance portal alert banners displaying locked RED indicators for suspended students.
  * Kiosk and exam hall scanner entry locks for suspended or debarred students.
* **Working Mechanism:** Modifying a student's status emits a real-time event. The faculty portal and kiosk terminals refresh their cached student states immediately.
* **Example:** Student Priya is suspended at 11:00 AM. At 11:30 AM, she attempts to attend a Physics Lab. The faculty member takes attendance on the portal—Priya's name is locked in red with a notice directing her to the Proctorial Office.

---

### Phase 25: Real Local Document OCR Verification (Python Tesseract)
* **Status:** `[ ] PENDING`
* **Objective:** Replace simulated mock OCR with real local image text extraction to catch mismatched or fraudulent uploads.
* **Technical Stack:** Python `pytesseract`, Pillow (PIL), OpenCV (image binarization).
* **Features Included:**
  * Local image preprocessing (grayscale, thresholding, noise removal).
  * Optical Character Recognition extracting Student Name, Enrollment Number, Date, and Amount.
  * Automated cross-check: `extracted_enrollment_id == logged_in_student_id`.
  * Staff Document Cockpit displaying the uploaded file side-by-side with extracted OCR fields and confidence badges.
* **Working Mechanism:** Uploaded images are preprocessed and parsed by Tesseract. The extracted text is parsed with regular expressions for enrollment numbers and dates, automatically flagging matches or mismatches.
* **Example:** A student uploads a bank deposit receipt. Tesseract reads "Enrollment: STU001 | Date: 12-Aug-2026 | Amount: ₹45,000". The system tags it `Auto-Verified (High Confidence)`, cutting staff review time from 3 minutes to 5 seconds.

---

### Phase 26: Printable QR Token Slip & Mobile Tracking Handshake
* **Status:** `[x] COMPLETED`
* **Objective:** Provide tangible proof when students leave the lobby kiosk and allow smartphone tracking from anywhere in the world.
* **Technical Stack:** Python ReportLab (PDF), `qrcode` (2D barcode generation), Flutter Mobile Web.
* **Features Included:**
  * Branded 1-page PDF Token Slip generator with university header and coat of arms.
  * Dynamic high-resolution QR code encoding the live tracking URL (`http://<host>/status?ref=...`).
  * "Download / Print Official Token Slip" button on the kiosk screen.
  * Responsive public mobile status page accessible via smartphone camera scan.
* **Working Mechanism:** Request submission generates a vector PDF containing reference details and an embedded QR code image. The student scans the QR code on screen to open the tracking URL on their personal mobile browser.
* **Example:** Aman finishes filing for withdrawal on a lobby kiosk. He scans the QR code on screen. On his metro ride home, he opens his phone and sees that the Library cleared his clearance 10 minutes ago.

---

### Phase 27: Academic Accreditation & CO/PO Reporting Engine
* **Status:** `[ ] PENDING`
* **Objective:** Eliminate the faculty burden of manually compiling Course Outcome and Program Outcome attainment spreadsheets for NAAC, NBA, and UGC reviews.
* **Technical Stack:** Python, Pandas, OpenPyXL, SQLite/PostgreSQL.
* **Features Included:**
  * Course Outcomes (CO1–CO4) to Program Outcomes (PO1–PO12) mapping models.
  * Automated attainment percentage calculation across internal and external exam marks.
  * 1-click export of pre-formatted Excel and PDF reports matching NAAC Criterion 2.6.
  * Accreditation Hub tab in the Staff Portal.
* **Working Mechanism:** Aggregates assessment marks for all students in a cohort, applies the university's threshold formulas, and outputs a completed attainment matrix.
* **Example:** The NAAC inspection committee asks for student retention and CO/PO attainment reports. The faculty coordinator clicks "Export NAAC Criterion 2.6 Report" and downloads the completed spreadsheet in 3 seconds.

---

### Phase 28: Multi-University White-Label Institutional Configurator
* **Status:** `[ ] PENDING`
* **Objective:** Ensure the platform can be deployed by any university campus without modifying code.
* **Technical Stack:** FastAPI, SQLite/PostgreSQL, Flutter Riverpod.
* **Features Included:**
  * Institution settings API (`/api/institution/config`).
  * Configurable branding: University Name, Crest/Logo, Theme Colors, Domain.
  * Dynamic clearance chain builder: Add, reorder, or remove clearance desks per campus policy.
  * Custom refund policy builder: Define custom day cutoff brackets and percentage slabs.
  * Admin Settings UI for campus IT directors.
* **Working Mechanism:** All UI views and backend clearance workflows query the active institution's configuration record dynamically.
* **Example:** An engineering college in Pune adopts UniAssist. The IT Director uploads their crest, sets up a 3-step clearance chain (`HOD` $\rightarrow$ `Accounts` $\rightarrow$ `Principal`), and saves. All kiosk screens update instantly.

---

### Phase 29: Intelligent Search & Policy Guidance (SQLite FTS5 / Hybrid RAG & Voice)
* **Status:** `[x] COMPLETED`
* **Objective:** Answer student inquiries with 100% legal accuracy, zero hallucinations, and zero cloud costs.
* **Technical Stack:** SQLite `FTS5` (BM25 Inverted Index), Google Gemini 1.5 Flash (Free Tier), Python.
* **Features Included:**
  * Virtual FTS5 table indexing official university handbooks, ordinances, and refund circulars.
  * Sub-5ms keyword search returning verified legal clauses with bolded search term snippets.
  * Optional conversational AI layer passing retrieved clauses to Gemini free tier for personalized, friendly student advice.
  * Fail-safe offline fallback rendering verified legal cards when disconnected.
* **Working Mechanism:** Student queries are matched against the FTS5 index. The retrieved clause is injected into a strict prompt template alongside the student's live profile, generating an accurate 2-line conversational answer.
* **Example:** Aman asks: *"Can I write exams with 71% attendance?"*. The system retrieves Ordinance 7.2 (75% mandatory rule) and replies: *"Aman, at 71% you are 4% short of the 75% cutoff. You are eligible to apply for Dean Condonation using Form AC-04 before Nov 15th."*
