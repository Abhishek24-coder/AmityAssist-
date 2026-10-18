# UNIASSIST

UNIASSIST is a workflow-centric Student Service and Procedure Guidance Platform for universities.

It acts as a digital front desk that guides students through official procedures from intent to completion:

```text
Intent -> Information -> Documents -> Submission -> Processing -> Completion
```

UNIASSIST is not a chatbot-only project, not an LLM project, and not a prediction system. Assistant-style interaction is only one interface over the structured workflow engine.

## Current Status

This repository currently contains the UNIASSIST prototype and target-stack scaffolding. The older static frontend remains useful for validating backend flows locally, but the intended kiosk/tablet frontend should continue in `frontend_flutter/`.

### Target Stack

- Frontend: Flutter for kiosk/tablet/web target
- State management: Riverpod
- Backend: FastAPI
- Database: PostgreSQL
- Authentication: JWT
- Caching: Redis
- Storage: MinIO or AWS S3
- Containerization: Docker
- Architecture: Clean Architecture, Repository Pattern, RBAC

### Phase 1 Status

Implemented in this phase:

- Structured Withdrawal Intelligence workflow API.
- Official withdrawal guide endpoint with steps, departments, required documents, forms, timelines, and statuses.
- Generated withdrawal checklist items when a student confirms a withdrawal request.
- Workflow event tracking for submitted withdrawal requests.
- PostgreSQL schema draft for the target platform.
- Docker Compose foundation for FastAPI, PostgreSQL, Redis, and MinIO.
- Environment-based backend configuration for database, Redis, JWT, S3/MinIO, and CORS.

Still local/prototype-based:

- Runtime database remains SQLite until PostgreSQL/Docker are available locally or deployed.
- Existing static HTML/CSS/JS remains a prototype validation surface only.
- `frontend_flutter/` contains the Flutter/Riverpod scaffold for the kiosk-grade interface.
- Existing session verification remains prototype-based until JWT authentication is implemented.

## Development Phases

### Phase 1: Withdrawal Intelligence MVP

Goal: Build the first workflow-centric procedure module.

Status: In progress.

Includes:

- Withdrawal guidance
- Withdrawal knowledge base
- Required document generation
- Form repository
- Checklist engine
- Workflow guidance
- Status tracking
- Official timeline guidance
- Refund process guidance without outcome prediction

### Phase 2: Core Platform Foundation

Goal: Move the backend fully onto the production platform foundation.

Planned:

- PostgreSQL runtime integration
- JWT authentication
- RBAC authorization
- Redis caching
- MinIO/S3 document storage
- Audit logging
- Repository pattern
- Clean Architecture layering

Status: Not started.

### Phase 3: Flutter / Kiosk Frontend

Goal: Build the student-facing UNIASSIST kiosk/tablet frontend using Flutter and Riverpod.

Planned:

- Student login
- Procedure dashboard
- Withdrawal workflow screens
- Checklist screen
- Form repository
- Document upload screen
- Status tracker
- Responsive mobile/web layouts

Status: Scaffold started. Login and withdrawal guidance screens exist; complete kiosk journey still remains.

Kiosk expectations:

- Touch-first flows with large tap targets.
- Minimal free typing.
- Clear session reset after completion or inactivity.
- Privacy-aware display of student data.
- Print/download/handoff support for official forms.
- Voice support only where the device/browser supports it.

## Existing Prototype Features

The older prototype currently includes:

- Expanded student lifecycle database and seed data.
- Student and staff backend routes for profiles, notices, exams, scholarships, grievances, documents, and chat.
- Conversational AI routing for academics, scholarships, exams, grievances, withdrawals, Hinglish/Hindi/English prompts, and refund estimates.
- Glassmorphic student dashboard.
- Student lifecycle view modules:
  - Academics tab with exam results and backpaper registration.
  - Scholarship Hub with scheme discovery and one-click application.
  - Grievance Desk with ticket form and timeline tracker.
  - Document AI panel with scan animation, OCR fields, and fraud warnings.
  - Floating voice widget using the browser Web Speech API.

## Quick Start: Current Local Prototype

Run these commands from the repository root:

```powershell
cd "c:\Users\WINDOWS 11\OneDrive\Desktop\Assist"
```

### 1. Install Dependencies

```powershell
pip install -r backend\requirements.txt
```

### 2. Start Backend

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

API docs:

```text
http://127.0.0.1:8000/api/docs
```

### 3. Start Frontend

Use a localhost frontend server instead of opening the file directly. This is important for browser voice permissions.

```powershell
cd frontend
python -m http.server 5500 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:5500/index.html
```

## Login / UI Behavior

The app starts with only the verification screen visible. The sidebar, topbar dashboard shell, module navigation, and voice widget appear only after successful student verification.

Demo login:

```text
Student ID: STU001
```

You can also use seeded institutional email addresses.

## Voice System

The floating voice widget appears after login.

- `Mic`: starts browser speech transcription and sends the transcript to AI Advisor when a session is active.
- `Speak`: reads the latest AI Advisor reply aloud.

Notes:

- Use Chrome or Edge for the best Web Speech API support.
- Microphone access requires browser permission.
- Run the frontend from `http://127.0.0.1:5500/index.html`; raw `file://` pages may block or limit voice behavior.

## Test Suite

Run:

```powershell
python -m pytest
```

Expected current result:

```text
231 passed (100% pass rate)
```

## Main Endpoints

```text
POST /api/auth/verify
POST /api/chat/message
GET  /api/student/profile
GET  /api/student/notices
GET  /api/student/exams
POST /api/student/backpaper
GET  /api/student/scholarships
POST /api/student/scholarships/apply
GET  /api/student/grievances
POST /api/student/grievances
POST /api/documents/upload
GET  /api/health
```

## Project Structure

```text
AmityAssist-/
  backend/
    main.py
    database/
    middleware/
    models/
    routes/
    services/
    tests/
  database/
    chatbot.db
  documentation/
    README.md
  frontend/
    index.html
    css/styles.css
    js/app.js
  task.md
  pytest.ini
```

## Phase 6 Next

Phase 6 is the staff portal and end-to-end verification phase:

- Continue kiosk frontend work in `frontend_flutter/`.
- Staff Portal tab.
- Approval center.
- Grievance responses.
- Document audit records.
- Staff portal API actions.
- Full client-server walkthrough.

## Target Stack Startup

Docker and Flutter are not currently available in this local environment. Once Docker is installed, the target-stack services can be started with:

```powershell
docker compose up --build
```

Services:

```text
FastAPI:     http://127.0.0.1:8000
API docs:    http://127.0.0.1:8000/api/docs
PostgreSQL:  localhost:5432
Redis:       localhost:6379
MinIO:       http://127.0.0.1:9001
```
