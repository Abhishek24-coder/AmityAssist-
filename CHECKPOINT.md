# UniAssist: Master Checkpoint & Implementation Tracker

This document provides the authoritative, phase-by-phase execution status of **UniAssist**. It records every completed milestone with verified tick marks (`[x]`) and clearly identifies pending roadmap phases with unchecked marks (`[ ]`) so any developer or AI agent can immediately see what is operational and what remains to be built.

---

## 📊 High-Level Status Summary

* **Phases 0–24, 26, 29 (Baseline & Core Institutional Expansion):** ✅ **COMPLETED (Verified with 143+ automated tests)**
* **Phases 25, 27, 28 (Remaining Institutional Modules):** ⏳ **PENDING (Planned for Execution)**

---

## Part 1: Completed Phases (Fully Implemented & Verified)

### [x] Phase 0: Project Hygiene, Foundation & Runtime Setup
* `[x]` Clean root repository setup with `.gitignore` for Python caches, SQLite WAL/SHM files, uploads, and Flutter build outputs.
* `[x]` Virtual environment setup (`.venv`) with verified dependencies in `backend/requirements.txt`.
* `[x]` Root documentation baseline (`README.md`, `DEVELOPMENT_PHASES.md`).
* `[x]` Docker Compose foundation for API, PostgreSQL, Redis, and MinIO storage.

### [x] Phase 1: Withdrawal Intelligence Workflow Baseline
* `[x]` Official procedure steps seeded in database (`procedure_steps`).
* `[x]` Required documents and download forms catalog seeded in database (`procedure_documents`, `procedure_forms`).
* `[x]` Core withdrawal guidance endpoints: `GET /api/withdrawal/guide`, `GET /api/withdrawal/documents`.
* `[x]` Unique withdrawal reference ID generator (`WD-XXXXXXXX`).
* `[x]` Dynamic checklist generator based on student reason (Academic, Medical, Financial).

### [x] Phase 2: Core Student Lifecycle & Staff APIs
* `[x]` Student profile retrieval endpoint (`GET /api/student/profile`).
* `[x]` Personalized academic notices endpoint (`GET /api/student/notices`).
* `[x]` Exam schedules and past semester results (`GET /api/student/exams`).
* `[x]` Backpaper examination registration (`POST /api/student/backpaper`).
* `[x]` Scholarship discovery and application (`GET /api/student/scholarships`, `POST /api/student/scholarships/apply`).
* `[x]` Grievance submission and tracking (`GET /api/student/grievances`, `POST /api/student/grievances`).
* `[x]` Admin grievance resolution endpoints (`GET /api/admin/grievances`, `POST /api/admin/grievances/{id}/resolve`).

### [x] Phase 3: Conversational AI Router & FSM Baseline
* `[x]` Natural language intent classification service (`backend/services/nlp_service.py`).
* `[x]` Deterministic state-machine (FSM) session manager (`backend/services/chat_service.py`).
* `[x]` Rule-based routing for Academics, Scholarships, Grievances, Withdrawals, and Notices.
* `[x]` Basic refund calculation logic embedded in conversation flow.

### [x] Phase 4: Design System & Kiosk UI Scaffolding
* `[x]` High-contrast, modern design tokens in `frontend_flutter/lib/src/core/theme/kiosk_theme.dart`.
* `[x]` Accessible touch targets (minimum 48x48 dp) optimized for public touchscreen kiosks.
* `[x]` Responsive layouts supporting Kiosk Wide View, Desktop View, and Mobile Split View.

### [x] Phase 5: Student Lifecycle Presentation Views
* `[x]` Flutter Academic screen with circular attendance progress rings.
* `[x]` Flutter Scholarship Hub displaying eligibility criteria and 1-tap application.
* `[x]` Flutter Grievance Desk with visual status badges and submission dialogs.
* `[x]` Universal Download Service (`download_service.dart`) supporting in-browser PDF download and preview.

### [x] Phase 6: JWT Authentication & Role-Based Access Control (RBAC)
* `[x]` Stateless JWT token generation and decoding (`backend/security/jwt.py`).
* `[x]` Role-based permission gatekeeper (`backend/security/rbac.py`).
* `[x]` Student login endpoint with Enrollment ID and PIN: `POST /api/auth/login`.
* `[x]` Staff role-based login: `POST /api/auth/staff-login`.
* `[x]` Route-level identity matching ensuring students can only access their own records.

### [x] Phase 7: Production Runtime Abstraction & Fallbacks
* `[x]` Automatic database backend detection in `backend/database/connection.py` (SQLite local vs PostgreSQL server).
* `[x]` Cache service with in-memory fallback (`backend/services/cache_service.py`) when Redis is unavailable.
* `[x]` Storage service with local filesystem fallback (`backend/services/storage_service.py`) when MinIO/S3 is unavailable.

### [x] Phase 8: Document Intelligence Baseline & Duplicate Detection
* `[x]` File upload endpoint with MIME type detection and file extension whitelist (`backend/routes/documents.py`).
* `[x]` Cryptographic SHA-256 hash calculation for every uploaded document.
* `[x]` Automated duplicate detection comparing incoming file hashes against prior submissions.
* `[x]` Structured metadata capture (file size, extension, SHA-256, upload timestamp).

### [x] Phase 9: Generic Workflow Engine
* `[x]` Configurable workflow engine (`backend/services/workflow_service.py`).
* `[x]` Dynamic state progression (`SUBMITTED` $\rightarrow$ `UNDER_REVIEW` $\rightarrow$ `APPROVED` $\rightarrow$ `COMPLETED`).
* `[x]` Department assignment logic based on procedure type.

### [x] Phase 10: Multi-Role Staff Portal Scaffolding
* `[x]` Staff operational dashboard in Flutter (`staff_dashboard_screen.dart`).
* `[x]` Staff withdrawal queue inspection view (`staff_withdrawal_screen.dart`).
* `[x]` Staff grievance response view (`staff_grievance_screen.dart`).
* `[x]` Staff document review panel (`staff_document_screen.dart`).

### [x] Phase 11: Analytics & Institutional Reports
* `[x]` System statistics API (`GET /api/admin/stats`).
* `[x]` Administrative bottleneck metrics and workflow funnel analysis.
* `[x]` PDF and CSV report export foundation in backend.

### [x] Phase 12: Multi-Campus Scaffolding
* `[x]` Multi-campus database models (`campuses` table).
* `[x]` Campus-scoped procedure lookups (`GET /api/campuses`, `GET /api/campuses/{id}`).

### [x] Phase 13–14: Deployment Hardening & Security Middleware
* `[x]` Production Docker Compose configuration (`docker-compose.production.yml`).
* `[x]` Configurable rate limiting and payload size guards.
* `[x]` Security headers middleware (`X-Content-Type-Options`, `X-Frame-Options`, strict CSP).

### [x] Phase 15: Full Student Kiosk Touch Journey
* `[x]` Kiosk Welcome screen with Student Login vs Guest Mode (`kiosk_welcome_screen.dart`).
* `[x]` 45-second auto-expiring ambient privacy timer with countdown overlay.
* `[x]` Interactive tap-based Advisor Wizard modal (`digital_counselor_modal.dart`).
* `[x]` Complete Forms Catalog screen with category filters and instant download (`forms_catalog_screen.dart`).

### [x] Phase 16: Staff Operations Frontend Expansion
* `[x]` Staff withdrawal status toggling (Approve / Reject / Pending Dues).
* `[x]` Staff grievance resolution forms with resolution comments.
* `[x]` Staff document inspection with verification status flags.

### [x] Phase 17: CORS & Navigation Stability Fixes
* `[x]` Starlette middleware ordering corrected: `CORSMiddleware` registered as outermost wrapper to properly handle browser preflight `OPTIONS` requests.
* `[x]` Flutter back-button routing fixed: Replaced `context.go()` with `context.push()` to preserve the navigation history stack.
* `[x]` Fallback route hardening preventing anonymous users from being pushed to the student dashboard.

### [x] Phase 18: Advanced Conversational AI Foundation
* `[x]` Conversational memory summarizer (`backend/services/advanced_ai_service.py`).
* `[x]` Domain guardrail filter restricting queries to university lifecycle topics.
* `[x]` Google Gemini API integration configuration (`settings.llm_enabled`, `gemini_api_key`).
* `[x]` Safe local fallback reply builder when no external LLM is configured.

### [x] Phase 19: Compliance & Audit Systems
* `[x]` Tamper-evident audit logging service (`backend/services/audit_service.py`).
* `[x]` GDPR / DPDP data export endpoint (`GET /api/compliance/export/{student_id}`).
* `[x]` Right-to-be-forgotten anonymization endpoint (`POST /api/compliance/anonymize/{student_id}`).

### [x] Phase 20: System Parity & Verification Baseline
* `[x]` System diagnostics health matrix endpoint: `GET /api/system/parity-check`.
* `[x]` Verified test suite: 110 automated tests passing (`pytest -q`).

---

## Part 2: Pending Roadmap Phases (The Institutional Expansion)

These phases address the concrete real-world operational problems discovered on campus (the 48 withdrawal bottlenecks, the remote Canada student, the ₹200 lost ID card deadlock, the physical paper notesheet peon runaround, and accreditation reporting).

---

### [x] Phase 21: Multi-Department "No-Dues" Clearance & Itemized Vouchers
*Goal: Eliminate the 5-building physical runaround and clerk confusion with a digital clearance chain and pre-itemized fee vouchers.*
* `[x]` Backend: Expand clearance models with 4 sequential department gates (`LIBRARY`, `HOSTEL`, `ACCOUNTS`, `REGISTRAR`).
* `[x]` Backend: Add department sign-off endpoint: `POST /api/withdrawal/{ref}/clear/{department}` with officer notes and timestamps.
* `[x]` Backend: Generate standardized clearance voucher citing the exact university ordinance code so no clerk can ask *"What is this fee for?"*.
* `[x]` Frontend: Build an interactive visual clearance timeline stepper in `withdrawal_home_screen.dart` and `request_status_screen.dart` with green checkmarks and real-time status.
* `[x]` Frontend: Add role-specific clearance buttons and dialog in the Staff Portal for Library, Hostel, Accounts, and Registrar desks.

### [x] Phase 22: Smart Financial Offsetting (The ₹200 Lost ID Card Solution)
*Goal: Prevent halting a ₹1,00,000 withdrawal refund over a minor ₹200 lost plastic card or library fine.*
* `[x]` Backend: Implement `offset_from_caution_deposit` logic in `withdrawal_workflow.py`.
* `[x]` Backend: Auto-adjust refundable caution deposit ledger (e.g., ₹10,000 $\longrightarrow$ ₹9,800) when an asset fee is approved.
* `[x]` Frontend: Add the **"Deduct from Security Deposit"** 1-tap checkbox on the student kiosk screen and staff clearance card.
* `[x]` Backend: Update clearance state to `CLEARED_VIA_OFFSET` instantly without requiring physical bank visits.

### [x] Phase 23: Collaborative Digital "Notesheet" Workflow
*Goal: Replace physical peons carrying paper folders with a digital, hierarchical approval document featuring in-flight typo corrections.*
* `[x]` Backend: Create `backend/routes/notesheet.py` and data models (`notesheets`, `notesheet_signatures`, `notesheet_edits`).
* `[x]` Backend: Implement multi-tier approval hierarchy: `Supervisor` $\rightarrow$ `HOD` $\rightarrow$ `HOI (Director)` $\rightarrow$ `Pro-VC` $\rightarrow$ `Vice Chancellor`.
* `[x]` Backend: Implement **In-Flight Collaborative Editing**: authorized officers can modify course codes or typos with an audit annotation without rejecting the entire file.
* `[x]` Frontend: Build the Digital Notesheet viewer and signature interface in the Staff Portal.

### [x] Phase 24: Centralized Real-Time Student Status Registry
*Goal: Eliminate the communication black hole where faculty miss emails and suspended students attend classes.*
* `[x]` Backend: Add operational status flags to student records (`ACTIVE`, `UNDER_CLEARANCE`, `WITHDRAWN`, `SUSPENDED`, `DEBARRED`).
* `[x]` Backend: Broadcast status updates via API and SSE events upon Proctorial Board action.
* `[x]` Frontend: Faculty attendance portal shows instant RED alert banners for suspended students.
* `[x]` Frontend: Kiosk terminals and exam barcode scanners display visual entry locks for suspended or debarred students.

### [ ] Phase 25: Real Local Document OCR Verification (Python Tesseract)
*Goal: Replace simulated mock OCR with real image text extraction to catch mismatched or fraudulent uploads.*
* `[ ]` Backend: Integrate `pytesseract` in `backend/routes/documents.py`.
* `[ ]` Backend: Extract Student Name, Enrollment Number, and Date from uploaded ID cards and bank deposit slips.
* `[ ]` Backend: Compare extracted Enrollment Number against the logged-in student profile (`extracted_id == student_id`).
* `[ ]` Frontend: Staff Document Cockpit displays uploaded image side-by-side with extracted OCR fields and green/amber match indicators.

### [x] Phase 26: Printable QR Token Slip & Mobile Tracking Handshake
*Goal: Provide tangible proof when students leave the lobby kiosk and allow smartphone tracking from anywhere (e.g., Canada).*
* `[x]` Backend: Create `backend/services/token_pdf_service.py` to generate official 1-page PDF slips with embedded 2D QR codes.
* `[x]` Backend: Add endpoint `GET /api/withdrawal/{ref}/slip` returning the downloadable PDF stream.
* `[x]` Frontend: Add "Download / Print Official Token Slip" button on the kiosk screen upon request submission.
* `[x]` Frontend: Build a responsive, public mobile status tracking page (`/status?ref=...`) accessible via smartphone camera scan.

### [ ] Phase 27: Academic Accreditation & CO/PO Reporting Engine
*Goal: Eliminate the faculty burden of manually compiling Course Outcome and Program Outcome attainment spreadsheets for NAAC/NBA.*
* `[ ]` Backend: Build `backend/services/accreditation_service.py` mapping course grades to Program Outcomes (PO1 to PO12) and Course Outcomes (CO1 to CO4).
* `[ ]` Backend: Endpoints to export pre-formatted Excel / PDF reports for NAAC Criterion 2.6.
* `[ ]` Frontend: Build the **Accreditation Hub** tab in the Staff Portal with 1-click export buttons for annual cohorts.

### [ ] Phase 28: Multi-University White-Label Institutional Configurator
*Goal: Ensure the platform can be deployed by any university (Amity, Galgotias, Sharda, DU) without code modifications.*
* `[ ]` Backend: Create `backend/routes/institution.py` allowing super-admins to configure university name, crest logo, theme colors, and custom refund day slabs.
* `[ ]` Backend: Dynamic clearance chain builder (add, rename, or remove clearance desks per campus policy).
* `[ ]` Frontend: Admin Settings screen to upload university branding and adjust clearance steps dynamically.

### [x] Phase 29: Intelligent Search & Policy Guidance (SQLite FTS5 / Hybrid RAG & Voice)
*Goal: Answer student inquiries with 100% legal accuracy, zero hallucinations, and voice push-to-talk guidance.*
* `[x]` Backend: Implement SQLite `FTS5` virtual table indexing official university handbooks, ordinances, and refund policies.
* `[x]` Backend: Endpoint `GET /api/policy/search?q=...` returning BM25 ranked legal clauses with highlighted snippets.
* `[x]` Backend: Endpoint `POST /api/policy/guide` providing personalized hybrid RAG advice (attendance condonation, withdrawal refund slabs, caution deposit offset).
* `[x]` Backend: Endpoint `POST /api/voice/query` delivering speech synthesis parameters and natural speech responses.
* `[x]` Frontend: Digital Counselor modal adds Policy & Voice AI (FTS5) tab with search, quick query chips, push-to-talk mic, TTS playback, and 1-tap action shortcuts.
