# Implementation Plan — Student Lifecycle Management Platform (AmityAssist)

We are converting the secure withdrawal chatbot into a complete AI-driven Student Lifecycle Management Platform for a university (modeled after Amity University). The system will feature a premium glassmorphic frontend, a personalized student dashboard, simulated Document AI OCR/fraud detection, a voice-activated AI assistant, and a multi-role admin/staff control panel.

---

## User Review Required

> [!IMPORTANT]
> **Key Architectural Choices & Scope:**
> 1. **Mock Services**: To keep execution self-contained and run-time dependencies zero (per existing architecture), features like Speech-to-Text, Text-to-Speech, and Document OCR will be implemented using HTML5 native APIs (Web Speech API) and backend simulation logic (simulating document classification/OCR/fraud checks).
> 2. **Multi-Role Flow**: A dropdown/role selector will be provided at the login/verification screen and in the dashboard to toggle between the **Student** view and various **Staff/Admin** views (Registrar, Admission Team, Finance, Scholarship Dept, etc.) to allow convenient demonstration of all workflows.
> 3. **Database Re-Seeding**: During startup, the SQLite database schema will be updated, and the database will be re-seeded with extensive profile info (attendance, CGPA, branch, notices, back papers, and scholarships) to enable full personalization.

---

## Proposed Changes

### Database Layer

#### [MODIFY] [seed.py](file:///c:/Users/WINDOWS%2011/OneDrive/Desktop/Assist/backend/database/seed.py)
- Expand the schema with new tables: `users` (for staff accounts), `notices`, `grievances`, `scholarships`, `scholarship_applications`, `examinations`, `internships`.
- Update the `students` table to add fields: `branch`, `semester`, `attendance`, `cgpa`, `fee_status`, `fee_due`, `hostel_status`, `scholarship_status`, `academic_performance`, `interests`.
- Add rich mock data: notices targeted to specific branches, sample examinations/results, internship postings, and department staff accounts.

---

### Backend API & Services

#### [MODIFY] [schemas.py](file:///c:/Users/WINDOWS%2011/OneDrive/Desktop/Assist/backend/models/schemas.py)
- Add schemas for new endpoints: notice list, scholarship application, exam results, grievance registration, and staff request operations.
- Update `VerifyResponse` to include the student's full profile details (attendance, CGPA, branch, etc.).

#### [MODIFY] [chat_service.py](file:///c:/Users/WINDOWS%2011/OneDrive/Desktop/Assist/backend/services/chat_service.py)
- Extend the FSM state machine to handle interactive inquiries about:
  - **Academics / Exams**: Asking about CGPA, attendance, or registering back papers.
  - **Scholarships**: Recommending scholarships based on CGPA and auto-applying.
  - **Grievance Desk**: Submitting grievances conversationally.
  - **Withdrawals**: Guide student through withdrawal steps, calculating tuition refund based on enrollment date, and listing required documents.
- Support multilingual responses (Hindi, Hinglish, English) based on voice toggles or user message language detection.

#### [NEW] [student.py](file:///c:/Users/WINDOWS%2011/OneDrive/Desktop/Assist/backend/routes/student.py)
- Add API endpoints for:
  - `GET /api/student/profile`: Fetch student profile.
  - `GET /api/student/notices`: Fetch personalized notices based on branch/semester.
  - `GET /api/student/exams`: Fetch exam schedules, grades, and admit cards.
  - `POST /api/student/backpaper`: Register for back papers.
  - `GET /api/student/scholarships`: Fetch eligible scholarships.
  - `POST /api/student/scholarships/apply`: Apply for a scholarship.
  - `POST /api/student/grievances`: File a grievance and track status.
  - `GET /api/student/internships`: Fetch internship opportunities.

#### [MODIFY] [documents.py](file:///c:/Users/WINDOWS%2011/OneDrive/Desktop/Assist/backend/routes/documents.py)
- Update upload endpoint to perform mock Document AI analysis:
  - OCR extraction of student name, ID, and signatures.
  - Verification checks (valid document, missing fields, duplicate detection, image quality).
  - Fraud detection (simulated checks for altered text, mismatched signatures, or fake stamps).
  - Save results to the `documents` table to display in the Admin Portal.

#### [MODIFY] [admin.py](file:///c:/Users/WINDOWS%2011/OneDrive/Desktop/Assist/backend/routes/admin.py)
- Expand dashboard APIs for staff roles:
  - `GET /api/admin/grievances`: Fetch grievances for coordinator/registrar.
  - `POST /api/admin/grievances/{id}/resolve`: Resolve grievance with comments.
  - `GET /api/admin/documents`: Fetch uploaded documents with Document AI flags.
  - `POST /api/admin/documents/{id}/verify`: Mark document verified or fraudulent.

#### [MODIFY] [main.py](file:///c:/Users/WINDOWS%2011/OneDrive/Desktop/Assist/backend/main.py)
- Mount the new `student` router.
- Clear/reset DB during local lifespan startup if structure changes are detected or environment is reset.

---

### Frontend UI & UX

#### [MODIFY] [index.html](file:///c:/Users/WINDOWS%2011/OneDrive/Desktop/Assist/frontend/index.html)
- Redesign the layout with a responsive, glassmorphic sidebar and high-fidelity tab screens:
  1. **Verify Screen**: Log in as a Student or select a Staff Role (Registrar, Admission, etc.).
  2. **Student Dashboard Tab**:
     - Personalized welcome and profile card.
     - Widget grid: Academics (Circular attendance chart, CGPA card), Finance (Fee due badge, hostel status), Scholarship (Current merit status).
     - Target Notices card (only showing notices relevant to the student's branch/semester).
     - Upcoming Deadlines and recommendations.
  3. **Academics & Exams Tab**:
     - Marks card showing grades.
     - Admit Card section: download admit card or register for back papers.
  4. **Scholarship Hub Tab**:
     - Discover eligible schemes, view application statuses, and auto-apply.
  5. **Document AI Center Tab**:
     - File drag-and-drop area.
     - Side-by-side Document AI OCR scanner (simulated green scanning bar with detected fields, image quality score, stamp/signature validity, duplicate check, and fraud check alerts).
  6. **Grievance Desk Tab**:
     - Category dropdown and description to file complaints.
     - Status tracker timeline (Submitted -> Under Review -> Resolved).
  7. **Withdrawal Wizard Tab**:
     - Conversational wizard side-by-side with a refund calculator (calculates refund based on days enrolled, lists fees outstanding).
  8. **Staff Portal Tab**:
     - Swapped layout showing requests pending review, document audit logs (with OCR details), grievances desk, and approval/rejection buttons.
  9. **Voice AI floating widget**:
     - Float button to trigger Microphone listening (Web Speech API) or synthesized responses.
     - Voice configurations (English/Hindi/Hinglish).

#### [MODIFY] [app.js](file:///c:/Users/WINDOWS%2011/OneDrive/Desktop/Assist/frontend/js/app.js)
- Handle tab switching, form submittals, and dashboard data fetching.
- Implement HTML5 Web Speech API for voice interactions and text-to-speech feedback.
- Add Document AI simulation interface: when a document is uploaded, show a scanning animation and render JSON-like OCR audit data.
- Handle staff actions (updating withdrawals, responding to grievances, verifying OCR results).

#### [MODIFY] [styles.css](file:///c:/Users/WINDOWS%2011/OneDrive/Desktop/Assist/frontend/css/styles.css)
- Implement premium glassmorphic styling:
  - `background: rgba(255, 255, 255, 0.4)` with `backdrop-filter: blur(12px)`.
  - Haromonious color palette (Amity Blue `#1B325D`, Amity Yellow `#FFCB05`, soft jade greens, light slate).
  - Modern card designs with hover effects, micro-animations, circular progress rings, and a toggle for Dark Mode.
  - Fully responsive mobile layout.

---

## Verification Plan

### Automated Tests
- Extend existing pytest suite in `backend/tests/` to validate:
  - Personalized notice fetching (`test_student.py`)
  - Scholarship eligibility logic and application storage (`test_student.py`)
  - Grievance registration and response logic (`test_student.py`)
  - Document AI OCR results & fraud flags storage (`test_documents.py`)
- Run commands:
  ```bash
  pytest -v
  ```

### Manual Verification
- Run the FastAPI backend: `uvicorn backend.main:app --reload`
- Open `frontend/index.html` in browser.
- Perform the following tests:
  1. Log in as Student `STU001` -> Verify personalized dashboard widgets (CGPA, Attendance, targeted notices).
  2. Speak a voice command or type "Register for back papers" -> Verify AI responds correctly and walks through registration.
  3. Upload an ID card / medical certificate -> Verify simulated scanning animations, OCR validation, signature check, and fraud check alerts.
  4. File a Grievance -> Switch to Staff Role (Department Coordinator) -> View grievance, type resolution, submit -> Switch back to student -> Verify grievance shows resolved with staff comments.
  5. Go to Withdrawal Wizard -> Calculate refund, upload signature file, type CONFIRM -> Verify request logged -> Log in as Registrar -> Approve withdrawal -> Check mock emails.
