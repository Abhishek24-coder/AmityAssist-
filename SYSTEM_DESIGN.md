# UniAssist: System Design & Architecture Specification

This document provides the complete, end-to-end technical system design for **UniAssist**. It details how every component, service, data pipeline, and user interface works and interacts across the platform.

---

## 1. High-Level Architecture Overview

UniAssist is architected as a distributed, service-oriented platform separating the touch-first presentation layer, the high-throughput API gateway, the workflow state machine, and the persistent data layer.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             PRESENTATION TIER                               │
│                                                                             │
│  ┌───────────────────────────────┐     ┌─────────────────────────────────┐  │
│  │   LOBBY KIOSK TABLETS         │     │   WEB & MOBILE CLIENTS          │  │
│  │   • Flutter Touch-First UI    │     │   • Student Personal Portal     │  │
│  │   • 45s Inactivity Auto-Purge │     │   • Department Staff Cockpit    │  │
│  │   • Tap-Based Advisor Wizard  │     │   • Dean & Executive Dashboard  │  │
│  └───────────────┬───────────────┘     └────────────────┬────────────────┘  │
└──────────────────┼──────────────────────────────────────┼───────────────────┘
                   │ HTTPS / REST API & WebSockets        │
                   ▼                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY & APPLICATION TIER                     │
│                               (FASTAPI / PYTHON 3.11+)                      │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Middleware Stack: CORS (Outer) -> TrustedHost -> SecurityHeaders     │  │
│  │ JWT Authentication & Role-Based Access Control (RBAC)                 │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │                                      │
│  ┌───────────────────────────┐       │       ┌───────────────────────────┐  │
│  │ CORE LIFECYCLE ROUTERS    │       │       │ WORKFLOW & ADMIN ROUTERS  │  │
│  │ • /api/auth               │◄──────┤──────►│ • /api/admin/notesheet    │  │
│  │ • /api/student/profile    │       │       │ • /api/admin/grievance    │  │
│  │ • /api/student/academics  │       │       │ • /api/admin/clearance    │  │
│  │ • /api/withdrawal         │       │       │ • /api/admin/accreditation│  │
│  │ • /api/forms              │       │       │ • /api/documents          │  │
│  │ • /api/chat (Advisor)     │       │       │ • /api/institution/config│  │
│  └───────────────────────────┘       │       └───────────────────────────┘  │
│                                      ▼                                      │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ SERVICE ENGINES:                                                      │  │
│  │ • State Machine (FSM) Workflow Engine  • Refund Calculation Engine    │  │
│  │ • Smart Caution Deposit Offset Engine  • Digital Notesheet Engine     │  │
│  │ • Real-Time Student Status Registry    • CO/PO Accreditation Engine   │  │
│  │ • Local Tesseract OCR Engine           • Token Slip PDF Generator     │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
┌─────────────────────────┐   ┌─────────────────────────┐   ┌─────────────────────────┐
│     DATABASE LAYER      │   │  INTELLIGENCE & SEARCH  │   │     STORAGE LAYER       │
│ • SQLite (Dev/Kiosks)   │   │ • SQLite FTS5 Search    │   │ • Local File Storage    │
│ • PostgreSQL (Prod)     │   │   (BM25 Inverted Index) │   │ • MinIO / S3 Buckets    │
│ • Parameterized Queries │   │ • Hybrid Cloud LLM      │   │ • Content-Addressable   │
│ • Immutable Audit Logs  │   │   (Gemini Flash RAG)    │   │   SHA-256 Hashing       │
└─────────────────────────┘   └─────────────────────────┘   └─────────────────────────┘
```

---

## 2. Frontend Architecture (Flutter Web & Kiosk)

The frontend is implemented in `frontend_flutter/` using Flutter 3.x and Dart, ensuring a single codebase runs seamlessly on lobby kiosk tablets, desktop web browsers, and mobile devices.

### Key Architectural Subsystems:
1. **Touch-First Design System (`lib/src/core/theme/`):**
   * High-contrast, accessibility-compliant color tokens (Deep Navy `#0A192F`, Warm Gold, Emerald Green, Warning Crimson).
   * Minimum touch targets of 48x48 dp for kiosk reliability.
   * Responsive adaptive layouts (Kiosk Wide View, Desktop Split View, Mobile Compact View).
2. **State Management (`flutter_riverpod`):**
   * Decoupled functional domains using `StateNotifierProvider` and `FutureProvider`.
   * Clear separation between presentation widgets and application business logic.
3. **Session Privacy & Auto-Expiring Timer:**
   * An ambient `KioskTimerProvider` monitors user interaction.
   * If no touch or input is detected for **45 seconds**, an overlay warning modal counts down for 10 seconds.
   * If untouched, all session tokens, cached profile data, and form states are purged from memory, automatically returning the terminal to the Welcome screen.
4. **Client-Side Download & Document Bridge (`download_service.dart`):**
   * Universal document handling using HTML blob anchors on web and file system drivers on native platforms.
   * Supports immediate in-browser preview or direct physical download with sanitized file naming.

---

## 3. Backend Architecture (FastAPI & Modular Services)

The backend in `backend/` is designed around asynchronous, non-blocking Python 3.11+ using FastAPI, strict Pydantic v2 schemas, and parameterized SQL operations.

### Key Architectural Subsystems:
1. **Middleware Ordering & Security:**
   * **CORSMiddleware (Outermost):** Positioned correctly to handle browser preflight `OPTIONS` requests before authentication or security headers execute.
   * **SecurityHeadersMiddleware:** Enforces `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, and strict CSP policies.
   * **TrustedHostMiddleware:** Guards against HTTP Host header injection attacks.
2. **Authentication & Role-Based Access Control (RBAC):**
   * Stateless JWT tokens (`HS256`) signed with short expiration windows.
   * Enforces role separation: `STUDENT`, `STAFF_LIBRARY`, `STAFF_HOSTEL`, `STAFF_ACCOUNTS`, `HOD`, `DEAN`, `REGISTRAR`, `ADMIN`.
3. **Dual-Runtime Storage & Database Abstraction:**
   * Automatic environment detection in `backend/database/connection.py`.
   * **Development & Standalone Kiosks:** Uses SQLite with full-text search (`FTS5`) and local disk storage.
   * **Production Multi-Server Clusters:** Swappable drop-in configuration for PostgreSQL connection pooling, Redis caching, and MinIO/S3 object buckets.

---

## 4. Detailed Component Design & Workflows

---

### 4.1 Multi-Department "No-Dues" Clearance & Refund Engine

```
[ Student Initiates Withdrawal ]
               │
               ▼
[ 1. Deterministic UGC Refund Math ]
  • Analyzes: Semester Start Date vs Current Date
  • Calculates exact refund slab (e.g. 50% tuition minus ₹1,000 fee)
               │
               ▼
[ 2. Generates Standardized Clearance Voucher ]
  • Immutable Reference ID: AMITY-WTH-2026-0042
  • Cites exact university ordinance code (No clerk confusion)
               │
               ▼
[ 3. Sequential Clearance Pipeline ]
  ┌─────────────────────────────────────────────────────────────┐
  │ Step 1: Library Desk       ──> Verifies 0 unreturned books   │
  │ Step 2: Hostel Warden Desk  ──> Verifies room key handover   │
  │ Step 3: Accounts Desk       ──> Reconciles fee ledger/bank   │
  │ Step 4: Registrar Desk      ──> Digital sign-off & seal      │
  └─────────────────────────────────────────────────────────────┘
               │
               ▼
[ 4. Mobile QR Handshake & Real-Time Sync ]
  • Generates official PDF Token Slip with dynamic QR code
  • Student tracks clearance on mobile phone from anywhere in the world
```

* **Data Model:** `clearance_requests`, `clearance_steps`, `clearance_audit_log`.
* **State Invariant:** No request can transition to `COMPLETED` unless all preceding departmental gates have valid digital signatures and officer timestamps.

---

### 4.2 Smart Financial Offsetting (The ₹200 Lost ID Card Solution)

```
[ Department Officer Flags Minor Asset Due ]
(e.g., Lost Plastic ID Card: ₹200 / Unreturned Book Fine: ₹50)
                       │
                       ▼
         [ Is Asset Replacement Cost <= ₹2,000? ]
                       │
             ┌─────────┴─────────┐
             ▼ YES               ▼ NO (Major Damage)
  [ Offer Smart Offsetting ]   [ Standard Bank Challan Required ]
  "Deduct ₹200 from your
   refundable deposit?"
             │
             ▼
  [ Student Checks Box ]
             │
             ▼
  [ Automated Ledger Re-balancing ]
  • Refundable Caution Deposit: ₹10,000 ──> ₹9,800
  • Asset Status: Marked as CLEARED_VIA_OFFSET
  • Clearance Workflow Continues Instantly Without Stopping
```

* **Advantage:** Prevents halting a ₹1,00,000 refund for days over a ₹200 lost plastic card.

---

### 4.3 Collaborative Digital "Notesheet" Workflow

```
[ Faculty Initiates Notesheet ] ──> [ HOD Desk ] ──> [ HOI / Director ] ──> [ Pro-VC ] ──> [ Vice Chancellor ]
                                        │                     │                    │
                                        ▼                     ▼                    ▼
                           ┌─────────────────────────────────────────────────────────────────────────┐
                           │               COLLABORATIVE IN-FLIGHT EDITING LAYER                     │
                           │ Senior officer notices typo in course code or student name:             │
                           │ • Edits field directly in digital document                              │
                           │ • Appends automated audit note: "Corrected CS101 to CS102 - HOD"        │
                           │ • File advances immediately (NO REJECTION, NO PEON RUNAROUND)           │
                           └─────────────────────────────────────────────────────────────────────────┘
```

* **Eliminates:** Physical peons running red paper folders across campus, and file rejections over minor administrative typos.
* **Audit Trail:** Every edit, comment, and signature is recorded with the officer's Employee ID, IP address, and cryptographic timestamp.

---

### 4.4 Centralized Real-Time Student Status Registry

```
[ Disciplinary / Attendance Event ]
(e.g., Student Suspended for 14 Days or Debarred for Attendance)
                 │
                 ▼
[ Proctorial Board Updates Status in Registry ]
  Status: TEMPORARILY_SUSPENDED
                 │
                 ▼
[ IMMEDIATE REAL-TIME BROADCAST TO ALL INTERFACES ]
  ├── 1. Faculty Attendance Portal: Student highlighted in RED with warning banner
  ├── 2. Exam Hall Entry Scanner: Barcode scan triggers visual lock & warning
  ├── 3. Campus Kiosks: Account locked; prompts student to visit Proctor's office
  └── 4. Library / Facilities: Borrowing privileges temporarily suspended
```

* **Eliminates:** The communication failure where faculty miss emails and unwittingly allow suspended students into classes or exam halls.

---

### 4.5 Document Upload & Local Automated OCR Verification

```
[ Student Uploads ID Card / Bank Challan (PNG/JPG/PDF) ]
                       │
                       ▼
[ 1. Cryptographic SHA-256 Hash Check ]
  • Rejects identical duplicate files instantly
                       │
                       ▼
[ 2. Python Tesseract Local OCR Engine ]
  • Binarizes image matrix, detects text bounding boxes
  • Extracts: Student Name, Enrollment Number, Date, Amount
                       │
                       ▼
[ 3. Automated Profile Cross-Check ]
  • Compares extracted Enrollment Number with logged-in Student ID
  • MATCH: Status = AUTO_VERIFIED (Confidence >= 95%)
  • MISMATCH: Status = MISMATCH_FLAGGED (Warns student immediately)
                       │
                       ▼
[ 4. Staff Inspection Cockpit ]
  • Displays uploaded document side-by-side with extracted OCR text
  • Reduces clerk verification time from 3 minutes to 5 seconds
```

---

### 4.6 Grievance Desk with SLA Countdown & Automatic Dean Escalation

* **Categories:** *Hostel Infrastructure*, *Academic Evaluation*, *Fee Discrepancies*, *Harassment / Ragging / Safety*.
* **Privacy:** Supports 1-tap **Anonymous Submission** with a cryptographic retrieval token.
* **SLA Countdown Timer:**
  * Safety / Harassment: Mandatory **24-hour resolution SLA**.
  * Facilities / Hostel: Mandatory **48-hour resolution SLA**.
* **Automatic Escalation:** If the assigned department does not log an action before the timer expires, the ticket turns RED and automatically alerts the Dean of Student Welfare.

---

### 4.7 Printable QR Token Slip Generator

* **Engine:** Headless PDF rendering service (`backend/services/token_pdf_service.py`).
* **Output:** Clean, official 1-page A4 document featuring:
  * University Header and Coat of Arms.
  * Unique Reference ID (`AMITY-CLR-2026-0042`).
  * Student Name, Enrollment Number, Course, and Date.
  * Itemized Department Clearance Checklist Table.
  * **Dynamic 2D QR Code:** Encodes the live tracking URL (`http://<host>/status?ref=...`).
* **Mobile Handshake:** Scanning the QR code with any smartphone camera opens a responsive, read-only tracking view without requiring login.

---

### 4.8 Accreditation & CO/PO Reporting Engine

* **Purpose:** Alleviates the faculty burden of manually compiling Course Outcome (CO) and Program Outcome (PO) attainment spreadsheets for NAAC, NBA, and UGC accreditation.
* **Mechanism:**
  * Maps internal evaluation marks, final exam results, and course projects against configured program outcomes (PO1 to PO12).
  * Automatically calculates attainment percentages across active, withdrawn, and graduated cohorts.
  * **1-Click Export:** Generates official Excel/PDF reports matching NAAC Criterion 2.6 templates.

---

### 4.9 Multi-University White-Label Configurator

* **Purpose:** Ensures the platform is universal and can be deployed at any university without code modifications.
* **Configuration Capabilities:**
  * **Institution Identity:** University Name, Crest/Logo, Color Palette, and Domain.
  * **Custom Department Chain:** Dynamically add, reorder, or remove clearance desks (e.g., add *Proctorial Desk*, remove *Hostel Desk* for day-scholar campuses).
  * **Custom Refund Policies:** Define custom cutoff day brackets and refund percentages.
  * **Document Templates:** Upload university-specific application forms and guideline PDFs.

---

## 5. Security, Privacy & Regulatory Compliance

1. **GDPR & Digital Personal Data Protection (DPDP) Compliance:**
   * Right to Data Portability: Students can export their complete profile, marks, and audit logs as a structured JSON/PDF file.
   * Right to be Forgotten: Anonymizes personal identifiers while preserving mathematical accreditation aggregates.
2. **Tamper-Evident Audit Logging:**
   * Every administrative action (approval, rejection, document view, notesheet edit) is written to an append-only audit table with IP address, employee ID, and UTC timestamp.
3. **Kiosk Boundary Lockdown:**
   * Prevents browser navigation escape, disables developer tools on touchscreens, and isolates downloaded files.
