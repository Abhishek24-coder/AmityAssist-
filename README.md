# UniAssist

UniAssist is a workflow-centric student service and procedure guidance platform for a university. It is designed as a digital front desk: students can verify their identity, see personalized academic and service information, receive guided withdrawal support, upload documents for mock OCR/fraud checks, file grievances, discover scholarships, and track request status.

The current implementation is a local prototype using FastAPI, SQLite, and a static HTML/CSS/JavaScript frontend. That HTML frontend is only for rapid browser validation of the flows already built. The real kiosk-grade student interface should continue in `frontend_flutter/` as a touch-first Flutter web/tablet app. Docker/PostgreSQL/Redis/MinIO foundation files are also present for the target stack.

## Current Status

Completed baseline:

- Phase 0 project hygiene and setup docs.
- Phase 1 withdrawal intelligence workflow API, checklist generation, official steps, required documents, forms, timelines, and status tracking.
- Phase 2 student/staff backend APIs for profile, notices, exams, backpapers, scholarships, grievances, documents, admin grievance handling, and admin document audit.
- Phase 3 conversational assistant routing for academics, exams, scholarships, grievances, notices, hostel/fees/documents/internships, multilingual hints, voice command markers, and withdrawal refund guidance.
- Prototype frontend alignment for the student dashboard, academics, scholarships, grievances, document upload/OCR result panel, withdrawal status/checklist/steps/forms, dark mode, and Web Speech API controls.
- Flutter kiosk scaffold for login and withdrawal guidance in `frontend_flutter/`.
- Phase 11 staff analytics: lifecycle snapshot, workflow funnel, bottleneck detection, and CSV/PDF report exports.
- Phase 12 multi-campus configuration: campus-scoped procedures, workflow ownership, and cross-campus student lookup.
- Phase 13 deployment foundation: production Compose, Kubernetes manifests, persistent infrastructure, and PostgreSQL migration extensions.
- Phase 14 production hardening: configurable limits, security headers, telemetry, readiness probes, and guarded backup tooling.
- Phase 15 full student kiosk journey in `frontend_flutter/`: complete touch-optimized Riverpod UI with login, dashboard, academics, scholarships, grievances, document center with OCR checks, multi-step withdrawal guide, notifications, and auto-expiring privacy session.
- Student Document Center now includes a recent-upload history with verification status and staff notes.
- Phase 16 staff portal frontend expansion: Flutter staff dashboard, withdrawal queue actions, grievance resolution, document verification, batch workflow actions, and backend response normalization.
- Phase 18 advanced conversational AI: contextual memory summaries, optional Gemini integration settings, safe local fallback, domain guardrails, sentiment metadata, and escalation flags.
- Phase 19 compliance & audit system: GDPR personal data export, right-to-be-forgotten / anonymization, retention policies, automated cleanup, and tamper-evident audit queries.
- Phase 20 system parity & polish: real-time system diagnostics matrix (`/api/system/parity-check`), multi-phase end-to-end integration verification, and 100% passing test suite.
- Phase 21 multi-department clearance: 4 sequential clearance gates (Library, Hostel, Accounts, Registrar) with standardized legal vouchers.
- Phase 22 smart financial offsetting: 1-tap auto-deduction of minor asset fines (lost ID ₹200) from refundable security deposit.
- Phase 23 collaborative digital notesheet: hierarchical 5-tier approval chain (`Supervisor` ➔ `HOD` ➔ `HOI` ➔ `Pro-VC` ➔ `VC`) with in-flight collaborative editing and audit logs, eliminating paper peon couriers and file rejections.
- Phase 24 centralized real-time student status registry: real-time operational state machine (`ACTIVE`, `UNDER_CLEARANCE`, `WITHDRAWN`, `SUSPENDED`, `DEBARRED`), live SSE event broadcast, faculty attendance warning banners, and kiosk entry locks.
- Phase 25 real local document OCR verification: Python Tesseract image text extraction with student ID cross-matching (`MATCH`/`MISMATCH`/`NOT_FOUND`), confidence scoring, and Staff Document OCR Cockpit.
- Phase 26 printable QR token slip: ReportLab vector PDF slip generation with dynamic 2D QR codes linking to public mobile status tracking.
- Phase 27 academic accreditation & CO/PO reporting engine: automated Course Outcome (CO1–CO4) and Program Outcome (PO1–PO12) attainment matrix calculation, cohort summaries, and 1-click NAAC Criterion 2.6 CSV/PDF export.
- Phase 28 multi-university white-label configurator: institution branding settings (name, crest URL, theme colors), dynamic clearance chain desk configuration, and custom refund day slabs.
- Phase 29 intelligent search & policy guidance: SQLite FTS5 sub-5ms BM25 ordinance search, hybrid RAG guidance, and push-to-talk voice endpoints.

Remaining production work:

- Live PostgreSQL/Redis/MinIO cloud cluster deployment & monitoring alerts.
- Physical kiosk hardware deployment & touchscreen calibration.

## Quick Start

Run from the repository root. If Python is already on PATH:

```powershell
cd C:\Users\HP\ANtiAgentBuilding
pip install -r backend\requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

If Python is not on PATH in this Codex machine, use the checked local virtual environment:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal:

```powershell
cd C:\Users\HP\ANtiAgentBuilding\frontend
python -m http.server 5500 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:5500/index.html
```

API docs:

```text
http://127.0.0.1:8000/api/docs
```

Demo student:

```text
Student ID: STU001
```

## Tests

```powershell
py -m pytest
```

The current verified result is `176 passed` with 0 failures.

## Main Local Prototype Endpoints

```text
POST /api/auth/verify
POST /api/auth/login
POST /api/auth/staff/login
POST /api/chat/message
GET  /api/student/profile
GET  /api/student/notices
GET  /api/student/exams
POST /api/student/backpaper
GET  /api/student/scholarships
POST /api/student/scholarships/apply
GET  /api/student/grievances
POST /api/student/grievances
GET  /api/withdrawal/guide
GET  /api/withdrawal/documents
GET  /api/withdrawal/status/{student_id}
POST /api/withdrawal/apply
GET  /api/withdrawal/{ref}/slip
GET  /api/withdrawal/track/{ref}
POST /api/documents/upload
GET  /api/admin/grievances
POST /api/admin/grievances/{id}/resolve
GET  /api/admin/documents
POST /api/admin/documents/{id}/verify
POST /api/notesheets
GET  /api/notesheets
GET  /api/notesheets/{id_or_ref}
POST /api/notesheets/{id_or_ref}/action
POST /api/notesheets/{id_or_ref}/edit-field
GET  /api/registry/status/{student_id}
POST /api/registry/status/update
GET  /api/registry/history/{student_id}
GET  /api/registry/roster/{branch_or_course}
GET  /api/registry/events
GET  /api/policy/search?q=...
POST /api/policy/guide
POST /api/voice/query
GET  /api/accreditation/co-attainment
GET  /api/accreditation/po-attainment
GET  /api/accreditation/cohort-summary
GET  /api/accreditation/export
GET  /api/institution/config
PUT  /api/institution/config
GET  /api/institution/clearance-chain
PUT  /api/institution/clearance-chain
GET  /api/institution/refund-slabs
PUT  /api/institution/refund-slabs
GET  /api/reports/analytics
GET  /api/reports/funnel
GET  /api/reports/bottlenecks
GET  /api/reports/export?report=analytics&format=csv
GET  /api/campuses
GET  /api/campuses/students?campus_code=NOIDA
GET  /api/campuses/{campus_code}/procedure-rules
PUT  /api/campuses/{campus_code}/procedure-rules/{procedure_type}
GET  /api/compliance/export/{student_id}
POST /api/compliance/erasure
GET  /api/compliance/audit-logs
GET  /api/compliance/retention-policies
POST /api/compliance/retention-cleanup
GET  /api/system/parity-check
GET  /api/health
```

## Target Stack

- Frontend: Flutter/Riverpod for kiosk/tablet/web target, static HTML/CSS/JS for current prototype testing only.
- Backend: FastAPI.
- Database: SQLite locally, PostgreSQL target.
- Cache/session/queue: Redis target.
- File storage: local uploads now, MinIO/S3 target.
- Auth: prototype student verification now, JWT/RBAC target.
- Advanced AI: local contextual fallback by default; set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY` to enable Gemini.
- Deployment: Docker Compose foundation included.

## Production deployment

Use the Phase 13 artifacts in [`deploy/`](deploy/README.md). Copy `.env.production.example` to `.env.production`, replace every placeholder, then start the stack with `docker compose --env-file .env.production -f docker-compose.production.yml up --build`.
