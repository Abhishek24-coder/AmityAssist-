# UniAssist: Master Implementation Blueprint & Operational Architecture

This document serves as the complete technical and functional specification for **UniAssist**—a universal, workflow-centric student service and procedure orchestration platform designed to eliminate the bureaucratic friction, physical runaround, lost paperwork, and administrative overload in university environments.

---

## 1. The Real-World Problem Context

In actual university operations (as observed on the ground with over 48 simultaneous student withdrawal cases), simple, transparent procedures have collapsed into chaotic, high-friction administrative bottlenecks:

1. **The Remote Student & Frustrated Clerks:** A student moves abroad (e.g., to Canada) and desperately tries to get clearance remotely. When someone visits the Accounts or Examination office on campus, clerks either do not know the protocol, are too frustrated to answer, or ask absurd questions like: *"Why are you paying this fee? What is this fee for?"*.
2. **The ₹200 Lost ID Card Deadlock:** A student completing a ₹1,00,000 withdrawal refund has their entire file frozen because they lost their plastic ID card (worth ₹200). The clerk demands the student visit a physical bank counter in another block, pay a ₹200 challan, and bring back a paper slip, delaying a large refund for days over a trivial fee.
3. **The Paper "Notesheet" & Peon Runaround:** Official files move through an administrative chain (Supervisor $\rightarrow$ HOD $\rightarrow$ HOI $\rightarrow$ Pro-VC $\rightarrow$ Vice Chancellor) via physical paper folders carried by office peons. If a senior official spots a minor typo or wrong subject code on page 2, the entire physical folder is rejected and sent back down the chain, forcing faculty to re-print, re-sign, and restart from zero.
4. **The Communication Black Hole (Suspended Students):** Official notifications (e.g., student suspensions or debarments) are broadcast via email. Some faculty read it, while others miss it. Suspended students continue attending classes or exams because there is no single, real-time source of truth for student status.
5. **The Accreditation & CO/PO Reporting Burden:** Faculty coordinators spend late nights manually stitching spreadsheets to track Course Outcomes (CO) and Program Outcomes (PO) marks mapping for accreditation bodies (NAAC, NBA, UGC) while simultaneously tracking active, withdrawn, and graduated student files.
6. **Institutional Customization Need:** The application cannot be hardcoded for one specific university campus; it must be **generalized and configurable** so any university can set up its own clearance chains, refund slabs, and branding.

---

## 2. Technical Stack & Architecture

UniAssist is architected as a high-performance, modular system designed for physical kiosk terminals, web browsers, and mobile devices.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   FRONTEND (FLUTTER WEB / KIOSK)                       │
│  • Touch-First Kiosk UI (Large Buttons, Minimal Typing, Riverpod)      │
│  • Auto-Expiring Session Timer (45s Inactivity Privacy Purge)          │
│  • Responsive Student & Staff Portals (Web / Tablet / Mobile)          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST & WebSockets
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     BACKEND (FASTAPI / PYTHON 3.11+)                   │
│  • Decoupled Modular Routers (Auth, Clearance, Notesheets, Documents)  │
│  • Strict Pydantic v2 Request/Response Schemas & Data Validation       │
│  • JWT Authentication & Fine-Grained Role-Based Access Control (RBAC)  │
│  • Deterministic Workflow State Machine Engine                         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌─────────────────┐       ┌───────────────────┐      ┌──────────────────┐
│ DATABASE LAYER  │       │ INTELLIGENCE & OCR│      │ STORAGE & FILES  │
│ SQLite (Dev) /  │       │ SQLite FTS5 Search│      │ Local Uploads /  │
│ PostgreSQL(Prod)│       │ Python Tesseract  │      │ MinIO / AWS S3   │
│ Inverted Index  │       │ Hybrid LLM/Gemini │      │ Branded PDF Gen  │
└─────────────────┘       └───────────────────┘      └──────────────────┘
```

* **Frontend Layer (Flutter):** Built with Google Flutter for cross-platform responsiveness. Optimized for lobby touchscreens (large button targets, guided wizards) with automatic privacy session timers.
* **Backend Layer (FastAPI):** High-throughput asynchronous Python backend using modular routers, parameterized SQL execution, and JWT token authentication.
* **Database & Search Layer:** SQLite with full-text search (`FTS5`) for development and local kiosks; PostgreSQL with `pgvector` or full-text indexing for production multi-server deployments.
* **Intelligence Layer:** Deterministic state machines for legal and financial math, complemented by local FTS5 policy search and optional free-tier AI summarization.

---

## 3. Core Modules, Processes & Real-World Examples

---

### Module 1: Multi-Department "No-Dues" Clearance & Refund Engine

#### The Problem It Solves
Stops the multi-day physical runaround between 5 campus buildings, and provides full transparency for students abroad (e.g., Canada) who cannot visit offices in person.

#### How It Works
1. **Application:** Student initiates a clearance request on the kiosk or web portal.
2. **Automated Fee Ledger Audit:** The system automatically audits the student's enrollment date against the academic calendar and computes the exact legal refund slab according to UGC guidelines (e.g., 80% tuition refund minus ₹1,000 administrative fee).
3. **Itemized Fee Voucher Generation:** Generates a standardized, digital route voucher with an immutable tracking ID (e.g., `AMITY-WTH-2026-0042`). No clerk can ask *"What is this fee for?"* because the voucher cites the exact ordinance code.
4. **Sequential Clearance Pipeline:** The request automatically queues across authorized departments:
   $$\text{Library} \longrightarrow \text{Hostel} \longrightarrow \text{Accounts (Ledger)} \longrightarrow \text{Registrar}$$
5. **Staff Portal Sign-Off:** Each department officer logs into their portal, reviews the file, and clicks **"Clear Dues"** with one tap.

#### Real-World Walkthrough Example
* **Student:** Rohan Verma (B.Tech CSE, Semester 1) moved abroad to Canada and applies for withdrawal online on Day 18 of the semester. Total tuition paid: ₹1,20,000.
* **System Action:** System calculates: Day 18 falls in the 16–30 day slab (50% refund). Net refund calculated: ₹59,000 (`₹1,20,000 × 50% - ₹1,000 processing fee`).
* **Clearance Progression:**
  * Central Library: Librarian logs in, checks system, sees 0 books issued $\rightarrow$ clicks `[Approve Clearance]`.
  * Hostel Office: Warden verifies room inspection $\rightarrow$ clicks `[Approve Clearance]`.
  * Accounts Office: Officer verifies bank account details $\rightarrow$ marks voucher `[Processed for Wire Transfer]`.
  * Registrar: Final digital seal applied.
* **Outcome:** Rohan tracks the entire progression live on his phone from Toronto with zero physical campus visits.

---

### Module 2: Smart Financial Offsetting (The ₹200 Lost ID Card Solution)

#### The Problem It Solves
Prevents a ₹1,00,000 refund from being blocked for days because of a missing ₹200 plastic card or a ₹50 overdue library book.

#### How It Works
1. When a clearance officer flags a minor missing asset (e.g., Lost Student ID Card, Unreturned Lab Manual, Minor Library Overdue Fine), they enter the asset replacement cost.
2. Instead of halting the workflow and demanding a paper bank challan, the system prompts the student with a **Smart Offsetting Checkbox**:
   > *"You have an outstanding fee of ₹200 for [Lost Plastic ID Card]. Would you like to deduct this directly from your refundable Security Deposit of ₹10,000?"*
3. The student checks the box $\longrightarrow$ the system automatically updates the ledger:
   * *Security Deposit Refundable:* ₹10,000 $\longrightarrow$ ₹9,800.
   * *Asset Clearance Status:* Instantly marked as `CLEARED via Deposit Offset`.
4. The workflow continues immediately without pausing.

#### Real-World Walkthrough Example
* Aman is completing his clearance. The security guard notes that Aman lost his ID card.
* In the old system: Aman had to walk to Block 2, stand in a bank queue for 45 minutes to pay ₹200, get a physical pink receipt, take it back to the guard, and wait for the guard's signature.
* In UniAssist: The guard taps `[Flag Lost ID - ₹200]`. Aman receives an alert on his screen, taps `[Deduct ₹200 from Security Deposit]`. The guard's screen turns GREEN instantly. The clearance is finished in 10 seconds.

---

### Module 3: The Collaborative Digital "Notesheet" Workflow

#### The Problem It Solves
Eliminates physical peons carrying paper folders across campus and prevents entire files from being rejected over minor typos.

#### How It Works
1. **Initiation:** A faculty member or coordinator initiates an official administrative Notesheet (e.g., *Disciplinary Action*, *Fee Waiver Request*, *Special Exam Condonation*).
2. **Sequential Approval Hierarchy:** Configured per university policy:
   $$\text{Faculty Coordinator} \longrightarrow \text{HOD} \longrightarrow \text{HOI (Director)} \longrightarrow \text{Pro-VC} \longrightarrow \text{Vice Chancellor}$$
3. **Collaborative In-Flight Editing:**
   * If the Dean or HOD notices a mistake (e.g., typo in the student's name, wrong course code, or missing date), they do not reject the file.
   * Authorized officers can click **"Suggest Edit / Modify Field"**, correct the text, and append a digital audit note (e.g., *"Corrected course code from CS101 to CS102 - HOD"*).
4. **Digital Sign-Off:** Each officer signs with their digital credentials. The file advances to the next desk instantly with zero physical transit time.

#### Real-World Walkthrough Example
* A suspension notesheet for Student S-104 is drafted by the disciplinary committee.
* The physical folder used to take 6 days to travel from the department to the Vice Chancellor’s office via peons.
* On day 5, the Pro-VC noticed the semester was marked as "Semester 4" instead of "Semester 3". The paper folder was rejected and sent back to the supervisor, losing another week.
* In UniAssist: The Pro-VC clicks `[Edit Metadata]`, changes Semester 4 to Semester 3, adds a 1-sentence note, and clicks `[Approve & Forward to Vice Chancellor]`. The Vice Chancellor approves it 5 minutes later. Total time: 2 hours instead of 2 weeks.

---

### Module 4: Centralized Student Registry & Real-Time Status Alerts

#### The Problem It Solves
Stops the communication failure where suspended or debarred students continue attending classes because faculty missed an email announcement.

#### How It Works
1. **Single Source of Truth:** Every student record has an active operational status:
   * `ACTIVE_ENROLLED`
   * `UNDER_CLEARANCE`
   * `WITHDRAWN_ARCHIVED`
   * `TEMPORARILY_SUSPENDED`
   * `DEBARRED_ATTENDANCE`
2. **Immediate System-Wide Sync:** When the Proctor or Registrar marks a student as `SUSPENDED`, this status is pushed instantly across the entire platform:
   * **Faculty Attendance Portal:** The student's name is highlighted in RED with a banner: *"SUSPENDED - Cannot Attend Lab/Class until [Date]"*.
   * **Exam Hall Scanner:** Scanning the student's barcode at the exam hall door displays a visual lock: *"Entry Debarred by Proctorial Board"*.
   * **Campus Kiosk:** Logging in informs the student: *"Your account is temporarily suspended. Please report to the Proctorial Office."*

#### Real-World Walkthrough Example
* Student Priya is suspended for 14 days following a disciplinary hearing at 11:00 AM.
* At 11:02 AM, the Proctorial Board updates her status to `TEMPORARILY_SUSPENDED`.
* At 11:30 AM, Priya tries to enter the Physics Lab. The faculty member takes attendance on the portal—Priya's name is locked in red. The faculty member politely directs Priya to the department office without any confusion or reliance on unread emails.

---

### Module 5: Academic Accreditation & Lifecycle Records (CO / PO Engine)

#### The Problem It Solves
Relieves faculty from the late-night burden of manually digging through paper records to calculate Course Outcomes (CO) and Program Outcomes (PO) for accreditation bodies (NAAC, NBA, UGC).

#### How It Works
1. **Continuous Lifecycle Archival:** When a student graduates, withdraws, or advances semesters, their academic achievements, internal assessment marks, and backpaper records are permanently indexed in an immutable archival table.
2. **CO/PO Attainment Matrix Engine:** The system maps internal and external marks against the university's configured Course Outcomes (CO1, CO2, CO3) and Program Outcomes (PO1 to PO12).
3. **1-Click Accreditation Export:** Faculty coordinators can navigate to the **Accreditation Hub**, select an academic year and department, and tap:
   * `[Export NAAC Criterion 2.6 Report (CO-PO Attainment)]`
   * `[Export Student Progression & Retention Summary]`
   * The system outputs a pre-formatted Excel / PDF report ready for direct submission to inspection committees.

#### Real-World Walkthrough Example
* The NAAC peer review team visits campus and requests proof of student retention and Course Outcome attainment for the 2024–2025 B.Tech cohort.
* In the old system: 3 faculty members spent an entire weekend sorting through old marksheets and paper files.
* In UniAssist: The coordinator logs into the Staff Portal, selects *Cohort 2024*, taps *Export NAAC Matrix*, and downloads the validated file in 4 seconds.

---

### Module 6: Multi-University Generalization (White-Label Configurator)

#### The Problem It Solves
Ensures UniAssist is a universal, plug-and-play platform that can be deployed at any university campus (Amity, Galgotias, Sharda, Delhi University, etc.) without rewriting code.

#### How It Works
1. **Super-Admin Institution Settings:** A clean administrative panel where university administrators can configure:
   * **Institution Branding:** Name, Logo, Theme Colors (e.g., Amity Navy/Gold vs Galgotias Blue).
   * **Department Registry:** Add, rename, or reorder clearance desks (e.g., add *Proctor Office*, remove *Hostel Office* for day-scholar campuses).
   * **Custom Refund Rules:** Define custom refund percentages and cutoff days matching the university's specific ordinances.
   * **Custom Forms Repository:** Upload university-specific application PDFs.
2. **Dynamic Tenant Isolation:** All database queries scope automatically to the active campus or institution ID.

#### Real-World Walkthrough Example
* An engineering college in Pune adopts UniAssist.
* Instead of hiring developers to recode the app, the IT Director opens the Admin Configurator:
  * Uploads their university crest.
  * Sets up a 3-step clearance chain: `Department HOD` $\rightarrow$ `Accounts` $\rightarrow$ `Principal`.
  * Saves the configuration.
* All kiosk screens and student portals update immediately to reflect the new institutional workflow.

---

### Module 7: Physical-to-Digital Kiosk Bridge (QR Slip & Privacy Purge)

#### The Problem It Solves
Provides tangible proof when students leave the lobby kiosk and ensures student privacy in public spaces.

#### How It Works
1. **45-Second Inactivity Guard:** An automated background timer detects when a student walks away. If no touch is registered for 45 seconds, the screen displays a 10-second countdown and completely purges all cached student profile data, returning to the Welcome screen.
2. **Printable Token Slip with Live QR:**
   * Completing any major transaction (Withdrawal, Grievance, Backpaper Registration) prompts: `[Print / Save Official Token Slip]`.
   * The kiosk renders a clean, branded 1-page PDF featuring:
     * University Header & Coat of Arms
     * Tracking Reference Number (`AMITY-CLR-2026-0042`)
     * Timestamp & Student Metadata
     * Itemized Fee / Refund Breakdown
     * **A live, high-resolution QR code**.
3. **The Mobile Handshake:** Pointing any phone camera at the QR code opens a lightweight, mobile status page, allowing the student to track clearances on the go without installing an app.

---

## 4. Master Operational Flow

```
[ STUDENT AT LOBBY KIOSK ]
         │
         ├── Explores forms / searches policies (FTS5 Search)
         ├── Logs in via Student ID & PIN
         │
         ▼
[ INITIATES WITHDRAWAL / CLEARANCE ]
         │
         ├── System calculates exact refund slab deterministically
         ├── Minor unreturned asset? -> Opts for [Deduct from Security Deposit]
         │
         ▼
[ DIGITAL WORKFLOW GENERATED (REF: AMITY-CLR-0042) ]
         │
         ├── Kiosk prints/downloads Token Slip with QR Code
         ├── Student scans QR -> tracks live progress on personal smartphone
         │
         ▼
[ DEPARTMENT CLEARANCE DESKS (STAFF PORTAL) ]
         │
         ├── Library Staff: Verifies 0 books -> Clicks [Clear Dues]
         ├── Hostel Warden: Verifies room -> Clicks [Clear Dues]
         ├── Accounts Office: Ledger reconciled -> Clicks [Clear Dues]
         │
         ▼
[ DIGITAL NOTESHEET APPROVAL HIERARCHY ]
         │
         ├── Supervisor -> HOD -> HOI -> Pro-VC -> Vice Chancellor
         ├── In-flight edit corrects minor typos without file rejection
         │
         ▼
[ REGISTRAR FINAL DIGITAL SIGN-OFF ]
         │
         ├── Status updates to COMPLETED across all screens
         ├── Student receives final confirmation on smartphone
         └── Record auto-archived for NAAC/NBA CO-PO Accreditation
```

---

## 5. Phased Implementation Roadmap

To execute this platform cleanly and methodically, development is organized into 5 structured phases:

### Phase 1: Core Clearance Pipeline & Smart Financial Offsetting
* Implement multi-department clearance data models (`LIBRARY`, `HOSTEL`, `ACCOUNTS`, `REGISTRAR`).
* Build the automated UGC refund calculation engine.
* Build the **"Deduct from Security Deposit"** offsetting logic for lost ID cards and minor fines.
* Connect the student clearance view to the Staff Action Desks.

### Phase 2: Collaborative Digital Notesheet & Centralized Registry
* Build the multi-tier digital Notesheet hierarchy (`Supervisor` $\rightarrow$ `HOD` $\rightarrow$ `HOI` $\rightarrow$ `Pro-VC` $\rightarrow$ `VC`).
* Implement in-flight collaborative editing and audit annotation logging.
* Implement the centralized student status registry (`ACTIVE`, `SUSPENDED`, `DEBARRED`, `WITHDRAWN`) with real-time visual alerts across all faculty and kiosk screens.

### Phase 3: Dynamic Forms, Local OCR & QR Token Generation
* Build the branded 1-page PDF Token Slip generator with dynamic QR codes.
* Integrate local Python OCR (Tesseract) to auto-verify uploaded receipts and ID cards against active profiles.
* Implement the 45-second auto-expiring kiosk privacy timer.

### Phase 4: University Generalization Configurator & Accreditation Hub
* Build the institutional settings configurator (custom branding, configurable department chains, and custom fee slabs).
* Build the **Accreditation Export Engine** to generate Course Outcome (CO) and Program Outcome (PO) attainment matrices for NAAC / NBA reviews.

### Phase 5: Intelligent Search & Policy Guidance
* Implement SQLite `FTS5` full-text search over official university handbooks and ordinances.
* Connect optional conversational AI summaries to translate dense legal clauses into plain-English student advice.
* Execute end-to-end multi-campus load testing and verification.
