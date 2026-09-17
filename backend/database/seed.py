"""
Database schema creation and sample data seeding.

Security note: All INSERT statements use parameterised queries.
INSERT OR IGNORE makes repeated startups idempotent without duplicating data.
"""

import uuid
from .connection import get_connection

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT UNIQUE NOT NULL,
    course        TEXT NOT NULL,
    branch        TEXT NOT NULL,
    semester      INTEGER NOT NULL,
    enrolled_date TEXT NOT NULL,
    attendance    REAL NOT NULL DEFAULT 75.0,
    cgpa          REAL NOT NULL DEFAULT 7.0,
    fee_status    TEXT NOT NULL DEFAULT 'Paid' CHECK(fee_status IN ('Paid', 'Pending')),
    fee_due       REAL NOT NULL DEFAULT 0.0,
    hostel_status TEXT NOT NULL DEFAULT 'Day Scholar',
    scholarship_status TEXT NOT NULL DEFAULT 'None',
    academic_performance TEXT NOT NULL DEFAULT 'Good',
    interests     TEXT,
    previous_interactions INTEGER NOT NULL DEFAULT 0,
    campus_code   TEXT NOT NULL DEFAULT 'NOIDA'
);

CREATE TABLE IF NOT EXISTS users (     
    username      TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    role          TEXT NOT NULL CHECK(role IN ('Faculty', 'Department Coordinator', 'Finance Department', 'Scholarship Department', 'Examination Cell', 'Registrar', 'Admission Team', 'Administrator'))
);

CREATE TABLE IF NOT EXISTS campuses (
    code          TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    city          TEXT NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS campus_procedure_rules (
    campus_code        TEXT NOT NULL,
    procedure_type     TEXT NOT NULL,
    default_department TEXT NOT NULL,
    target_days        INTEGER NOT NULL,
    policy_note        TEXT,
    PRIMARY KEY (campus_code, procedure_type),
    FOREIGN KEY(campus_code) REFERENCES campuses(code)
);

CREATE TABLE IF NOT EXISTS conversations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      TEXT    NOT NULL,
    message         TEXT    NOT NULL,
    sender          TEXT    NOT NULL CHECK(sender IN ('student', 'bot')),
    detected_intent TEXT,
    sentiment       TEXT,
    timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(student_id) REFERENCES students(id)
);

CREATE TABLE IF NOT EXISTS withdrawal_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      TEXT    NOT NULL,
    reason          TEXT    NOT NULL,
    detected_intent TEXT,
    refund_amount   REAL    DEFAULT 0.0,
    status          TEXT    NOT NULL DEFAULT 'pending',
    reference_no    TEXT,
    current_step    INTEGER NOT NULL DEFAULT 1,
    timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(student_id) REFERENCES students(id)
);

CREATE TABLE IF NOT EXISTS procedure_steps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    procedure_code  TEXT NOT NULL,
    step_number     INTEGER NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    department      TEXT NOT NULL,
    timeline_text   TEXT NOT NULL,
    status_after    TEXT NOT NULL,
    UNIQUE(procedure_code, step_number)
);

CREATE TABLE IF NOT EXISTS procedure_documents (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    procedure_code    TEXT NOT NULL,
    document_key      TEXT NOT NULL,
    name              TEXT NOT NULL,
    description       TEXT NOT NULL,
    mandatory         INTEGER NOT NULL DEFAULT 1,
    applicable_reason TEXT NOT NULL DEFAULT 'all',
    form_url          TEXT,
    UNIQUE(procedure_code, document_key)
);

CREATE TABLE IF NOT EXISTS procedure_forms (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    procedure_code     TEXT NOT NULL,
    form_key           TEXT NOT NULL,
    name               TEXT NOT NULL,
    description        TEXT NOT NULL,
    download_url       TEXT NOT NULL,
    issuing_department TEXT NOT NULL,
    UNIQUE(procedure_code, form_key)
);

CREATE TABLE IF NOT EXISTS forms_catalog (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    form_key           TEXT NOT NULL UNIQUE,
    name               TEXT NOT NULL,
    category           TEXT NOT NULL,
    department         TEXT NOT NULL,
    description        TEXT NOT NULL,
    file_name          TEXT NOT NULL,
    download_url       TEXT NOT NULL,
    file_type          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS withdrawal_checklist_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      INTEGER NOT NULL,
    document_key    TEXT NOT NULL,
    label           TEXT NOT NULL,
    description     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending', 'uploaded', 'verified', 'rejected', 'not_required')),
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(request_id) REFERENCES withdrawal_requests(id)
);

CREATE TABLE IF NOT EXISTS workflow_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      INTEGER NOT NULL,
    status          TEXT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    actor           TEXT NOT NULL DEFAULT 'system',
    timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(request_id) REFERENCES withdrawal_requests(id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id        TEXT,
    actor_role      TEXT,
    action          TEXT NOT NULL,
    entity_type     TEXT NOT NULL,
    entity_id       TEXT,
    metadata        TEXT,
    timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      TEXT    NOT NULL,
    file_name       TEXT    NOT NULL,
    file_path       TEXT    NOT NULL,
    classification  TEXT    DEFAULT 'other',
    ocr_data        TEXT,
    verification_status TEXT DEFAULT 'pending' CHECK(verification_status IN ('pending', 'verified', 'fraud_detected', 'error')),
    verification_notes  TEXT,
    timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(student_id) REFERENCES students(id)
);

CREATE TABLE IF NOT EXISTS notices (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    content       TEXT NOT NULL,
    target_branch TEXT NOT NULL, -- "CSE", "ECE", "MBA", "Biotech", or "ALL"
    target_semester INTEGER NOT NULL, -- 0 for "ALL", or 1-8
    category      TEXT NOT NULL CHECK(category IN ('academics', 'exam', 'scholarship', 'internship', 'general')),
    timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scholarships (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    description   TEXT NOT NULL,
    eligibility_cgpa REAL NOT NULL,
    amount        REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS scholarship_applications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    TEXT NOT NULL,
    scholarship_id INTEGER NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
    timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(student_id) REFERENCES students(id),
    FOREIGN KEY(scholarship_id) REFERENCES scholarships(id)
);

CREATE TABLE IF NOT EXISTS examinations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    TEXT NOT NULL,
    subject_code  TEXT NOT NULL,
    subject_name  TEXT NOT NULL,
    exam_date     TEXT NOT NULL,
    grade         TEXT, -- NULL if exam has not happened yet
    type          TEXT NOT NULL DEFAULT 'regular' CHECK(type IN ('regular', 'backpaper')),
    backpaper_status TEXT DEFAULT 'none' CHECK(backpaper_status IN ('none', 'registered', 'paid')),
    FOREIGN KEY(student_id) REFERENCES students(id)
);

CREATE TABLE IF NOT EXISTS grievances (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    TEXT NOT NULL,
    category      TEXT NOT NULL CHECK(category IN ('academic', 'fee', 'hostel', 'exam', 'scholarship')),
    description   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'in_progress', 'resolved')),
    resolution    TEXT,
    timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(student_id) REFERENCES students(id)
);

CREATE TABLE IF NOT EXISTS internships (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    company       TEXT NOT NULL,
    description   TEXT NOT NULL,
    required_cgpa REAL NOT NULL,
    stipend       TEXT NOT NULL,
    deadline      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS departments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    display_name    TEXT NOT NULL,
    description     TEXT,
    contact_email   TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflows (
    id              TEXT PRIMARY KEY,
    student_id      TEXT NOT NULL,
    procedure_type  TEXT NOT NULL CHECK(procedure_type IN ('withdrawal', 'grievance', 'scholarship')),
    status          TEXT NOT NULL DEFAULT 'initiated' CHECK(status IN ('initiated', 'submitted', 'under_review', 'pending_approval', 'department_clearance', 'finance_processing', 'approved', 'rejected', 'completed')),
    assigned_department TEXT,
    metadata        TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    campus_code     TEXT NOT NULL DEFAULT 'NOIDA',
    FOREIGN KEY(student_id) REFERENCES students(id),
    FOREIGN KEY(assigned_department) REFERENCES departments(name)
);

CREATE TABLE IF NOT EXISTS workflow_checklist_items (
    id              TEXT PRIMARY KEY,
    workflow_id     TEXT NOT NULL,
    item_number     INTEGER NOT NULL,
    description     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'pending_review', 'approved')),
    notes           TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(workflow_id) REFERENCES workflows(id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id              TEXT PRIMARY KEY,
    student_id      TEXT NOT NULL,
    notification_type TEXT NOT NULL CHECK(notification_type IN ('workflow_status', 'alert', 'deadline', 'reminder', 'approval')),
    title           TEXT NOT NULL,
    message         TEXT NOT NULL,
    priority        TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('low', 'normal', 'high', 'urgent')),
    template_key    TEXT,
    template_data   TEXT,
    read_status     TEXT NOT NULL DEFAULT 'unread' CHECK(read_status IN ('unread', 'read')),
    sent_by         TEXT DEFAULT 'system',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    read_at         DATETIME,
    FOREIGN KEY(student_id) REFERENCES students(id)
);

CREATE TABLE IF NOT EXISTS notification_logs (
    id              TEXT PRIMARY KEY,
    notification_id TEXT NOT NULL,
    action          TEXT NOT NULL,
    details         TEXT,
    timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(notification_id) REFERENCES notifications(id)
);

CREATE TABLE IF NOT EXISTS notification_templates (
    id              TEXT PRIMARY KEY,
    template_key    TEXT NOT NULL UNIQUE,
    title_template  TEXT NOT NULL,
    message_template TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    default_priority TEXT NOT NULL DEFAULT 'normal',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS compliance_requests (
    id              TEXT PRIMARY KEY,
    student_id      TEXT NOT NULL,
    request_type    TEXT NOT NULL CHECK(request_type IN ('export', 'erasure', 'rectification', 'restriction')),
    status          TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'completed', 'rejected')),
    reason          TEXT,
    metadata        TEXT,
    requested_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    FOREIGN KEY(student_id) REFERENCES students(id)
);

CREATE TABLE IF NOT EXISTS data_retention_policies (
    entity_name     TEXT PRIMARY KEY,
    retention_days  INTEGER NOT NULL,
    description     TEXT NOT NULL,
    last_cleanup_at DATETIME
);
"""

# ---------------------------------------------------------------------------
# Sample Records
# ---------------------------------------------------------------------------

_SAMPLE_STUDENTS = [
    (
        "STU001",
        "Aisha Malik",
        "aisha.malik@uniassist.edu",
        "Computer Science",
        "CSE",
        6,
        "2023-08-01",
        82.5,
        8.75,
        "Paid",
        0.0,
        "Allocated (Hostel-3)",
        "50% Merit Scholarship",
        "Outstanding",
        "Artificial Intelligence, Web Development",
        4,
    ),
    (
        "STU002",
        "Rahul Sharma",
        "rahul.sharma@uni.edu",
        "Electronics and Communication",
        "ECE",
        4,
        "2024-08-05",
        68.0,
        6.45,
        "Pending",
        42000.0,
        "Day Scholar",
        "None",
        "Needs academic support",
        "Robotics, Embedded Systems",
        2,
    ),
    (
        "STU003",
        "Priya Nair",
        "priya.nair@uniassist.edu",
        "MBA",
        "MBA",
        2,
        "2025-07-10",
        91.0,
        9.1,
        "Paid",
        0.0,
        "Allocated (Hostel-1)",
        "Vice Chancellor's Fellowship",
        "Outstanding",
        "Finance, Consulting",
        5,
    ),
    (
        "STU004",
        "Kabir Mehta",
        "kabir.mehta@uniassist.edu",
        "Computer Science",
        "CSE",
        6,
        "2023-08-01",
        76.0,
        7.8,
        "Paid",
        0.0,
        "Day Scholar",
        "None",
        "Good",
        "Cloud Computing, DevOps",
        1,
    ),
    (
        "STU005",
        "Neha Verma",
        "neha.verma@uniassist.edu",
        "Biotechnology",
        "Biotech",
        4,
        "2024-08-03",
        88.0,
        8.2,
        "Paid",
        0.0,
        "Allocated (Hostel-2)",
        "Sports Excellence Award",
        "Very Good",
        "Genetics, Research",
        3,
    ),
    (
        "STU006",
        "Arjun Rao",
        "arjun.rao@uniassist.edu",
        "Mechanical Engineering",
        "ME",
        5,
        "2023-08-12",
        73.5,
        7.05,
        "Pending",
        18000.0,
        "Day Scholar",
        "None",
        "Average",
        "Automobile Design, CAD",
        0,
    ),
    (
        "STU007",
        "Sara Khan",
        "sara.khan@uniassist.edu",
        "Computer Science",
        "CSE",
        6,
        "2023-08-01",
        85.0,
        8.55,
        "Paid",
        0.0,
        "Allocated (Hostel-4)",
        "Merit Scholarship Applied",
        "Very Good",
        "Cybersecurity, Product Design",
        2,
    ),
    (
        "STU008",
        "Devansh Gupta",
        "devansh.gupta@uniassist.edu",
        "Electronics and Communication",
        "ECE",
        4,
        "2024-08-05",
        79.0,
        7.35,
        "Paid",
        0.0,
        "Day Scholar",
        "None",
        "Good",
        "VLSI, IoT",
        1,
    ),
    (
        "STU009",
        "Meera Iyer",
        "meera.iyer@uniassist.edu",
        "Computer Science",
        "CSE",
        6,
        "2023-08-01",
        93.0,
        9.25,
        "Paid",
        0.0,
        "Allocated (Hostel-5)",
        "Vice Chancellor's Fellowship Eligible",
        "Outstanding",
        "Machine Learning, Data Science",
        6,
    ),
    (
        "STU010",
        "Rohan Das",
        "rohan.das@uniassist.edu",
        "MBA",
        "MBA",
        2,
        "2025-07-10",
        71.0,
        7.1,
        "Pending",
        30000.0,
        "Day Scholar",
        "None",
        "Average",
        "Marketing, Analytics",
        1,
    ),
    (
        "STU011",
        "Tanya Bhatia",
        "tanya.bhatia@uniassist.edu",
        "Biotechnology",
        "Biotech",
        4,
        "2024-08-03",
        80.0,
        7.9,
        "Paid",
        0.0,
        "Allocated (Hostel-2)",
        "None",
        "Good",
        "Molecular Biology, Lab Research",
        2,
    ),
    (
        "STU012",
        "Ishaan Kapoor",
        "ishaan.kapoor@uniassist.edu",
        "Computer Science",
        "CSE",
        6,
        "2023-08-01",
        66.0,
        6.2,
        "Pending",
        55000.0,
        "Day Scholar",
        "None",
        "Needs academic support",
        "Gaming, Web Apps",
        0,
    ),
]

_SAMPLE_USERS = [
    ("registrar_staff", "Registrar Office Support", "Registrar"),
    ("admission_staff", "Admissions Helpdesk", "Admission Team"),
    ("finance_staff", "Finance Advisor Office", "Finance Department"),
    ("scholarship_staff", "Scholarship Desk Coordinator", "Scholarship Department"),
    ("exam_staff", "Examination Cell Controller", "Examination Cell"),
    ("coordinator_staff", "Academic Department Coordinator", "Department Coordinator"),
]

_SAMPLE_CAMPUSES = [
    ("NOIDA", "Amity University Noida", "Noida", 1),
    ("MUMBAI", "Amity University Mumbai", "Mumbai", 1),
    ("LUCKNOW", "Amity University Lucknow", "Lucknow", 1),
]

_CAMPUS_PROCEDURE_RULES = [
    ("NOIDA", "withdrawal", "Academic Affairs", 10, "Standard campus withdrawal clearance."),
    ("MUMBAI", "withdrawal", "Student Services", 12, "Mumbai campus requires student-services triage."),
    ("LUCKNOW", "withdrawal", "Registry", 9, "Lucknow registrar starts withdrawal review."),
    ("NOIDA", "grievance", "Student Services", 5, "Standard grievance turnaround."),
    ("MUMBAI", "grievance", "Student Services", 5, "Standard grievance turnaround."),
    ("LUCKNOW", "grievance", "Student Services", 5, "Standard grievance turnaround."),
    ("NOIDA", "scholarship", "Finance", 14, "Finance verifies scholarship eligibility."),
    ("MUMBAI", "scholarship", "Finance", 14, "Finance verifies scholarship eligibility."),
    ("LUCKNOW", "scholarship", "Finance", 14, "Finance verifies scholarship eligibility."),
]
_SAMPLE_NOTICES = [
    ("Mid-Semester Examinations Datesheet", "Mid-Semester Examinations for all undergraduate programs will commence on Oct 12, 2026. The detailed subject datesheet is available on the portal. Please ensure you clear any outstanding fees to receive your admit card.", "ALL", 0, "exam"),
    ("Wipro Campus Placement Internship Drive 2026", "Wipro is conducting an internship selection drive for CSE and ECE students of the 6th semester. Minimum required CGPA is 8.0. Register by June 25, 2026.", "CSE", 6, "internship"),
    ("Biotech Research Lab Renovation Notice", "The Biotech research labs will remain closed for maintenance and instrumentation upgrading from June 10 to June 15. Students requiring lab space can request reallocation from the Coordinator.", "Biotech", 0, "academics"),
    ("Merit Scholarship Renewal Application Open", "Applications for the renewal of Merit and VC Scholarships for the academic year 2026-27 are now open. Eligible students must submit their CGPA scorecards online by June 20, 2026.", "ALL", 0, "scholarship"),
    ("Academic Advisory Committee Grievance Cell Meeting", "The next meeting of the Student Grievance Redressal Committee is scheduled for June 18. Students who have logged grievances can join the open house at 2:00 PM in Block F-3.", "ALL", 0, "general"),
    ("ECE Electronics Lab Practical Datesheet", "The practical exams for Electronics circuits (semester 4) will be held from June 15 to June 17. Please contact your lab instructor for batch details.", "ECE", 4, "exam"),
    ("Microsoft Software Development Internship Opportunity", "Microsoft is offering summer internships for pre-final year students (semester 6). Stipend: 80,000 INR/month. Minimum CGPA: 8.5. CSE/ECE eligible.", "ALL", 6, "internship")
]

_SAMPLE_SCHOLARSHIPS = [
    ("Amity Merit Scholarship", "50% tuition fee waiver for academic toppers with CGPA 8.0 or above.", 8.0, 120000.0),
    ("Vice Chancellor's Fellowship", "100% tuition fee waiver for outstanding students with CGPA 9.0 or above.", 9.0, 240000.0),
    ("Sports Excellence Award", "25% fee waiver for students representing the university at state/national sports events.", 6.0, 60000.0)
]

_SAMPLE_EXAMINATIONS = [
    # Aisha Malik
    ("STU001", "CSE-301", "Computer Networks", "2025-11-20", "A", "regular", "none"),
    ("STU001", "CSE-302", "Software Engineering", "2025-11-22", "A+", "regular", "none"),
    ("STU001", "CSE-303", "Artificial Intelligence", "2025-11-25", "B+", "regular", "none"),
    ("STU001", "CSE-304", "Web Technology", "2026-06-12", None, "regular", "none"),
    ("STU001", "CSE-305", "Automata Theory", "2026-06-15", None, "regular", "none"),
    
    # Rahul Sharma
    ("STU002", "ECE-201", "Signals and Systems", "2025-11-18", "F", "regular", "registered"),
    ("STU002", "ECE-202", "Digital Circuit Design", "2025-11-20", "D", "regular", "none"),
    ("STU002", "ECE-203", "Analog Communications", "2025-11-23", "C+", "regular", "none"),
    ("STU002", "ECE-204", "Microprocessors", "2026-06-13", None, "regular", "none"),
    
    # Priya Nair
    ("STU003", "MBA-101", "Managerial Economics", "2025-05-15", "O", "regular", "none"),
    ("STU003", "MBA-102", "Financial Accounting", "2025-05-18", "A+", "regular", "none")
]

_SAMPLE_INTERNSHIPS = [
    ("Software Development Intern", "Google India", "Work on cutting-edge features for Google Cloud Platform. Requires strong DSA and Java/Python skills.", 8.5, "85,000 INR/month", "2026-08-30"),
    ("Data Analyst Intern", "Microsoft", "Analyze user behavior metrics and help design data dashboards. Requires SQL and PowerBI.", 8.0, "70,000 INR/month", "2026-09-15"),
    ("Robotics Systems Trainee", "Tesla India", "Build controllers and simulations for autonomous systems. Requires ROS, C++, and kinematics.", 8.2, "60,000 INR/month", "2026-07-20"),
    ("Research Associate (Biotech)", "Biocon", "Work in the gene-editing labs assisting senior molecular biologists. Requires biology background.", 7.5, "35,000 INR/month", "2026-06-30")
]

_WITHDRAWAL_STEPS = [
    ("withdrawal", 1, "Collect withdrawal reason", "Record the student's reason and determine whether any special documents are required.", "Student Services Desk", "Immediate during request initiation.", "submitted"),
    ("withdrawal", 2, "Generate required document list", "Create a personalized checklist using mandatory documents and reason-specific supporting documents.", "Registrar Office", "Generated immediately after intent confirmation.", "documents_pending"),
    ("withdrawal", 3, "Explain every required document", "Show why each document is needed, who issues it, and what quality checks apply.", "Student Services Desk", "Available immediately in UNIASSIST.", "documents_pending"),
    ("withdrawal", 4, "Provide downloadable forms", "Make official withdrawal forms and clearance formats available for download or kiosk printing.", "Registrar Office", "Available immediately in the form repository.", "documents_pending"),
    ("withdrawal", 5, "Guide document preparation", "Guide the student to upload clear, valid files before submission review.", "Student", "Student-dependent.", "documents_pending"),
    ("withdrawal", 6, "Guide submission process", "Submit the request to the Registrar Office with generated checklist and attachments.", "Registrar Office", "Generally same working day after all required files are ready.", "under_review"),
    ("withdrawal", 7, "Show departments involved", "Display Academic Department, Library, Hostel, Finance, and Accounts clearances where applicable.", "Registrar Office", "Generally 3-5 working days for clearances.", "department_clearance"),
    ("withdrawal", 8, "Show official timelines", "Display official timeline bands without predicting individual outcomes.", "Student Services Desk", "Visible throughout the request lifecycle.", "under_review"),
    ("withdrawal", 9, "Track process status", "Show status events from submission through department and finance processing.", "Registrar Office", "Updated whenever staff records an action.", "under_review"),
    ("withdrawal", 10, "Guide refund process", "Explain that finance processing begins after required approvals and clearances.", "Finance Office", "Generally 7-10 working days after complete clearance.", "finance_processing"),
    ("withdrawal", 11, "Mark workflow complete", "Close the request after university processing is completed or rejected with reason.", "Registrar Office", "After final staff action.", "completed"),
]

_WITHDRAWAL_DOCUMENTS = [
    ("withdrawal", "withdrawal_application", "Withdrawal Application Form", "Official request form signed by the student. Required for every withdrawal request.", 1, "all", "/forms/withdrawal-application.pdf"),
    ("withdrawal", "student_id_proof", "Student ID Proof", "University ID card or valid institutional identity proof used to match the student record.", 1, "all", None),
    ("withdrawal", "fee_clearance", "Fee Clearance Statement", "Finance record showing paid, pending, or adjustable dues before refund processing.", 1, "all", "/forms/fee-clearance.pdf"),
    ("withdrawal", "library_clearance", "Library Clearance", "Confirmation that books, equipment, or library penalties are settled.", 1, "all", "/forms/library-clearance.pdf"),
    ("withdrawal", "hostel_clearance", "Hostel Clearance", "Required if the student has a hostel allocation or hostel dues.", 0, "hostel", "/forms/hostel-clearance.pdf"),
    ("withdrawal", "medical_certificate", "Medical Certificate", "Required when withdrawal reason is medical or health-related.", 0, "health", None),
    ("withdrawal", "guardian_consent", "Guardian Consent Letter", "Consent or acknowledgement letter when required by university policy.", 0, "personal", "/forms/guardian-consent.pdf"),
]

_WITHDRAWAL_FORMS = [
    ("withdrawal", "withdrawal_application", "Withdrawal Application Form", "Primary form for initiating an official withdrawal request.", "/forms/withdrawal-application.pdf", "Registrar Office"),
    ("withdrawal", "fee_clearance", "Fee Clearance Form", "Finance clearance format used before refund processing.", "/forms/fee-clearance.pdf", "Finance Office"),
    ("withdrawal", "library_clearance", "Library Clearance Form", "Library no-dues confirmation format.", "/forms/library-clearance.pdf", "Library"),
    ("withdrawal", "hostel_clearance", "Hostel Clearance Form", "Hostel no-dues and handover format.", "/forms/hostel-clearance.pdf", "Hostel Office"),
]

_FORMS_CATALOG = [
    ("dl_form", "DL Form", "Logistics & Fleet", "Administration", "Driving License / Duty Driving Permission Format.", "1. DL FORM.docx", "/forms/1. DL FORM.docx", "docx"),
    ("transport_requisition", "Requisition for Transport", "Logistics & Fleet", "Transport Department", "Official transport booking requisition for university duty, guest pick-ups, and field visits.", "10. Requisition for Tranport.docx", "/forms/10. Requisition for Tranport.docx", "docx"),
    ("local_conveyance", "Local Conveyance Form", "Finance", "Finance & Accounts", "Reimbursement claim form for local travel expenses incurred on official work.", "11. Local Conveynce form.docx", "/forms/11. Local Conveynce form.docx", "docx"),
    ("advance_imprest_requisition", "Advance Imprest Requisition", "Finance", "Finance & Accounts", "Format for requesting official advance imprest funds.", "12.Advance  Imprest_Requisition-Hon pro Chancellor 16.11.2023.pdf", "/forms/12.Advance  Imprest_Requisition-Hon pro Chancellor 16.11.2023.pdf", "pdf"),
    ("mentoring_record_card", "Mentoring Record Card", "Student Welfare", "Student Mentorship Desk", "Individual student mentoring tracking card used by faculty mentors.", "13.Mentoring Record Card.doc", "/forms/13.Mentoring Record Card.doc", "doc"),
    ("revised_purchase_proposal", "Revised Purchase Proposal (2019)", "Procurement", "Purchase & Stores", "Formal purchase proposal format for equipment, consumables, and software licenses.", "14. Revised PURCHASE PROPOSAL 28.09.2019.docx", "/forms/14. Revised PURCHASE PROPOSAL 28.09.2019.docx", "docx"),
    ("migration_certificate_doc", "Migration Certificate Application (.doc)", "Academics", "Registrar Office", "Official application form for issuing migration certificates to outgoing students.", "15.Application Forms for issue of Migration Certificates to the Students.doc", "/forms/15.Application Forms for issue of Migration Certificates to the Students.doc", "doc"),
    ("migration_certificate_pdf", "Migration Certificate Application (.pdf)", "Academics", "Registrar Office", "Official PDF printable format for migration certificate application.", "15.Application for Migration Certificates.pdf", "/forms/15.Application for Migration Certificates.pdf", "pdf"),
    ("placement_opted_out", "Placement Opted Out Declaration", "Career & Placement", "Corporate Resource Centre (CRC)", "Formal declaration form for students opting out of campus placement drives.", "16.Declaration placement opted out form.docx", "/forms/16.Declaration placement opted out form.docx", "docx"),
    ("exit_interview_withdrawal", "Exit Interview Form for Withdrawal", "Student Welfare", "Registrar & Student Welfare Desk", "Exit interview and feedback questionnaire required during program withdrawal.", "17.Exit Interview form for Withdrawl.pdf", "/forms/17.Exit Interview form for Withdrawl.pdf", "pdf"),
    ("stationery_indent", "Stationery Indent Requisition", "Logistics & Stores", "Central Store", "Departmental stationery items indent requisition format.", "18.Stationery indent.docx", "/forms/18.Stationery indent.docx", "docx"),
    ("stationery_indent_form", "Stationery Indent Form (Alt)", "Logistics & Stores", "Central Store", "Alternative format for departmental stationery requisition.", "18.Stationery indent_form.docx", "/forms/18.Stationery indent_form.docx", "docx"),
    ("biometric_id_forget", "Biometric / ID Card Issue Application", "HR & IT", "IT Support & HR Desk", "Re-issue application for forgotten or missing biometric ID card (Teaching & Non-Teaching).", "19. Appl forget biometric id card_Teaching & Nonteaching.pdf", "/forms/19. Appl forget biometric id card_Teaching & Nonteaching.pdf", "pdf"),
    ("emergency_leave", "Emergency Leave Proforma", "HR & Staff", "HR Administration", "Emergency leave application proforma for faculty and staff.", "2.Performa for Emg Leave.docx", "/forms/2.Performa for Emg Leave.docx", "docx"),
    ("blank_exam_form", "Blank Examination Form", "Examinations", "Controller of Examinations", "Official blank examination application format for semester end exams.", "20. Blank exam form _20 .09. 2024.xlsx", "/forms/20. Blank exam form _20 .09. 2024.xlsx", "xlsx"),
    ("cartridge_refill_form", "Cartridge Refill Form", "IT & Logistics", "IT Support Desk", "Printer cartridge refill and replacement requisition form.", "21. Cartridge refill form.docx", "/forms/21. Cartridge refill form.docx", "docx"),
    ("degree_application_format", "Degree Application Format", "Examinations", "Controller of Examinations", "Official application format for obtaining degree certificate / convocation degree.", "22. Degree Application Format.pdf", "/forms/22. Degree Application Format.pdf", "pdf"),
    ("faculty_leave_application", "Faculty Leave Application", "HR & Staff", "HR Administration", "Formal leave application form for faculty members.", "23. Faculty Leave Application (1).pdf", "/forms/23. Faculty Leave Application (1).pdf", "pdf"),
    ("employee_id_card_form", "Employee ID Card Form", "HR & Staff", "HR Administration", "Application format for issuing official Employee ID card.", "24. ID Card form Employee.pdf", "/forms/24. ID Card form Employee.pdf", "pdf"),
    ("mentor_mentee_record_form", "Mentor-Mentee Record Form (2024)", "Student Welfare", "Academic Mentorship Cell", "Updated mentor-mentee interaction log and progress record format.", "25. Mentor Menttee Record Form_29.11.2024.docx", "/forms/25. Mentor Menttee Record Form_29.11.2024.docx", "docx"),
    ("blank_purchase_proposal", "Purchase Proposal Blank Format", "Procurement", "Purchase & Stores", "Standard blank proposal format for departmental procurement.", "26. PURCHASE PROPOSAL_Blank.docx", "/forms/26. PURCHASE PROPOSAL_Blank.docx", "docx"),
    ("rechecking_result_application", "Application for Rechecking of Result", "Examinations", "Controller of Examinations", "Official application for rechecking / re-evaluation of semester examination marks.", "27. APPLICATION FOR RECHECKING  OF RESULT.pdf", "/forms/27. APPLICATION FOR RECHECKING  OF RESULT.pdf", "pdf"),
    ("student_id_card_form", "Student ID Card Form", "Admissions & Registrar", "Registrar Office", "Application form for new or replacement Student Identity Card.", "28. student Id Card Form.docx", "/forms/28. student Id Card Form.docx", "docx"),
    ("stationery_indent_alt", "Stationery Indent Requisition (v2)", "Logistics & Stores", "Central Store", "Stationery requisition form version 2.", "29. stationary indent.docx", "/forms/29. stationary indent.docx", "docx"),
    ("class_arrangement", "Class Arrangement Format (2019)", "Academics", "Academic Affairs", "Format for adjusting and arranging classes during faculty absence.", "3.Class Arrangement(2019).docx", "/forms/3.Class Arrangement(2019).docx", "docx"),
    ("aset_faculty_contact_list", "List of ASET Faculty & Staff with Contact Details", "Directory", "ASET Dean Office", "Complete contact directory of ASET faculty and technical staff.", "5.List of ASET FACULTY & STAFF with Contact details 107.08.20.xlsx", "/forms/5.List of ASET FACULTY & STAFF with Contact details 107.08.20.xlsx", "xlsx"),
    ("financial_assistance_events", "Format for Financial Assistance for Events", "Finance", "Finance & Dean Student Welfare", "Requisition format for seeking university financial assistance for technical/cultural events.", "6 Format for Financial Asst. for Events.doc", "/forms/6 Format for Financial Asst. for Events.doc", "doc"),
    ("letter_parents_debarred", "Format Letter to Parents of Debarred Students", "Academics", "Examination & Academic Office", "Official template letter sent to parents regarding attendance shortage and debarment.", "7. Format Letter to Parents of Debarred Students.docx", "/forms/7. Format Letter to Parents of Debarred Students.docx", "docx"),
    ("tada_claim", "TA / DA Claim Format", "Finance", "Finance & Accounts", "Travelling Allowance and Daily Allowance claim form for official university travel.", "8. TA DA claim format.xls", "/forms/8. TA DA claim format.xls", "xls"),
    ("refreshment_cafeteria_req", "Requisition for Refreshment (Cafeteria)", "Logistics & Catering", "Hospitality & Logistics", "Requisition form for cafeteria refreshments for official meetings and seminars.", "9. Requisition for Refreshment Cafeteria-1.docx", "/forms/9. Requisition for Refreshment Cafeteria-1.docx", "docx"),
    ("aset_patents_list", "List of Patents Filed by ASET", "Research & Patents", "Dean Research & Development", "Comprehensive record of patents filed by ASET faculty and research scholars.", "List of Patents filed ASET 13_01_2021_vsk final.docx", "/forms/List of Patents filed ASET 13_01_2021_vsk final.docx", "docx")
]

_DEPARTMENTS = [
    ("Academic Affairs", "Academic Affairs Department", "Handles academic procedures, withdrawals, and registrations", "academic@uni.edu"),
    ("Student Services", "Student Services Department", "Student support and lifecycle management", "support@uni.edu"),
    ("Finance", "Finance Department", "Financial clearances and fee processing", "finance@uni.edu"),
    ("Registry", "Registry & Registrar Office", "Official records and documentation", "registry@uni.edu"),
]

_NOTIFICATION_TEMPLATES = [
    ("withdrawal_submitted", "Withdrawal Request Submitted", "Your withdrawal request has been submitted with reference number {reference_no}. You can track the status in your dashboard.", "workflow_status", "normal"),
    ("withdrawal_approved", "Withdrawal Request Approved", "Your withdrawal request (Ref: {reference_no}) has been approved. Refund processing will begin shortly.", "workflow_status", "high"),
    ("document_uploaded", "Document Uploaded Successfully", "Your document '{document_name}' has been uploaded and is being verified.", "alert", "normal"),
    ("document_verified", "Document Verified", "Your document '{document_name}' has been verified successfully.", "alert", "normal"),
    ("fee_deadline", "Fee Payment Deadline", "Your fee payment is due on {due_date}. Please complete payment to avoid late fees.", "deadline", "high"),
    ("exam_reminder", "Exam Reminder", "Your exam for {subject_name} is on {exam_date}. Please prepare and arrive 15 minutes early.", "reminder", "normal"),
    ("scholarship_approved", "Scholarship Approved", "Congratulations! Your application for {scheme_name} scholarship has been approved for {amount}.", "approval", "high"),
]


_SAMPLE_RETENTION_POLICIES = [
    ("conversations", 365, "Student conversational logs kept for 1 year for academic audit and support quality."),
    ("audit_logs", 730, "System and administrative action audit trails kept for 2 years for statutory compliance."),
    ("notifications", 180, "Student alerts and dispatched notifications kept for 6 months."),
    ("notification_logs", 180, "Delivery event logs kept for 6 months."),
]

def init_db() -> None:
    """Create tables and insert rich sample lifecycle data — safe to call multiple times."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Schema Migration Check: If 'cgpa' column is missing from students, recreate everything
    schema_ok = True
    try:
        cursor.execute("SELECT cgpa FROM students LIMIT 1")
    except Exception:
        schema_ok = False
        
    if not schema_ok:
        print("[DB] Dropping outdated tables to load expanded Student Lifecycle schema...")
        cursor.execute("DROP TABLE IF EXISTS conversations")
        cursor.execute("DROP TABLE IF EXISTS withdrawal_requests")
        cursor.execute("DROP TABLE IF EXISTS documents")
        cursor.execute("DROP TABLE IF EXISTS students")
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("DROP TABLE IF EXISTS notices")
        cursor.execute("DROP TABLE IF EXISTS scholarships")
        cursor.execute("DROP TABLE IF EXISTS scholarship_applications")
        cursor.execute("DROP TABLE IF EXISTS examinations")
        cursor.execute("DROP TABLE IF EXISTS grievances")
        cursor.execute("DROP TABLE IF EXISTS internships")
        cursor.execute("DROP TABLE IF EXISTS procedure_steps")
        cursor.execute("DROP TABLE IF EXISTS procedure_documents")
        cursor.execute("DROP TABLE IF EXISTS procedure_forms")
        cursor.execute("DROP TABLE IF EXISTS forms_catalog")
        cursor.execute("DROP TABLE IF EXISTS withdrawal_checklist_items")
        cursor.execute("DROP TABLE IF EXISTS workflow_events")
        cursor.execute("DROP TABLE IF EXISTS audit_logs")
        cursor.execute("DROP TABLE IF EXISTS workflow_checklist_items")
        cursor.execute("DROP TABLE IF EXISTS workflows")
        cursor.execute("DROP TABLE IF EXISTS departments")
        cursor.execute("DROP TABLE IF EXISTS notification_logs")
        cursor.execute("DROP TABLE IF EXISTS notifications")
        cursor.execute("DROP TABLE IF EXISTS notification_templates")
        cursor.execute("DROP TABLE IF EXISTS compliance_requests")
        cursor.execute("DROP TABLE IF EXISTS data_retention_policies")
        conn.commit()

    # Create all tables
    cursor.executescript(_SCHEMA)
    conn.commit()

    # Lightweight migrations for existing local SQLite files.
    existing_columns = [row["name"] for row in cursor.execute("PRAGMA table_info(withdrawal_requests)").fetchall()]
    if "reference_no" not in existing_columns:
        cursor.execute("ALTER TABLE withdrawal_requests ADD COLUMN reference_no TEXT")
    if "current_step" not in existing_columns:
        cursor.execute("ALTER TABLE withdrawal_requests ADD COLUMN current_step INTEGER NOT NULL DEFAULT 1")

    student_columns = [row["name"] for row in cursor.execute("PRAGMA table_info(students)").fetchall()]
    if "campus_code" not in student_columns:
        cursor.execute("ALTER TABLE students ADD COLUMN campus_code TEXT NOT NULL DEFAULT 'NOIDA'")
    workflow_columns = [row["name"] for row in cursor.execute("PRAGMA table_info(workflows)").fetchall()]
    if "campus_code" not in workflow_columns:
        cursor.execute("ALTER TABLE workflows ADD COLUMN campus_code TEXT NOT NULL DEFAULT 'NOIDA'")

    # Seed students
    cursor.executemany(
        "INSERT OR IGNORE INTO students (id, name, email, course, branch, semester, enrolled_date, attendance, cgpa, fee_status, fee_due, hostel_status, scholarship_status, academic_performance, interests, previous_interactions) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        _SAMPLE_STUDENTS,
    )
    
    # Seed users (staff)
    cursor.executemany(
        "INSERT OR IGNORE INTO users (username, name, role) VALUES (?, ?, ?)",
        _SAMPLE_USERS
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO campuses (code, name, city, active) VALUES (?, ?, ?, ?)",
        _SAMPLE_CAMPUSES,
    )
    cursor.executemany(
        "INSERT OR IGNORE INTO campus_procedure_rules (campus_code, procedure_type, default_department, target_days, policy_note) VALUES (?, ?, ?, ?, ?)",
        _CAMPUS_PROCEDURE_RULES,
    )
    cursor.execute("UPDATE students SET campus_code = 'MUMBAI' WHERE id IN ('STU003', 'STU007', 'STU010')")
    cursor.execute("UPDATE students SET campus_code = 'LUCKNOW' WHERE id IN ('STU005', 'STU008', 'STU011')")

    # Seed notices
    cursor.executemany(
        "INSERT OR IGNORE INTO notices (title, content, target_branch, target_semester, category) VALUES (?, ?, ?, ?, ?)",
        _SAMPLE_NOTICES
    )

    # Seed scholarships
    cursor.executemany(
        "INSERT OR IGNORE INTO scholarships (name, description, eligibility_cgpa, amount) VALUES (?, ?, ?, ?)",
        _SAMPLE_SCHOLARSHIPS
    )

    # Seed examinations
    cursor.executemany(
        "INSERT OR IGNORE INTO examinations (student_id, subject_code, subject_name, exam_date, grade, type, backpaper_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        _SAMPLE_EXAMINATIONS
    )

    # Seed internships
    cursor.executemany(
        "INSERT OR IGNORE INTO internships (title, company, description, required_cgpa, stipend, deadline) VALUES (?, ?, ?, ?, ?, ?)",
        _SAMPLE_INTERNSHIPS
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO procedure_steps (procedure_code, step_number, title, description, department, timeline_text, status_after) VALUES (?, ?, ?, ?, ?, ?, ?)",
        _WITHDRAWAL_STEPS
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO procedure_documents (procedure_code, document_key, name, description, mandatory, applicable_reason, form_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
        _WITHDRAWAL_DOCUMENTS
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO procedure_forms (procedure_code, form_key, name, description, download_url, issuing_department) VALUES (?, ?, ?, ?, ?, ?)",
        _WITHDRAWAL_FORMS
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO forms_catalog (form_key, name, category, department, description, file_name, download_url, file_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        _FORMS_CATALOG
    )

    # Seed departments
    cursor.executemany(
        "INSERT OR IGNORE INTO departments (name, display_name, description, contact_email) VALUES (?, ?, ?, ?)",
        _DEPARTMENTS
    )

    # Seed notification templates
    for template_key, title_template, message_template, notif_type, priority in _NOTIFICATION_TEMPLATES:
        template_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT OR IGNORE INTO notification_templates (id, template_key, title_template, message_template, notification_type, default_priority) VALUES (?, ?, ?, ?, ?, ?)",
            (template_id, template_key, title_template, message_template, notif_type, priority)
        )

    # Seed data retention policies
    cursor.executemany(
        "INSERT OR IGNORE INTO data_retention_policies (entity_name, retention_days, description) VALUES (?, ?, ?)",
        _SAMPLE_RETENTION_POLICIES
    )

    conn.commit()

    # Phase 29: Initialize and seed FTS5 policy search index
    from ..services.policy_search_service import PolicySearchService
    PolicySearchService.initialize_fts_index()

    print("[DB] Expanded Student Lifecycle Database seeded successfully.")
