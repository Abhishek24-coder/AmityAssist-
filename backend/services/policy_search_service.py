"""Phase 29: Intelligent Search & Policy Guidance Service.

Combines SQLite FTS5 (BM25 Inverted Index) for sub-5ms legal ordinance retrieval
with personalized hybrid RAG advice synthesis (attendance condonation, withdrawal
refund slabs, caution deposit offset, post-form submission guidance, and voice TTS guidance).
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from ..config import settings
from ..database.connection import get_connection
from ..services.nlp_service import score_sentiment
from ..services.advanced_ai_service import synthesize_guidance_with_gemini
from ..data.kiosk_master_procedures import MASTER_PROCEDURES, get_procedure_by_keyword


# ---------------------------------------------------------------------------
# Seed Ordinances & University Handbooks + Form Post-Download Workflows
# ---------------------------------------------------------------------------

DEFAULT_POLICIES = [
    # Core Ordinances
    {
        "doc_id": "POL-ACAD-01",
        "category": "Academics",
        "title": "Minimum Attendance Requirement & Dean's Condonation",
        "clause_code": "ORD-ACAD-7.2",
        "content": (
            "Minimum attendance requirement is 75% in every registered course to be eligible "
            "to sit for End Term Semester Examinations. If overall attendance is between 60% and 74%, "
            "the student may apply for Dean Condonation on medical or approved official university duty "
            "grounds by submitting Form AC-04 along with medical certificates at least 10 working days "
            "prior to exam commencement. Attendance below 60% constitutes mandatory debarment with zero condonation."
        ),
        "action_url": "/forms",
        "action_label": "Download Form AC-04 (Condonation)",
    },
    {
        "doc_id": "POL-WTH-01",
        "category": "Withdrawal & Refunds",
        "title": "Program Withdrawal & Tuition Fee Refund Mandates (UGC Aligned)",
        "clause_code": "ORD-WTH-14.1",
        "content": (
            "Withdrawal of admission and academic fee refunds adhere to UGC 2024 directives: "
            "(a) 15 days or more prior to formally notified admission deadline: 100% refund minus max processing fee INR 1,000; "
            "(b) Less than 15 days prior to admission deadline: 90% refund; "
            "(c) Up to 15 days post admission deadline: 80% refund; "
            "(d) Between 16 and 30 days post admission deadline: 50% refund; "
            "(e) Beyond 30 days post admission deadline: 0% tuition refund. "
            "Refundable Security/Caution Deposit of INR 10,000 is always refunded 100% across all slabs."
        ),
        "action_url": "/withdrawal",
        "action_label": "Start Withdrawal Procedure",
    },
    {
        "doc_id": "POL-FIN-01",
        "category": "Finance",
        "title": "Caution Deposit Smart Offsetting for Unreturned Assets & Fines",
        "clause_code": "ORD-FIN-14.4",
        "content": (
            "Under the Smart Financial Offsetting amendment, students undergoing departure or clearance "
            "with minor unreturned assets, lost plastic ID card replacement fees (INR 200), or library fines "
            "under INR 2,000 may opt for 1-tap direct deduction from their refundable caution deposit balance "
            "(standard balance INR 10,000). The clearance gate updates to CLEARED_VIA_OFFSET immediately without "
            "requiring physical bank visits or offline challans."
        ),
        "action_url": "/withdrawal",
        "action_label": "View Clearance Status",
    },
    {
        "doc_id": "POL-CLR-01",
        "category": "Clearance",
        "title": "Sequential 4-Gate Institutional Clearance Pipeline",
        "clause_code": "ORD-CLR-9.3",
        "content": (
            "Institutional departure, transfer certificate issuance, or withdrawal requires digital sign-off "
            "across 4 sequential clearance desks: Gate 1 Central Library (book returns & dues); Gate 2 Hostel & Mess Office "
            "(inventory inspection & room handover); Gate 3 Finance & Accounts (fee audit & deposit offset reconciliation); "
            "Gate 4 Registrar Office (final document audit & degree release). Each desk officer records digital authorization."
        ),
        "action_url": "/withdrawal",
        "action_label": "Track Clearance Gates",
    },
    {
        "doc_id": "POL-EXAM-01",
        "category": "Examinations",
        "title": "Backpaper & Supplementary Examination Guidelines",
        "clause_code": "ORD-EXAM-12.1",
        "content": (
            "Students with failed courses or seeking grade improvement may apply for Supplementary Backpaper Examinations. "
            "The examination fee is INR 1,500 per registered subject. Applications must be submitted through Form EX-02 within "
            "14 calendar days of semester grade sheet publication. Answer script re-evaluation is admissible within 7 days at INR 750 per subject."
        ),
        "action_url": "/forms",
        "action_label": "Download Form EX-02 (Backpaper)",
    },
    {
        "doc_id": "POL-HSTL-01",
        "category": "Hostel",
        "title": "Hostel Room Vacation, Inventory Handover & Key Return",
        "clause_code": "ORD-HSTL-18.2",
        "content": (
            "Hostel residents vacating campus quarters must conduct physical inventory inspection with the Assistant Warden. "
            "Room inventory checklist and key submission must be completed 24 hours prior to departure. Any physical room damage "
            "or missing fixtures will be offset against the hostel security deposit balance."
        ),
        "action_url": "/forms",
        "action_label": "Hostel Vacation Guidelines",
    },
    {
        "doc_id": "POL-GRV-01",
        "category": "Grievances",
        "title": "Student Grievance Redressal SLA & Proctorial Escalation",
        "clause_code": "ORD-GRV-22.5",
        "content": (
            "Formal student grievances submitted through the portal carry mandatory resolution SLAs: Academic and facility "
            "grievances must be addressed by the Department Coordinator within 48 hours. If unresolved after 48 hours, the ticket "
            "is automatically escalated to the Dean of Student Welfare. Harassment, ragging, or physical safety tickets have an emergency 24h SLA."
        ),
        "action_url": "/chat",
        "action_label": "File Formal Grievance",
    },
    {
        "doc_id": "POL-SCH-01",
        "category": "Scholarships",
        "title": "Merit & Financial Assistance Scholarship Renewal Criteria",
        "clause_code": "ORD-SCH-16.3",
        "content": (
            "Continuation of university merit scholarships requires maintaining a minimum CGPA of 8.0, minimum 80% attendance, "
            "and zero backpapers in the previous academic year. Need-based tuition concessions require annual submission of valid family "
            "income certificate before August 31st annually."
        ),
        "action_url": "/scholarship",
        "action_label": "Explore Scholarships",
    },
    {
        "doc_id": "ORD-HR-FACULTY-EXIT",
        "category": "HR & Faculty",
        "title": "Faculty & Staff Resignation & Relieving Clearance Procedure",
        "clause_code": "ORD-HR-24.1",
        "content": (
            "Faculty members or staff resigning from university service must submit formal written resignation notice "
            "to their Head of Department (HOD) and Dean of Faculty. Following notice acceptance, the employee must complete "
            "the Faculty Exit & No-Dues Clearance Dossier across 4 desks: (1) Department HOD (handover of course files, laboratory "
            "equipment, and continuous evaluation grades); (2) Central Library (return of all accessioned books and journals); "
            "(3) Central Stores & IT (handover of university laptop, printer assets, and biometric access); and (4) Finance & Accounts "
            "(salary reconciliation, advance imprest settlement, and provident fund transfer). Completed clearance dossier must be "
            "submitted to HR Administration Desk (Room 103, Administrative Block). Experience certificate and relieving letter SLA is 15 working days."
        ),
        "action_url": "/forms",
        "action_label": "Download Faculty Exit Format",
    },

    # --- Comprehensive Post-Download Form Procedures (All 30+ Catalog Forms) ---
    {
        "doc_id": "PROC-FORM-MIGRATION",
        "category": "Academics",
        "title": "Migration Certificate Application Procedure",
        "clause_code": "PROC-FORM-15",
        "content": (
            "After obtaining the Migration Certificate Application Form (.doc or .pdf), follow these steps: "
            "1. Attach attested photocopies of all semester grade sheets, provisional degree or bonafide certificate, "
            "university no-dues clearance slip, and student ID proof. "
            "2. Submit the completed application dossier to Registrar Office Window 2 (Room 102, Administrative Block). "
            "3. Official turnaround SLA is 3 to 5 working days. The migration certificate can be collected in person from Window 2 "
            "or dispatched via registered speed post to your home address."
        ),
        "action_url": "/forms",
        "action_label": "Download Migration Form",
    },
    {
        "doc_id": "PROC-FORM-RECHECKING",
        "category": "Examinations",
        "title": "Application for Rechecking & Re-evaluation of Result",
        "clause_code": "PROC-FORM-27",
        "content": (
            "After downloading the Application for Rechecking of Result, follow these steps: "
            "1. Clearly specify subject course codes, paper titles, and semester. "
            "2. Pay the rechecking fee of Rupees 500 per subject paper at the Accounts Counter (Room 14) or online gateway, "
            "and attach the payment receipt and photocopy of your current semester grade report. "
            "3. Submit the completed form to the Controller of Examinations (Examination Cell Window 3) within 15 calendar days "
            "of result declaration. Processing SLA is 21 working days."
        ),
        "action_url": "/forms",
        "action_label": "Download Rechecking Form",
    },
    {
        "doc_id": "PROC-FORM-STUDENT-ID",
        "category": "Admissions & Registrar",
        "title": "Student ID Card Re-issue & Duplicate Form",
        "clause_code": "PROC-FORM-28",
        "content": (
            "After downloading the Student ID Card Form, follow these steps: "
            "1. Fill your enrollment number, program, blood group, and emergency contact details. "
            "2. Attach 1 recent passport photograph (white background), copy of police lost report / NCR (if lost), "
            "and settle the Rupees 200 re-issue fee (or choose Smart Caution Deposit Offsetting). "
            "3. Submit the form to Student Services / Registrar Desk (Room 101). SLA is 48 hours for biometric smart card collection."
        ),
        "action_url": "/forms",
        "action_label": "Download Student ID Form",
    },
    {
        "doc_id": "PROC-FORM-CONDONATION",
        "category": "Academics",
        "title": "Attendance Condonation Application (Form AC-04)",
        "clause_code": "PROC-FORM-AC04",
        "content": (
            "After obtaining Form AC-04 (Attendance Condonation Application), follow these steps: "
            "1. Fill the course codes where your attendance is between 60% and 74.9%. "
            "2. Attach authentic medical certificates with prescription and hospital OPD slips, or verified university duty certificates. "
            "3. Submit the file to the Dean of Academic Affairs (Room 201, Academic Block) at least 10 working days prior to exam start. "
            "If approved, your exam admit card will be unblocked within 48 hours."
        ),
        "action_url": "/forms",
        "action_label": "Download Form AC-04",
    },
    {
        "doc_id": "PROC-FORM-EXIT-INTERVIEW",
        "category": "Student Welfare",
        "title": "Exit Interview Form for Program Withdrawal",
        "clause_code": "PROC-FORM-17",
        "content": (
            "After downloading the Exit Interview Form for Withdrawal, follow these steps: "
            "1. Complete the feedback questionnaire regarding academic experience, facilities, and reason for leaving. "
            "2. Verify completion of the 4 clearance gates (Library, Hostel, Accounts, Department Advisor). "
            "3. Attend a mandatory 15-minute exit counseling meeting with the Dean of Student Welfare (Room 106). "
            "Once signed, submit to Registrar Office (Room 102) to release caution deposit (Rupees 10,000) and tuition fee refund."
        ),
        "action_url": "/withdrawal",
        "action_label": "Open Withdrawal & Exit Portal",
    },
    {
        "doc_id": "PROC-FORM-WITHDRAWAL-APP",
        "category": "Withdrawal & Refunds",
        "title": "Program Withdrawal Application Form",
        "clause_code": "PROC-FORM-WTH",
        "content": (
            "After downloading the Program Withdrawal Application Form, follow these steps: "
            "1. State your primary reason for program withdrawal and attach parent/guardian consent letter, student identity proof, "
            "and a cancelled bank cheque or passbook copy showing IFSC code for NEFT refund transfer. "
            "2. Initiate digital clearance across Library, Hostel, and Finance gates. "
            "3. Submit the signed dossier to Registrar Office (Room 102). Tuition refund is calculated under UGC date slabs, "
            "and the Rupees 10,000 caution deposit is 100% refundable within 14 working days."
        ),
        "action_url": "/withdrawal",
        "action_label": "Start Withdrawal Procedure",
    },
    {
        "doc_id": "PROC-FORM-FEE-CLEARANCE",
        "category": "Finance",
        "title": "Fee Clearance Statement & No Dues Form",
        "clause_code": "PROC-FORM-FEE-CLR",
        "content": (
            "After downloading the Fee Clearance Form, follow these steps: "
            "1. Review pending semester tuition dues, fine assessments, or security balances. "
            "2. If you have outstanding dues under Rupees 2,000 (such as library penalties or lost ID card fee), "
            "check the Smart Offsetting box to auto-deduct from your caution deposit without visiting the bank. "
            "3. Submit the verified clearance slip to Finance & Accounts Counter (Window 4). Clearance updates to CLEARED immediately."
        ),
        "action_url": "/withdrawal",
        "action_label": "View Fee Clearance Gate",
    },
    {
        "doc_id": "PROC-FORM-LIBRARY-CLEARANCE",
        "category": "Clearance",
        "title": "Library No-Dues Clearance Form",
        "clause_code": "PROC-FORM-LIB-CLR",
        "content": (
            "After obtaining the Library Clearance Form, follow these steps: "
            "1. Physically return all borrowed books, reference volumes, and departmental CDs to the Central Library circulation counter. "
            "2. Settle any overdue late fines (Rupees 5 per day) or authorize direct offset against your caution deposit. "
            "3. The Chief Librarian will stamp and digitally clear your Library gate in the university ERP system."
        ),
        "action_url": "/withdrawal",
        "action_label": "View Library Clearance Gate",
    },
    {
        "doc_id": "PROC-FORM-HOSTEL-CLEARANCE",
        "category": "Hostel",
        "title": "Hostel Vacation & Handover Clearance Form",
        "clause_code": "PROC-FORM-HSTL-CLR",
        "content": (
            "After obtaining the Hostel Clearance Form, follow these steps: "
            "1. Request physical room inspection with your Assistant Warden 24 hours prior to vacating. "
            "2. Hand over room keys, almirah keys, and verify the room inventory checklist (fan, light fixtures, furniture). "
            "3. Obtain Warden sign-off and submit the stamped form to the Hostel Administration Desk (Campus Gate 2). "
            "Hostel security deposit refund is cleared within 7 working days."
        ),
        "action_url": "/withdrawal",
        "action_label": "View Hostel Clearance Gate",
    },
    {
        "doc_id": "PROC-FORM-DEGREE",
        "category": "Examinations",
        "title": "Degree Application & Convocation Format",
        "clause_code": "PROC-FORM-22",
        "content": (
            "After downloading the Degree Application Format, follow these steps: "
            "1. Attach attested photocopies of final cumulative grade sheet (all semesters passed), 10th class passing certificate "
            "(for date-of-birth verification), university no-dues clearance certificate, and Rupees 1,500 convocation fee receipt. "
            "2. Submit the dossier to the Controller of Examinations (Degree Cell Window 1). Turnaround SLA is 15 working days "
            "for provisional degree and convocation roll inclusion."
        ),
        "action_url": "/forms",
        "action_label": "Download Degree Application",
    },
    {
        "doc_id": "PROC-FORM-EXAM-BLANK",
        "category": "Examinations",
        "title": "Blank Examination Application Form",
        "clause_code": "PROC-FORM-20",
        "content": (
            "After downloading the Blank Examination Form, follow these steps: "
            "1. Enter your chosen core and elective course codes for the upcoming end-term semester exams. "
            "2. Verify that your attendance in each subject is above the 75% cutoff. "
            "3. Attach your semester exam fee challan and submit the form to the Examination Cell (Block 3, Room 110) "
            "before the notified semester examination cutoff date."
        ),
        "action_url": "/exams",
        "action_label": "Open Exam Application",
    },
    {
        "doc_id": "PROC-FORM-PLACEMENT-OPT",
        "category": "Career & Placement",
        "title": "Placement Opted Out Declaration Form",
        "clause_code": "PROC-FORM-16",
        "content": (
            "After downloading the Placement Opted Out Declaration Form, follow these steps: "
            "1. Fill your details and declare your chosen post-graduation plan (higher studies / GRE / GATE / civil services, entrepreneurship, or family business). "
            "2. Obtain parent / guardian endorsement signature. "
            "3. Submit the completed declaration to Corporate Resource Centre (CRC, Block E Ground Floor). "
            "You will be exempted from mandatory campus placement attendance without penalty."
        ),
        "action_url": "/forms",
        "action_label": "Download Placement Opt-Out Form",
    },
    {
        "doc_id": "PROC-FORM-TADA",
        "category": "Finance",
        "title": "Travelling & Daily Allowance (TA/DA) Claim Format",
        "clause_code": "PROC-FORM-08",
        "content": (
            "After downloading the TA / DA Claim Format, follow these steps: "
            "1. Enter departure and arrival dates, conveyance modes, and daily allowance entitlement. "
            "2. Attach original boarding passes, rail / air tickets, taxi bills, and event participation certificate "
            "along with the prior university duty approval sanction. "
            "3. Submit the claim to Finance & Accounts (Room 14) within 30 days of travel. Reimbursement SLA is 7 to 10 working days."
        ),
        "action_url": "/forms",
        "action_label": "Download TA/DA Claim Form",
    },
    {
        "doc_id": "PROC-FORM-LOCAL-CONV",
        "category": "Finance",
        "title": "Local Conveyance Reimbursement Form",
        "clause_code": "PROC-FORM-11",
        "content": (
            "After downloading the Local Conveyance Form, follow these steps: "
            "1. Fill travel date, destinations, official purpose, and kilometer reading or fare. "
            "2. Attach original fuel slips, metro receipts, or taxi invoices. "
            "3. Obtain HOD or reporting supervisor approval and submit to Finance Counter (Room 14). "
            "Reimbursement is processed within 5 working days."
        ),
        "action_url": "/forms",
        "action_label": "Download Local Conveyance Form",
    },
    {
        "doc_id": "PROC-FORM-IMPREST",
        "category": "Finance",
        "title": "Advance Imprest Requisition Form",
        "clause_code": "PROC-FORM-12",
        "content": (
            "After downloading the Advance Imprest Requisition Form, follow these steps: "
            "1. Specify the official purpose, event name, and detailed budget breakdown. "
            "2. Obtain sanction endorsement from the Pro-Chancellor / Registrar. "
            "3. Submit the sanctioned requisition to Finance & Accounts for check or bank transfer disbursement. "
            "Final bills and expense settlement must be submitted within 15 calendar days of event completion."
        ),
        "action_url": "/forms",
        "action_label": "Download Imprest Requisition",
    },
    {
        "doc_id": "PROC-FORM-MENTOR",
        "category": "Student Welfare",
        "title": "Mentoring Record Card & Mentor-Mentee Log",
        "clause_code": "PROC-FORM-13",
        "content": (
            "After downloading the Mentoring Record Card, follow these steps: "
            "1. Schedule your monthly 1-on-1 counseling session with your assigned faculty mentor. "
            "2. Update your attendance percentage, mid-term test scores, career ambitions, and any personal grievances. "
            "3. Both student and mentor sign the card; it is maintained in the Department Mentorship Cell for academic progress tracking."
        ),
        "action_url": "/forms",
        "action_label": "Download Mentoring Record",
    },
    {
        "doc_id": "PROC-FORM-PURCHASE",
        "category": "Procurement",
        "title": "Purchase Proposal & Requisition Format",
        "clause_code": "PROC-FORM-14",
        "content": (
            "After downloading the Purchase Proposal Format, follow these steps: "
            "1. Fill equipment or consumable specifications, quantity, and estimated budget code. "
            "2. Attach minimum 3 comparative vendor quotations and technical justification. "
            "3. Obtain HOD recommendation and submit to Central Purchase Committee (Stores Building). Review turnaround is 7 working days."
        ),
        "action_url": "/forms",
        "action_label": "Download Purchase Proposal",
    },
    {
        "doc_id": "PROC-FORM-STATIONERY",
        "category": "Logistics & Stores",
        "title": "Stationery Indent Requisition Format",
        "clause_code": "PROC-FORM-18",
        "content": (
            "After downloading the Stationery Indent Requisition, follow these steps: "
            "1. Itemize required office and classroom supplies (registers, markers, paper reams, printer cartridges). "
            "2. Obtain department coordinator signature. "
            "3. Submit indent to Central Store counter on distribution days (Tuesdays and Thursdays, 10 AM to 1 PM)."
        ),
        "action_url": "/forms",
        "action_label": "Download Stationery Indent",
    },
    {
        "doc_id": "PROC-FORM-BIOMETRIC",
        "category": "HR & IT",
        "title": "Biometric / ID Card Issue Application",
        "clause_code": "PROC-FORM-19",
        "content": (
            "After downloading the Biometric / Forgotten ID Card Application, follow these steps: "
            "1. Fill employee/student ID, department, and reason for re-issue. "
            "2. Obtain supervisor sign-off. "
            "3. Bring the form to IT Support & Biometrics Desk (Admin Block Room 105) for instant biometric re-registration and temporary RFID access clearance."
        ),
        "action_url": "/forms",
        "action_label": "Download Biometric Application",
    },
    {
        "doc_id": "PROC-FORM-FACULTY-LEAVE",
        "category": "HR & Staff",
        "title": "Faculty Leave Application & Emergency Leave Proforma",
        "clause_code": "PROC-FORM-23",
        "content": (
            "After downloading the Faculty Leave Application / Emergency Leave Proforma, follow these steps: "
            "1. Specify leave type (Casual, Earned, Duty, Medical, or Emergency). "
            "2. Secure substitute colleague teacher signatures on the class arrangement sheet. "
            "3. Submit the completed application to HR Administration (Room 103) at least 48 hours prior to planned absence "
            "(or within 24 hours of resuming for emergency leave)."
        ),
        "action_url": "/forms",
        "action_label": "Download Leave Application",
    },
    {
        "doc_id": "PROC-FORM-EMPLOYEE-ID",
        "category": "HR & Staff",
        "title": "Employee ID Card Form",
        "clause_code": "PROC-FORM-24",
        "content": (
            "After downloading the Employee ID Card Form, follow these steps: "
            "1. Fill employee personal details, blood group, designation, and department. "
            "2. Attach official appointment letter copy and one passport photograph with white background. "
            "3. Submit to HR Desk (Admin Block Room 103). SLA is 2 working days for card printing and campus access activation."
        ),
        "action_url": "/forms",
        "action_label": "Download Employee ID Form",
    },
    {
        "doc_id": "PROC-FORM-CLASS-ARRANGEMENT",
        "category": "Academics",
        "title": "Class Arrangement Format",
        "clause_code": "PROC-FORM-03",
        "content": (
            "After downloading the Class Arrangement Format, follow these steps: "
            "1. Enter subject names, classroom numbers, and scheduled lecture timings. "
            "2. Obtain written agreement signatures from covering faculty colleagues. "
            "3. Submit the form to Department Time-Table Coordinator 24 hours prior to leave."
        ),
        "action_url": "/forms",
        "action_label": "Download Class Arrangement Form",
    },
    {
        "doc_id": "PROC-FORM-FINANCIAL-ASST",
        "category": "Finance",
        "title": "Format for Financial Assistance for Events",
        "clause_code": "PROC-FORM-06",
        "content": (
            "After downloading the Financial Assistance Form for Events, follow these steps: "
            "1. Attach technical event brochure, expected guest list, and itemized expenditure proposal. "
            "2. Secure faculty advisor and student club head endorsement. "
            "3. Submit to Dean of Student Welfare (Room 106) at least 3 weeks prior to event date."
        ),
        "action_url": "/forms",
        "action_label": "Download Financial Asst Form",
    },
    {
        "doc_id": "PROC-FORM-DEBARRED-LETTER",
        "category": "Academics",
        "title": "Notice Letter to Parents of Debarred Students",
        "clause_code": "PROC-FORM-07",
        "content": (
            "Format Letter to Parents of Debarred Students is an institutional academic alert issued when student attendance falls below 60%. "
            "Parents must attend a mandatory proctorial meeting with the Department Head within 5 working days to establish an academic probation contract and remedial recovery plan."
        ),
        "action_url": "/forms",
        "action_label": "View Debarment Letter Format",
    },
    {
        "doc_id": "PROC-FORM-TRANSPORT",
        "category": "Logistics & Fleet",
        "title": "Requisition for Transport",
        "clause_code": "PROC-FORM-10",
        "content": (
            "After downloading the Requisition for Transport, follow these steps: "
            "1. Specify trip date, pickup/drop times, destination, passenger list, and official purpose. "
            "2. Obtain HOD sanction signature. "
            "3. Submit to Transport Officer (Campus Gate 2 Office) at least 48 hours prior to scheduled departure."
        ),
        "action_url": "/forms",
        "action_label": "Download Transport Requisition",
    },
    {
        "doc_id": "PROC-FORM-CAFETERIA",
        "category": "Logistics & Catering",
        "title": "Requisition for Refreshment (Cafeteria)",
        "clause_code": "PROC-FORM-09",
        "content": (
            "After downloading the Requisition for Refreshment (Cafeteria), follow these steps: "
            "1. Fill meeting / seminar name, venue room, guest count, and selected catering menu items. "
            "2. Obtain departmental financial approval. "
            "3. Submit to Hospitality & Cafeteria Manager 24 hours in advance."
        ),
        "action_url": "/forms",
        "action_label": "Download Refreshment Requisition",
    },
    {
        "doc_id": "PROC-FORM-PATENTS",
        "category": "Research & Patents",
        "title": "List of Patents & IP Disclosure Format",
        "clause_code": "PROC-FORM-PAT",
        "content": (
            "The Patents Directory and Invention Disclosure Format allows faculty and students to protect intellectual property. "
            "Complete patent disclosure forms, attach novelty claims and diagrams, and submit to Dean of Research & Development (Room 304). "
            "University provides 100% patent filing funding for approved inventions."
        ),
        "action_url": "/forms",
        "action_label": "View Patent Registry Format",
    },
    {
        "doc_id": "PROC-FORM-CARTRIDGE",
        "category": "IT & Logistics",
        "title": "Cartridge Refill Form",
        "clause_code": "PROC-FORM-21",
        "content": (
            "After downloading the Cartridge Refill Form, follow these steps: "
            "1. Record departmental printer serial number and model. "
            "2. Obtain lab technician endorsement. "
            "3. Take empty cartridge and form to IT Hardware Desk (Server Room, 2nd Floor). Turnaround SLA is 4 hours."
        ),
        "action_url": "/forms",
        "action_label": "Download Cartridge Requisition",
    },
    {
        "doc_id": "PROC-FORM-DIRECTORY",
        "category": "Directory",
        "title": "ASET Faculty & Staff Contact Directory",
        "clause_code": "PROC-FORM-05",
        "content": (
            "The Faculty & Staff Contact Directory provides official intercom extensions, office room numbers, email addresses, "
            "and consultation hours for all ASET professors, academic coordinators, and laboratory instructors."
        ),
        "action_url": "/forms",
        "action_label": "View Faculty Directory",
    },
    {
        "doc_id": "PROC-FORM-DL",
        "category": "Logistics & Fleet",
        "title": "Driving License / Duty Driving Permission Form",
        "clause_code": "PROC-FORM-01",
        "content": (
            "After downloading the DL Permission Form, follow these steps: "
            "1. Attach copy of valid state driving license and institutional appointment proof. "
            "2. Obtain Department Head sign-off. "
            "3. Submit to Campus Security & Fleet Office (Gate 1). Turnaround SLA is 24 hours."
        ),
        "action_url": "/forms",
        "action_label": "Download DL Permission Form",
    },
]


class PolicySearchService:
    """Provides SQLite FTS5 full-text search and personalized policy guidance."""

    @classmethod
    def initialize_fts_index(cls) -> None:
        """Create and populate the FTS5 virtual table if empty or incomplete."""
        conn = get_connection()
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS policy_fts USING fts5(
                doc_id UNINDEXED,
                category,
                title,
                clause_code,
                content,
                action_url UNINDEXED,
                action_label UNINDEXED,
                tokenize='porter unicode61'
            );
            """
        )

        cur = conn.execute("SELECT count(*) FROM policy_fts")
        count = cur.fetchone()[0]

        if count < len(DEFAULT_POLICIES):
            conn.execute("DELETE FROM policy_fts")
            for p in DEFAULT_POLICIES:
                conn.execute(
                    """
                    INSERT INTO policy_fts (doc_id, category, title, clause_code, content, action_url, action_label)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        p["doc_id"],
                        p["category"],
                        p["title"],
                        p["clause_code"],
                        p["content"],
                        p["action_url"],
                        p["action_label"],
                    ),
                )
            conn.commit()

    @classmethod
    def search_policies(
        cls,
        query: str,
        category: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search policy ordinances using BM25 ranking and snippet generation."""
        cls.initialize_fts_index()
        conn = get_connection()

        sanitized = re.sub(r"[^\w\s]", " ", query).strip()
        if not sanitized:
            return []

        STOP_WORDS = {
            "what", "whats", "should", "i", "do", "does", "did", "after", "getting", "the", "a", "an", "this",
            "that", "these", "those", "from", "how", "can", "could", "you", "take", "me", "tell", "where", "is",
            "are", "was", "were", "be", "been", "being", "have", "has", "had", "having",
            "of", "to", "for", "in", "on", "at", "by", "with", "my", "your", "his", "her", "their", "our",
            "please", "want", "would", "like", "get", "downloading", "got", "need", "know", "about",
            "which", "we", "he", "she", "they", "them", "here", "there", "it", "its", "and", "or", "but",
            "if", "then", "else", "so", "as", "just", "not", "no", "dont", "don't", "ask", "asked", "asking",
            "say", "said", "saying", "speak", "tell", "told", "talk", "kuch", "nahi", "kya", "kyun", "kaise",
            "kab", "kisko", "kis", "mera", "meri", "mere", "tera", "teri", "tere", "uska", "uski", "uske",
            "iska", "iski", "iske", "maine", "mujhe", "tumhe", "apko", "aapko", "hai", "hain", "ko", "se",
            "me", "mein", "par", "ka", "ki", "ke", "batao", "bataiye", "dijiye", "kijiye", "karna", "karo",
            "nothing", "none", "cancel", "stop", "never", "ruko", "ok", "okay", "haan", "ha", "yes", "ye",
            "yeh", "wo", "woh", "sir", "mam", "madam", "bro", "hello", "hi", "hey", "namaste", "thanks", "thank"
        }
        GENERIC_META_WORDS = {
            "student", "students", "university", "college", "campus", "department",
            "official", "documents", "document", "service", "services", "center",
            "kiosk", "desk", "portal", "system", "office", "section", "cell", "page",
            "screen", "window", "block", "room"
        }
        all_words = [token.lower() for token in sanitized.split() if token]
        content_words = [w for w in all_words if len(w) >= 3 and w not in STOP_WORDS]
        substantive_words = [w for w in content_words if w not in GENERIC_META_WORDS]
        # Strictly require substantive keywords. Queries containing only generic words (e.g. 'student office') must never trigger FTS policy retrieval
        if not substantive_words:
            return []
        search_words = substantive_words

        # Progressive matching: Pass 1 with AND (high precision), Pass 2 with OR (high recall)
        for operator in (" AND ", " OR "):
            if operator == " OR " and len(search_words) < 2:
                # OR is redundant if only 1 substantive word was present
                continue

            tokens = [f'"{w}"*' if len(w) >= 4 else f'"{w}"' for w in search_words]
            match_expr = operator.join(tokens)

            params: list[Any] = []
            sql = """
                SELECT
                    doc_id,
                    category,
                    title,
                    clause_code,
                    content,
                    action_url,
                    action_label,
                    snippet(policy_fts, 4, '<mark>', '</mark>', '...', 28) AS snippet_text,
                    bm25(policy_fts) AS rank_score
                FROM policy_fts
                WHERE policy_fts MATCH ?
            """
            params.append(match_expr)

            if category and category.lower() != "all":
                sql += " AND category = ?"
                params.append(category)

            sql += " ORDER BY rank_score ASC LIMIT ?"
            params.append(limit)

            try:
                cur = conn.execute(sql, params)
                rows = cur.fetchall()
                if rows:
                    results = []
                    for r in rows:
                        row_dict = {
                            "doc_id": r["doc_id"],
                            "category": r["category"],
                            "title": r["title"],
                            "clause_code": r["clause_code"],
                            "content": r["content"],
                            "action_url": r["action_url"],
                            "action_label": r["action_label"],
                            "snippet": r["snippet_text"] or (r["content"][:160] + "..."),
                            "score": round(float(r["rank_score"]), 3),
                        }
                        # For Pass 2 (OR), verify substantive content/title overlap and BM25 threshold
                        if operator == " OR ":
                            t_lower = row_dict["title"].lower()
                            c_lower = row_dict["content"].lower()
                            has_title_match = any(sw in t_lower for sw in search_words)
                            has_content_match = any(sw in c_lower for sw in search_words)
                            if not has_title_match and not has_content_match:
                                continue
                            # BM25 scores are negative (e.g. -2.5 is strong, -0.6 is weak). Filter out weak matches without title match
                            if row_dict["score"] > -0.75 and not has_title_match:
                                continue
                        results.append(row_dict)
                    if results:
                        return results
            except sqlite3.OperationalError:
                continue

        # Fallback with exact LIKE for single meaningful substantive term >= 4 chars
        meaningful_terms = [w for w in search_words if len(w) >= 4]
        if not meaningful_terms:
            return []

        fallback_sql = """
            SELECT doc_id, category, title, clause_code, content, action_url, action_label
            FROM policy_fts
            WHERE content LIKE ? OR title LIKE ?
            LIMIT ?
        """
        key_term = meaningful_terms[0]
        like_pat = f"%{key_term}%"
        cur = conn.execute(fallback_sql, (like_pat, like_pat, limit))
        results = []
        for r in cur.fetchall():
            results.append(
                {
                    "doc_id": r["doc_id"],
                    "category": r["category"],
                    "title": r["title"],
                    "clause_code": r["clause_code"],
                    "content": r["content"],
                    "action_url": r["action_url"],
                    "action_label": r["action_label"],
                    "snippet": r["content"][:160] + "...",
                    "score": 0.0,
                }
            )
        return results

    @classmethod
    def _expand_multilingual_query(cls, query: str) -> str:
        """Expand Hindi and Hinglish keywords to English terms so SQLite FTS5 matches English policy documents."""
        q_low = query.lower()
        additions = []
        hindi_map = {
            "विड्रॉल": "withdrawal",
            "वापसी": "withdrawal refund",
            "रिफंड": "refund",
            "हटना": "withdrawal",
            "छोड़ना": "withdrawal",
            "कौशन": "caution deposit",
            "कॉशन": "caution deposit",
            "डिपॉजिट": "caution deposit",
            "सिक्योरिटी": "caution deposit",
            "ऑफसेट": "smart offset",
            "कटौती": "offset deduction",
            "पहचान पत्र": "id card fine offset",
            "आईडी": "id card",
            "कार्ड": "id card",
            "अटेंडेंस": "attendance",
            "उपस्थिति": "attendance condonation",
            "हाजिरी": "attendance",
            "छूट": "condonation relaxation",
            "कंडोनेशन": "condonation",
            "परीक्षा": "examination exam",
            "एग्जाम": "examination exam",
            "एडमिट कार्ड": "admit card",
            "बैकपेपर": "backpaper exam",
            "बैक": "backpaper",
            "पुनर्मूल्यांकन": "rechecking re-evaluation",
            "फीस": "fee dues clearance",
            "शुल्क": "fee dues",
            "बकाया": "dues",
            "क्लियरेंस": "clearance gate",
            "नो ड्यूज": "no dues clearance",
            "फॉर्म": "form procedure download",
            "आवेदन": "application form",
            "प्रपत्र": "form application",
            "माइग्रेशन": "migration certificate",
            "शिकायत": "grievance complaint ticket",
            "स्कॉलरशिप": "scholarship",
            "छात्रवृत्ति": "scholarship",
            "job chhod": "faculty staff resignation relieving clearance",
            "job chhodna": "faculty staff resignation relieving clearance",
            "job chhodani": "faculty staff resignation relieving clearance",
            "naukri chhodna": "faculty staff resignation relieving clearance",
            "resignation": "faculty staff resignation relieving clearance",
            "relieving": "faculty staff resignation relieving clearance",
            "istifa": "faculty staff resignation relieving clearance",
            "इस्तीफा": "faculty staff resignation relieving clearance",
            "नौकरी छोड़ना": "faculty staff resignation relieving clearance",
        }
        for k, v in hindi_map.items():
            if k in query or k in q_low:
                additions.append(v)
        if additions:
            return f"{query} {' '.join(additions)}"
        return query

    @classmethod
    def _is_policy_relevant_to_query(cls, query: str, policy: dict[str, Any]) -> bool:
        """Verify that the policy has substantive lexical overlap with the query to prevent false-positive ordinance dumps."""
        STOP = {
            "what", "whats", "should", "i", "do", "does", "did", "after", "getting", "the", "a", "an", "this",
            "that", "these", "those", "from", "how", "can", "could", "you", "take", "me", "tell", "where", "is",
            "are", "was", "were", "be", "been", "being", "have", "has", "had", "having",
            "of", "to", "for", "in", "on", "at", "by", "with", "my", "your", "his", "her", "their", "our",
            "please", "want", "would", "like", "get", "downloading", "got", "need", "know", "about",
            "which", "we", "he", "she", "they", "them", "here", "there", "it", "its", "and", "or", "but",
            "not", "no", "dont", "don't", "ask", "asked", "kuch", "nahi", "kya", "kyun", "kaise", "hai", "hain"
        }
        GENERIC_META = {
            "student", "students", "university", "college", "campus", "department",
            "official", "documents", "document", "service", "services", "center",
            "kiosk", "desk", "portal", "system", "office", "section", "cell", "page",
            "screen", "window", "block", "room"
        }
        all_tokens = [w.lower() for w in re.sub(r"[^\w\s]", " ", query).split() if len(w) >= 3 and w.lower() not in STOP]
        substantive_tokens = [t for t in all_tokens if t not in GENERIC_META]
        check_tokens = substantive_tokens if substantive_tokens else all_tokens
        if not check_tokens:
            return False

        title_lower = policy.get("title", "").lower()
        content_lower = policy.get("content", "").lower()
        clause_code = policy.get("clause_code", "").lower()

        # Direct match in title or clause code is high confidence
        if any(t in title_lower or t in clause_code for t in check_tokens):
            return True

        # Content match requires at least one substantive token of length >= 4
        return any(len(t) >= 4 and t in content_lower for t in check_tokens)

    @classmethod
    def hybrid_guidance(
        cls,
        query: str,
        student_id: str | None = None,
        page_context: dict[str, Any] | None = None,
        language: str = "en-IN",
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Synthesize zero-hallucination guidance combining live student profile, FTS5 policy clauses, ambient screen awareness, and optional Gemini AI synthesis."""
        conn = get_connection()

        # Retrieve student record if authenticated
        student: dict[str, Any] | None = None
        if student_id and student_id != "GUEST" and student_id != "PUBLIC":
            cur = conn.execute(
                "SELECT id, name, course, branch, semester, attendance, cgpa, fee_status, fee_due FROM students WHERE id = ?",
                (student_id,),
            )
            row = cur.fetchone()
            if row:
                student = dict(row)

        is_authenticated = student is not None
        student_name = (student or {}).get("name", "").split()[0] if is_authenticated else "Student"
        attendance = float((student or {}).get("attendance", 75.0))

        q_lower = query.lower()

        # =========================================================================
        # 00. Conversational, Greetings, Small Talk, Negations & Cancellations Guard
        # =========================================================================
        q_clean = re.sub(r"[^\w\s]", " ", q_lower).strip()
        words = q_clean.split()
        word_count = len(words)

        # A. Negations, Dismissals, and Cancellations ("I did not ask", "Maine nahi pucha", "kuch nahi", "stop", "cancel")
        is_negation_or_dismissal = any(
            phrase in q_clean or phrase in query for phrase in [
                "did not ask", "didnt ask", "not asking", "not ask", "never asked",
                "maine nahi pucha", "maine ye nahi", "maine yeh nahi", "ye nahi pucha", "yeh nahi pucha",
                "ye nahi", "yeh nahi", "not this", "wrong answer", "galat hai", "yeh galat hai", "ye galat hai",
                "kuch nahi", "kuch nhi", "kuch nahi chahiye", "nothing", "nothing required",
                "never mind", "nevermind", "no need", "koi zaroorat nahi", "koi jarurat nahi",
                "nahi chahiye", "rehne do", "rehne de", "dont need", "don't need", "cancel", "stop", "ruko",
                "chhodo", "choro",
                "नहीं पूछा", "यह नहीं पूछा", "मैंने नहीं पूछा", "मैंने यह नहीं पूछा", "कुछ नहीं", "नहीं चाहिए",
                "गलत है", "यह गलत है", "रोको", "रुकिए", "बंद करो", "छोड़ो"
            ]
        ) or (
            word_count <= 4 and any(w in words or w in query for w in ["nahi", "not", "no", "नहीं"]) and any(w in words or w in query for w in ["ask", "pucha", "kuch", "need", "chahiye", "bol", "bola", "पूछा", "कुछ", "चाहिए"])
        )

        if is_negation_or_dismissal:
            if language == "hi-IN":
                ack_msg = (
                    f"समझा {student_name}, क्षमा करें! "
                    "कृपया बताएं कि आपको विश्वविद्यालय फॉर्म, उपस्थिति नियम, फीस, परीक्षा या किस प्रक्रिया में सहायता चाहिए?"
                )
            elif language == "hi-Latn":
                ack_msg = (
                    f"Samajh gaya {student_name}, mafi chahta hoon! "
                    "Aap batayein aapko university forms, attendance rules, fees, exams ya kis policy me help chahiye?"
                )
            else:
                ack_msg = (
                    f"Understood, {student_name}! My apologies. "
                    "Please let me know what university form, attendance rule, fee clearance, or campus policy you'd like help with."
                )
            return {
                "answer": ack_msg,
                "domain": "Conversational",
                "citations": [],
                "recommended_action": None,
                "action_url": None,
                "voice_speech_text": ack_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # B. Pure Greetings ("hello", "hi", "hey", "namaste", "good morning", "how are you")
        is_pure_greeting = (
            q_clean in (
                "hello", "hi", "hey", "helo", "hlo", "hii", "hiii",
                "namaste", "namaskar", "pranam", "good morning", "good afternoon", "good evening",
                "kaise ho", "kya haal hai", "kaisa hai", "how are you", "how are you doing", "whats up", "what s up",
                "नमस्ते", "नमस्कार", "प्रणाम", "सुप्रभात"
            ) or (
                word_count <= 3 and any(w in ("hello", "hi", "hey", "namaste", "namaskar", "नमस्ते", "नमस्कार", "प्रणाम") for w in (words + [query.strip()]))
                and not any(domain_kw in q_clean for domain_kw in ["fee", "form", "attendance", "exam", "hostel", "refund", "clearance", "withdrawal", "scholarship", "grade", "marks", "result", "degree"])
            )
        )
        if is_pure_greeting:
            if language == "hi-IN":
                greet_msg = (
                    f"नमस्ते {student_name}! मैं UniAssist, आपका विश्वविद्यालय AI परामर्शदाता (Counselor) हूँ। "
                    "आज मैं फॉर्म, उपस्थिति नियम (75%), फीस रिफंड, परीक्षाओं या कैंपस प्रक्रियाओं में आपकी क्या सहायता कर सकता हूँ?"
                )
            elif language == "hi-Latn":
                greet_msg = (
                    f"Namaste {student_name}! Main UniAssist hoon, aapka university AI counselor. "
                    "Aaj main aapki forms, attendance rules (75%), fee refunds, examinations, ya campus policies me kya madad kar sakta hoon?"
                )
            else:
                greet_msg = (
                    f"Hello {student_name}! I am UniAssist, your university AI counselor. "
                    "How can I assist you today with official forms, attendance rules (75%), fee refunds, exams, or campus policies?"
                )
            return {
                "answer": greet_msg,
                "domain": "Conversational",
                "citations": [],
                "recommended_action": None,
                "action_url": None,
                "voice_speech_text": greet_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # C. Gratitude & Thanks ("thanks", "thank you", "dhanyawad", "shukriya")
        is_gratitude = (
            q_clean in (
                "thanks", "thank you", "thank u", "thx", "dhanyawad", "dhanyawaad", "shukriya",
                "bahut dhanyawad", "thank you so much", "thanks a lot", "many thanks",
                "धन्यवाद", "शुक्रिया", "बहुत धन्यवाद"
            ) or (
                word_count <= 4 and any(w in words or w in query for w in ["thanks", "thank", "dhanyawad", "shukriya", "धन्यवाद", "शुक्रिया"])
                and not any(domain_kw in q_clean for domain_kw in ["fee", "form", "attendance", "exam", "refund", "withdrawal"])
            )
        )
        if is_gratitude:
            if language == "hi-IN":
                thank_msg = f"आपका स्वागत है, {student_name}! यदि आपको कैंपस प्रक्रियाओं या फॉर्म के बारे में कुछ और पूछना हो तो बेझिझक बताएं।"
            elif language == "hi-Latn":
                thank_msg = f"Aapka swagat hai, {student_name}! University procedures ya forms ke baare me jab bhi zaroorat ho, aap pooch sakte hain."
            else:
                thank_msg = f"You are very welcome, {student_name}! Feel free to ask whenever you need assistance with university procedures or documents."
            return {
                "answer": thank_msg,
                "domain": "Conversational",
                "citations": [],
                "recommended_action": None,
                "action_url": None,
                "voice_speech_text": thank_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # D. Identity & Help Inquiries ("who are you", "tum kaun ho", "what can you do")
        domain_terms = ["form", "फॉर्म", "fee", "फीस", "attendance", "अटेंडेंस", "उपस्थिति", "exam", "परीक्षा", "clearance", "refund", "withdrawal", "hostel", "scholarship", "grade", "marks", "degree", "migration"]
        is_identity = (
            any(
                phrase in q_clean or phrase in query for phrase in [
                    "who are you", "tum kaun ho", "aap kaun ho", "what can you do", "kya kar sakte ho",
                    "आप कौन हैं", "तुम कौन हो", "आप क्या कर सकते हैं"
                ]
            )
            or (
                (q_clean in ("help", "help me", "can you help me", "madad", "sahayata", "मदद", "सहायता")
                 or (word_count <= 3 and any(w in words for w in ["help", "madad", "sahayata"])))
                and not any(dt in q_clean or dt in query for dt in domain_terms)
            )
        )
        if is_identity:
            if language == "hi-IN":
                ident_msg = (
                    f"मैं UniAssist हूँ, विश्वविद्यालय कियोस्क का आधिकारिक AI परामर्शदाता। "
                    "मैं उपस्थिति नियम (75% सीमा, मेडिकल छूट), विड्रॉल रिफंड, कॉशन डिपॉजिट ऑफसेट, सभी 31 फॉर्म डाउनलोड करने और विश्वविद्यालय नियमों को समझाने में आपकी सहायता करता हूँ।"
                )
            elif language == "hi-Latn":
                ident_msg = (
                    f"Main UniAssist hoon, university kiosk ka official AI counselor. "
                    "Main attendance rules (75% threshold, medical condonation), withdrawal fee refund aur caution deposit offset, sabhi 31 forms download karne, aur university rules samjhane me help karta hoon."
                )
            else:
                ident_msg = (
                    f"I am UniAssist, the official AI counselor for the university kiosk. "
                    "I can assist you with attendance rules (75% cutoff, medical condonation), program withdrawal refunds, caution deposit offsets, downloading all 31 verified forms, and university ordinances."
                )
            return {
                "answer": ident_msg,
                "domain": "Conversational",
                "citations": [],
                "recommended_action": "Browse Forms & Policies",
                "action_url": "/forms",
                "voice_speech_text": ident_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # E. Affirmation / Closing ("okay", "ok", "thik hai", "got it") without prior active flow
        is_pure_acknowledgment = (
            q_clean in ("ok", "okay", "thik hai", "theek hai", "got it", "samajh gaya", "samajh gayi", "all right", "alright", "fine", "cool", "done")
        )
        if is_pure_acknowledgment and not history:
            if language == "hi-IN":
                ack_msg = f"बढ़िया {student_name}! किसी अन्य विश्वविद्यालय प्रक्रिया में सहायता चाहिए तो अवश्य बताएं।"
            elif language == "hi-Latn":
                ack_msg = f"Badhiya {student_name}! Kisi aur university procedure me help chahiye ho toh zaroor batayein."
            else:
                ack_msg = f"Great {student_name}! Let me know if you need assistance with any other university procedure."
            return {
                "answer": ack_msg,
                "domain": "Conversational",
                "citations": [],
                "recommended_action": None,
                "action_url": None,
                "voice_speech_text": ack_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # =========================================================================
        # 00B. Direct UI Navigation & Screen Routing Intent Guard (Phase 1)
        # =========================================================================
        is_dashboard_nav = any(kw in q_clean or kw in query for kw in [
            "dashboard", "डैशबोर्ड", "student dashboard", "open dashboard", "go to dashboard",
            "where can i go to student dashboard", "where is student dashboard", "dashboard kahan hai",
            "dashboard par kaise jaun", "dashboard kaise khole", "show dashboard", "go to dashboard"
        ])
        if is_dashboard_nav:
            if language == "hi-IN":
                dash_ans = (
                    f"{student_name}, आप नीचे दिए गए 'Open Student Dashboard' बटन पर क्लिक करके या ऊपर मुख्य नेविगेशन बार से सीधे अपना स्टूडेंट डैशबोर्ड खोल सकते हैं। "
                    "वहाँ आपकी लाइव उपस्थिति (Attendance), पंजीकृत विषय, और फीस स्थिति उपलब्ध है।"
                )
            elif language == "hi-Latn":
                dash_ans = (
                    f"{student_name}, aap neeche diye gaye 'Open Student Dashboard' button par click karke seedha apna Student Dashboard khol sakte hain. "
                    "Wahan aapki live attendance percentage, enrolled courses, aur fee clearance status show hota hai."
                )
            else:
                dash_ans = (
                    f"{student_name}, you can access your Student Dashboard directly by clicking 'Open Student Dashboard' below or via the top navigation bar. "
                    "It displays your live attendance percentage, enrolled courses, and fee clearance status."
                )
            return {
                "answer": dash_ans,
                "domain": "Navigation",
                "citations": [],
                "recommended_action": "Open Student Dashboard",
                "action_url": "/dashboard",
                "voice_speech_text": dash_ans,
                "screen_instruction": "Click 'Open Student Dashboard' below to navigate to your student home.",
                "highlight_target": "Open Student Dashboard",
                "engine": "UniAssist Policy Engine",
            }

        is_profile_nav = any(kw in q_clean or kw in query for kw in [
            "my profile", "student profile", "open profile", "profile kahan hai", "view profile",
            "मेरी प्रोफाइल", "प्रोफाइल कहाँ है"
        ])
        if is_profile_nav:
            if language == "hi-IN":
                prof_ans = f"{student_name}, आप नीचे दिए गए 'View Student Profile' बटन पर क्लिक करके अपना छात्र प्रोफाइल, शाखा, सेमेस्टर और शैक्षणिक रिकॉर्ड देख सकते हैं।"
            elif language == "hi-Latn":
                prof_ans = f"{student_name}, aap neeche diye gaye 'View Student Profile' button par click karke apna profile, branch, semester aur academic records dekh sakte hain."
            else:
                prof_ans = f"{student_name}, you can view your official profile, branch, semester, and registered academic records by clicking 'View Student Profile' below."
            return {
                "answer": prof_ans,
                "domain": "Navigation",
                "citations": [],
                "recommended_action": "View Student Profile",
                "action_url": "/profile",
                "voice_speech_text": prof_ans,
                "screen_instruction": None,
                "highlight_target": "View Student Profile",
                "engine": "UniAssist Policy Engine",
            }

        is_tracking_nav = any(kw in q_clean or kw in query for kw in [
            "track token", "token tracking", "clearance token", "token status", "track clearance",
            "टोकन ट्रैक", "टोकन कहाँ देखें"
        ])
        if is_tracking_nav:
            if language == "hi-IN":
                tr_ans = f"{student_name}, आप अपना 4-गेट विड्रॉल क्लीयरेंस स्टेटस देखने के लिए 'Track Clearance Token' पर क्लिक कर सकते हैं।"
            elif language == "hi-Latn":
                tr_ans = f"{student_name}, aap apna 4-gate clearance progress check karne ke liye 'Track Clearance Token' par click kar sakte hain."
            else:
                tr_ans = f"{student_name}, you can monitor your multi-desk clearance progress and token status by clicking 'Track Clearance Token' below."
            return {
                "answer": tr_ans,
                "domain": "Navigation",
                "citations": [],
                "recommended_action": "Track Clearance Token",
                "action_url": "/tracking",
                "voice_speech_text": tr_ans,
                "screen_instruction": None,
                "highlight_target": "Track Clearance Token",
                "engine": "UniAssist Policy Engine",
            }

        # Expand bilingual keywords (Hindi/Hinglish to English) so SQLite FTS5 matches English documents
        expanded_query = cls._expand_multilingual_query(query)
        policies = cls.search_policies(expanded_query, limit=3)
        if not policies and expanded_query != query:
            policies = cls.search_policies(query, limit=3)

        # =========================================================================
        # 0. Domain Boundary Guardrail (Math, Coding, Sports, Off-Topic Queries)
        # =========================================================================
        is_math = bool(re.search(r'\b\d+\s*[\+\-\*\/]\s*\d+\b', q_lower)) or any(w in q_lower for w in [
            "whats 2+2", "what is 2+2", "2+2", "2 + 2", "math question", "solve this equation",
            "calculate ", "multiplication table", "square root"
        ])
        is_coding = any(w in q_lower for w in [
            "python code", "code in python", "code for addition", "arithmatic operators", "arithmetic operators",
            "write a function", "write a code", "write code", "javascript code", "java code", "c++ code",
            "html code", "css code", "sql query to", "for loop in", "while loop in"
        ])
        is_trivia = any(w in q_lower for w in [
            "world cup", "football match", "cricket match", "who won the", "who is the prime minister",
            "who is the president", "tell me a joke", "tell me a story", "sing a song",
            "what is the weather", "recipe for", "capital of france"
        ])
        if is_math or is_coding or is_trivia:
            if language == "hi-IN":
                refusal_msg = (
                    f"{student_name}, मैं UniAssist विश्वविद्यालय कियोस्क परामर्शदाता (Counselor) हूँ। "
                    "मैं केवल विश्वविद्यालय अकादमिक नीतियों, उपस्थिति, फीस, परीक्षाओं, आधिकारिक फॉर्म और कैंपस प्रक्रियाओं में सहायता कर सकता हूँ। "
                    "विश्वविद्यालय से संबंधित किसी भी नियम या फॉर्म के बारे में बेझिझक पूछें।"
                )
            elif language == "hi-Latn":
                refusal_msg = (
                    f"{student_name}, main UniAssist Campus Counselor hoon. "
                    "Main keval university academic policies, attendance, fees, examinations, official forms, aur campus procedures me help kar sakta hoon. "
                    "University se related queries ke baare me poochiye."
                )
            else:
                refusal_msg = (
                    f"{student_name}, I am the UniAssist University Kiosk Counselor. "
                    "I am strictly dedicated to assisting you with university academic policies, attendance rules, fee clearances, examinations, and official student forms. "
                    "Please let me know how I can assist you with your campus and university queries today."
                )

            return {
                "answer": refusal_msg,
                "domain": "Domain Boundary Guard",
                "citations": [],
                "recommended_action": None,
                "action_url": None,
                "voice_speech_text": refusal_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # =========================================================================
        # 0A. Multi-Turn Affirmative Follow-Up ("mujhe chahiye", "yes", "proceed", "haan")
        # =========================================================================
        is_short_affirmative = (
            q_lower in ("mujhe chahiye", "mujhe chahiye.", "mujhe chaahiye", "mujhe chaahiye.", "haan", "yes", "ha", "sure", "ok", "okay", "proceed", "kardo", "please help", "batao", "bataiye", "aur batao", "haan ji", "yes please")
            or (len(q_lower.split()) <= 4 and any(w in q_lower for w in ["chahiye", "chaahiye", "haan", "kardo", "batao", "bataiye"]) and not any(neg in q_lower for neg in ["nahi", "no", "not", "cancel"]))
        )
        if is_short_affirmative and history:
            last_assistant_turn = ""
            for h in reversed(history):
                role = str(h.get("role", "")).lower()
                if role in ("assistant", "model", "bot", "counselor"):
                    last_assistant_turn = str(h.get("content") or h.get("text") or "").lower()
                    break

            if "ac-04" in last_assistant_turn or "condonation" in last_assistant_turn or "attendance" in last_assistant_turn:
                matching_clause = next((p for p in DEFAULT_POLICIES if p["doc_id"] == "PROC-FORM-CONDONATION"), DEFAULT_POLICIES[0])
                if language == "hi-IN":
                    ans = (
                        f"{student_name}, फॉर्म AC-04 (अटेंडेंस कंडोनेशन एप्लीकेशन) भरने के मुख्य चरण ये हैं: "
                        "1. जिन विषयों में आपकी अटेंडेंस 60% से 74.9% के बीच है, उनके कोर्स कोड भरें। "
                        "2. अस्पताल का वास्तविक मेडिकल सर्टिफिकेट या विश्वविद्यालय आधिकारिक ड्यूटी पत्र संलग्न करें। "
                        "3. परीक्षा शुरू होने से कम से कम 10 कार्यदिवस पहले डीन एकेडमिक्स (कमरा 201) को जमा करें। "
                        "स्वीकृति मिलने के 48 घंटे में आपका एडमिट कार्ड अनब्लॉक हो जाएगा।"
                    )
                elif language == "hi-Latn":
                    ans = (
                        f"{student_name}, Form AC-04 (Attendance Condonation Application) submit karne ke steps: "
                        "1. Jin courses me attendance 60% se 74.9% hai, unke subject codes mention karein. "
                        "2. Authentic medical prescription / OPD slip ya official university duty letter attach karein. "
                        "3. Exam start hone se at least 10 working days pehle Dean Academic Affairs (Room 201) ko submit karein. "
                        "Approval ke 48 hours me aapka exam admit card unblock ho jayega."
                    )
                else:
                    ans = (
                        f"{student_name}, here are the step-by-step submission instructions for Form AC-04: "
                        "1. List all registered course codes where your attendance is between 60% and 74.9%. "
                        "2. Attach authentic medical OPD slips / certificates or verified university duty letters. "
                        "3. Submit the completed file to the Dean of Academic Affairs (Room 201) at least 10 working days before exam commencement. "
                        "Upon Dean approval, your admit card will be unblocked within 48 hours."
                    )
                return {
                    "answer": ans,
                    "domain": "Academics",
                    "citations": [matching_clause],
                    "recommended_action": "Download Form AC-04 (Condonation)",
                    "action_url": "/forms",
                    "voice_speech_text": ans,
                    "screen_instruction": None,
                    "highlight_target": None,
                    "engine": "UniAssist Policy Engine",
                }
            elif "ex-02" in last_assistant_turn or "backpaper" in last_assistant_turn or "supplementary" in last_assistant_turn:
                matching_clause = next((p for p in DEFAULT_POLICIES if p["clause_code"] == "ORD-EXAM-12.1"), DEFAULT_POLICIES[4])
                if language == "hi-IN":
                    ans = (
                        f"{student_name}, बैकपेपर परीक्षा के लिए Form EX-02 भरने के चरण: "
                        "1. रिजल्ट घोषित होने के 14 दिनों के भीतर प्रति विषय ₹1,500 परीक्षा शुल्क का भुगतान करें। "
                        "2. फॉर्म EX-02 में अपने बैकपेपर विषयों के कोड और शीर्षक स्पष्ट रूप से दर्ज करें। "
                        "3. शुल्क रसीद के साथ फॉर्म परीक्षा सेल (ब्लॉक 3, कमरा 110) में जमा करें।"
                    )
                elif language == "hi-Latn":
                    ans = (
                        f"{student_name}, Supplementary Backpaper ke liye Form EX-02 submit karne ke steps: "
                        "1. Grade sheet aane ke 14 calendar days ke andar INR 1,500 per subject examination fee pay karein. "
                        "2. Form EX-02 me failed course codes fill karein. "
                        "3. Fee receipt ke saath Examination Cell (Block 3, Room 110) me submit karein."
                    )
                else:
                    ans = (
                        f"{student_name}, to apply for supplementary backpapers using Form EX-02: "
                        "1. Fill failed subject codes within 14 calendar days of grade sheet publication. "
                        "2. Pay examination fee of INR 1,500 per registered subject. "
                        "3. Submit the application along with challan receipt to the Examination Cell (Block 3, Room 110)."
                    )
                return {
                    "answer": ans,
                    "domain": "Examinations",
                    "citations": [matching_clause],
                    "recommended_action": "Download Form EX-02 (Backpaper)",
                    "action_url": "/forms",
                    "voice_speech_text": ans,
                    "screen_instruction": None,
                    "highlight_target": None,
                    "engine": "UniAssist Policy Engine",
                }

        # =========================================================================
        # 0A-2. Kiosk-First "Where to Get / How to Download" Retrieval Engine
        # =========================================================================
        is_where_to_get_query = any(wg in q_lower for wg in [
            "कहाँ से लूँगा", "कहाँ से मिलेगा", "यहाँ कहाँ से मिलेगा", "कहाँ मिलेगा", "कहाँ से प्राप्त",
            "kahan se milega", "kahan se lu", "kahan se luga", "yahan kahan se milega", "kahan milega",
            "download kaise", "download kahan", "where to get", "where do i get", "how do i get",
            "where can i get", "where can i find", "where to download", "how to download",
            "how can i get this", "where is the form", "how do i obtain", "wo kahan se", "woh kahan se"
        ])

        if is_where_to_get_query:
            # 1. First, check if current query names a specific procedure/form
            target_proc = get_procedure_by_keyword(query)

            # 2. If not specified in current turn (e.g. "अरे मतलब वो कहाँ से लूँगा यहाँ कहाँ से मिलेगा?"), resolve from history
            if not target_proc and history:
                combined_history_text = " ".join([
                    str(h.get("content") or h.get("text") or "").lower()
                    for h in reversed(history[-4:])
                ])
                target_proc = get_procedure_by_keyword(combined_history_text)

            # 3. Default to attendance condonation if coming from attendance context, or general catalog
            if not target_proc:
                target_proc = MASTER_PROCEDURES["attendance_condonation"]

            # Generate precise Kiosk-First guidance: Direct button access, verified real submission room, zero wandering
            if language == "hi-IN":
                kiosk_ans = (
                    f"{student_name}, आपको {target_proc['hindi_name']} के लिए कॉलेज में कहीं भी भटकने की ज़रूरत नहीं है! "
                    f"आप इसी UniAssist कियोस्क स्क्रीन पर नीचे दिए गए '{target_proc['action_label']}' बटन पर क्लिक करके इसे तुरंत यहीं से डाउनलोड कर सकते हैं। "
                    f"फॉर्म में विवरण भरने और आवश्यक दस्तावेज़ संलग्न करने के बाद, इसे {target_proc['submission_office']} में जमा करें।"
                )
                k_speech = (
                    f"{student_name}, आपको कहीं भटकने की ज़रूरत नहीं है। "
                    f"इसी स्क्रीन पर '{target_proc['action_label']}' बटन पर क्लिक करके इसे तुरंत डाउनलोड करें, "
                    f"और भरकर {target_proc['submission_office']} में जमा करें।"
                )
            elif language == "hi-Latn":
                kiosk_ans = (
                    f"{student_name}, aapko {target_proc['official_name']} ke liye college me kahin bhatakne ki zaroorat nahi hai! "
                    f"Aap isi UniAssist screen par niche diye gaye '{target_proc['action_label']}' button par click karke ise turant yahin se download kar sakte hain. "
                    f"Form fill karke aur required documents attach karke ise {target_proc['submission_office']} me submit karein."
                )
                k_speech = (
                    f"{student_name}, aapko kahin bhatakne ki zaroorat nahi hai. "
                    f"Isi screen par '{target_proc['action_label']}' button par click karke form download karein aur {target_proc['submission_office']} me submit karein."
                )
            else:
                kiosk_ans = (
                    f"{student_name}, you do not need to wander anywhere across campus for this form! "
                    f"You can download {target_proc['official_name']} directly right here on this UniAssist screen by clicking the '{target_proc['action_label']}' button below. "
                    f"After filling it out and attaching required paperwork, submit it to {target_proc['submission_office']}."
                )
                k_speech = (
                    f"{student_name}, you do not need to wander around campus. "
                    f"Click the '{target_proc['action_label']}' button right on this screen to download it immediately, "
                    f"then submit to {target_proc['submission_office']}."
                )

            clean_citation = {
                "doc_id": target_proc["form_code"],
                "category": target_proc["category"],
                "title": target_proc["official_name"],
                "clause_code": target_proc["form_code"],
                "content": f"Official verified procedure for {target_proc['official_name']}. Direct 1-click download via UniAssist Kiosk.",
                "action_url": target_proc["action_url"],
                "action_label": target_proc["action_label"],
            }

            return {
                "answer": kiosk_ans,
                "domain": target_proc["category"],
                "citations": [clean_citation],
                "recommended_action": target_proc["action_label"],
                "action_url": target_proc["action_url"],
                "voice_speech_text": k_speech,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # =========================================================================
        # 0B. Faculty & Staff Resignation / Employment Relieving Protocol
        # =========================================================================
        is_faculty_exit = (
            any(f_kw in q_lower for f_kw in ["faculty", "professor", "teacher", "employee", "staff", "शिक्षक", "फैकल्टी"])
            and any(ex_kw in q_lower for ex_kw in ["job chhod", "resign", "resignation", "leaving job", "quit", "quitting", "relieving", "istifa", "इस्तीफा", "नौकरी छोड़ना", "छोड़नी है"])
        ) or any(pure_exit in q_lower for pure_exit in [
            "faculty resignation", "professor resignation", "faculty job exit", "teacher resignation", "job chhodani hai", "naukri chhodani"
        ])
        if is_faculty_exit:
            faculty_clause = next((p for p in DEFAULT_POLICIES if p["doc_id"] == "ORD-HR-FACULTY-EXIT"), DEFAULT_POLICIES[0])
            if language == "hi-IN":
                faculty_ans = (
                    "फैकल्टी एवं स्टाफ सदस्यों के लिए सेवा मुक्ति (Resignation) और नो-ड्यूज प्रक्रिया विश्वविद्यालय के आधिकारिक नियमों के तहत संचालित होती है:\n"
                    "1. अपने विभागाध्यक्ष (HOD) एवं संकाय डीन को औपचारिक त्यागपत्र (Resignation Notice) प्रस्तुत करें।\n"
                    "2. नोटिस स्वीकृति के बाद 4 अनिवार्य विभागों से नो-ड्यूज क्लियरेंस पूर्ण करें: (क) विभाग HOD (कोर्स फाइलें, प्रयोगशाला उपकरण एवं आंतरिक मूल्यांकन अंक हैंडओवर), "
                    "(ख) केंद्रीय पुस्तकालय (समस्त पुस्तकें एवं जर्नल वापसी), (ग) सेंट्रल स्टोर एवं आईटी (लैपटॉप, प्रिंटर एसेट एवं बायोमेट्रिक एक्सेस हैंडओवर), तथा (घ) वित्त एवं लेखा (वेतन समाधान एवं पीएफ ट्रांसफर)।\n"
                    "3. पूर्ण क्लियरेंस डोजियर प्रशासनिक ब्लॉक स्थित HR डेस्क (कमरा 103) में जमा करें। अनुभव प्रमाण पत्र एवं रिलीविंग लेटर का SLA 15 कार्यदिवस है।"
                )
                f_speech = "फैकल्टी रेजिग्नेशन के लिए अपने HOD को नोटिस दें और 4 काउंटरों (HOD, लाइब्रेरी, आईटी स्टोर, एवं एकाउंट्स) से नो-ड्यूज करवाकर HR डेस्क कमरा 103 में जमा करें। रिलीविंग लेटर 15 दिनों में जारी होता है।"
            elif language == "hi-Latn":
                faculty_ans = (
                    "Faculty aur Staff resignation process University ke verified rules ke mutabiq chalta hai:\n"
                    "1. Apne HOD aur Dean of Faculty ko formal resignation notice submit karein.\n"
                    "2. Notice acceptance ke baad 4 counters se No-Dues clearance complete karein: "
                    "(a) Department HOD (course files, lab equipment aur internal marks handover), "
                    "(b) Central Library (book returns), "
                    "(c) Stores & IT (laptop, printer assets aur biometric access handover), aur "
                    "(d) Finance & Accounts (salary reconciliation aur PF transfer).\n"
                    "3. Completed clearance file HR Administration Desk (Room 103, Administrative Block) me submit karein. "
                    "Experience certificate aur Relieving letter ka SLA 15 working days hai."
                )
                f_speech = "Faculty resignation ke liye apne HOD ko notice dein aur Department, Library, IT Stores aur Finance se No-Dues clear karwake HR Desk Room 103 me submit karein."
            else:
                faculty_ans = (
                    "Faculty and academic staff resignation procedure is governed under official university regulations:\n"
                    "1. Submit a formal written resignation notice to your Head of Department (HOD) and Dean of Faculty.\n"
                    "2. Upon acceptance, complete the Faculty No-Dues Clearance across 4 desks: "
                    "(a) Department HOD (handover of course dossiers, lab custody, and continuous evaluation records), "
                    "(b) Central Library (return of all accessioned library books), "
                    "(c) Stores & IT (handover of university laptop, printer assets, and biometric deactivation), and "
                    "(d) Finance & Accounts (final salary audit and provident fund reconciliation).\n"
                    "3. Submit the completed clearance dossier to HR Administration Desk (Room 103, Administrative Block). "
                    "Official relieving letter and experience certificate turnaround SLA is 15 working days."
                )
                f_speech = "For faculty resignation, submit notice to your HOD, complete 4-desk No-Dues clearance across Department, Library, IT Stores, and Finance, then submit to HR Desk Room 103."

            return {
                "answer": faculty_ans,
                "domain": "HR & Faculty",
                "citations": [faculty_clause],
                "recommended_action": "Download Faculty Exit Format",
                "action_url": "/forms",
                "voice_speech_text": f_speech,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # =========================================================================
        # 0C. Vague Form Clarification ("mujhe form bharna hai", "help with form")
        # =========================================================================
        is_generic_form_request = (
            any(gf in q_lower for gf in [
                "mujhe form bharna", "form bharana hai", "form bharna hai", "form bharna chahta",
                "form kaise bhare", "form bharne me madad", "form bharne mein madad", "form chahiye",
                "i want to fill a form", "help me fill a form", "how to fill form", "want to fill form",
                "need to fill a form", "need to fill out a form", "fill out a form", "fill a form",
                "fill the form", "help with form", "help with a form", "which form to",
                "फॉर्म भरना है", "फॉर्म भरना", "फॉर्म भरने में मदद", "फॉर्म चाहिए", "फॉर्म भरना चाहता"
            ]) and not any(spec in q_lower for spec in [
                "backpaper", "supplementary", "ex-02", "ac-04", "condonation", "migration", "degree",
                "rechecking", "leave", "id card", "tada", "conveyance", "imprest", "purchase", "stationery",
                "hostel", "clearance", "withdrawal", "विड्रॉल", "कंडोनेशन", "माइग्रेशन"
            ])
        )
        if is_generic_form_request:
            if language == "hi-IN":
                clarify_msg = (
                    f"{student_name}, UniAssist पोर्टल पर सभी 31 आधिकारिक विश्वविद्यालय फॉर्म उपलब्ध हैं। "
                    "कृपया बताइए कि आपको किस कार्य के लिए फॉर्म भरना है? उदाहरण के लिए:\n"
                    "1. बैकपेपर परीक्षा (Form EX-02)\n"
                    "2. उपस्थिति छूट / Condonation (Form AC-04)\n"
                    "3. माइग्रेशन या प्रोविजनल डिग्री प्रमाणपत्र (Form 15 & 22)\n"
                    "4. एडमिशन विड्रॉल एवं फीस रिफंड (Form WTH)\n"
                    "5. फैकल्टी एवं स्टाफ लीव / आईडी कार्ड (Form 23 & 24)\n\n"
                    "आप इनमें से किस फॉर्म के बारे में जानकारी चाहते हैं?"
                )
                v_msg = f"{student_name}, हमारे पोर्टल पर 31 फॉर्म उपलब्ध हैं। क्या आपको बैकपेपर Form EX-02, अटेंडेंस Form AC-04, माइग्रेशन, या विड्रॉल का फॉर्म भरना है?"
            elif language == "hi-Latn":
                clarify_msg = (
                    f"{student_name}, UniAssist portal par sabhi 31 official university forms available hain. "
                    "Kya aap bata sakte hain ki aapko kis kaam ke liye form bharna hai? Jaise ki:\n"
                    "1. Supplementary Backpaper Exam (Form EX-02)\n"
                    "2. Attendance Shortage Condonation (Form AC-04)\n"
                    "3. Migration ya Degree Application (Form 15 & 22)\n"
                    "4. Admission Withdrawal & Refund (Form WTH)\n"
                    "5. Faculty Leave / Staff Forms (Form 23 & 24)\n\n"
                    "Aapko kaunsa form bharna hai?"
                )
                v_msg = f"{student_name}, UniAssist par 31 forms available hain. Aapko Backpaper Form EX-02, Attendance Form AC-04, Migration, ya Withdrawal me se kaunsa form bharna hai?"
            else:
                clarify_msg = (
                    f"{student_name}, UniAssist provides download and submission workflows for all 31 official university forms. "
                    "Could you please specify which process you need a form for? For example:\n"
                    "1. Supplementary Backpaper Exams (Form EX-02)\n"
                    "2. Attendance Shortage Condonation (Form AC-04)\n"
                    "3. Migration or Degree Certificate (Form 15 & 22)\n"
                    "4. Program Withdrawal & Fee Refund (Form WTH)\n"
                    "5. Faculty Leave or Staff Applications (Form 23 & 24)\n\n"
                    "Which form would you like guidance on?"
                )
                v_msg = f"{student_name}, UniAssist hosts 31 university forms. Please specify if you need Backpaper Form EX-02, Attendance Form AC-04, Migration, or Withdrawal."

            top_sample_policies = [p for p in DEFAULT_POLICIES if p["doc_id"] in ("POL-EXAM-01", "PROC-FORM-CONDONATION", "PROC-FORM-MIGRATION")]
            return {
                "answer": clarify_msg,
                "domain": "Forms Navigation",
                "citations": top_sample_policies,
                "recommended_action": "Browse All 31 Forms",
                "action_url": "/forms",
                "voice_speech_text": v_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # =========================================================================
        # 1. Broad Navigation: "Where can you take me?" / "What portals are available?"
        # =========================================================================
        is_broad_nav = any(w in q_lower for w in [
            "where can you take me", "what can you take me", "where can you navigate", "which pages", "available portals",
            "कहाँ ले जा सकते", "कहाँ जा सकते", "पोर्टल", "नेविगेट", "सुविधाएं", "विकल्प", "क्या कर सकते"
        ])
        if is_broad_nav:
            if language == "hi-IN":
                nav_answer = (
                    f"{student_name}, मैं आपको 5 प्रमुख कैंपस पोर्टलों पर ले जा सकता हूँ:\n"
                    "1. फॉर्म और आवेदन कैटलॉग (/forms) - सभी 31 विश्वविद्यालय फॉर्म डाउनलोड और प्रक्रिया।\n"
                    "2. विड्रॉल और क्लियरेंस पोर्टल (/withdrawal) - 4-गेट डिजिटल क्लियरेंस, यूजीसी रिफंड स्लैब और कॉशन डिपॉजिट ट्रैकिंग।\n"
                    "3. परीक्षा और बैकपेपर पोर्टल (/exams) - बैकपेपर पंजीकरण, पुनर्मूल्यांकन और एडमिट कार्ड।\n"
                    "4. छात्र शिकायत निवारण पटल (/chat) - 48 घंटे के समाधान वादे के साथ औपचारिक शिकायत।\n"
                    "5. छात्रवृत्ति सहायता (/scholarship) - मेरिट नवीनीकरण और शुल्क रियायत।\n\n"
                    "आप कहाँ जाना चाहते हैं?"
                )
                voice_text = f"{student_name}, मैं आपको फॉर्म कैटलॉग, विड्रॉल पोर्टल, परीक्षा, शिकायत या स्कॉलरशिप पोर्टल पर ले जा सकता हूँ। आप कहाँ जाना चाहते हैं?"
            elif language == "hi-Latn":
                nav_answer = (
                    f"{student_name}, main aapko 5 primary campus destinations par guide kar sakta hoon: "
                    "1. Forms Catalog (/forms), 2. Program Withdrawal & Clearance (/withdrawal), "
                    "3. Exams (/exams), 4. Grievance Desk (/chat), aur 5. Scholarships (/scholarship). "
                    "Aap kahan jana chahte hain?"
                )
                voice_text = f"{student_name}, main aapko Forms Catalog, Withdrawal Cockpit, Exams, ya Grievance Desk par guide kar sakta hoon. Kahan jana chahte hain?"
            else:
                nav_answer = (
                    f"{student_name}, I can guide and navigate you directly to 5 primary campus destinations:\n"
                    "1. Forms & Applications Catalog (/forms) - View, download, and follow submission procedures for all 31 university forms.\n"
                    "2. Program Withdrawal & Clearance Cockpit (/withdrawal) - 4-gate digital clearance, UGC refund slabs, and caution deposit tracking.\n"
                    "3. Examination & Rechecking Schedule (/exams) - Backpaper registration, grade re-evaluation, and admit cards.\n"
                    "4. Student Grievance Redressal Desk (/chat) - Formal ticket submission with 48h resolution SLA.\n"
                    "5. Scholarships & Financial Aid (/scholarship) - Merit renewals and fee concessions.\n\n"
                    "Where would you like to go?"
                )
                voice_text = (
                    f"{student_name}, I can navigate you to the Forms Catalog, Program Withdrawal Cockpit, "
                    "Examination Portal, Grievance Redressal Desk, or Scholarships. Just tell me where you'd like to go."
                )

            return {
                "answer": nav_answer,
                "domain": "University Portals",
                "citations": [],
                "recommended_action": "Browse Forms & Portals",
                "action_url": "/forms",
                "voice_speech_text": voice_text,
            }

        # =========================================================================
        # 2. Specific Navigation Request: "Take me to [portal]"
        # =========================================================================
        is_specific_nav = any(w in q_lower for w in [
            "take me to", "navigate to", "open the", "go to the", "show me the",
            "ले चलो", "खोलो", "दिखाओ", "जाना है", "ओपन करो"
        ])
        if is_specific_nav:
            if any(w in q_lower for w in ["withdrawal", "clearance", "refund", "exit", "विड्रॉल", "क्लियरेंस", "रिफंड"]):
                if language == "hi-IN":
                    ans = f"{student_name}, विड्रॉल और क्लियरेंस पोर्टल खोला जा रहा है। यहाँ आप अपने सभी 4 डिजिटल गेट्स और ₹10,000 की कॉशन डिपॉजिट वापसी को ट्रैक कर सकते हैं।"
                    sp = "विड्रॉल और क्लियरेंस पोर्टल पर ले जाया जा रहा है।"
                else:
                    ans = f"{student_name}, opening the Program Withdrawal & Clearance Cockpit. You can track all 4 digital gates and your 100% refundable caution deposit here."
                    sp = "Navigating to the Program Withdrawal and Clearance portal now."
                return {
                    "answer": ans,
                    "domain": "Withdrawal Navigation",
                    "citations": [],
                    "recommended_action": "Open Withdrawal Portal",
                    "action_url": "/withdrawal",
                    "voice_speech_text": sp,
                }
            elif any(w in q_lower for w in ["form", "catalog", "document", "फॉर्म", "दस्तावेज़", "आवेदन"]):
                if language == "hi-IN":
                    ans = f"{student_name}, विश्वविद्यालय फॉर्म कैटलॉग खोला जा रहा है। यहाँ आप सभी 31 फॉर्म डाउनलोड कर सकते हैं।"
                    sp = "विश्वविद्यालय फॉर्म कैटलॉग पर ले जाया जा रहा है।"
                else:
                    ans = f"{student_name}, opening the University Forms & Applications Catalog. You can find and download all 31 academic, financial, examination, and logistics forms here."
                    sp = "Navigating to the University Forms Catalog now."
                return {
                    "answer": ans,
                    "domain": "Forms Navigation",
                    "citations": [],
                    "recommended_action": "Open Forms Catalog",
                    "action_url": "/forms",
                    "voice_speech_text": sp,
                }
            elif any(w in q_lower for w in ["exam", "recheck", "backpaper", "परीक्षा", "बैकपेपर", "पुनर्मूल्यांकन"]):
                if language == "hi-IN":
                    ans = f"{student_name}, परीक्षा और पुनर्मूल्यांकन पोर्टल खोला जा रहा है। आप यहाँ अपनी परीक्षा पात्रता, बैकपेपर और एडमिट कार्ड देख सकते हैं।"
                    sp = "परीक्षा और पुनर्मूल्यांकन पोर्टल पर ले जाया जा रहा है।"
                else:
                    ans = f"{student_name}, opening the Examination & Rechecking Portal. You can verify your exam eligibility, apply for re-evaluation, or download Form EX-02."
                    sp = "Navigating to the Examination Portal now."
                return {
                    "answer": ans,
                    "domain": "Exams Navigation",
                    "citations": [],
                    "recommended_action": "Open Examination Portal",
                    "action_url": "/exams",
                    "voice_speech_text": sp,
                }
            elif any(w in q_lower for w in ["grievance", "complaint", "ticket", "शिकायत"]):
                if language == "hi-IN":
                    ans = f"{student_name}, छात्र शिकायत निवारण पटल खोला जा रहा है। यहाँ 48 घंटे के अनिवार्य समाधान के साथ टिकट दर्ज कर सकते हैं।"
                    sp = "छात्र शिकायत निवारण पटल पर ले जाया जा रहा है।"
                else:
                    ans = f"{student_name}, opening the Student Grievance Redressal Desk. Academic and facility tickets carry a mandatory 48-hour resolution SLA."
                    sp = "Navigating to the Student Grievance Redressal Desk now."
                return {
                    "answer": ans,
                    "domain": "Grievance Navigation",
                    "citations": [],
                    "recommended_action": "Open Grievance Desk",
                    "action_url": "/chat",
                    "voice_speech_text": sp,
                }
            elif any(w in q_lower for w in ["scholarship", "स्कॉलरशिप", "छात्रवृत्ति"]):
                if language == "hi-IN":
                    ans = f"{student_name}, छात्रवृत्ति और वित्तीय सहायता पोर्टल खोला जा रहा है। आप मेरिट नवीनीकरण और शुल्क रियायत की जानकारी देख सकते हैं।"
                    sp = "छात्रवृत्ति और वित्तीय सहायता पोर्टल पर ले जाया जा रहा है।"
                else:
                    ans = f"{student_name}, opening the Scholarships & Financial Aid Portal. You can review merit renewal criteria (CGPA 8.0+) and tuition concessions."
                    sp = "Navigating to Scholarships and Financial Aid now."
                return {
                    "answer": ans,
                    "domain": "Scholarship Navigation",
                    "citations": [],
                    "recommended_action": "Open Scholarships",
                    "action_url": "/scholarship",
                    "voice_speech_text": sp,
                }

        # =========================================================================
        # 3. Ambient Screen Navigation & Situational Counselor: "What page are we on & what next?"
        # =========================================================================
        is_form_inquiry = any(w in q_lower for w in [
            "after getting", "after downloading", "after taking", "migration", "certificate", "rechecking", "फॉर्म के बाद"
        ])
        is_ambient_navigation = not is_form_inquiry and (
            any(w in q_lower for w in [
                "what to click", "which button", "which option", "how do i proceed", "where to click",
                "what should i do here", "what should i do next", "what do i do next", "what to do next",
                "what page are we on", "what page is this", "which page is this", "which screen is this",
                "what screen are we on", "where am i", "where are we", "what next", "what is next",
                "what should i do", "how to proceed", "next step", "what to do now", "tell me what to do",
                "where do we go", "what can i do here",
                "which page i am on", "which page am i on", "what page i am on", "what page am i on",
                "which page are we on", "what screen i am on", "what screen am i on", "which screen i am on",
                "what page is open", "which page is open", "current page", "current screen",
                "where am i right now", "tell me which page", "tell me what page",
                "क्या क्लिक करें", "कहाँ क्लिक", "हम किस पेज पर हैं", "यह कौन सा पेज है", "किस स्क्रीन पर हैं",
                "आगे क्या करना चाहिए", "अगला कदम", "अब क्या करें", "मुझे क्या करना चाहिए", "आगे क्या करूँ",
                "यहाँ क्या करें", "मैं किस पेज पर हूँ", "हम किस स्क्रीन पर हैं", "यह कौन सी स्क्रीन है",
                "मैं कहाँ हूँ", "हम कहाँ हैं", "यह कौन सा पेज", "कौन सा पेज",
                "main kis page par hoon", "hum kis page par hain", "ye kaun sa page hai", "yeh kaun sa page hai",
                "kaun sa page hai", "konsa page hai", "kahan par hain", "main kahan hoon", "hum kahan hain"
            ])
            or (
                ("page" in q_lower or "screen" in q_lower or "पेज" in q_lower or "स्क्रीन" in q_lower)
                and any(w in q_lower for w in ["what", "which", "where", "tell", "current", "this", "kaun", "konsa", "kahan", "kis"])
            )
        )

        if is_ambient_navigation:
            effective_context = page_context or {
                "screen_name": "Student Services Kiosk Dashboard",
                "route": "/dashboard",
                "primary_action": "Explore Services Catalog",
                "available_actions": ["Explore Services Catalog", "Check Active Request Status", "Ask Digital Counselor"],
            }
            scr_name = effective_context.get("screen_name") or "the current screen"
            primary_act = effective_context.get("primary_action")
            available = effective_context.get("available_actions") or []
            actions_str = ", ".join([f"'{a}'" for a in available[:3]])
            student_name = (student or {}).get("name", "Student").split()[0]
            student_attendance = (student or {}).get("attendance", "N/A")
            student_fee = (student or {}).get("fee_status", "N/A")

            # Try generating dynamic, intelligent counselor advice via Ollama
            ai_counselor_reply = None
            ai_engine_name = "SQLite FTS5 (Local Offline)"
            try:
                from .local_llm_service import call_ollama_llama3
                lang_rule = "Respond strictly in pure, natural Devanagari Hindi (हिन्दी)." if language == "hi-IN" else "Respond in warm, spoken English."
                sys_inst = (
                    "You are UniAssist, an empathetic digital campus counselor at a university kiosk.\n"
                    f"{lang_rule}\n"
                    "When asked about the current page, location, or next steps:\n"
                    f"1. Clearly state that the student is currently on '{scr_name}' (Route: {effective_context.get('route', '/')}) and explain its primary purpose.\n"
                    "2. Recommend the specific next action they should take based on the available actions.\n"
                    "3. Speak warmly and empathetically in 2 to 3 concise spoken sentences without markdown asterisks (**).\n"
                    "4. End with a helpful offer to assist with that step.\n"
                    "5. Never guess or claim they are on any screen other than the specified ACTIVE PAGE."
                )
                user_msg = (
                    f"STUDENT: {student_name} (Attendance: {student_attendance}%, Fee Status: {student_fee})\n"
                    f"ACTIVE PAGE: {scr_name} (URL: {effective_context.get('route', '/')})\n"
                    f"PRIMARY RECOMMENDED ACTION: {primary_act or 'Explore Options'}\n"
                    f"AVAILABLE ACTIONS ON THIS PAGE: {actions_str}\n"
                    f"STUDENT QUERY: {query}"
                )
                ollama_out = call_ollama_llama3(user_msg, sys_inst, history=history)
                if ollama_out and len(ollama_out.strip()) > 20:
                    ai_counselor_reply = ollama_out.strip()
                    ai_engine_name = "Ollama Local AI (Llama 3.2)"
            except Exception:
                pass

            if ai_counselor_reply:
                nav_answer = ai_counselor_reply
                v_speech = ai_counselor_reply
            elif language == "hi-IN":
                nav_answer = (
                    f"{student_name}, हम वर्तमान में {scr_name} पर हैं। "
                    f"यहाँ से आगे बढ़ने के लिए आपका सबसे अच्छा अगला कदम '{primary_act or (available[0] if available else 'Explore')}' का चयन करना है। "
                    f"इसके अलावा आप {actions_str} भी कर सकते हैं। मैंने अनुशंसित विकल्प को स्क्रीन पर हाइलाइट कर दिया है।"
                )
                v_speech = f"हम {scr_name} पर हैं। आगे बढ़ने के लिए '{primary_act or 'हाइलाइट किए गए बटन'}' पर क्लिक करें।"
            elif language == "hi-Latn":
                nav_answer = (
                    f"{student_name}, hum abhi {scr_name} par hain. "
                    f"Aage badhne ke liye best step '{primary_act or (available[0] if available else 'Explore')}' select karna hai. "
                    f"Aap {actions_str} bhi choose kar sakte hain. Maine recommended action highlight kar diya hai."
                )
                v_speech = f"Hum {scr_name} par hain. Proceed karne ke liye '{primary_act or 'highlighted button'}' par click karein."
            else:
                nav_answer = (
                    f"{student_name}, we are currently on the {scr_name}. "
                    f"Your best next step here is to select '{primary_act or (available[0] if available else 'Explore')}'. "
                    f"You can also choose from {actions_str}. I have highlighted the recommended action on your screen."
                )
                v_speech = f"We are on the {scr_name}. To proceed, click {primary_act or 'the highlighted button'}."

            return {
                "answer": nav_answer,
                "domain": "Screen Navigation",
                "citations": [],
                "recommended_action": primary_act or (available[0] if available else "Proceed"),
                "action_url": effective_context.get("route", "/"),
                "voice_speech_text": v_speech,
                "screen_instruction": f"Click '{primary_act or 'Proceed'}' to continue.",
                "highlight_target": primary_act or (available[0] if available else None),
                "engine": ai_engine_name,
            }

        # =========================================================================
        # 4. Multi-Persona Deterministic Domain Dispatcher
        # Prioritized to eliminate keyword collisions across Hinglish, English & Hindi
        # =========================================================================

        # 4A. Student ID Card Re-issue (Duplicate ID Card)
        is_id_card_query = (
            (
                any(w in q_lower for w in ["id card", "duplicate id", "lost id", "lost my id", "identity card", "पहचान पत्र", "आईडी कार्ड"])
                or (any(w in q_lower for w in ["id", "आईडी"]) and any(w in q_lower for w in ["kho gaya", "gum", "lost", "duplicate", "naya", "bane", "banega", "kho gya", "खो", "गुम", "डुप्लिकेट", "नया"]))
            )
            and not any(w in q_lower for w in ["offset", "caution deposit", "ऑफसेट", "कट सकता", "कट सकती", "काट सकते"])
        )

        # 4B. Hostel Vacation & Security Deposit Refund
        is_hostel_vacate_query = (
            any(w in q_lower for w in [
                "hostel chhodna", "hostel vacate", "vacate hostel", "hostel leave", "leave hostel",
                "hostel room handover", "hostel security deposit", "hostel deposit wapas",
                "हॉस्टल छोड़ना", "हॉस्टल खाली", "हॉस्टल छोड़", "कमरा छोड़ना", "हॉस्टल सिक्योरिटी"
            ])
            or ("hostel" in q_lower and any(w in q_lower for w in ["chhod", "vacate", "leave", "deposit", "handover", "खाली", "छोड़", "room"]))
            or ("हॉस्टल" in q_lower and any(w in q_lower for w in ["छोड़", "खाली", "डिपॉजिट", "वापस"]))
        )

        # 4C. Answer Script Re-checking & Re-evaluation
        is_rechecking_query = any(w in q_lower for w in [
            "rechecking", "re-evaluation", "reevaluation", "re-checking", "re check", "re evaluate",
            "answer script re", "copy recheck", "marks recheck", "paper recheck", "re-eval",
            "पुनर्मूल्यांकन", "रीचेकिंग", "कॉपी रीचेक"
        ])

        # 4D. Supplementary & Backpaper Examinations
        is_backpaper_query = any(w in q_lower for w in [
            "backpaper", "back paper", "supplementary", "supple exam", "arrear", "fail ho gaya",
            "बैकपेपर", "सप्लीमेंट्री", "सप्ली", "बैक पेपर"
        ])

        # 4E. Degree Certificate & Convocation
        is_degree_query = (
            any(w in q_lower for w in [
                "degree certificate", "apply degree", "degree apply", "degree kaise", "convocation",
                "उपाधि", "डिग्री प्रमाण पत्र", "डिग्री प्रमाण", "डिग्री आवेदन", "डिग्री कैसे"
            ])
            or ("degree" in q_lower and any(w in q_lower for w in ["certificate", "convocation", "apply", "collect", "milegi", "mil sakti", "कागज", "प्रमाण"]))
        )

        # 4F. Migration Certificate
        is_migration_query = (
            any(w in q_lower for w in [
                "migration certificate", "migration apply", "migration kaise", "माइग्रेशन प्रमाण पत्र", "माइग्रेशन"
            ])
            or ("migration" in q_lower and any(w in q_lower for w in ["certificate", "form", "apply", "प्रमाण"]))
        )

        # 4G. Student Grievance & Anti-Ragging
        is_grievance_query = any(w in q_lower for w in [
            "ragging", "complaint", "harassment", "grievance", "shikayat", "proctor", "ragging complaint",
            "रैगिंग", "शिकायत", "प्रताड़ना", "धमकी"
        ])

        # 4H. Merit & Need Scholarships
        is_scholarship_query = any(w in q_lower for w in [
            "scholarship", "merit scholarship", "scholarship renewal", "fee concession", "fee waiver",
            "financial aid", "स्कॉलरशिप", "छात्रवृत्ति", "मेरिट स्कॉलरशिप", "फीस छूट"
        ])

        # 4I. Smart Caution Deposit Offsetting
        is_offset_query = (
            any(w in q_lower for w in [
                "caution deposit", "offset", "deposit se cut", "deposit cut", "fine cut",
                "fine caution deposit", "fine cut sakti", "library fine",
                "कॉशन डिपॉजिट", "स्मार्ट ऑफसेट", "डिपॉजिट से कट", "डिपॉजिट से काट", "जुर्माना ऑफसेट"
            ])
            or ("deposit" in q_lower and any(w in q_lower for w in ["offset", "fine", "cut", "deduct", "library"]))
        )

        # 4J. Program Withdrawal & UGC Fee Refund
        is_withdrawal_query = (
            any(w in q_lower for w in [
                "withdrawal", "program withdrawal", "course withdrawal", "drop out", "cancel admission",
                "admission cancel", "fee refund", "fees refund", "tuition refund",
                "विड्रॉल", "दाखिला रद्द", "एडमिशन कैंसिल", "फीस रिफंड", "कॉलेज छोड़ना", "विश्वविद्यालय छोड़ना"
            ])
            or ("refund" in q_lower and any(w in q_lower for w in ["fee", "tuition", "admission", "fees", "फीस", "ट्यूशन"]))
        )

        # 4K. Attendance & Condonation
        is_attendance_query = any(w in q_lower for w in [
            "attendance", "condonation", "debar", "absent", "shortage",
            "अटेंडेंस", "उपस्थिति", "हाजिरी", "कंडोनेशन", "कम अटेंडेंस"
        ])

        # 4L. Post-Form Download Procedure ("After downloading...", "Where to submit...")
        is_post_form_query = any(w in q_lower for w in [
            "after getting", "after downloading", "what to do after", "what should i do after",
            "where to submit", "where do i submit", "how to submit", "what documents to attach",
            "which documents", "what to do with", "after taking", "submit this form", "submit the form",
            "next step after", "what after getting", "what do i do with this",
            "डाउनलोड करने के बाद", "फॉर्म के बाद", "कहाँ जमा", "कैसे जमा"
        ])

        # 4M. Vague Form Clarification ("mujhe form bharna hai", "form chahiye")
        is_vague_form_query = (
            any(w in q_lower for w in [
                "form bharna", "form chahiye", "mujhe form", "need a form", "want a form",
                "give me a form", "give form", "फॉर्म चाहिए", "फॉर्म भरना", "फॉर्म दें"
            ])
            and len(q_lower.split()) <= 6
        )

        if is_id_card_query:
            id_policy = next((p for p in policies if p["doc_id"] == "PROC-FORM-STUDENT-ID"), DEFAULT_POLICIES[11] if len(DEFAULT_POLICIES) > 11 else DEFAULT_POLICIES[0])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, यदि आपका छात्र पहचान पत्र (Student ID Card) खो गया है, तो आप 48 घंटे में नया बायोमेट्रिक आईडी कार्ड प्राप्त कर सकते हैं:\n\n"
                    "1. कियोस्क से छात्र आईडी कार्ड पुनः जारी फॉर्म (Form 28) डाउनलोड करके भरें।\n"
                    "2. अकाउंट्स काउंटर पर ₹200 का शुल्क जमा करें (या इसे कॉशन डिपॉजिट से स्मार्ट ऑफसेट करवाएं)।\n"
                    "3. एक पासपोर्ट साइज फोटो और पुलिस गुमशुदगी रिपोर्ट (GD/NCR) संलग्न करें।\n"
                    "4. इसे छात्र सेवा पटल (कमरा नंबर 101, प्रशासनिक भवन) में जमा करें। आपका नया कार्ड 48 घंटे में तैयार हो जाएगा।"
                )
                voice_text = f"{student_name}, डुप्लिकेट आईडी कार्ड के लिए फॉर्म 28 भरकर, ₹200 शुल्क और फोटो के साथ कमरा 101 में जमा करें। यह 48 घंटे में जारी हो जाएगा।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, agar aapka student ID card kho gaya hai toh aap 48 ghante me duplicate ID card prapt kar sakte hain:\n\n"
                    "1. Kiosk se Student ID Card Re-issue Form (Form 28) download karke fill karein.\n"
                    "2. Accounts Window par ₹200 fee submit karein ya caution deposit se direct offset karein.\n"
                    "3. 1 passport size photo aur police lost report (GD/NCR copy) attach karein.\n"
                    "4. Ise Student Section (Room 101, Administrative Block) me submit karein. 48 hours me naya smart card mil jayega."
                )
                voice_text = f"{student_name}, duplicate ID card ke liye Form 28 fill karke 200 rupees fee ke sath Room 101 me submit karein. Yeh 48 ghante me mil jayega."
            else:
                answer = (
                    f"{student_name}, if your student ID card is lost, you can obtain a duplicate biometric smart card within 48 hours:\n\n"
                    "1. Download and fill the Student ID Card Re-issue Form (Form 28) directly from this kiosk.\n"
                    "2. Settle the ₹200 re-issue fee at Accounts Window 4 (or choose 1-tap Smart Caution Deposit Offsetting).\n"
                    "3. Attach 1 passport photograph and a copy of your police lost report / NCR.\n"
                    "4. Submit the dossier to Student Services / Registrar Desk (Room 101, Administrative Block). Turnaround SLA is 48 hours."
                )
                voice_text = f"{student_name}, for a duplicate ID card, download Form 28, attach 200 Rupees fee and your photo, and submit it at Room 101. It will be ready in 48 hours."

            res = {
                "answer": answer,
                "domain": "Student ID Services",
                "citations": [id_policy],
                "recommended_action": "Download Duplicate ID Form (Form 28)",
                "action_url": "/forms",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_hostel_vacate_query:
            hostel_policy = next((p for p in policies if p["doc_id"] in ("POL-HSTL-01", "PROC-FORM-HOSTEL-CLR")), DEFAULT_POLICIES[5])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, हॉस्टल कमरा खाली करने और सिक्योरिटी डिपॉजिट वापस प्राप्त करने की आधिकारिक प्रक्रिया:\n\n"
                    "1. कियोस्क से हॉस्टल वेकेशन एवं हैंडओवर क्लीयरेंस फॉर्म डाउनलोड करें।\n"
                    "2. कमरा छोड़ने से 24 घंटे पहले सहायक वार्डन (कमरा नंबर 102, हॉस्टल ब्लॉक) के साथ भौतिक इन्वेंट्री सत्यापन कराएं।\n"
                    "3. कमरे और अलमारी की चाबियां हॉस्टल कार्यालय में जमा कराएं।\n"
                    "4. वार्डन हस्ताक्षर युक्त क्लीयरेंस पर्ची प्राप्त करें। आपकी हॉस्टल सिक्योरिटी डिपॉजिट 7 कार्य दिवसों में बैंक खाते में वापस कर दी जाएगी।"
                )
                voice_text = f"{student_name}, हॉस्टल खाली करने के लिए इन्वेंट्री जांच करवाकर चाबियां कमरा 102 में सौंपें। सिक्योरिटी डिपॉजिट 7 दिनों में वापस मिल जाएगी।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, hostel room vacate karne aur security deposit wapas lene ke liye verified steps yeh hain:\n\n"
                    "1. Kiosk se Hostel Vacation Clearance Form download karein.\n"
                    "2. Room chhodne se 24 ghante pehle Assistant Warden (Room 102) ke sath physical inventory check karayein.\n"
                    "3. Room aur almirah keys Hostel Office me hand over karein.\n"
                    "4. Warden sign-off ke baad aapki refundable security deposit 7 working days me account me aa jayegi."
                )
                voice_text = f"{student_name}, hostel vacate karne ke liye Assistant Warden Room 102 se inventory verify karwake keys handover karein. Deposit 7 din me refund hogi."
            else:
                answer = (
                    f"{student_name}, to vacate your hostel room and claim your security deposit refund under Ordinance ORD-HSTL-18.2:\n\n"
                    "1. Download the Hostel Vacation & Handover Clearance Form from this kiosk.\n"
                    "2. Complete physical inventory and room inspection with the Assistant Warden (Room 102, Hostel Block) 24 hours prior to departure.\n"
                    "3. Hand over your room and almirah keys to the Hostel Administration Desk.\n"
                    "4. Obtain the Assistant Warden's signed clearance. Your refundable security deposit will be processed within 7 working days."
                )
                voice_text = f"{student_name}, to vacate the hostel, complete an inventory check with the Warden in Room 102 and hand over your keys. Your security deposit will be refunded within 7 working days."

            res = {
                "answer": answer,
                "domain": "Hostel & Accommodation",
                "citations": [hostel_policy],
                "recommended_action": "Download Hostel Clearance Form",
                "action_url": "/forms",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_rechecking_query:
            recheck_policy = next((p for p in policies if p["doc_id"] in ("PROC-FORM-RECHECKING", "POL-EXAM-01")), DEFAULT_POLICIES[4])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, उत्तर पुस्तिका के पुनर्मूल्यांकन (Rechecking / Re-evaluation) के आधिकारिक नियम:\n\n"
                    "1. आवेदन फॉर्म: कियोस्क से फॉर्म 27 (Application for Rechecking of Result) डाउनलोड करें।\n"
                    "2. निर्धारित शुल्क: ₹500 प्रति विषय/पेपर (अकाउंट्स विंडो या ऑनलाइन पोर्टल पर देय)।\n"
                    "3. समय सीमा: परिणाम घोषित होने के 15 दिनों के भीतर आवेदन करना अनिवार्य है।\n"
                    "4. जमा करने का स्थान: परीक्षा सेल (खिड़की संख्या 3, प्रशासनिक भवन)। संशोधित परिणाम 21 कार्य दिवसों में जारी किया जाता है।"
                )
                voice_text = f"{student_name}, रीचेकिंग के लिए परिणाम के 15 दिनों के भीतर फॉर्म 27 भरकर ₹500 प्रति पेपर के साथ परीक्षा सेल विंडो 3 में जमा करें।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, answer script rechecking aur re-evaluation ke verified rules yeh hain:\n\n"
                    "1. Application: Kiosk se Form 27 (Rechecking Form) download karein.\n"
                    "2. Fee: ₹500 per subject paper, payable at Accounts Window ya online.\n"
                    "3. Deadline: Result declare hone ke 15 calendar days ke andar apply karna compulsory hai.\n"
                    "4. Submission: Examination Cell (Window 3, Admin Block) me submit karein. Processing SLA 21 working days hai."
                )
                voice_text = f"{student_name}, rechecking ke liye result aane ke 15 din ke andar Form 27 fill karke 500 rupees per paper ke sath Examination Cell Window 3 me submit karein."
            else:
                answer = (
                    f"{student_name}, for answer script re-evaluation and rechecking under University Ordinance ORD-EXAM-12.4:\n\n"
                    "1. Application Form: Download Form 27 (Application for Rechecking of Result) from this kiosk.\n"
                    "2. Prescribed Fee: ₹500 per subject/course paper, payable online or at Accounts Counter.\n"
                    "3. Submission Window: You must apply within 15 calendar days of result declaration.\n"
                    "4. Submission Desk: Examination Cell (Window 3, Administrative Block). The re-evaluated result SLA is 21 working days."
                )
                voice_text = f"{student_name}, for re-evaluation, submit Form 27 with 500 Rupees per paper at Examination Cell Window 3 within 15 days of result declaration."

            res = {
                "answer": answer,
                "domain": "Examinations",
                "citations": [recheck_policy],
                "recommended_action": "Download Rechecking Form (Form 27)",
                "action_url": "/forms",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_backpaper_query:
            backpaper_policy = next((p for p in policies if p["clause_code"] == "ORD-EXAM-12.1"), DEFAULT_POLICIES[4])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, बैकपेपर एवं सप्लीमेंट्री परीक्षा की आधिकारिक नियमावली (अध्यादेश ORD-EXAM-12.1):\n\n"
                    "1. निर्धारित शुल्क: ₹1,500 प्रति विषय/कोर्स।\n"
                    "2. आवश्यक फॉर्म: फॉर्म EX-02 (बैकपेपर परीक्षा आवेदन पत्र)।\n"
                    "3. समय सीमा: सेमेस्टर ग्रेड शीट जारी होने के 14 दिनों के भीतर आवेदन करना आवश्यक है।\n"
                    "4. जमा करने का स्थान: परीक्षा सेल (खिड़की संख्या 1, प्रशासनिक भवन)। एडमिट कार्ड परीक्षा से 5 दिन पूर्व जारी किया जाता है।"
                )
                voice_text = f"{student_name}, बैकपेपर परीक्षा के लिए फॉर्म EX-02 भरकर ₹1,500 प्रति विषय के साथ परीक्षा सेल विंडो 1 में 14 दिनों के भीतर जमा करें।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, backpaper aur supplementary exam ke verified rules yeh hain:\n\n"
                    "1. Examination Fee: ₹1,500 per registered subject course.\n"
                    "2. Form: Form EX-02 (Supplementary Examination Form) kiosk se download karein.\n"
                    "3. Timeline: Result sheet publish hone ke 14 calendar days ke andar submit karein.\n"
                    "4. Submission: Examination Cell (Window 1, Admin Block). Admit card exam se 5 din pehle mil jayega."
                )
                voice_text = f"{student_name}, backpaper ke liye Form EX-02 fill karke 1,500 rupees per subject ke sath Examination Cell Window 1 me submit karein."
            else:
                answer = (
                    f"{student_name}, supplementary and backpaper examinations are governed by Ordinance ORD-EXAM-12.1:\n\n"
                    "1. Prescribed Fee: ₹1,500 per registered course paper.\n"
                    "2. Prescribed Form: Form EX-02 (Supplementary / Backpaper Examination Application).\n"
                    "3. Submission Deadline: Must be submitted within 14 calendar days of semester grade sheet publication.\n"
                    "4. Submission Counter: Examination Cell Counter (Window 1, Ground Floor, Admin Block). Admit cards are issued 5 days prior to exams."
                )
                voice_text = f"{student_name}, to register for backpapers, submit Form EX-02 along with 1,500 Rupees per course at Examination Cell Window 1 within 14 days."

            res = {
                "answer": answer,
                "domain": "Examinations",
                "citations": [backpaper_policy],
                "recommended_action": "Download Backpaper Form EX-02",
                "action_url": "/forms",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_degree_query:
            degree_policy = next((p for p in policies if p["doc_id"] == "PROC-FORM-DEGREE"), DEFAULT_POLICIES[4])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, आधिकारिक उपाधि / डिग्री प्रमाण पत्र (Degree Certificate) प्राप्त करने की प्रक्रिया यह है:\n\n"
                    "1. कियोस्क से फॉर्म 22 (Degree Application & Convocation Format) डाउनलोड करें।\n"
                    "2. आवश्यक दस्तावेज: विश्वविद्यालय नो-ड्यूज (No-Dues) पर्ची, सभी सेमेस्टर मार्कशीट की फोटोकॉपी, और प्रोविजनल सर्टिफिकेट संलग्न करें।\n"
                    "3. जमा करने का स्थान: रजिस्ट्रार कार्यालय (खिड़की संख्या 2, प्रशासनिक भवन)।\n"
                    "4. जारी करने की समय सीमा: आवेदन के 7 से 10 कार्य दिवसों के भीतर डिग्री तैयार कर डाक द्वारा भेजी जाती है या व्यक्तिगत रूप से दी जाती है।"
                )
                voice_text = f"{student_name}, डिग्री प्रमाण पत्र के लिए फॉर्म 22 भरकर, सभी मार्कशीट और नो-ड्यूज पर्ची के साथ रजिस्ट्रार खिड़की 2 में जमा करें।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, official Degree Certificate ke liye verified steps yeh hain:\n\n"
                    "1. Kiosk se Form 22 (Degree Application Form) download karein.\n"
                    "2. Attachments: University No-Dues clearance slip, sabhi semester marksheets ki copies, aur provisional certificate.\n"
                    "3. Submission: Registrar Office (Window 2, Administrative Block).\n"
                    "4. Delivery SLA: 7 se 10 working days me degree dispatch ya collect kar sakte hain."
                )
                voice_text = f"{student_name}, degree certificate ke liye Form 22 fill karke No-Dues slip ke sath Registrar Window 2 me submit karein. Yeh 7 se 10 din me mil jayegi."
            else:
                answer = (
                    f"{student_name}, to apply for your official Degree Certificate under University Ordinance:\n\n"
                    "1. Application Form: Download Form 22 (Degree Application & Convocation Format) from this kiosk.\n"
                    "2. Mandatory Attachments: Complete University No-Dues clearance slip, copies of all semester grade marksheets, and provisional degree.\n"
                    "3. Submission Desk: Registrar Office Window 2 (Ground Floor, Admin Block).\n"
                    "4. Turnaround SLA: Official degree certificate is issued within 7 to 10 working days (available via registered post or in-person collection)."
                )
                voice_text = f"{student_name}, to obtain your degree certificate, submit Form 22 along with your marksheet copies and No-Dues slip to Registrar Window 2. It takes 7 to 10 working days."

            res = {
                "answer": answer,
                "domain": "Academic Records",
                "citations": [degree_policy],
                "recommended_action": "Download Degree Application Form (Form 22)",
                "action_url": "/forms",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_migration_query:
            migration_policy = next((p for p in policies if p["doc_id"] == "PROC-FORM-MIGRATION"), DEFAULT_POLICIES[4])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, माइग्रेशन प्रमाण पत्र (Migration Certificate) प्राप्त करने की आधिकारिक प्रक्रिया:\n\n"
                    "1. कियोस्क से फॉर्म 15 (Migration Certificate Application) डाउनलोड करें।\n"
                    "2. आवश्यक दस्तावेज: अंतिम सेमेस्टर मार्कशीट, आईडी प्रूफ, और नो-ड्यूज क्लीयरेंस पर्ची संलग्न करें।\n"
                    "3. निर्धारित शुल्क: ₹300 (अकाउंट्स काउंटर पर देय)।\n"
                    "4. जमा करने का स्थान: रजिस्ट्रार कार्यालय (खिड़की संख्या 2)। 3 से 5 कार्य दिवसों में प्रमाण पत्र जारी कर दिया जाता है।"
                )
                voice_text = f"{student_name}, माइग्रेशन प्रमाण पत्र के लिए फॉर्म 15 भरकर ₹300 शुल्क के साथ रजिस्ट्रार खिड़की 2 में जमा करें। यह 3 से 5 दिनों में मिल जाएगा।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, Migration Certificate ke liye verified steps yeh hain:\n\n"
                    "1. Kiosk se Form 15 (Migration Application) download karein.\n"
                    "2. Attachments: Final marksheet copy, student ID proof, aur No-Dues slip.\n"
                    "3. Prescribed Fee: ₹300 at Accounts Counter.\n"
                    "4. Submission: Registrar Office (Window 2, Admin Block). SLA 3 se 5 working days hai."
                )
                voice_text = f"{student_name}, migration certificate ke liye Form 15 fill karke 300 rupees fee ke sath Registrar Window 2 me submit karein. SLA 3 se 5 din hai."
            else:
                answer = (
                    f"{student_name}, to obtain your Migration Certificate under University Ordinance:\n\n"
                    "1. Application Form: Download Form 15 (Migration Certificate Application) from this kiosk.\n"
                    "2. Required Attachments: Attested copy of final semester grade report, student ID proof, and University No-Dues clearance.\n"
                    "3. Prescribed Fee: ₹300, payable at Accounts Window 4.\n"
                    "4. Submission Desk: Registrar Office Window 2 (Admin Block). SLA is 3 to 5 working days for collection or speed post dispatch."
                )
                voice_text = f"{student_name}, to get your migration certificate, submit Form 15 with 300 Rupees fee and your No-Dues slip at Registrar Window 2. It will be ready in 3 to 5 working days."

            res = {
                "answer": answer,
                "domain": "Academic Records",
                "citations": [migration_policy],
                "recommended_action": "Download Migration Form (Form 15)",
                "action_url": "/forms",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_grievance_query:
            grievance_policy = next((p for p in policies if p["clause_code"] == "ORD-GRV-22.5"), DEFAULT_POLICIES[6])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, छात्र सुरक्षा और शिकायत निवारण अध्यादेश ORD-GRV-22.5 के तहत पूरी तरह संरक्षित हैं:\n\n"
                    "1. रैगिंग पर शून्य सहनशीलता: रैगिंग या उत्पीड़न की किसी भी शिकायत पर 24 घंटे के भीतर आपातकालीन प्रॉक्टोरियल जांच और कार्रवाई होती है।\n"
                    "2. अनिवार्य समय सीमा (SLA): सामान्य शैक्षणिक और सुविधा संबंधी शिकायतों का 48 घंटे के भीतर अनिवार्य निवारण किया जाता है।\n"
                    "3. शिकायत पटल: आप कियोस्क से सीधे औपचारिक शिकायत दर्ज कर सकते हैं या प्रॉक्टर / छात्र कल्याण डीन (कमरा नंबर 105, प्रशासनिक भवन) से व्यक्तिगत रूप से संपर्क कर सकते हैं।"
                )
                voice_text = f"{student_name}, रैगिंग या उत्पीड़न पर तुरंत 24 घंटे में आपातकालीन कार्रवाई होती है। आप सीधे कमरा 105 में प्रॉक्टर से मिल सकते हैं या कियोस्क से शिकायत दर्ज कर सकते हैं।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, campus safety aur grievance redressal Ordinance ORD-GRV-22.5 ke under guaranteed hai:\n\n"
                    "1. Zero Tolerance Anti-Ragging: Ragging ya harassment par immediate 24-hour Proctorial emergency action hoti hai.\n"
                    "2. Resolution SLA: Academic aur campus facility grievances ka mandatory 48-hour resolution SLA hai.\n"
                    "3. Action: Aap kiosk par direct grievance ticket lodge kar sakte hain ya Dean of Student Welfare (Room 105, Admin Block) se mil sakte hain."
                )
                voice_text = f"{student_name}, ragging par 24-hour emergency SLA hai. Aap direct Room 105 me Proctor se mil sakte hain ya kiosk par complaint register kar sakte hain."
            else:
                answer = (
                    f"{student_name}, student safety and grievances are strictly governed under Ordinance ORD-GRV-22.5:\n\n"
                    "1. Zero Tolerance for Ragging: Any harassment or ragging allegation triggers an immediate 24-hour emergency Proctorial investigation.\n"
                    "2. Mandatory SLA: General academic and facility grievances carry a mandatory 48-hour resolution SLA by the Department Coordinator, escalating to Dean Student Welfare.\n"
                    "3. Lodge Action: You can lodge a formal grievance ticket right now on this kiosk, or meet the Proctor and Dean of Student Welfare in Room 105 (Administrative Block)."
                )
                voice_text = f"{student_name}, ragging carries a zero tolerance policy and an emergency 24-hour response. You can report it immediately at Room 105 or file a grievance on this kiosk."

            res = {
                "answer": answer,
                "domain": "Student Grievance & Welfare",
                "citations": [grievance_policy],
                "recommended_action": "File Formal Grievance",
                "action_url": "/chat",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_scholarship_query:
            sch_policy = next((p for p in policies if p["clause_code"] == "ORD-SCH-16.3"), DEFAULT_POLICIES[7])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, विश्वविद्यालय छात्रवृत्ति एवं फीस छूट अध्यादेश ORD-SCH-16.3 द्वारा संचालित होती है:\n\n"
                    "1. मेरिट छात्रवृत्ति नवीनीकरण मानदंड: पिछले शैक्षणिक सत्र में न्यूनतम 8.0 CGPA, कम से कम 80% कुल उपस्थिति, और कोई सक्रिय बैकपेपर नहीं होना चाहिए।\n"
                    "2. लाभ: आगामी सत्र की ट्यूशन फीस में 50% की सीधी छूट।\n"
                    "3. आवेदन: नया सेमेस्टर शुरू होने के 15 दिनों के भीतर फॉर्म SCH-01 और ग्रेड कार्ड छात्रवृत्ति प्रकोष्ठ (कमरा नंबर 204, एकेडमिक ब्लॉक) में जमा करें।\n"
                    "4. वित्तीय सहायता: ₹3,00,000 से कम वार्षिक पारिवारिक आय वाले छात्र आय प्रमाण पत्र के साथ आवेदन कर सकते हैं।"
                )
                voice_text = f"{student_name}, मेरिट छात्रवृत्ति के लिए न्यूनतम 8.0 CGPA, 80% उपस्थिति और शून्य बैकपेपर होना अनिवार्य है। कमरा 204 में फॉर्म SCH-01 जमा करें।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, merit scholarship renewal criteria Ordinance ORD-SCH-16.3 ke under yeh hain:\n\n"
                    "1. Criteria: Minimum 8.0 CGPA, 80% previous semester attendance, aur zero backpapers.\n"
                    "2. Benefit: Upcoming semester tuition fee me 50% waiver.\n"
                    "3. Renewal: Semester shuru hone ke 15 days me Form SCH-01 aur grade card Scholarship Cell (Room 204) me submit karein."
                )
                voice_text = f"{student_name}, scholarship renewal ke liye minimum 8.0 CGPA aur 80 percent attendance zaroori hai. Form SCH-01 Room 204 me submit karein."
            else:
                answer = (
                    f"{student_name}, university scholarships and concessions are governed by Ordinance ORD-SCH-16.3:\n\n"
                    "1. Merit Scholarship Renewal Criteria: You must maintain a minimum CGPA of 8.0, achieve at least 80% overall attendance in the preceding semester, and have zero active backpapers.\n"
                    "2. Benefit: 50% tuition fee waiver for the upcoming academic year.\n"
                    "3. Submission: Submit Form SCH-01 with semester grade cards to the Scholarship Cell (Room 204, Academic Block) within 15 calendar days of semester commencement.\n"
                    "4. Need-Based Aid: Concessions require annual submission of verified family income certificate (< ₹3 Lakh p.a.)."
                )
                voice_text = f"{student_name}, merit scholarship renewal requires a minimum 8.0 CGPA, 80 percent attendance, and zero backpapers. Submit Form SCH-01 in Room 204."

            res = {
                "answer": answer,
                "domain": "Scholarships",
                "citations": [sch_policy],
                "recommended_action": "Explore Scholarships",
                "action_url": "/scholarship",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_offset_query:
            offset_policy = next((p for p in policies if p["clause_code"] == "ORD-FIN-14.4"), DEFAULT_POLICIES[2])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, स्मार्ट कॉशन डिपॉजिट ऑफसेटिंग प्रोटोकॉल (अध्यादेश ORD-FIN-14.4) के तहत:\n\n"
                    "1. पात्र शुल्क: खोए हुए छात्र पहचान पत्र का शुल्क (₹200), लाइब्रेरी की विलंब पेनल्टी, या ₹2,000 से कम के बकाए को सीधे आपकी ₹10,000 की वापसी योग्य कॉशन डिपॉजिट राशि से काटा जा सकता है।\n"
                    "2. त्वरित क्लियरेंस: इसके लिए आपको बैंक जाने या लंबी कतारों में लगने की आवश्यकता नहीं है; स्मार्ट ऑफसेट चेकबॉक्स चुनते ही संबंधित गेट तुरंत क्लियर हो जाता है।\n"
                    "3. शेष राशि: आपकी बची हुई कॉशन डिपॉजिट राशि संस्थान छोड़ने पर 100% आपके बैंक खाते में वापस कर दी जाती है।"
                )
                voice_text = f"{student_name}, स्मार्ट ऑफसेटिंग के तहत ₹2,000 तक का जुर्माना या ₹200 आईडी शुल्क सीधे कॉशन डिपॉजिट से कट जाता है, बैंक जाने की आवश्यकता नहीं है।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, Smart Caution Deposit Offsetting (Ordinance ORD-FIN-14.4) ke mutabiq:\n\n"
                    "1. Eligible Dues: Library fine, lost ID card fee (₹200), ya ₹2,000 tak ki minor penalties direct aapke ₹10,000 refundable caution deposit se auto-deduct ho jati hain.\n"
                    "2. Instant Clearance: Bank jaane ki zarurat nahi hoti; Smart Offset tick karte hi clearance gate instantly clear ho jata hai.\n"
                    "3. Balance Refund: Bachi hui deposit amount withdrawal ke waqt 100% refund milti hai."
                )
                voice_text = f"{student_name}, Smart Offsetting se 2,000 rupees tak ke fines direct caution deposit se deduct ho jate hain bina bank jaye."
            else:
                answer = (
                    f"{student_name}, under the Smart Caution Deposit Offsetting Protocol (Ordinance ORD-FIN-14.4):\n\n"
                    "1. Eligible Charges: Unreturned library book fines, lost student ID replacement fees (₹200), or minor facility charges under ₹2,000 can be auto-deducted directly from your refundable caution deposit (standard balance ₹10,000).\n"
                    "2. Instant Clearance: You do not need to make offline bank visits or queue at accounts counters. Checking the 'Smart Offset' checkbox clears the clearance gate immediately.\n"
                    "3. Balance Return: The remaining balance of your caution deposit is refunded 100% to your bank account upon institutional clearance."
                )
                voice_text = f"{student_name}, under Smart Offsetting, fines under 2,000 Rupees or the 200 Rupees lost ID fee can be auto-deducted from your caution deposit without visiting the bank."

            res = {
                "answer": answer,
                "domain": "Finance & Accounts",
                "citations": [offset_policy],
                "recommended_action": "View Clearance & Offset",
                "action_url": "/withdrawal",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_withdrawal_query:
            wth_policy = next((p for p in policies if p["clause_code"] == "ORD-WTH-14.1"), DEFAULT_POLICIES[1])
            offset_policy = next((p for p in policies if p["clause_code"] == "ORD-FIN-14.4"), DEFAULT_POLICIES[2])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, विश्वविद्यालय विड्रॉल और फीस रिफंड प्रक्रिया यूजीसी 2024 दिशानिर्देशों एवं अध्यादेश ORD-WTH-14.1 द्वारा संचालित होती है:\n\n"
                    "1. ट्यूशन फीस रिफंड स्लैब: (क) प्रवेश अंतिम तिथि से 15 दिन या अधिक पूर्व: 100% रिफंड (अधिकतम ₹1,000 प्रोसेसिंग शुल्क काटकर); (ख) 15 दिन से कम पूर्व: 90%; (ग) अंतिम तिथि के 15 दिनों के भीतर: 80%; (घ) 16 से 30 दिनों के भीतर: 50%; (ङ) 30 दिनों के बाद: ट्यूशन फीस शून्य रिफंड।\n"
                    "2. कॉशन डिपॉजिट: आपकी ₹10,000 की कॉशन डिपॉजिट राशि सभी तारीखों पर 100% सुरक्षित और वापस की जाती है।\n"
                    "3. 4-गेट डिजिटल क्लीयरेंस: लाइब्रेरी, हॉस्टल, एकाउंट्स और रजिस्ट्रार गेट्स क्लियर होते हैं।\n"
                    "4. आवेदन: अभिभावक सहमति पत्र और बैंक चेक प्रति के साथ रजिस्ट्रार कार्यालय (कमरा नंबर 102) में जमा करें।"
                )
                voice_text = f"{student_name}, विश्वविद्यालय विड्रॉल यूजीसी नियमों के अनुसार होता है। ट्यूशन फीस 100% से 50% तक रिफंड होती है और ₹10,000 कॉशन डिपॉजिट पूरा वापस मिलता है।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, university withdrawal UGC norms aur Ordinance ORD-WTH-14.1 ke mutabiq hoti hai:\n\n"
                    "1. Tuition Slabs: 15+ days prior: 100% (-₹1,000 processing fee); <15 days: 90%; 15 days post: 80%; 16-30 days post: 50%; 30+ days: 0%.\n"
                    "2. Caution Deposit: ₹10,000 caution deposit 100% refundable hai har slab me.\n"
                    "3. Clearance: Library, Hostel, Accounts, aur Registrar ke 4 digital gates clear karne hote hain.\n"
                    "4. Submission: Registrar Office (Room 102) me parents consent letter aur cancelled cheque ke sath submit karein."
                )
                voice_text = f"{student_name}, withdrawal me UGC slabs ke mutabiq 100% se 50% tuition refund milti hai aur 10,000 caution deposit poora wapas milta hai."
            else:
                answer = (
                    f"{student_name}, university program withdrawal is governed by Ordinance ORD-WTH-14.1 and UGC directives:\n\n"
                    "1. Tuition Refund Slabs: (a) 15+ days prior to admission deadline: 100% refund (minus max ₹1,000 processing fee); (b) <15 days prior: 90%; (c) Up to 15 days post deadline: 80%; (d) 16-30 days post deadline: 50%; (e) Beyond 30 days: 0%.\n"
                    "2. Caution Deposit: Your ₹10,000 refundable caution deposit is 100% refundable across all calendar dates.\n"
                    "3. 4-Gate Digital Clearance: Track clearance across Library, Hostel, Accounts, and Registrar.\n"
                    "4. Submission: Submit the signed withdrawal form with parent consent and cancelled bank cheque to Registrar Office (Room 102)."
                )
                voice_text = f"{student_name}, university program withdrawal follows UGC slabs with up to 100% tuition refund and a 100% refundable caution deposit of 10,000 Rupees."

            res = {
                "answer": answer,
                "domain": "Withdrawal & Refunds",
                "citations": [wth_policy, offset_policy],
                "recommended_action": "Start Withdrawal Procedure",
                "action_url": "/withdrawal",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_attendance_query:
            matching_clause = next((p for p in policies if p["clause_code"] == "ORD-ACAD-7.2"), DEFAULT_POLICIES[0])
            if attendance >= 75.0:
                if language == "hi-IN":
                    answer = (
                        f"{student_name}, आपकी वर्तमान उपस्थिति {attendance:.1f}% है, जो अध्यादेश ORD-ACAD-7.2 के 75% कटऑफ को पूरा करती है। "
                        "आप बिना किसी रुकावट के अंतिम सेमेस्टर परीक्षा देने के लिए पूरी तरह पात्र हैं। क्या आप परीक्षा शेड्यूल देखना चाहते हैं?"
                    )
                elif language == "hi-Latn":
                    answer = (
                        f"{student_name}, aapki attendance {attendance:.1f}% hai, jo 75% cutoff ko meet karti hai under ORD-ACAD-7.2. "
                        "Aap semester exams ke liye fully eligible hain."
                    )
                else:
                    answer = (
                        f"{student_name}, your current attendance is {attendance:.1f}%, which meets the 75% cutoff under "
                        "Ordinance ORD-ACAD-7.2. You are fully eligible to sit for End Term Semester Examinations without any condonation."
                    )
                recommended_action = "View Exam Schedule"
                action_url = "/exams"
            elif 60.0 <= attendance < 75.0:
                shortfall = 75.0 - attendance
                if language == "hi-IN":
                    answer = (
                        f"{student_name}, आपकी वर्तमान उपस्थिति {attendance:.1f}% है (75% के कटऑफ से {shortfall:.1f}% कम)। "
                        "अध्यादेश ORD-ACAD-7.2 के अनुसार, आप मेडिकल प्रमाण पत्र या अधिकृत ड्यूटी पत्र के साथ फॉर्म AC-04 जमा करके "
                        "डीन छूट (Condonation) प्राप्त कर सकते हैं। यह आवेदन परीक्षा शुरू होने से 10 दिन पहले डीन शैक्षणिक मामले (कमरा 201) में जमा करना होता है।"
                    )
                elif language == "hi-Latn":
                    answer = (
                        f"{student_name}, aapki attendance {attendance:.1f}% hai ({shortfall:.1f}% short of 75%). "
                        "Under ORD-ACAD-7.2, aap medical grounds par Form AC-04 submit karke Dean Condonation le sakte hain Room 201 me. "
                        "Kya aap Form AC-04 download karna chahte hain?"
                    )
                else:
                    answer = (
                        f"{student_name}, your recorded attendance is {attendance:.1f}% ({shortfall:.1f}% short of the mandatory 75% cutoff). "
                        "Under Ordinance ORD-ACAD-7.2, you are eligible to request Dean's Condonation on medical or approved official "
                        "duty grounds by filing Form AC-04 at the Dean's Office (Room 201) before the 10-day exam deadline."
                    )
                recommended_action = "Download Form AC-04 (Condonation)"
                action_url = "/forms"
            else:
                if language == "hi-IN":
                    answer = (
                        f"{student_name}, आपकी दर्ज उपस्थिति {attendance:.1f}% है, जो 60% की न्यूनतम सीमा से कम है। "
                        "अध्यादेश ORD-ACAD-7.2 के अनुसार, 60% से कम उपस्थिति पर परीक्षा में बैठना वर्जित है। "
                        "कृपया तुरंत मार्गदर्शन के लिए अपने विभाग समन्वयक से संपर्क करें।"
                    )
                else:
                    answer = (
                        f"{student_name}, your recorded attendance is {attendance:.1f}%, which falls below the critical 60% threshold. "
                        "Under Ordinance ORD-ACAD-7.2, attendance below 60% constitutes mandatory debarment. Please meet your Department "
                        "Coordinator immediately for proctorial guidance."
                    )
                recommended_action = "Contact Academic Advisor"
                action_url = "/chat"

            res = {
                "answer": answer,
                "domain": "Academics",
                "citations": [matching_clause],
                "recommended_action": recommended_action,
                "action_url": action_url,
                "voice_speech_text": answer,
                "engine": "UniAssist Policy Engine",
            }

        elif is_post_form_query or any(f_kw in q_lower for f_kw in [
            "tada", "conveyance", "biometric", "imprest", "mentoring", "purchase proposal", "stationery",
            "blank exam", "placement opted"
        ]):
            proc = get_procedure_by_keyword(query)
            form_matches = [p for p in policies if p["doc_id"].startswith("PROC-") or "Form" in p["title"]]
            best_form = form_matches[0] if form_matches else (policies[0] if policies else None)

            if proc:
                content_text = (
                    f"Verified Procedure for {proc['title']}:\n"
                    f"1. Action at Kiosk: {proc['kiosk_action']}\n"
                    f"2. Required Attachments: {', '.join(proc['attachments_required'])}\n"
                    f"3. Submission Room & Window: {proc['submission_room']} ({proc['window']})\n"
                    f"4. Turnaround SLA: {proc['sla_working_days']} working days\n"
                    f"5. Associated Fee: {proc['fee']}"
                )
                f_title = proc["title"]
                f_act = proc.get("action_label", f"Download {f_title}")
                f_url = proc.get("action_url", "/forms")
            elif best_form:
                content_text = best_form['content']
                f_title = best_form['title']
                f_act = best_form.get("action_label", f"Download {f_title}")
                f_url = best_form.get("action_url", "/forms")
            else:
                content_text = "Please download the required form and submit it to the designated department window."
                f_title = "University Application Form"
                f_act = "Download Form"
                f_url = "/forms"

            if language == "hi-IN":
                answer = f"{student_name}, {f_title} के लिए आधिकारिक प्रक्रिया और जमा करने के निर्देश:\n\n{content_text}"
                clean_speech = f"{student_name}, {f_title} के लिए: {content_text}"
            else:
                answer = f"{student_name}, here is the verified post-download submission procedure for {f_title}:\n\n{content_text}"
                clean_speech = f"{student_name}, for {f_title}: {content_text}".replace("₹", "Rupees ").replace("INR ", "Rupees ")

            res = {
                "answer": answer,
                "domain": "Post-Download Procedure",
                "citations": [best_form] if best_form else [],
                "recommended_action": f_act,
                "action_url": f_url,
                "voice_speech_text": clean_speech,
                "engine": "UniAssist Policy Engine",
            }

        elif is_vague_form_query:
            if language == "hi-IN":
                answer = (
                    f"{student_name}, UniAssist के पास सभी 31 आधिकारिक विश्वविद्यालय फॉर्म उपलब्ध हैं। "
                    "कृपया स्पष्ट करें कि आपको कौन सा फॉर्म चाहिए? मुख्य विकल्प हैं:\n"
                    "• माइग्रेशन प्रमाण पत्र (फॉर्म 15)\n"
                    "• परिणाम पुनर्मूल्यांकन / रीचेकिंग (फॉर्म 27)\n"
                    "• डुप्लिकेट छात्र आईडी कार्ड (फॉर्म 28)\n"
                    "• उपस्थिति छूट - कंडोनेशन (फॉर्म AC-04)\n"
                    "• बैकपेपर परीक्षा (फॉर्म EX-02)\n"
                    "• विश्वविद्यालय विड्रॉल एवं नो-ड्यूज फॉर्म\n\n"
                    "आप सीधे विश्वविद्यालय फॉर्म कैटलॉग भी खोल सकते हैं।"
                )
                voice_text = f"{student_name}, UniAssist में सभी 31 फॉर्म उपलब्ध हैं। आपको माइग्रेशन, रीचेकिंग, डुप्लिकेट आईडी, या विड्रॉल में से कौन सा फॉर्म चाहिए?"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, UniAssist par sabhi 31 official university forms available hain. "
                    "Aapko kaunsa form chahiye? Common options:\n"
                    "• Migration Certificate (Form 15)\n"
                    "• Result Rechecking (Form 27)\n"
                    "• Duplicate Student ID Card (Form 28)\n"
                    "• Attendance Condonation (Form AC-04)\n"
                    "• Backpaper Examination (Form EX-02)\n"
                    "• Program Withdrawal & Clearance Form\n\n"
                    "Aap direct Forms Catalog bhi open kar sakte hain."
                )
                voice_text = f"{student_name}, aapko kaunsa form chahiye? Migration, rechecking, duplicate ID, ya backpaper? Aap batayein main download karwa deta hoon."
            else:
                answer = (
                    f"{student_name}, UniAssist hosts all 31 verified university application forms. "
                    "Could you specify which form you need? Popular forms include:\n"
                    "• Migration Certificate (Form 15)\n"
                    "• Result Rechecking & Re-evaluation (Form 27)\n"
                    "• Duplicate Student ID Card (Form 28)\n"
                    "• Attendance Condonation Application (Form AC-04)\n"
                    "• Backpaper Supplementary Examination (Form EX-02)\n"
                    "• Program Withdrawal & No-Dues Clearance\n\n"
                    "You can also browse the full catalog directly."
                )
                voice_text = f"{student_name}, which of the 31 university forms do you need? For example, Migration, Rechecking, Duplicate ID, or Backpaper?"

            res = {
                "answer": answer,
                "domain": "Forms Catalog",
                "citations": [],
                "recommended_action": "Open Forms Catalog",
                "action_url": "/forms",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif policies and cls._is_policy_relevant_to_query(query, policies[0]):
            top_p = policies[0]
            p_title = top_p.get("title", "University Policy")
            p_content = top_p.get("content", "")
            if language == "hi-IN":
                answer = (
                    f"{student_name}, {p_title} के संबंध में विश्वविद्यालय की सत्यापित नियमावली:\n\n"
                    f"{p_content}"
                )
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, {p_title} ke verified rules yeh hain:\n\n"
                    f"{p_content}"
                )
            else:
                answer = (
                    f"{student_name}, regarding {p_title}, here is the official university guidance:\n\n"
                    f"{p_content}"
                )
            res = {
                "answer": answer,
                "domain": top_p.get("category", "General Policies"),
                "citations": policies[:3],
                "recommended_action": top_p.get("action_label", "View Details"),
                "action_url": top_p.get("action_url", "/forms"),
                "voice_speech_text": answer.replace("₹", "Rupees ").replace("INR ", "Rupees "),
                "engine": "UniAssist Policy Engine",
            }
        else:
            if language == "hi-IN":
                fallback_msg = (
                    f"{student_name}, मुझे आपके इस प्रश्न से संबंधित कोई विशिष्ट विश्वविद्यालय अध्यादेश नहीं मिला। "
                    "UniAssist सभी 31 फॉर्म, विड्रॉल रिफंड, उपस्थिति छूट (Condonation), कॉशन डिपॉजिट ऑफसेट, बैकपेपर परीक्षा, "
                    "और छात्रवृत्ति नियमों में पूरी सहायता करता है। कृपया इनमें से किसी भी विषय पर पूछें।"
                )
            elif language == "hi-Latn":
                fallback_msg = (
                    f"{student_name}, mujhe aapke question se matching koi specific ordinance nahi mila. "
                    "UniAssist sabhi 31 forms, Attendance Condonation, Withdrawal Refund, Caution Deposit Offsets, "
                    "Backpapers, aur Scholarships me help provide karta hai. Please inme se kisi topic par poochiye."
                )
            else:
                fallback_msg = (
                    f"{student_name}, I could not find a specific university ordinance matching your inquiry. "
                    "UniAssist provides guidance for all 31 university forms, Academics, Attendance Condonation, "
                    "Withdrawal Refunds, Smart Caution Deposit Offsets, Backpapers, Grievances, and Scholarships. "
                    "Please try asking with one of these topics."
                )

            res = {
                "answer": fallback_msg,
                "domain": "General",
                "citations": [],
                "recommended_action": "Browse Forms & Policies",
                "action_url": "/forms",
                "voice_speech_text": fallback_msg,
                "engine": "UniAssist Policy Engine",
            }

        # Gemini / Ollama synthesis on policy questions if enabled
        if "engine" not in res:
            res["engine"] = "SQLite FTS5 (Local Offline)"

        citations_for_gemini = res.get("citations") or policies or []
        if settings.llm_enabled or settings.is_ollama_enabled or settings.llm_provider.lower() in ("ollama", "gemini", "local"):
            is_deterministic_domain = res.get("domain") in (
                "Academics",
                "Withdrawal & Refunds",
                "Withdrawal & Caution Deposit Offset",
                "Finance & Accounts",
                "Hostel & Accommodation",
                "Student ID Services",
                "Certificates & Identity",
                "Academic Records",
                "Examinations",
                "Student Grievance & Welfare",
                "Scholarships",
                "Post-Download Procedure",
                "Forms Catalog",
                "Forms Navigation",
                "Withdrawal Navigation",
                "Exams Navigation",
                "Grievance Navigation",
                "Scholarship Navigation",
                "University Portals",
                "Domain Boundary Guard",
                "HR & Faculty",
                "Conversational",
                "Navigation",
            )
            # Invoke LLM synthesis ONLY for un-indexed or general questions (never overwrite verified UniAssist Policy Engine ground truth)
            if res.get("engine") != "UniAssist Policy Engine" and not is_deterministic_domain:
                gemini_res = synthesize_guidance_with_gemini(
                    query=query,
                    citations=citations_for_gemini,
                    student=student,
                    page_context=page_context,
                    language=language,
                    return_source=True,
                    history=history,
                )
                if gemini_res:
                    text, engine_name = gemini_res
                    if "Offline" not in engine_name or not is_deterministic_domain:
                        res["answer"] = text
                        res["voice_speech_text"] = text
                        res["engine"] = engine_name

        # Ambient Screen Awareness Enhancement - ONLY attach when query specifically relates to active screen navigation
        if page_context and res.get("domain") not in ("Domain Boundary Guard", "General") and is_ambient_navigation:
            scr_name = page_context.get("screen_name") or "the current page"
            primary_act = page_context.get("primary_action")
            if primary_act:
                if language == "hi-IN":
                    res["screen_instruction"] = f"इस {scr_name} पर, आप तुरंत आगे बढ़ने के लिए '{primary_act}' पर क्लिक कर सकते हैं।"
                else:
                    res["screen_instruction"] = f"On this {scr_name}, you can click '{primary_act}' to proceed immediately."
                res["highlight_target"] = primary_act

        # Guaranteed UI Action Button for all campus services
        if res.get("domain") not in ("Conversational", "Domain Boundary Guard"):
            if not res.get("action_url"):
                res["action_url"] = "/forms"
            if not res.get("recommended_action"):
                res["recommended_action"] = "Open Forms Catalog"

        return res

