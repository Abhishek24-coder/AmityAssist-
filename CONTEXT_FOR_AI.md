# UniAssist: Developer & AI Agent Context Manual

This document provides complete, unfiltered architectural context for any **AI Agent, LLM, or software developer** working on the **UniAssist** codebase. Read this file first before writing code, modifying database schemas, or implementing new features.

---

## 1. What UniAssist Is (And What It Is NOT)

* **UniAssist is NOT just a chatbot.** Do not attempt to reduce this project to a generic ChatGPT wrapper.
* **UniAssist IS an End-to-End Procedural Orchestration Platform and Digital Front Desk** for university environments.
* It bridges physical lobby touchscreen kiosks, administrative department staff desks (Library, Hostel, Accounts, Registrar), and personal student mobile devices into a single, unified, audit-proof workflow.

---

## 2. The Real-World Ground Truth (The Human Context)

Every line of code in this repository must solve real, agonizing friction observed on the ground in university administrative corridors:

1. **The 48 Withdrawal Bottlenecks & The Canada Student:**
   * A cohort of 48 students applied for withdrawal at once. One student moved abroad to Canada and is desperately trying to get clearances remotely.
   * When someone visits the Examination or Accounts desk on campus, clerks are uninformed or ask absurd questions like: *"Why are you paying this fee? What fee is this?"*.
   * **The Rule:** The system must generate standardized, pre-itemized clearance vouchers with immutable reference IDs citing the exact university ordinance code so no clerk can claim ignorance.
2. **The ₹200 Lost ID Card Deadlock (Smart Financial Offsetting):**
   * A student undergoing a ₹1,00,000 refund had their entire process halted for days because they lost their ₹200 plastic ID card, and a clerk demanded they walk to a bank counter in another block to pay a physical challan.
   * **The Rule:** Always support **Smart Deposit Offsetting**. If an asset fee is minor (under ₹2,000), allow the student to check a box to deduct it directly from their refundable caution deposit, letting the clearance continue instantly.
3. **The Paper "Notesheet" & The Physical Peon Runaround:**
   * Official approvals move through an administrative chain: `Supervisor` $\rightarrow$ `HOD` $\rightarrow$ `HOI` $\rightarrow$ `Pro-VC` $\rightarrow$ `VC`. Office peons physically carry paper folders across campus. If someone spots a single typo on page 2, the folder is rejected and everyone restarts from zero.
   * **The Rule:** Provide a **Collaborative Digital Notesheet** where senior officers can correct minor typos in-flight with an audit annotation without rejecting the entire file.
4. **The Communication Black Hole (Suspended Students):**
   * Suspensions are announced via email. Half the faculty miss the email, and suspended students continue attending labs or exams.
   * **The Rule:** Student status (`ACTIVE`, `SUSPENDED`, `DEBARRED`) must be a centralized, real-time single source of truth across all faculty attendance screens, exam hall scanners, and kiosks.
5. **The Accreditation & CO/PO Reporting Nightmare:**
   * Faculty spend late nights stitching spreadsheets to map Course Outcomes (CO) and Program Outcomes (PO) for NAAC and NBA reviews.
   * **The Rule:** The platform must auto-archive student progression and provide 1-click export of pre-formatted NAAC/NBA attainment matrices.
6. **Multi-University Generalization:**
   * Do not hardcode institutional names or static 4-step chains. The platform must be white-label and configurable so any university (Amity, Galgotias, Sharda, DU) can set up its own clearance chain, fee slabs, and branding.

---

## 3. Strict Architectural Commandments (DO NOT BREAK)

When modifying or expanding this codebase, you must adhere strictly to these architectural rules:

### Rule 1: Maintain the Dual-Runtime Abstraction
* The backend is designed to run in two environments without changing code:
  1. **Local Development & Standalone Kiosks:** Uses SQLite (`backend/database/connection.py`), local disk storage (`uploads/`), and in-memory caches.
  2. **Production Cloud Clusters:** Swappable for PostgreSQL (`DATABASE_URL`), MinIO / S3 object storage, and Redis.
* **Never write PostgreSQL-only raw SQL that breaks SQLite compatibility** (e.g., avoid proprietary JSON operators; use standard SQL with parameterized queries).

### Rule 2: Preserve the Middleware Stack Order
* In Starlette and FastAPI, middleware executes in reverse order of registration.
* **`CORSMiddleware` MUST be the outermost middleware** so it handles browser preflight `OPTIONS` requests before `SecurityHeadersMiddleware` or authentication checks execute. Do not reorder middleware in `backend/main.py` without understanding this requirement.

### Rule 3: Parameterized SQL Execution Only
* **Never use raw f-string SQL interpolation.** Always execute queries using parameter substitution (`cursor.execute("SELECT ... WHERE id = ?", (student_id,))`) to prevent SQL injection vulnerabilities.

### Rule 4: Flutter Navigation History Stack
* On web and kiosk, using `context.go()` clears the navigation history, which breaks the physical/browser back-button.
* **Always use `context.push()` for nested screens** so that `context.canPop()` remains true and the back button returns to the previous screen.
* Ensure fallback navigation routes safely check authentication status (e.g., unauthenticated users must route to `/services` or `/login`, never directly to `/dashboard`).

### Rule 5: Public Kiosk Touch & Privacy Standards
* Touch targets in `frontend_flutter/` must maintain a minimum size of 48x48 dp.
* All kiosk screens must be wired to the ambient `KioskTimerProvider`: if a terminal remains idle for 45 seconds, all cached user tokens and personal records must be purged, returning the terminal to the Welcome screen.

---

## 4. How to Execute Work Using `CHECKPOINT.md`

1. **Step 1: Inspect Status:**
   * Open [CHECKPOINT.md](file:///c:/Users/HP/ANtiAgentBuilding/CHECKPOINT.md).
   * Note that **Phases 0 through 20 are 100% completed and verified** with 110 passing automated tests.
   * Review the pending roadmap: **Phases 21 through 29**.
2. **Step 2: Understand the Immediate Target:**
   * Pick the next pending phase (e.g., **Phase 21: Multi-Department Clearance & Itemized Vouchers** or **Phase 22: Smart Financial Offsetting**).
   * Read the corresponding functional requirements in [SYSTEM_DESIGN.md](file:///c:/Users/HP/ANtiAgentBuilding/SYSTEM_DESIGN.md) and [GOAL.md](file:///c:/Users/HP/ANtiAgentBuilding/GOAL.md).
3. **Step 3: Execute Methodically:**
   * Write clean, modular code in backend routes and Flutter presentation widgets.
   * Write automated test cases in `backend/tests/`.
   * Run the test suite: `.venv\Scripts\python.exe -m pytest -q` and verify that all existing tests plus your new tests pass (0 failures).
4. **Step 4: Update the Checkpoint:**
   * Once a phase is verified, edit [CHECKPOINT.md](file:///c:/Users/HP/ANtiAgentBuilding/CHECKPOINT.md) and change `[ ]` to `[x]` for the completed items.

---

## 5. Directory Map & Key Files

* **`backend/main.py`**: FastAPI application entry point, middleware registration, and router mounting.
* **`backend/routes/`**: Modular API routers (`student.py`, `withdrawal.py`, `admin.py`, `forms.py`, `documents.py`, `auth.py`).
* **`backend/services/`**: Core business logic (`withdrawal_workflow.py`, `advanced_ai_service.py`, `chat_service.py`, `audit_service.py`).
* **`backend/database/connection.py`**: Dual-runtime database connection manager (SQLite / PostgreSQL).
* **`backend/database/seed.py`**: Seed data script for initial university courses, students, forms, and policies.
* **`frontend_flutter/lib/src/features/`**: Flutter feature modules:
  * `kiosk/`: Welcome screen, ambient inactivity timer, and touch controls.
  * `chat/`: Digital Advisor wizard modal and state notifier.
  * `forms/`: Forms catalog screen with instant PDF download bridge.
  * `withdrawal/`: Withdrawal guidance, checklist, and clearance timeline.
  * `staff/`: Multi-role staff action desks and grievance review.
* **`CHECKPOINT.md`**: Authoritative phase execution tracker.
* **`SYSTEM_DESIGN.md`**: Full architectural design specification.
* **`GOAL.md`**: Core project origin, mentor story, and institutional objectives.
* **`PHASE_BY_PHASE_EXECUTION.md`**: Detailed technical execution breakdown for every phase.
