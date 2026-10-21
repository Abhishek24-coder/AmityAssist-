"""Phase 29: Intelligent Search & Policy Guidance Service.

Combines SQLite FTS5 (BM25 Inverted Index) for sub-5ms legal ordinance retrieval
with personalized hybrid RAG advice synthesis (attendance condonation, withdrawal
refund slabs, caution deposit offset, post-form submission guidance, and voice TTS guidance).
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from typing import Any

from ..config import settings
from ..database.connection import get_connection
from ..services.nlp_service import score_sentiment
from ..services.advanced_ai_service import synthesize_guidance_with_gemini
from ..services.local_llm_service import strip_markdown_stars
from ..data.kiosk_master_procedures import MASTER_PROCEDURES, get_procedure_by_keyword


# ---------------------------------------------------------------------------
# Seed Ordinances & University Handbooks + Form Post-Download Workflows
# ---------------------------------------------------------------------------

DEFAULT_POLICIES = [
    # Core Ordinances
    {
        "doc_id": "ORD-ADM-01",
        "category": "Admissions & Enrollment",
        "title": "Fresh Student Admission & Document Verification Guidelines",
        "clause_code": "ORD-ADM-1.1",
        "content": (
            "Procedure for Fresh / New Student Admission & Enrollment: "
            "1. Online Registration & Merit Allotment: Submit the Admission Application (Form ADM-01) on the admissions portal with academic credentials and qualifying entrance exam rank/scores (JEE/CUET/State CET). "
            "2. Document Verification Dossier: Present original 10th and 12th marksheets, Transfer Certificate (TC), Migration Certificate, Character Certificate, and 4 passport-size photographs at the Directorate of Admissions (Room 101, Central Block). "
            "3. Fee Payment & Provisional Enrollment: Deposit the first-semester academic fee and refundable caution deposit (INR 10,000) online via the ERP payment gateway or offline at Accounts Counter (Room 14). "
            "4. Biometric ID Card & LMS Activation: Report to IT Center (Room 105) for biometric RFID student smart identity card generation and university LMS email credentials."
        ),
        "action_url": "/forms",
        "action_label": "Download Admission Guidelines (ADM-01)",
    },
    {
        "doc_id": "POL-ACAD-01",
        "category": "Academics",
        "title": "Minimum Attendance Requirement & Medical Condonation",
        "clause_code": "ORD-ACAD-7.2",
        "content": (
            "Minimum attendance requirement is 75% in every registered course to be eligible "
            "to sit for End Term Semester Examinations. The 25% absence margin is provided specifically to absorb medical leave, "
            "illness, personal emergencies, and unavoidable absences. If overall attendance falls between 60.0% and 74.9% due to serious "
            "documented illness, the student may apply for Dean's Medical Condonation by submitting Form AC-04 along with hospital "
            "OPD receipts and doctor certificates at least 10 working days prior to exam commencement. Attendance below 60% constitutes "
            "mandatory debarment with zero condonation permitted."
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
        "doc_id": "PROC-FORM-ADMISSION",
        "category": "Admissions & Registrar",
        "title": "New Student Admission Application (Form ADM-01)",
        "clause_code": "PROC-FORM-ADM01",
        "content": (
            "After obtaining Form ADM-01 (New Student Admission Application), follow these steps: "
            "1. Complete applicant details, academic record scores, and selected program stream. "
            "2. Attach attested photocopies of 10th and 12th marksheets, national/state entrance exam rank card, Transfer Certificate (TC), and Migration Certificate. "
            "3. Present original certificates for physical verification at Directorate of Admissions (Room 101, Central Block). "
            "4. Pay the first-semester academic fee and refundable caution deposit (INR 10,000) online via ERP or at Accounts Counter. Provisional allotment letter issued within 24 hours."
        ),
        "action_url": "/forms",
        "action_label": "Download Form ADM-01",
    },
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
            "2. Verify completion of the 4 digital clearance gates (Library, conditional Hostel, Accounts, Registrar). "
            "3. Submit digitally on the kiosk portal (/withdrawal). "
            "Once digital notesheet review is approved by Registrar, download your official Clearance Slip (PDF), releasing caution deposit (Rupees 10,000) and eligible tuition fee refund."
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
            "2. Initiate digital clearance across the 4 automated gates: Library, Hostel (if resident hosteller; bypassed for day-scholars), and Finance. "
            "3. Complete submission digitally on this kiosk portal (/withdrawal). Tuition refund is calculated under UGC date slabs, "
            "and the Rupees 10,000 caution deposit is 100% refundable with instant digital clearance slip download upon Registrar approval."
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
        """Create and populate university_policies table and FTS5 virtual table if empty or incomplete."""
        conn = get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS university_policies (
                doc_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                clause_code TEXT NOT NULL,
                content TEXT NOT NULL,
                action_url TEXT,
                action_label TEXT,
                is_custom INTEGER DEFAULT 0,
                updated_at TEXT
            );
            """
        )
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

        cur = conn.execute("SELECT count(*) FROM university_policies")
        pol_count = cur.fetchone()[0]

        now = datetime.utcnow().isoformat()
        for p in DEFAULT_POLICIES:
            conn.execute(
                """
                INSERT OR IGNORE INTO university_policies (doc_id, category, title, clause_code, content, action_url, action_label, is_custom, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    p["doc_id"],
                    p["category"],
                    p["title"],
                    p["clause_code"],
                    p["content"],
                    p.get("action_url", "/forms"),
                    p.get("action_label", "View Policy"),
                    now,
                ),
            )
        conn.commit()

        cur = conn.execute("SELECT count(*) FROM university_policies")
        pol_count = cur.fetchone()[0]

        cur = conn.execute("SELECT count(*) FROM policy_fts")
        count = cur.fetchone()[0]

        if count < pol_count:
            conn.execute("DELETE FROM policy_fts")
            all_rows = conn.execute("SELECT doc_id, category, title, clause_code, content, action_url, action_label FROM university_policies").fetchall()
            for p in all_rows:
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
    def list_policies(cls) -> list[dict[str, Any]]:
        """List all university policies, including custom user-created/edited ones."""
        cls.initialize_fts_index()
        conn = get_connection()
        rows = conn.execute(
            "SELECT doc_id, category, title, clause_code, content, action_url, action_label, is_custom, updated_at "
            "FROM university_policies ORDER BY is_custom DESC, category ASC, title ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def get_policy(cls, doc_id: str) -> dict[str, Any] | None:
        """Fetch a specific policy ordinance by its document identifier."""
        cls.initialize_fts_index()
        conn = get_connection()
        row = conn.execute(
            "SELECT doc_id, category, title, clause_code, content, action_url, action_label, is_custom, updated_at "
            "FROM university_policies WHERE doc_id = ?",
            (doc_id.strip(),)
        ).fetchone()
        return dict(row) if row else None

    @classmethod
    def upsert_policy(
        cls,
        doc_id: str,
        category: str,
        title: str,
        clause_code: str,
        content: str,
        action_url: str = "/forms",
        action_label: str = "View Policy",
        is_custom: bool = True,
    ) -> dict[str, Any]:
        """Insert or update a policy ordinance and synchronize FTS5 index in real time."""
        cls.initialize_fts_index()
        conn = get_connection()
        now = datetime.utcnow().isoformat()
        clean_doc = doc_id.strip()
        clean_cat = category.strip()
        clean_title = title.strip()
        clean_code = clause_code.strip().upper()
        clean_content = content.strip()
        clean_url = (action_url or "/forms").strip()
        clean_label = (action_label or "View Policy").strip()

        conn.execute(
            """
            INSERT INTO university_policies (doc_id, category, title, clause_code, content, action_url, action_label, is_custom, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                category = excluded.category,
                title = excluded.title,
                clause_code = excluded.clause_code,
                content = excluded.content,
                action_url = excluded.action_url,
                action_label = excluded.action_label,
                is_custom = excluded.is_custom,
                updated_at = excluded.updated_at
            """,
            (clean_doc, clean_cat, clean_title, clean_code, clean_content, clean_url, clean_label, 1 if is_custom else 0, now)
        )
        # Real-time FTS5 virtual table sync
        conn.execute("DELETE FROM policy_fts WHERE doc_id = ?", (clean_doc,))
        conn.execute(
            """
            INSERT INTO policy_fts (doc_id, category, title, clause_code, content, action_url, action_label)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (clean_doc, clean_cat, clean_title, clean_code, clean_content, clean_url, clean_label)
        )
        conn.commit()
        return cls.get_policy(clean_doc)

    @classmethod
    def delete_policy(cls, doc_id: str) -> dict[str, Any]:
        """Delete custom policy or reset a modified default policy to original seed."""
        cls.initialize_fts_index()
        conn = get_connection()
        clean_doc = doc_id.strip()
        orig = next((p for p in DEFAULT_POLICIES if p["doc_id"] == clean_doc), None)
        if orig:
            now = datetime.utcnow().isoformat()
            conn.execute(
                """
                UPDATE university_policies SET
                    category = ?, title = ?, clause_code = ?, content = ?, action_url = ?, action_label = ?, is_custom = 0, updated_at = ?
                WHERE doc_id = ?
                """,
                (orig["category"], orig["title"], orig["clause_code"], orig["content"], orig.get("action_url", "/forms"), orig.get("action_label", "View Policy"), now, clean_doc)
            )
            conn.execute("DELETE FROM policy_fts WHERE doc_id = ?", (clean_doc,))
            conn.execute(
                """
                INSERT INTO policy_fts (doc_id, category, title, clause_code, content, action_url, action_label)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (orig["doc_id"], orig["category"], orig["title"], orig["clause_code"], orig["content"], orig.get("action_url", "/forms"), orig.get("action_label", "View Policy"))
            )
            conn.commit()
            return {"status": "reset", "message": f"Policy '{clean_doc}' reset to original default seed.", "policy": orig}
        else:
            conn.execute("DELETE FROM university_policies WHERE doc_id = ?", (clean_doc,))
            conn.execute("DELETE FROM policy_fts WHERE doc_id = ?", (clean_doc,))
            conn.commit()
            return {"status": "deleted", "message": f"Custom policy '{clean_doc}' deleted successfully."}

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
                        has_faculty_kw = any(kw in query.lower() for kw in ["faculty", "staff", "employee", "teacher", "prof", "phd supervisor"])
                        if not has_faculty_kw:
                            results.sort(key=lambda x: (1 if x.get("category") in ("HR & Staff", "HR & Faculty") else 0, x.get("score", 0)))
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
            "एडमिशन": "admission fresh student enrollment",
            "दाखिला": "admission fresh student enrollment",
            "प्रवेश": "admission fresh student enrollment",
            "naya admission": "fresh student admission",
            "new admission": "fresh student admission",
        }
        for k, v in hindi_map.items():
            if k in query or k in q_low:
                additions.append(v)
        if additions:
            return f"{query} {' '.join(additions)}"
        return query

    @classmethod
    def _is_policy_relevant_to_query(cls, query: str, policy: dict[str, Any]) -> bool:
        """Verify that the policy has genuine substantive lexical overlap with the query, preventing false-positive form dumps on generic words like 'semester' or 'course'."""
        STOP = {
            "what", "whats", "should", "i", "do", "does", "did", "after", "getting", "the", "a", "an", "this",
            "that", "these", "those", "from", "how", "can", "could", "you", "take", "me", "tell", "where", "is",
            "are", "was", "were", "be", "been", "being", "have", "has", "had", "having",
            "of", "to", "for", "in", "on", "at", "by", "with", "my", "your", "his", "her", "their", "our",
            "please", "want", "would", "like", "get", "downloading", "got", "need", "know", "about",
            "which", "we", "he", "she", "they", "them", "here", "there", "it", "its", "and", "or", "but",
            "not", "no", "dont", "don't", "ask", "asked", "kuch", "nahi", "kya", "kyun", "kaise", "hai", "hain",
            "batao", "bataao", "bataiye", "bata", "tatha", "aur", "chahiye", "karein", "karna", "kare", "hoga", "hogi"
        }
        GENERIC_META = {
            "student", "students", "university", "college", "campus", "department",
            "official", "documents", "document", "service", "services", "center",
            "kiosk", "desk", "portal", "system", "office", "section", "cell", "page",
            "screen", "window", "block", "room",
            "semester", "semesters", "sem", "course", "courses", "class", "classes",
            "subject", "subjects", "rule", "rules", "policy", "policies", "procedure", "procedures",
            "form", "forms", "application", "applications", "details", "info", "information",
            "guidelines", "guide", "process", "time", "date", "fee", "fees", "academic", "academics"
        }
        all_tokens = [w.lower() for w in re.sub(r"[^\w\s]", " ", query).split() if len(w) >= 3 and w.lower() not in STOP]
        substantive_tokens = [t for t in all_tokens if t not in GENERIC_META]
        check_tokens = substantive_tokens if substantive_tokens else all_tokens
        if not check_tokens:
            return False

        title_lower = policy.get("title", "").lower()
        content_lower = policy.get("content", "").lower()
        clause_code = policy.get("clause_code", "").lower()

        # Direct match in title or clause code with substantive tokens
        if any(t in title_lower or t in clause_code for t in check_tokens):
            return True

        # Content match requires at least TWO distinct substantive tokens of length >= 4
        matched_content_tokens = [t for t in check_tokens if len(t) >= 4 and t in content_lower]
        if len(matched_content_tokens) >= 2:
            return True

        return False

    @classmethod
    def _check_misconduct_or_bunk_query(cls, q_clean: str, q_lower: str) -> bool:
        """Detect inappropriate, misconduct, cheating, bunking, or proxy attendance inquiries."""
        # 1. Bunking & skipping classes
        bunk_patterns = [
            r"\bbunk\b", r"\bbunking\b", r"\bbunks\b",
            r"bunk kaise", r"kaise bunk", r"bunk kare", r"bunk mare", r"bunk maare", r"bunk marna", r"bunk marne",
            r"mass bunk", r"class bunk", r"college bunk", r"lecture bunk",
            r"skip class", r"skip classes", r"skip lecture", r"skip lectures",
            r"how to bunk", r"how to skip class", r"class kaise chhode", r"class chhod de",
            r"बंक", r"क्लास बंक", r"कॉलेज बंक"
        ]
        if any(re.search(pat, q_lower) for pat in bunk_patterns):
            return True

        # 2. Proxy attendance & fake presence
        proxy_patterns = [
            r"\bproxy\b", r"proxy attendance", r"proxy kaise", r"kaise proxy", r"proxy lagaye", r"proxy lagana",
            r"fake attendance", r"attendance cheat", r"attendance hack", r"attendance fraud",
            r"nakli attendance", r"jhoothi attendance", r"attendance kaise badhaye bina class",
            r"प्रॉक्सी"
        ]
        if any(re.search(pat, q_lower) for pat in proxy_patterns):
            return True

        # 3. Cheating, paper leak, copying
        cheat_patterns = [
            r"\bcheat\b", r"\bcheating\b", r"cheat in exam", r"cheat in exams", r"cheating kaise",
            r"exam me cheat", r"paper leak", r"leak paper", r"nakal kaise", r"nakal karna",
            r"copy kaise kare exam", r"chori kaise kare", r"pass kaise ho bina padhe cheat",
            r"नकल", r"चीटिंग"
        ]
        if any(re.search(pat, q_lower) for pat in cheat_patterns):
            return True

        # 4. Fake documents, forgery
        fake_doc_patterns = [
            r"fake medical", r"fake certificate", r"nakli medical", r"jhootha medical",
            r"forge signature", r"fake sign", r"fake doctor slip",
        ]
        if any(re.search(pat, q_lower) for pat in fake_doc_patterns):
            return True

        # 5. Harassment, troubling faculty/staff/students, disruption
        harass_patterns = [
            r"pareshaan\s+kaise", r"kaise\s+pareshaan", r"pareshan\s+kaise", r"kaise\s+pareshan",
            r"tang\s+kaise", r"kaise\s+tang", r"satana\s+kaise", r"pareshaan\s+kare", r"pareshan\s+kare",
            r"pareshaan\s+karna", r"pareshan\s+karna", r"pareshaan\s+karen", r"pareshan\s+karen",
            r"trouble\s+teacher", r"harass\s+teacher", r"disturb\s+teacher", r"annoy\s+teacher",
            r"trouble\s+faculty", r"harass\s+faculty", r"disturb\s+faculty",
            r"trouble\s+staff", r"harass\s+staff", r"trouble\s+professor", r"harass\s+professor",
            r"how\s+to\s+trouble", r"how\s+to\s+harass", r"how\s+to\s+annoy", r"how\s+to\s+disturb",
            r"teacher\s+ko\s+pareshaan", r"faculty\s+ko\s+pareshaan", r"staff\s+ko\s+pareshaan",
            r"professor\s+ko\s+pareshaan", r"teacher\s+ko\s+pareshan", r"faculty\s+ko\s+pareshan",
            r"staff\s+ko\s+pareshan", r"professor\s+ko\s+pareshan",
            r"ko\s+pareshaan", r"ko\s+pareshan", r"ko\s+tang",
            r"शिक्षक को परेशान", r"परेशान कैसे", r"तंग कैसे"
        ]
        if any(re.search(pat, q_lower) for pat in harass_patterns):
            return True

        # 6. Ragging, bribery, illegal acts
        misconduct_patterns = [
            r"ragging kaise", r"how to rag", r"\bbribe\b", r"rishwat", r"ghoos kaise",
        ]
        if any(re.search(pat, q_lower) for pat in misconduct_patterns):
            return True

        return False

    @classmethod
    def hybrid_guidance(
        cls,
        query: str,
        student_id: str | None = None,
        page_context: dict[str, Any] | None = None,
        language: str = "en-IN",
        history: list[dict[str, Any]] | None = None,
        is_staff: bool = False,
        staff_role: str | None = None,
    ) -> dict[str, Any]:
        """Synthesize zero-hallucination guidance combining live student profile, FTS5 policy clauses, ambient screen awareness, and optional Gemini AI synthesis."""
        conn = get_connection()

        # Determine staff status
        is_staff_user = bool(
            is_staff
            or (page_context and (page_context.get("is_staff") or "/staff" in str(page_context.get("route", "")).lower()))
        )
        staff_designation = staff_role or (page_context.get("staff_role") if page_context else None) or "Registrar Staff"

        # Check page context for public routes
        route_name = ""
        if page_context and isinstance(page_context, dict):
            route_name = str(page_context.get("route", "")).lower().strip()

        is_public_page = bool(route_name and route_name in ("/", "/services", "/login", "/welcome"))

        # Retrieve student record ONLY if authenticated, NOT on a public page, AND NOT a staff user
        effective_student_id = None if (is_staff_user or is_public_page) else student_id
        if not effective_student_id and page_context and isinstance(page_context, dict) and not is_staff_user and not is_public_page:
            effective_student_id = page_context.get("student_id")

        student: dict[str, Any] | None = None
        if not is_staff_user and not is_public_page and effective_student_id and str(effective_student_id).strip().upper() not in ("GUEST", "PUBLIC", "NONE", "NULL", ""):
            clean_sid = str(effective_student_id).strip().upper()
            cur = conn.execute(
                "SELECT id, name, course, branch, semester, attendance, cgpa, fee_status, fee_due FROM students WHERE UPPER(TRIM(id)) = ?",
                (clean_sid,),
            )
            row = cur.fetchone()
            if row:
                student = dict(row)

        is_authenticated = student is not None
        student_name = staff_designation if is_staff_user else ((student or {}).get("name", "").split()[0] if is_authenticated else "Guest")
        greeting_prefix = f"{student_name}, " if is_authenticated else (f"{staff_designation}, " if is_staff_user else "")
        attendance = float((student or {}).get("attendance", 75.0))

        q_lower = query.lower()
        q_clean = re.sub(r"[^\w\s\u0900-\u097F]", " ", q_lower).strip()
        words = q_clean.split()
        word_count = len(words)

        # =========================================================================
        # 00-SECURITY & PRIVACY GUARD: Student PII, Passwords, Mass Dumps
        # =========================================================================
        is_pii_query = (
            any(w in q_lower for w in [
                "stu001", "stu002", "stu003", "stu004", "stu005", "aisha", "aisha sharma", "rahul sharma", "other student", "another student",
                "private fee details", "display all student records", "all student records", "roll numbers in database",
                "reveal student", "password or hash", "student password", "reveal password"
            ])
            and any(k in q_lower for k in ["details", "records", "phone", "mobile", "password", "hash", "fee", "private", "display all", "reveal", "attendance", "cgpa", "account"])
            and not (is_authenticated and student and (str(student.get("id", "")).lower() in q_lower or (str(student.get("name", "")).lower().split()[0] in q_lower and "other" not in q_lower)))
        )
        if is_pii_query:
            pii_msg = (
                f"I am sorry, {student_name}, but I cannot disclose personal contact details, private financial records, or credentials of other students. "
                "Under university data privacy regulations and security ordinances, users are not authorized to view or disclose confidential credentials or records."
            )
            return {
                "answer": pii_msg,
                "domain": "Security & Data Privacy Guard",
                "citations": [DEFAULT_POLICIES[0]],
                "recommended_action": "Sign In" if not is_authenticated else "View My Profile",
                "action_url": "/login" if not is_authenticated else "/profile",
                "voice_speech_text": pii_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # =========================================================================
        # 00-ROLE-BASED PERSONAL RECORD ACCESS GUARD: Staff vs Authenticated Student vs Guest
        # =========================================================================
        is_personal_record_query = (
            any(p in q_clean or p in q_lower for p in [
                "my attendance", "meri attendance", "mera attendance", "mere attendance", "kitni attendance", "attendance kitni",
                "मेरी अटेंडेंस", "मेरा अटेंडेंस", "अटेंडेंस कितनी", "कितनी अटेंडेंस", "उपस्थिति कितनी", "मेरी उपस्थिति", "मेरा हाजिरी", "मेरी हाजिरी",
                "my fee", "my fees", "meri fee", "mera fee", "fees due", "fee due", "fee status", "kitni fee bachi", "baki fee",
                "मेरी फीस", "मेरा फीस", "फीस कितनी", "बकाया फीस", "फीस का स्टेटस", "कितनी फीस बाकी", "फीस ड्यू",
                "my cgpa", "mera cgpa", "my grade", "my grades", "mera grade", "my marks", "mera marks", "mere marks",
                "मेरा सीजीपीए", "मेरी सीजीपीए", "मेरे मार्क्स", "मेरा रिजल्ट", "मेरे अंक",
                "my status", "mera status", "my application", "meri application", "my withdrawal status", "mera withdrawal status",
                "मेरा स्टेटस", "मेरी एप्लीकेशन", "मेरा विड्रॉल", "विड्रॉल स्टेटस",
                "my refund status", "mera refund kitna", "my refund amount", "who am i", "my profile", "my account", "mera account",
                "open my account", "aisha s account", "aisha account", "my admit card", "mera admit card",
                "मेरा रिफंड", "मेरा अकाउंट", "मेरी प्रोफाइल", "मेरा एडमिट कार्ड"
            ])
            or (
                not is_authenticated
                and not is_staff_user
                and any(p in q_clean for p in [
                    "can i write semester exams with my current attendance",
                    "can i write exam with my attendance",
                    "can i give exam with my attendance",
                    "am i eligible for exam with my attendance",
                    "my clearance status",
                    "check my status",
                ])
            )
        )

        if not is_authenticated and not is_staff_user and is_personal_record_query:
            if language == "hi-IN":
                guard_ans = (
                    "आप वर्तमान में अतिथि (Guest) के रूप में UniAssist का उपयोग कर रहे हैं। "
                    "अपनी व्यक्तिगत उपस्थिति (Attendance), सीजीपीए, बकाया फीस या आवेदन स्थिति देखने के लिए कृपया अपनी छात्र आईडी (Student ID) से लॉगिन करें।"
                )
                guard_v = "आप वर्तमान में गेस्ट मोड में हैं। अपनी व्यक्तिगत उपस्थिति, फीस या आवेदन स्थिति देखने के लिए कृपया अपनी स्टूडेंट आईडी से लॉगिन करें।"
            elif language == "hi-Latn":
                guard_ans = (
                    "Aap filhaal Guest ke roop mein UniAssist use kar rahe hain. "
                    "Apni personal attendance, CGPA, fee dues ya application clearance status check karne ke liye please Student ID se sign in karein."
                )
                guard_v = "Aap Guest mode mein hain. Apni personal attendance, fee dues ya application status dekhne ke liye please Student ID se sign in karein."
            else:
                guard_ans = (
                    "You are currently browsing as a Guest. "
                    "To view your personal attendance percentage, CGPA, fee dues, or application clearance status, please sign in with your verified Student ID."
                )
                guard_v = "You are currently browsing as a Guest. Please sign in with your Student ID to view your personal records."

            return {
                "answer": guard_ans,
                "domain": "Student Account Authentication",
                "citations": [DEFAULT_POLICIES[0]],
                "recommended_action": "Sign In as Student",
                "action_url": "/login",
                "voice_speech_text": guard_v,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        if is_staff_user and is_personal_record_query:
            if language == "hi-IN":
                staff_personal_ans = (
                    f"प्रशासनिक अधिकारी ({staff_designation}) के रूप में, आपके पास स्टाफ एडमिन पोर्टल का अधिकार है। "
                    "किसी भी छात्र की व्यक्तिगत उपस्थिति, फीस स्थिति, या क्लीयरेंस रिकॉर्ड देखने के लिए कृपया स्टूडेंट रजिस्ट्री ('/staff/registry') में उनका रोल नंबर खोजें।"
                )
                staff_v = f"{staff_designation}, छात्रों की उपस्थिति या फीस देखने के लिए कृपया स्टूडेंट रजिस्ट्री में रोल नंबर सर्च करें।"
            elif language == "hi-Latn":
                staff_personal_ans = (
                    f"Administrative officer ({staff_designation}) ke roop me aapke paas Staff Portal ka access hai. "
                    "Kisi bhi student ki personal attendance, fee records, ya clearance dossier dekhne ke liye please Student Registry ('/staff/registry') me unka Roll Number search karein."
                )
                staff_v = f"{staff_designation}, students ki attendance ya fee records dekhne ke liye Student Registry me search karein."
            else:
                staff_personal_ans = (
                    f"As an administrative staff member ({staff_designation}), you have staff portal access. "
                    "To inspect any student's personal attendance, fee status, or clearance dossier, please search their Roll Number in the Student Registry (/staff/registry)."
                )
                staff_v = f"{staff_designation}, you can inspect student attendance and fees by searching their Roll Number in the Student Registry."

            return {
                "answer": staff_personal_ans,
                "domain": "Staff Administration",
                "citations": [],
                "recommended_action": "Open Student Registry",
                "action_url": "/staff/registry",
                "voice_speech_text": staff_v,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        if is_authenticated and not is_staff_user:
            if any(fq in q_clean for fq in ["my fee", "my fees", "meri fee", "mera fee", "fees due", "fee due", "fee status", "kitni fee bachi", "baki fee"]):
                due = float(student.get("fee_due") or 0)
                stat = student.get("fee_status", "Clear")
                if language == "hi-IN":
                    fee_ans = (
                        f"{student_name}, आपकी वर्तमान फीस स्थिति '{stat}' है और कुल बकाया राशि ₹{due:,.0f} है। "
                        "यदि कोई बकाया राशि है, तो आप स्टूडेंट डैशबोर्ड पर जाकर इसका ऑनलाइन भुगतान कर सकते हैं।"
                    )
                elif language == "hi-Latn":
                    fee_ans = (
                        f"{student_name}, aapka fee status '{stat}' hai aur outstanding dues ₹{due:,.0f} hain. "
                        "Dues clear karne ke liye aap Student Dashboard par online payment kar sakte hain."
                    )
                else:
                    fee_ans = (
                        f"{student_name}, your recorded fee status is '{stat}' with outstanding dues of INR {due:,.0f}. "
                        "You can review your fee ledger and complete payments directly on your Student Dashboard."
                    )
                return {
                    "answer": fee_ans,
                    "domain": "Fee Clearance & Accounts",
                    "citations": [DEFAULT_POLICIES[2]],
                    "recommended_action": "View Fee Ledger",
                    "action_url": "/dashboard",
                    "voice_speech_text": fee_ans,
                    "screen_instruction": None,
                    "highlight_target": None,
                    "engine": "UniAssist Policy Engine",
                }

            if any(cq in q_clean for cq in ["my cgpa", "mera cgpa", "my grade", "my grades", "mera grade", "my marks", "mera marks"]):
                cgpa_val = student.get("cgpa", "N/A")
                sem_val = student.get("semester", "N/A")
                course_val = student.get("course", "Degree Program")
                if language == "hi-IN":
                    cgpa_ans = (
                        f"{student_name}, आपका वर्तमान संचयी ग्रेड प्वाइंट औसत (CGPA) **{cgpa_val}** है "
                        f"({course_val}, सेमेस्टर {sem_val})। शैक्षणिक विवरण और मार्कशीट देखने के लिए डैशबोर्ड देखें।"
                    )
                elif language == "hi-Latn":
                    cgpa_ans = (
                        f"{student_name}, aapka current recorded CGPA **{cgpa_val}** hai "
                        f"({course_val}, Semester {sem_val}). Marksheets aur academic progress ke liye Dashboard check karein."
                    )
                else:
                    cgpa_ans = (
                        f"{student_name}, your current recorded CGPA is **{cgpa_val}** "
                        f"in {course_val} (Semester {sem_val}). You can review your detailed semester grade reports on your Dashboard."
                    )
                return {
                    "answer": cgpa_ans,
                    "domain": "Academic Records",
                    "citations": [DEFAULT_POLICIES[0]],
                    "recommended_action": "View Academic Records",
                    "action_url": "/dashboard",
                    "voice_speech_text": cgpa_ans,
                    "screen_instruction": None,
                    "highlight_target": None,
                    "engine": "UniAssist Policy Engine",
                }

        # =========================================================================
        # 00-DISCIPLINE: Institutional Misconduct, Bunking, Proxy & Cheating Guard
        # =========================================================================
        if cls._check_misconduct_or_bunk_query(q_clean, q_lower):
            is_harass = any(re.search(pat, q_lower) for pat in [
                r"pareshaan", r"pareshan", r"tang", r"satana",
                r"trouble", r"harass", r"annoy", r"disturb"
            ])
            if is_harass:
                if language == "hi-IN":
                    refusal_msg = (
                        f"मुझे क्षमा करें, {student_name}, मैं इस बारे में सहायता नहीं कर सकता (I am sorry, I cannot help with this)। "
                        "विश्वविद्यालय अनुशासन संहिता (Student Code of Conduct) के तहत किसी भी शिक्षक, कर्मचारी या छात्र को परेशान करना सख्त वर्जित और दंडनीय अपराध है। "
                        "UniAssist केवल आधिकारिक शैक्षणिक नियमों, उपस्थिति, परीक्षा और फॉर्मों में सहायता करता है।"
                    )
                    voice_text = "मुझे क्षमा करें, मैं इस बारे में सहायता नहीं कर सकता। विश्वविद्यालय अनुशासन संहिता के तहत शिक्षकों या कर्मचारियों को परेशान करना सख्त वर्जित है।"
                elif language == "hi-Latn":
                    refusal_msg = (
                        f"Sorry {student_name}, main is baare me help nahi kar sakta. "
                        "University Code of Conduct ke mutabiq teachers, faculty, staff ya fellow students ko pareshaan karna strictly prohibited aur punishable offence hai. "
                        "UniAssist keval official academic rules, attendance, exams aur forms me help provide karta hai."
                    )
                    voice_text = "Sorry, main is baare me help nahi kar sakta. University Code of Conduct ke mutabiq teachers ya staff ko pareshaan karna strictly prohibited hai."
                else:
                    refusal_msg = (
                        f"I am sorry, {student_name}, but I cannot assist with this request. "
                        "Under the University Student Code of Conduct and Disciplinary Ordinances, harassing, disturbing, or causing trouble to teachers, faculty members, staff, or fellow students is strictly prohibited and subject to disciplinary action or debarment. "
                        "UniAssist is strictly dedicated to assisting with verified university policies, examinations, and official forms."
                    )
                    voice_text = "I am sorry, but I cannot assist with this request. Harassing or troubling teachers or university staff is strictly prohibited under institutional discipline regulations."
            else:
                if language == "hi-IN":
                    refusal_msg = (
                        "माफ़ कीजिए, मैं इस बारे में सहायता नहीं कर सकता (Sorry, I can't help with this)। "
                        "विश्वविद्यालय अध्यादेश ORD-ACAD-7.2 के अनुसार प्रत्येक पंजीकृत पाठ्यक्रम में न्यूनतम 75% कक्षा उपस्थिति अनिवार्य है। "
                        "कक्षाएं बंक करना, प्रॉक्सी लगाना, या परीक्षा में अनुचित साधनों का उपयोग करना गंभीर अनुशासनहीनता है और इससे परीक्षा से निष्कासन (Debarment) हो सकता है।"
                    )
                    voice_text = "माफ़ कीजिए, मैं इस बारे में सहायता नहीं कर सकता। विश्वविद्यालय नियमावली के तहत 75% उपस्थिति अनिवार्य है। कक्षाएं बंक करना या प्रॉक्सी लगाना अनुशासनहीनता मानी जाती है।"
                elif language == "hi-Latn":
                    refusal_msg = (
                        "Sorry, I can't help with this. University regulations (Ordinance ORD-ACAD-7.2) ke mutabiq har registered course me minimum 75% attendance maintain karna mandatory hai. "
                        "Classes bunk karna, proxy attendance lagana, ya exam me cheating karna serious academic indiscipline maana jata hai aur isse student ko debar kiya ja sakta hai."
                    )
                    voice_text = "Sorry, I can't help with this. University regulations require minimum 75% attendance. Bunking classes or proxy attendance is considered academic indiscipline."
                else:
                    refusal_msg = (
                        "Sorry, I can't help with this. Under University Ordinance ORD-ACAD-7.2, students are strictly required to maintain a minimum of 75% attendance in every course. "
                        "Bunking lectures, proxy attendance, cheating in examinations, or falsifying medical certificates violates institutional academic discipline and can lead to immediate debarment."
                    )
                    voice_text = "Sorry, I can't help with this. University regulations mandate minimum 75% attendance. Skipping classes, proxy attendance, or academic misconduct is strictly prohibited."

            return {
                "answer": refusal_msg,
                "domain": "Institutional Discipline Guard",
                "citations": [DEFAULT_POLICIES[0]],
                "recommended_action": "View Attendance Policy (ORD-ACAD-7.2)",
                "action_url": "/forms",
                "voice_speech_text": voice_text,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # =========================================================================
        # 00. Conversational, Greetings, Small Talk, Negations & Cancellations Guard
        # =========================================================================
        q_clean = re.sub(r"[^\w\s]", " ", q_lower).strip()
        words = q_clean.split()
        word_count = len(words)

        # Check if user is replying to an interactive cross-question from previous turn
        if history:
            last_assistant_turn = ""
            for h in reversed(history):
                role = str(h.get("role", "")).lower()
                if role in ("assistant", "model", "bot", "counselor"):
                    last_assistant_turn = str(h.get("content") or h.get("text") or "").lower()
                    break

            if any(cq in last_assistant_turn for cq in [
                "looking to withdraw", "faculty member applying for leave", "faculty / staff member",
                "विड्रॉल और फीस रिफंड", "फैकल्टी/स्टाफ सदस्य हैं", "faculty/staff member hain"
            ]):
                if any(sw in q_clean for sw in ["student", "withdraw", "withdrawal", "refund", "1", "student_withdrawal", "छात्र", "विद्यार्थी"]) or q_clean in ("1", "option 1", "student", "i am a student", "i am student", "im a student", "im student"):
                    query = "program withdrawal and fee refund"
                    q_lower = query.lower()
                    q_clean = re.sub(r"[^\w\s]", " ", q_lower).strip()
                    words = q_clean.split()
                    word_count = len(words)
                elif any(fw in q_clean for fw in ["faculty", "staff", "form 23", "teacher", "2", "faculty_leave", "फैकल्टी", "अवकाश"]) or q_clean in ("2", "option 2", "faculty", "i am a faculty", "i am faculty", "im a faculty", "im faculty", "leave"):
                    query = "faculty leave application form 23"
                    q_lower = query.lower()
                    q_clean = re.sub(r"[^\w\s]", " ", q_lower).strip()
                    words = q_clean.split()
                    word_count = len(words)
                elif any(hw in q_clean for hw in ["hostel", "room", "vacate", "3", "hostel_vacate", "हॉस्टल"]) or q_clean in ("3", "option 3", "hostel", "hostel_vacate"):
                    query = "hostel clearance and room handover"
                    q_lower = query.lower()
                    q_clean = re.sub(r"[^\w\s]", " ", q_lower).strip()
                    words = q_clean.split()
                    word_count = len(words)
            elif any(tq in last_assistant_turn for tq in [
                "select which ticket status you would like to track",
                "grievance tickets on record",
                "choose from your existing tickets",
                "kaunse ticket ka status",
            ]):
                query = f"ticket status {query}"
                q_lower = query.lower()
                q_clean = re.sub(r"[^\w\s]", " ", q_lower).strip()
                words = q_clean.split()
                word_count = len(words)

        # A. Negations, Dismissals, and Cancellations ("I did not ask", "Maine nahi pucha", "kuch nahi", "stop", "cancel")
        is_negation_or_dismissal = (
            any(
                phrase in q_clean or phrase in query for phrase in [
                    "did not ask", "didnt ask", "not asking", "not ask", "never asked",
                    "maine nahi pucha", "maine ye nahi", "maine yeh nahi", "ye nahi pucha", "yeh nahi pucha",
                    "ye nahi", "yeh nahi", "not this", "wrong answer", "galat hai", "yeh galat hai", "ye galat hai",
                    "kuch nahi", "kuch nhi", "kuch nahi chahiye", "nothing", "nothing required",
                    "never mind", "nevermind", "no need", "koi zaroorat nahi", "koi jarurat nahi",
                    "nahi chahiye", "rehne do", "rehne de", "dont need", "don't need", "stop", "ruko",
                    "chhodo", "choro",
                    "नहीं पूछा", "यह नहीं पूछा", "मैंने नहीं पूछा", "मैंने यह नहीं पूछा", "कुछ नहीं", "नहीं चाहिए",
                    "गलत है", "यह गलत है", "रोको", "रुकिए", "बंद करो", "छोड़ो"
                ]
            )
            or (q_clean in ("cancel", "cancel it", "cancel that", "please cancel"))
            or (
                word_count <= 4 and any(w in words or w in query for w in ["nahi", "not", "no", "नहीं"]) and any(w in words or w in query for w in ["ask", "pucha", "kuch", "need", "chahiye", "bol", "bola", "पूछा", "कुछ", "चाहिए"])
            )
        ) and not any(w in q_clean for w in ["admission", "withdrawal", "course", "degree", "seat", "hostel", "form", "daakhila", "dakhila"])

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
            if is_staff_user:
                if language == "hi-IN":
                    greet_msg = (
                        f"नमस्ते {staff_designation}! मैं UniAssist, आपका विश्वविद्यालय प्रशासनिक AI परामर्शदाता (Counselor) हूँ। "
                        "स्टाफ एडमिन पोर्टल पर विड्रॉल कतार (Withdrawal Queue), डिजिटल नोटशीट्स, ओसीआर ऑडिट या क्लीयरेंस अप्रूवल में मैं आपकी क्या सहायता कर सकता हूँ?"
                    )
                elif language == "hi-Latn":
                    greet_msg = (
                        f"Namaste {staff_designation}! Main UniAssist Admin Counselor hoon. "
                        "Staff portal par pending withdrawal queue, digital notesheets, OCR audit ya clearance approvals me main aapki kya madad kar sakta hoon?"
                    )
                else:
                    greet_msg = (
                        f"Hello {staff_designation}! I am UniAssist, your Administrative AI Counselor. "
                        "How can I assist you with the pending withdrawal queue, digital notesheets, OCR document audit, or clearance gate approvals today?"
                    )
                return {
                    "answer": greet_msg,
                    "domain": "Staff Administration",
                    "citations": [],
                    "recommended_action": "Open Staff Admin Portal",
                    "action_url": "/staff",
                    "voice_speech_text": greet_msg,
                    "screen_instruction": None,
                    "highlight_target": None,
                    "engine": "UniAssist Policy Engine",
                }
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
            if is_staff_user:
                if language == "hi-IN":
                    ident_msg = (
                        f"मैं UniAssist हूँ, स्टाफ एडमिनिस्ट्रेशन एवं रजिस्ट्रार सेल का आधिकारिक AI परामर्शदाता। "
                        "मैं छात्र विड्रॉल कतार (Withdrawal Queue) की समीक्षा, क्लीयरेंस गेट्स (लाइब्रेरी/हॉस्टल/अकाउंट्स), डिजिटल नोटशीट्स, और अध्यादेश नियमों के अनुपालन में आपकी सहायता करता हूँ।"
                    )
                elif language == "hi-Latn":
                    ident_msg = (
                        f"Main UniAssist hoon, Staff Administration & Registrar Cell ka official AI counselor. "
                        "Main pending withdrawal review queue, clearance gates sign-off, digital notesheets, aur institutional ordinances audit me help karta hoon."
                    )
                else:
                    ident_msg = (
                        f"I am UniAssist, the official Administrative AI Counselor for Staff and Registrar Operations. "
                        "I assist staff with auditing student withdrawal queues, verifying digital clearance gates, managing digital notesheets, and reviewing institutional ordinances."
                    )
                return {
                    "answer": ident_msg,
                    "domain": "Staff Administration",
                    "citations": [],
                    "recommended_action": "Review Staff Queue",
                    "action_url": "/staff",
                    "voice_speech_text": ident_msg,
                    "screen_instruction": None,
                    "highlight_target": None,
                    "engine": "UniAssist Policy Engine",
                }
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
        is_math = (
            not any(w in q_lower for w in ["grv-", "ord-", "pol-", "proc-", "form", "ticket", "2024-", "2025-", "2026-", "2027-"])
            and bool(re.search(r'\b\d+\s*[\+\*\/]\s*\d+\b|\b\d+\s+\-\s+\d+\b', q_lower))
        ) or any(w in q_lower for w in [
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
        is_general_off_topic = any(w in q_lower for w in [
            "recipe", "cooking", "movie", "song", "lyrics", "weather today", "girlfriend", "boyfriend",
            "cricket match", "football match", "ipl score", "pubg", "minecraft", "free fire", "play a game",
            "write an essay", "who is elon musk", "who is narendra modi", "prime minister",
            "stock market", "crypto", "bitcoin", "tell me a joke", "tell a joke", "sing a song",
            "tell me a story", "capital of", "who invented", "chat with me", "are you human",
            "love you", "marry me", "dance for me"
        ])
        if is_math or is_coding or is_trivia or is_general_off_topic:
            if language == "hi-IN":
                refusal_msg = (
                    f"मुझे क्षमा करें, {student_name}, लेकिन मैं UniAssist विश्वविद्यालय कियोस्क परामर्शदाता (Counselor) हूँ। "
                    "मैं केवल विश्वविद्यालय अकादमिक नीतियों, उपस्थिति, फीस, परीक्षाओं, आधिकारिक फॉर्म और कैंपस प्रक्रियाओं में सहायता कर सकता हूँ। "
                    "विश्वविद्यालय से संबंधित किसी भी नियम या फॉर्म के बारे में बेझिझक पूछें।"
                )
            elif language == "hi-Latn":
                refusal_msg = (
                    f"Sorry {student_name}, main UniAssist Campus Counselor hoon. "
                    "Main keval university academic policies, attendance, fees, examinations, official forms, aur campus procedures me help kar sakta hoon. "
                    "University se related queries ke baare me poochiye."
                )
            else:
                refusal_msg = (
                    f"I am sorry, {student_name}, but I am the UniAssist University Kiosk Counselor. "
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
        # 00-Meta. Anti-Hallucination & Policy Meta Inquiries Guard
        # =========================================================================
        is_missing_rule_query = any(phrase in q_lower for phrase in [
            "cannot find in your records", "not in your records", "not present in the knowledge base",
            "not present in your knowledge base", "rule that you cannot find", "rule you don't know", "rule you dont know"
        ])
        if is_missing_rule_query:
            if "refund" in q_lower or "deadline" in q_lower:
                gap_msg = (
                    f"I am sorry, {student_name}, but I cannot verify a refund deadline for a policy that is not present in our official university knowledge base. "
                    "UniAssist only provides verified guidance based on published university ordinances and UGC regulations. Please consult the Registrar Office (Room 102) or Accounts Section for officially notified semester cut-off dates."
                )
            else:
                gap_msg = (
                    f"I am sorry, {student_name}, but I can only provide guidance on officially notified university ordinances and procedures documented in our knowledge base. "
                    "I cannot speculate or state a rule that is not present in official university records. If you require clarification on an unrecorded regulation, please contact the Registrar Office (Room 102)."
                )
            return {
                "answer": gap_msg,
                "domain": "Policy Guardrails",
                "citations": [],
                "recommended_action": "Browse Forms & Policies",
                "action_url": "/forms",
                "voice_speech_text": gap_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        is_guarantee_query = any(phrase in q_lower for phrase in [
            "can you guarantee", "guarantee that the university will approve", "guarantee my application", "guarantee approval"
        ])
        if is_guarantee_query:
            guar_msg = (
                f"I am sorry, {student_name}, but as an automated AI counselor, I cannot guarantee application approval. "
                "All university applications (including withdrawals, scholarship renewals, attendance condonations, and grievances) are subject to official verification, desk clearance, and final administrative approval by the competent authorities."
            )
            return {
                "answer": guar_msg,
                "domain": "Policy Guardrails",
                "citations": [],
                "recommended_action": "Check Status",
                "action_url": "/tracking",
                "voice_speech_text": guar_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        is_friend_vs_policy = (
            any(phrase in q_lower for phrase in [
                "my friend says", "friend says", "friend told me", "the policy says one thing but my friend says another"
            ])
            and not any(w in q_lower for w in ["seven days", "7 days", "100% refund", "hundred percent"])
        )
        if is_friend_vs_policy:
            fvp_msg = (
                f"{student_name}, official university policies, published ordinances, and UGC guidelines always take legal precedence over peer advice or rumors. "
                "Administrative processes (such as refunds, attendance condonation, and clearances) are governed strictly by notified rules and verified timelines."
            )
            return {
                "answer": fvp_msg,
                "domain": "Policy Guardrails",
                "citations": [],
                "recommended_action": "Browse Forms & Policies",
                "action_url": "/forms",
                "voice_speech_text": fvp_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        is_why_query = any(phrase in q_lower for phrase in [
            "why did you give that answer", "why did you say that", "why that answer", "source of this answer", "why did you give this answer"
        ])
        if is_why_query:
            why_msg = (
                f"{student_name}, my guidance is strictly derived from verified university ordinances (such as ORD-ACAD-7.2 for attendance, ORD-WTH-14.1 for withdrawal refunds, and UGC guidelines) "
                "and officially published institutional procedure workflows to ensure accurate, zero-hallucination assistance."
            )
            return {
                "answer": why_msg,
                "domain": "Policy Guardrails",
                "citations": [],
                "recommended_action": "Browse Forms & Policies",
                "action_url": "/forms",
                "voice_speech_text": why_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        is_attendance_correction = any(phrase in q_lower for phrase in [
            "attendance correction", "request an attendance correction", "correct my attendance", "attendance galat", "attendance mistake"
        ])
        if is_attendance_correction:
            att_corr_msg = (
                f"{student_name}, to request an attendance correction: "
                "1. Report the discrepancy to your course teacher or department academic coordinator within 3 working days of the class. "
                "2. Provide proof of presence (such as laboratory log entries, submitted tutorial work, or physical register sign-offs). "
                "3. Once verified, the course coordinator submits an official Attendance Rectification Slip to the Dean of Academic Affairs (Room 201) to update your live ERP attendance record."
            )
            return {
                "answer": att_corr_msg,
                "domain": "Academics",
                "citations": [{"doc_id": "POL-ACAD-01", "category": "Academics", "title": "Minimum Attendance Requirement & Correction", "clause_code": "ORD-ACAD-7.2"}],
                "recommended_action": "View Attendance Record",
                "action_url": "/dashboard",
                "voice_speech_text": att_corr_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        is_exam_schedule_query = any(phrase in q_lower for phrase in [
            "when are my semester examinations scheduled", "semester examination schedule", "examination schedule", "exam datesheet", "exam date sheet", "when are my exams"
        ])
        if is_exam_schedule_query:
            exam_sched_msg = (
                f"{student_name}, semester examinations are conducted as per the official Academic Calendar published by the Controller of Examinations. "
                "Detailed course-wise datesheets and room seating allocations are published on the Student Examination Portal (/exams) and departmental notice boards at least 15 days prior to examination commencement."
            )
            return {
                "answer": exam_sched_msg,
                "domain": "Examinations",
                "citations": [{"doc_id": "POL-EXAM-01", "category": "Examinations", "title": "Backpaper & Supplementary Examination Guidelines", "clause_code": "ORD-EXAM-12.1"}],
                "recommended_action": "View Exam Schedule",
                "action_url": "/exams",
                "voice_speech_text": exam_sched_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # =========================================================================
        # 00-ADMISSIONS: Fresh / New Student Admission Procedure & Guidelines
        # =========================================================================
        is_new_admission = (
            any(phrase in q_clean for phrase in [
                "new admission", "fresh admission", "admission procedure", "admission process",
                "how to take admission", "how to get admission", "procedure for new admission",
                "procedure for admission", "process for new admission", "steps for admission",
                "admission guidelines", "new student admission", "fresh student admission",
                "admission documents", "admission eligibility", "apply for admission",
                "admission kaise", "admission lene ka", "admission process kya hai",
                "admission ki prakriya", "daakhila", "dakhila"
            ])
            or (
                "admission" in q_clean
                and any(w in q_clean for w in ["procedure", "process", "new", "fresh", "apply", "steps", "guide", "guidelines", "rule", "rules", "how"])
                and not any(w in q_clean for w in ["withdraw", "withdrawal", "cancel", "cancellation", "refund"])
            )
            or (
                any(w in query for w in ["एडमिशन", "दाखिला", "प्रवेश"])
                and any(w in query for w in ["प्रक्रिया", "नया", "नये", "कैसे", "नियम", "दस्तावेज"])
                and not any(w in query for w in ["रद्द", "वापस", "रिफंड", "विड्रॉल"])
            )
        )
        if is_new_admission:
            adm_policy = next((p for p in DEFAULT_POLICIES if p["doc_id"] == "ORD-ADM-01"), DEFAULT_POLICIES[0])
            if language == "hi-IN":
                adm_ans = (
                    f"{student_name}, नए छात्र प्रवेश (Fresh Student Admission) की आधिकारिक 4-चरणीय प्रक्रिया:\n\n"
                    "1. ऑनलाइन पंजीकरण एवं मेरिट आवंटन: विश्वविद्यालय पोर्टल पर फॉर्म ADM-01 भरें और प्रवेश परीक्षा स्कोर/12वीं के अंक दर्ज करें।\n"
                    "2. दस्तावेज सत्यापन: मूल 10वीं/12वीं अंकपत्र, स्थानांतरण प्रमाण पत्र (TC), माइग्रेशन, चरित्र प्रमाण पत्र, और 4 पासपोर्ट फोटो के साथ प्रवेश निदेशालय (कमरा 101, केंद्रीय ब्लॉक) में सत्यापन कराएं।\n"
                    "3. फीस भुगतान: प्रथम सेमेस्टर शैक्षणिक शुल्क और प्रतिदेय सुरक्षा जमा (INR 10,000) ऑनलाइन ईआरपी या लेखा काउंटर (कमरा 14) पर जमा करें।\n"
                    "4. बायोमेट्रिक एवं पहचान पत्र: आईटी सेल (कमरा 105) में बायोमेट्रिक आरएफआईडी छात्र पहचान पत्र और आधिकारिक एलएमएस लॉगिन क्रेडेंशियल प्राप्त करें।"
                )
                voice_text = f"{student_name}, नए प्रवेश के लिए फॉर्म ADM-01 भरें, कमरा 101 में दस्तावेज सत्यापित कराएं, और फीस जमा करके बायोमेट्रिक आईडी प्राप्त करें।"
            elif language == "hi-Latn":
                adm_ans = (
                    f"{student_name}, new student admission ki official 4-step procedure:\n\n"
                    "1. Online Registration & Merit Allotment: University admissions portal par Form ADM-01 bharein aur qualifying entrance scorecard upload karein.\n"
                    "2. Document Verification Dossier: Original 10th & 12th marksheets, Transfer Certificate (TC), Migration Certificate, aur 4 passport photos lekar Directorate of Admissions (Room 101, Central Block) me physical verification karayein.\n"
                    "3. Fee Payment: First semester tuition fee aur refundable caution deposit (INR 10,000) online ERP gateway ya Accounts Counter (Room 14) par deposit karein.\n"
                    "4. Biometric RFID ID & LMS: IT Center (Room 105) se biometric student ID card aur university email credentials collect karein."
                )
                voice_text = f"{student_name}, new admission ke liye Form ADM-01 submit karein, Room 101 me verification karayein, aur fee deposit karke biometric ID lein."
            else:
                adm_ans = (
                    f"{student_name}, here is the official 4-stage procedure for Fresh Student Admission & Enrollment:\n\n"
                    "1. Online Registration & Merit Allotment: Submit the Admission Application (Form ADM-01) with academic credentials and qualifying entrance exam rank/scores (JEE/CUET/State CET).\n"
                    "2. Document Verification Dossier: Present original 10th and 12th marksheets, Transfer Certificate (TC), Migration Certificate, Character Certificate, and 4 passport-size photographs at the Directorate of Admissions (Room 101, Central Block).\n"
                    "3. Fee Payment & Provisional Enrollment: Deposit the first-semester academic fee and refundable caution deposit (INR 10,000) online via the ERP payment gateway or offline at Accounts Counter (Room 14).\n"
                    "4. Biometric ID Card & LMS Activation: Report to IT Center (Room 105) for biometric RFID student smart identity card generation and university LMS email credentials."
                )
                voice_text = f"{student_name}, the procedure for new admission involves online registration via Form ADM-01, document verification at Room 101, fee payment, and biometric ID card issuance."

            return {
                "answer": adm_ans,
                "domain": "Admissions & Enrollment",
                "citations": [adm_policy],
                "recommended_action": "Download Form ADM-01 (Admission)",
                "action_url": "/forms",
                "voice_speech_text": voice_text,
                "screen_instruction": None,
                "highlight_target": "Download Form ADM-01 (Admission)",
                "engine": "UniAssist Policy Engine",
            }

        # A01: Attendance requirement
        is_attendance_requirement = (
            any(w in q_lower for w in ["attendance requirement", "minimum attendance", "attendance cutoff", "attendance criteria", "attendance policy", "attendance for my course"])
            and not any(w in q_lower for w in ["below", "shortage", "condonation", "less than", "kam", "correction", "गलत", "कम", "scholarship", "scholarships", "छात्रवृत्ति", "स्कॉलरशिप", "cgpa", "renewal"])
        )
        if is_attendance_requirement:
            att_req_msg = (
                f"Under University Ordinance ORD-ACAD-7.2, every student must maintain a minimum attendance of 75% in each registered course to be eligible to appear in End Term Semester Examinations. "
                f"A 25% margin is permitted for personal contingencies. Your current recorded attendance is {attendance:.1f}%, which meets eligibility requirements."
            )
            return {
                "answer": att_req_msg,
                "domain": "Academics",
                "citations": [DEFAULT_POLICIES[0]],
                "recommended_action": "View Attendance Policy (ORD-ACAD-7.2)",
                "action_url": "/forms",
                "voice_speech_text": att_req_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A02: Below attendance requirement
        is_below_attendance = (
            ("attendance" in q_lower or "उपस्थिति" in q_lower)
            and any(w in q_lower for w in ["below", "shortage", "less than", "kam", "debar", "कम", "गिर जाए", "कम हो जाए"])
            and not any(w in q_lower for w in ["correction", "galat", "mistake", "theek"])
        )
        if is_below_attendance:
            if is_staff_user:
                staff_att_msg = (
                    f"{staff_designation}, administrative guidelines under Attendance Ordinance ORD-ACAD-7.2:\n\n"
                    "1. **75% Mandatory Cutoff**: Students must maintain a minimum 75% attendance for semester exam eligibility.\n"
                    "2. **Dean's Condonation (60.0% to 74.9%)**: Deans may grant medical/representation condonation upon verification of Form AC-04.\n"
                    "3. **Compulsory Debarment (<60%)**: Attendance below 60.0% requires compulsory debarment with zero exemption allowed.\n"
                    "4. **Staff Roster Audit**: Verify medical dossiers, audit debarment lists, and manage student rosters via the Staff Portal (/staff)."
                )
                return {
                    "answer": staff_att_msg,
                    "domain": "Academics",
                    "citations": [DEFAULT_POLICIES[0], DEFAULT_POLICIES[1]],
                    "recommended_action": "Staff Admin Portal",
                    "action_url": "/staff",
                    "voice_speech_text": f"{staff_designation}, Ordinance ORD-ACAD-7.2 requires 75% attendance. Condonation applies between 60% and 74.9%. Debarment below 60%. Audit rosters on the Staff Portal.",
                    "screen_instruction": None,
                    "highlight_target": None,
                    "engine": "UniAssist Policy Engine",
                }
            below_att_msg = (
                f"Under University Ordinance ORD-ACAD-7.2, if your attendance falls below the mandatory 75% threshold:\n"
                "1. Attendance between 60.0% and 74.9%: You may apply for Dean's Attendance Condonation (Form AC-04) by submitting authentic medical certificates or official university representation letters at least 10 working days prior to examinations.\n"
                "2. Attendance below 60.0%: Condonation is strictly impermissible. You will be debarred from taking end-term semester exams for that course and must repeat the course during the summer term or next academic cycle."
            )
            return {
                "answer": below_att_msg,
                "domain": "Academics",
                "citations": [DEFAULT_POLICIES[0], DEFAULT_POLICIES[1]],
                "recommended_action": "Download Form AC-04 (Condonation)",
                "action_url": "/forms",
                "voice_speech_text": below_att_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A03: Medical leave application
        is_medical_leave = any(w in q_lower for w in [
            "medical leave", "apply for a medical leave", "apply for medical leave", "sick leave", "hospital leave"
        ]) and not any(w in q_lower for w in ["faculty", "staff", "form 23"])
        if is_medical_leave:
            med_msg = (
                f"Under University Ordinance ORD-ACAD-7.2, to apply for medical leave and attendance condonation:\n"
                "1. Download Form AC-04 (Attendance Condonation Application) from '/forms'.\n"
                "2. Attach government hospital OPD slips, medical prescription, and a registered physician fitness certificate.\n"
                "3. Submit the completed application dossier to the Dean of Academic Affairs (Room 201) within 3 working days of returning to campus."
            )
            return {
                "answer": med_msg,
                "domain": "Academics",
                "citations": [DEFAULT_POLICIES[1]],
                "recommended_action": "Download Form AC-04 (Condonation)",
                "action_url": "/forms",
                "voice_speech_text": med_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A06: Download examination admit card
        is_admit_card_download = any(w in q_lower for w in [
            "download my examination admit card", "download admit card", "download hall ticket",
            "where can i download my admit card", "get admit card", "admit card download", "download my admit card"
        ])
        if is_admit_card_download:
            admit_dl_msg = (
                f"You can download your Examination Admit Card directly from the Student ERP Portal under the 'Academic' tab -> 'Examination Hall Ticket' or via the Examination Portal at '/exams'. "
                "Admit cards are released 7 calendar days before semester examinations commence for all students who have cleared semester fee dues and meet the 75% attendance requirement."
            )
            return {
                "answer": admit_dl_msg,
                "domain": "Examinations",
                "citations": [DEFAULT_POLICIES[4]],
                "recommended_action": "Open Examination Portal",
                "action_url": "/exams",
                "voice_speech_text": admit_dl_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A07: Error on admit card
        is_admit_card_error = (
            ("admit card" in q_lower or "hall ticket" in q_lower)
            and any(w in q_lower for w in ["error", "mistake", "wrong", "correction", "discrepancy", "galat"])
        )
        if is_admit_card_error:
            admit_err_msg = (
                f"If there is an error on your admit card (such as misspelled name, incorrect course code, wrong photograph, or missing subject):\n"
                "1. Immediately report to the Examination Cell (Room 110, Admin Block) at least 3 working days prior to examination commencement.\n"
                "2. Present your physical Student ID card, semester fee payment receipt, and a written discrepancy memo.\n"
                "3. The Examination Controller will verify records and issue a rectified hall ticket on the spot."
            )
            return {
                "answer": admit_err_msg,
                "domain": "Examinations",
                "citations": [DEFAULT_POLICIES[4]],
                "recommended_action": "Visit Examination Cell (Room 110)",
                "action_url": "/exams",
                "voice_speech_text": admit_err_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A08: Revaluation of marks
        is_revaluation = (
            any(w in q_lower for w in [
                "revaluation", "re-evaluation", "rechecking", "scrutiny of marks", "revaluation of my marks", "re-checking"
            ])
            and not any(w in q_lower for w in ["portal", "show me", "take me", "navigate to", "open the", "go to", "where do i submit", "what documents"])
        )
        if is_revaluation:
            reval_msg = (
                f"To apply for revaluation or rechecking of marks:\n"
                "1. Download Form EX-03 (Re-evaluation & Scrutiny Application, PROC-FORM-27) from '/forms'.\n"
                "2. Submit the form at Examination Cell Window 3 within 15 calendar days of official result declaration.\n"
                "3. The fee is INR 500 per paper for re-totalling and INR 750 per paper for full answer book re-evaluation. Revaluation results are announced within 21 working days."
            )
            return {
                "answer": reval_msg,
                "domain": "Examinations",
                "citations": [DEFAULT_POLICIES[4]],
                "recommended_action": "Download Form EX-03 (Re-evaluation)",
                "action_url": "/forms",
                "voice_speech_text": reval_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A09: Supplementary / backpaper examination
        is_supplementary = any(w in q_lower for w in [
            "apply for a supplementary examination", "apply for supplementary", "apply for backpaper",
            "supplementary exam application", "backpaper application"
        ])
        if is_supplementary:
            supp_msg = (
                f"Under University Ordinance ORD-EXAM-12.1, to apply for supplementary backpaper examinations:\n"
                "1. Download Form EX-02 (Supplementary Examination Form) from '/forms'.\n"
                "2. Submit the form within 14 calendar days of grade sheet publication along with an exam fee of INR 1,500 per registered subject at the Examination Cell (Room 110).\n"
                "3. Supplementary examinations are conducted 30 days after regular semester results are declared."
            )
            return {
                "answer": supp_msg,
                "domain": "Examinations",
                "citations": [DEFAULT_POLICIES[4]],
                "recommended_action": "Download Form EX-02 (Backpaper)",
                "action_url": "/forms",
                "voice_speech_text": supp_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A10: Duplicate marksheet
        is_duplicate_marksheet = any(w in q_lower for w in [
            "duplicate marksheet", "duplicate grade sheet", "request a duplicate marksheet", "lost marksheet", "lost my marksheet"
        ])
        if is_duplicate_marksheet:
            dup_msg = (
                f"To request a duplicate marksheet or grade report:\n"
                "1. Download Form AC-07 (Application for Duplicate Marksheet / Transcript, PROC-FORM-19) from '/forms'.\n"
                "2. Attach a copy of the police lost report (NCR/FIR) or notarized indemnity affidavit, plus your student ID proof.\n"
                "3. Pay the duplicate certificate fee of INR 500 at the Accounts Counter and submit the completed file at Registrar Office Window 2. Issuance SLA is 7 working days."
            )
            return {
                "answer": dup_msg,
                "domain": "Academics",
                "citations": [DEFAULT_POLICIES[0]],
                "recommended_action": "Download Form AC-07 (Duplicate Marksheet)",
                "action_url": "/forms",
                "voice_speech_text": dup_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A11: Apply for scholarship
        is_scholarship_apply = (
            any(w in q_lower for w in ["apply for a scholarship", "apply for scholarship", "scholarship application", "how do i get a scholarship"])
            and not any(w in q_lower for w in ["status", "check", "track"])
        )
        if is_scholarship_apply:
            sch_msg = (
                f"To apply for university scholarships and financial aid:\n"
                "1. Visit the Scholarships Portal at '/scholarship' or download Form 14 (Scholarship Application Form) from '/forms'.\n"
                "2. Merit scholarships require maintaining a minimum CGPA of 8.0 with no standing backpapers. Need-based scholarships require verified family income certificates under INR 2.5 LPA.\n"
                "3. Submit the completed application with academic transcripts and income proof to the Dean of Student Welfare (DSW Office, Ground Floor) by September 30."
            )
            return {
                "answer": sch_msg,
                "domain": "Scholarships",
                "citations": [],
                "recommended_action": "Open Scholarships Portal",
                "action_url": "/scholarship",
                "voice_speech_text": sch_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A12: Check status of scholarship
        is_scholarship_status = any(w in q_lower for w in [
            "status of my scholarship", "check scholarship status", "scholarship status", "where can i check the status of my scholarship"
        ])
        if is_scholarship_status:
            sch_stat_msg = (
                f"You can track your scholarship application status directly online on the Scholarships Portal at '/scholarship' or by visiting the Dean of Student Welfare (DSW) Scholarship Cell at Room 104, Admin Block. "
                "Please have your Student ID or scholarship application acknowledgement receipt ready."
            )
            return {
                "answer": sch_stat_msg,
                "domain": "Scholarships",
                "citations": [],
                "recommended_action": "Open Scholarships Portal",
                "action_url": "/scholarship",
                "voice_speech_text": sch_stat_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A13: Update address in records
        is_address_update = (
            ("address" in q_lower or "पता" in q_lower)
            and any(w in q_lower for w in ["update", "change", "modify", "correction", "records"])
        )
        if is_address_update:
            addr_msg = (
                f"To update your permanent or correspondence address in university records:\n"
                "1. Download Form PROC-FORM-21 (Student Record Rectification Form) from '/forms'.\n"
                "2. Attach valid self-attested government address proof (Aadhaar Card, Passport, Voter ID, or Utility Bill).\n"
                "3. Submit the form to the Registrar Office (Window 1, Ground Floor). Changes are verified and updated in your official ERP profile within 3 working days."
            )
            return {
                "answer": addr_msg,
                "domain": "Student Records",
                "citations": [],
                "recommended_action": "Download Form PROC-FORM-21",
                "action_url": "/forms",
                "voice_speech_text": addr_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A14: Change registered phone number
        is_phone_update = (
            ("phone" in q_lower or "mobile" in q_lower or "contact number" in q_lower)
            and any(w in q_lower for w in ["change", "update", "registered", "modify"])
        )
        if is_phone_update:
            phone_msg = (
                f"To change your registered mobile number for university ERP and SMS alerts:\n"
                "1. Visit the Registrar Office (Room 102) or the Campus IT Helpdesk in person.\n"
                "2. Present your physical Student ID card for in-person identity verification.\n"
                "3. An instant OTP verification will be sent to your new mobile number to authenticate ownership, after which your student record is updated immediately."
            )
            return {
                "answer": phone_msg,
                "domain": "Student Records",
                "citations": [],
                "recommended_action": "Visit Registrar Office (Room 102)",
                "action_url": "/services",
                "voice_speech_text": phone_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A15: Apply for hostel room
        is_hostel_apply = (
            ("hostel" in q_lower or "हॉस्टल" in q_lower)
            and any(w in q_lower for w in ["apply for a hostel room", "apply for hostel", "hostel room allotment", "hostel application", "hostel admission", "hostel room"])
            and not any(w in q_lower for w in ["vacate", "handover", "clearance", "leave", "chhodna", "khali"])
        )
        if is_hostel_apply:
            hostel_msg = (
                f"To apply for hostel accommodation on campus:\n"
                "1. Download Form PROC-FORM-12 (Hostel Admission & Room Allotment Form) from '/forms'.\n"
                "2. Attach your semester fee receipt, 2 passport-size photographs, and signed parental undertaking.\n"
                "3. Submit the application to the Chief Warden Office (Hostel Affairs Desk). Room allotment is granted based on residential distance and academic merit before semester commencement."
            )
            return {
                "answer": hostel_msg,
                "domain": "Hostel Affairs",
                "citations": [DEFAULT_POLICIES[3]],
                "recommended_action": "Download Form PROC-FORM-12",
                "action_url": "/forms",
                "voice_speech_text": hostel_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A16: Lost something on campus (Lost and Found)
        is_lost_and_found = (
            any(w in q_lower for w in [
                "lose something", "lost something", "lost and found", "lost item", "found item", "lost my", "kuch kho gaya"
            ])
            and not any(w in q_lower for w in ["offset", "caution", "deposit", "fine", "200", "withdrawal", "refund"])
        )
        if is_lost_and_found:
            lost_msg = (
                f"If you have lost any personal property (such as ID cards, bags, electronics, or books) on campus:\n"
                "1. Immediately report the loss to the Central Security Office / Lost & Found Desk located at the Admin Block Ground Floor (Security Control Room).\n"
                "2. Provide a description of the item, approximate time, and last known location to be logged in the Campus Lost & Found Register.\n"
                "3. You may also check the active Lost & Found bulletin board or file an inquiry via the Grievance Desk at '/chat'."
            )
            return {
                "answer": lost_msg,
                "domain": "Campus Security",
                "citations": [],
                "recommended_action": "Visit Security Control Room",
                "action_url": "/chat",
                "voice_speech_text": lost_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A17: Access to university library
        is_library_access = (
            ("library" in q_lower or "पुस्तकालय" in q_lower)
            and any(w in q_lower for w in ["access", "entry", "membership", "get access to the university library", "how can i get access"])
            and not any(w in q_lower for w in ["fine", "penalty", "due"])
        )
        if is_library_access:
            lib_msg = (
                f"To access the Central University Library:\n"
                "1. Tap your active RFID-enabled Student ID Card at the Library Gate 1 turnstiles.\n"
                "2. Library membership is automatically activated upon student enrollment. Undergraduate students can borrow up to 4 books for 14 days; postgraduate students up to 6 books for 21 days.\n"
                "3. The Central Library is open from 8:00 AM to 10:00 PM on weekdays, and 9:00 AM to 5:00 PM on weekends and examination periods."
            )
            return {
                "answer": lib_msg,
                "domain": "Library Services",
                "citations": [DEFAULT_POLICIES[2]],
                "recommended_action": "View Library Gate 1",
                "action_url": "/services",
                "voice_speech_text": lib_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A18: Library account incorrect fine
        is_library_fine = (
            ("library" in q_lower or "पुस्तकालय" in q_lower)
            and any(w in q_lower for w in ["fine", "penalty", "charge", "dues"])
            and any(w in q_lower for w in ["incorrect", "wrong", "error", "dispute", "mistake", "galat", "what should i do"])
        )
        if is_library_fine:
            lib_fine_msg = (
                f"If your library account displays an incorrect fine or overdue fee:\n"
                "1. Visit the Library Circulation Counter (Gate 1) with your Student ID card and book accession numbers.\n"
                "2. Request the duty librarian to cross-reference the physical accession return register and book RFID scan logs for rectification.\n"
                "3. If verified, the librarian will issue a Fine Correction Slip to clear the dues in the KOHA Library ERP system immediately."
            )
            return {
                "answer": lib_fine_msg,
                "domain": "Library Services",
                "citations": [DEFAULT_POLICIES[2]],
                "recommended_action": "Visit Library Circulation Desk",
                "action_url": "/services",
                "voice_speech_text": lib_fine_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A19: Placement office location
        is_placement_office = any(w in q_lower for w in [
            "placement office", "corporate resource centre", "training and placement", "placement cell", "find the university's placement office"
        ])
        if is_placement_office:
            crc_msg = (
                f"The Corporate Resource Centre (CRC) / Training & Placement Office is located on the 2nd Floor of CRC Block 3, Room 205. "
                "The office is open Monday through Friday from 9:30 AM to 5:00 PM. You can also reach the placement team via email at placement@university.edu or check campus recruitment drives on the Student Portal."
            )
            return {
                "answer": crc_msg,
                "domain": "Career Services",
                "citations": [],
                "recommended_action": "Visit CRC Block 3 Room 205",
                "action_url": "/services",
                "voice_speech_text": crc_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # A20: Official campus rules / ordinances
        is_official_rules = any(w in q_lower for w in [
            "official campus rules", "campus rules", "university rules", "official rules", "where can i find the official campus rules"
        ])
        if is_official_rules:
            rules_msg = (
                f"All official campus rules, academic ordinances, examination bylaws, and student code of conduct regulations are available on the UniAssist portal under Forms & Policies at '/forms'. "
                "Official printed copies of the Student Handbook and Ordinances are also maintained at the Registrar Office (Room 102) and Dean of Student Welfare (DSW) Office."
            )
            return {
                "answer": rules_msg,
                "domain": "University Ordinances",
                "citations": [DEFAULT_POLICIES[0]],
                "recommended_action": "Browse Forms & Policies",
                "action_url": "/forms",
                "voice_speech_text": rules_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # =========================================================================
        # 00-AI & POLICY VERIFICATION HANDLERS (AI02 - AI17)
        # =========================================================================

        # AI02: Summarize withdrawal in 3 points
        is_wth_3_points = (
            any(w in q_lower for w in ["three points", "3 points", "summarize the withdrawal", "summarize withdrawal"])
            and any(w in q_lower for w in ["withdrawal", "withdraw"])
        )
        if is_wth_3_points:
            summary_3_msg = (
                f"Here is the official university withdrawal procedure summarized in 3 points:\n"
                "1. Application: Download and submit Form PROC-FORM-08 with your original admission letter and student ID card.\n"
                "2. 4-Desk Clearance: Complete digital No-Dues clearance across Department HOD, Central Library, Hostel Warden, and Accounts.\n"
                "3. Final Verification & Refund: Submit the completed dossier to Registrar Office Window 2; tuition fee refund is processed per UGC sliding slabs and caution deposit is refunded 100%."
            )
            return {
                "answer": summary_3_msg,
                "domain": "Withdrawal",
                "citations": [DEFAULT_POLICIES[5]],
                "recommended_action": "Open Withdrawal Cockpit",
                "action_url": "/withdrawal",
                "voice_speech_text": summary_3_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI03: Simple Hindi withdrawal
        is_wth_hindi = (
            any(w in q_lower for w in ["hindi", "हिन्दी"])
            and any(w in q_lower for w in ["withdrawal", "withdraw", "procedure", "same procedure", "विड्रॉल", "प्रक्रिया"])
        )
        if is_wth_hindi:
            hi_wth_msg = (
                f"विश्वविद्यालय विड्रॉल (प्रवेश निरस्तीकरण) की सरल प्रक्रिया:\n"
                "1. आवेदन: UniAssist पोर्टल ('/forms') से Form PROC-FORM-08 डाउनलोड करें और भरें।\n"
                "2. 4-काउंटर नो-ड्यूज: अपने विभाग (HOD), केंद्रीय पुस्तकालय, हॉस्टल वार्डन, और लेखा विभाग से डिजिटल नो-ड्यूज क्लियरेंस प्राप्त करें।\n"
                "3. अंतिम जमा एवं रिफंड: पूरा फॉर्म रजिस्ट्रार कार्यालय (कमरा 102, विंडो 2) में जमा करें। यूजीसी नियमों के अनुसार आपकी फीस का रिफंड और 100% कॉशन डिपॉजिट सीधे आपके बैंक खाते में भेजा जाएगा।"
            )
            return {
                "answer": hi_wth_msg,
                "domain": "Withdrawal",
                "citations": [DEFAULT_POLICIES[5]],
                "recommended_action": "विड्रॉल पोर्टल खोलें",
                "action_url": "/withdrawal",
                "voice_speech_text": hi_wth_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI04: Explain to first-year student
        is_wth_first_year = (
            any(w in q_lower for w in ["first year", "first-year", "fresher"])
            and any(w in q_lower for w in ["withdrawal", "withdraw", "procedure"])
        )
        if is_wth_first_year:
            fy_msg = (
                f"Welcome to UniAssist! If you are a first-year student looking to withdraw from your course, here is how the process works in simple steps:\n"
                "1. First, download Form PROC-FORM-08 from our Forms Catalog at '/forms'.\n"
                "2. Next, obtain signed No-Dues clearance from your Department Coordinator, the Library, and the Hostel Office to confirm no books or fees are pending.\n"
                "3. Finally, submit the form with your fee receipt at Registrar Office Window 2. Your tuition refund is calculated based on UGC timelines, and your 100% caution deposit will be credited to your bank account."
            )
            return {
                "answer": fy_msg,
                "domain": "Withdrawal",
                "citations": [DEFAULT_POLICIES[5]],
                "recommended_action": "Download Form PROC-FORM-08",
                "action_url": "/forms",
                "voice_speech_text": fy_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI06: Policy not present in knowledge base
        is_not_present_kb = any(w in q_lower for w in [
            "not present in the knowledge base", "not in the knowledge base", "not present in your knowledge base", "policy not present"
        ])
        if is_not_present_kb:
            kb_gap_msg = (
                f"I am sorry, {student_name}, but I cannot verify a refund deadline for a policy that is not present in our official university knowledge base. "
                "UniAssist only provides verified guidance based on published university ordinances and UGC regulations. Please consult the Registrar Office (Room 102) or Accounts Section for officially notified calendar dates."
            )
            return {
                "answer": kb_gap_msg,
                "domain": "Policy Guardrails",
                "citations": [],
                "recommended_action": "Browse Forms & Policies",
                "action_url": "/forms",
                "voice_speech_text": kb_gap_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI07: Exact refund amount disclaimer
        is_exact_refund_amount = (
            any(w in q_lower for w in ["exact amount", "exact refund", "how much exact", "exact rupees"])
            and any(w in q_lower for w in ["refund", "receive"])
        )
        if is_exact_refund_amount:
            exact_amt_msg = (
                f"I am sorry, {student_name}, but as an automated AI counselor, I cannot calculate or quote an exact rupee refund amount without access to your verified fee receipts and formal withdrawal application timestamp. "
                "Refund amounts depend on the applicable UGC percentage slab and fee component deductions (caution deposits are 100% refundable, while exam fees and admission processing charges may vary). Please submit Form PROC-FORM-08 at Accounts Section Window 4 for an audited calculation."
            )
            return {
                "answer": exact_amt_msg,
                "domain": "Policy Guardrails",
                "citations": [DEFAULT_POLICIES[5]],
                "recommended_action": "Open Withdrawal Cockpit",
                "action_url": "/withdrawal",
                "voice_speech_text": exact_amt_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI08: Which office handles withdrawal verification
        is_wth_office = (
            any(w in q_lower for w in ["which office", "who handles", "responsible office"])
            and any(w in q_lower for w in ["withdrawal", "verification"])
        )
        if is_wth_office:
            office_msg = (
                f"The Academic Section of the Registrar Office (Room 102, Window 2) is the designated authority that handles final withdrawal verification and order issuance. "
                "Additionally, 4 individual clearing desks handle operational verification: 1. Department HOD; 2. Central Library; 3. Chief Warden Office; and 4. Finance & Accounts Section."
            )
            return {
                "answer": office_msg,
                "domain": "Withdrawal",
                "citations": [DEFAULT_POLICIES[5]],
                "recommended_action": "Visit Registrar Office (Room 102)",
                "action_url": "/withdrawal",
                "voice_speech_text": office_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI10: 100% refund rumor
        is_100_refund_rumor = any(w in q_lower for w in [
            "every student gets a 100% refund", "every student gets 100% refund", "100% refund. is that true", "everyone gets 100% refund"
        ])
        if is_100_refund_rumor:
            rumor_100_msg = (
                f"I am sorry, {student_name}, but that rumor is incorrect. Under University Ordinance ORD-WTH-14.1 and UGC Guidelines, a 100% tuition refund (minus up to INR 1,000 processing charges) is granted ONLY if the withdrawal application is formally submitted at least 15 calendar days before the formally notified last date of admission. "
                "If submitted later, refund percentages decrease to 90%, 80%, 50%, and 0%. However, your security/caution deposit is always 100% refundable."
            )
            return {
                "answer": rumor_100_msg,
                "domain": "Policy Guardrails",
                "citations": [DEFAULT_POLICIES[5]],
                "recommended_action": "View Refund Ordinance (ORD-WTH-14.1)",
                "action_url": "/withdrawal",
                "voice_speech_text": rumor_100_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI11: 7-day refund rumor
        is_7_day_rumor = any(w in q_lower for w in [
            "takes exactly seven days", "takes exactly 7 days", "exactly seven days", "exactly 7 days", "seven days. confirm", "7 days. confirm"
        ])
        if is_7_day_rumor:
            rumor_7_msg = (
                f"I am sorry, {student_name}, but I cannot confirm that claim. Official university regulations and Finance Department timelines specify that fee refunds take approximately 15 to 30 working days to process following the complete sign-off of all 4 departmental clearances. A 7-day refund turnaround is not guaranteed by official policy."
            )
            return {
                "answer": rumor_7_msg,
                "domain": "Policy Guardrails",
                "citations": [DEFAULT_POLICIES[5]],
                "recommended_action": "View Refund Ordinance (ORD-WTH-14.1)",
                "action_url": "/withdrawal",
                "voice_speech_text": rumor_7_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI12: Link for withdrawal form
        is_wth_link = any(w in q_lower for w in [
            "official link for the withdrawal form", "link for the withdrawal form", "link for withdrawal form", "withdrawal form link"
        ])
        if is_wth_link:
            link_msg = (
                f"You can download the official Course Withdrawal Application Form (Form PROC-FORM-08) directly from the UniAssist Forms Catalog at '/forms', or initiate your digital clearance on the Program Withdrawal Cockpit at '/withdrawal'."
            )
            return {
                "answer": link_msg,
                "domain": "Withdrawal",
                "citations": [DEFAULT_POLICIES[5]],
                "recommended_action": "Download Form PROC-FORM-08",
                "action_url": "/forms",
                "voice_speech_text": link_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI13: Complete required documents without omitting
        is_wth_full_docs = any(w in q_lower for w in [
            "do not omit any required document", "without omitting any document", "all required documents", "complete list of documents"
        ]) and any(w in q_lower for w in ["withdrawal", "policy", "withdraw"])
        if is_wth_full_docs:
            docs_msg = (
                f"Here is the official university withdrawal policy with the complete, unabridged list of all mandatory documents:\n"
                "1. Completed and signed Course Withdrawal Application Form (Form PROC-FORM-08).\n"
                "2. Original Provisional Admission Offer Letter.\n"
                "3. Original University Fee Payment Receipts (all semesters).\n"
                "4. Physical Student Identity Card (surrendered).\n"
                "5. Multi-Desk No-Dues Clearance Certificate signed by Department HOD, Central Library, Chief Hostel Warden, and Central Labs.\n"
                "6. Cancelled Bank Cheque or bank passbook copy displaying account holder name, account number, and IFSC code for electronic refund remittance."
            )
            return {
                "answer": docs_msg,
                "domain": "Withdrawal",
                "citations": [DEFAULT_POLICIES[5]],
                "recommended_action": "Download Form PROC-FORM-08",
                "action_url": "/forms",
                "voice_speech_text": docs_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI14: Don't know what documents I have
        is_wth_help_docs = any(w in q_lower for w in [
            "don't know what documents i have", "dont know what documents i have", "what documents do i have", "help me with documents"
        ]) and any(w in q_lower for w in ["withdraw", "withdrawal"])
        if is_wth_help_docs:
            help_docs_msg = (
                f"Do not worry, {student_name}, let's build your document checklist step by step:\n"
                "1. Do you have your physical Student ID card?\n"
                "2. Do you have your semester admission fee receipt or transaction ID?\n"
                "3. Do you have any books borrowed from the Central Library or pending hostel room keys to return?\n"
                "Please check which of these items you currently have on hand, and download Form PROC-FORM-08 from '/forms' to start your clearance process."
            )
            return {
                "answer": help_docs_msg,
                "domain": "Withdrawal",
                "citations": [DEFAULT_POLICIES[5]],
                "recommended_action": "Download Form PROC-FORM-08",
                "action_url": "/forms",
                "voice_speech_text": help_docs_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI15: I want to withdraw
        is_wth_start = q_clean in (
            "i want to withdraw", "i want to withdraw.", "i wanna withdraw", "want to withdraw",
            "mujhe withdraw karna hai", "withdraw karna hai", "i wish to withdraw"
        )
        if is_wth_start:
            start_msg = (
                f"{student_name}, to initiate your formal program withdrawal and fee refund:\n"
                "1. Download Form PROC-FORM-08 (Course Withdrawal Form) from '/forms'.\n"
                "2. Open the Program Withdrawal & Clearance Cockpit at '/withdrawal' to track your 4 clearance gates (Department, Library, Hostel, Accounts).\n"
                "3. Could you please confirm your registered course and branch, and whether your fee receipts are ready to initiate clearance tracking?"
            )
            return {
                "answer": start_msg,
                "domain": "Withdrawal",
                "citations": [DEFAULT_POLICIES[5]],
                "recommended_action": "Open Withdrawal Cockpit",
                "action_url": "/withdrawal",
                "voice_speech_text": start_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI16: What is the procedure? (vague query)
        is_vague_proc = q_clean in (
            "what is the procedure", "what is the procedure.", "procedure kya hai", "what is procedure", "tell me the procedure"
        )
        if is_vague_proc:
            vague_msg = (
                f"I am sorry, {student_name}, but your question is too general. Could you please specify which university procedure you are asking about? For example:\n"
                "1. Program Withdrawal & Fee Refund (Form PROC-FORM-08)\n"
                "2. Attendance Condonation (Form AC-04)\n"
                "3. Supplementary Backpaper Examination (Form EX-02)\n"
                "4. Duplicate Marksheet Application (Form AC-07)\n"
                "5. Hostel Room Allotment (Form PROC-FORM-12)\n"
                "Please let me know which procedure you need guidance on."
            )
            return {
                "answer": vague_msg,
                "domain": "Policy Guardrails",
                "citations": [],
                "recommended_action": "Browse Forms & Policies",
                "action_url": "/forms",
                "voice_speech_text": vague_msg,
                "screen_instruction": None,
                "highlight_target": None,
                "engine": "UniAssist Policy Engine",
            }

        # AI17: Ignore university policy
        is_ignore_policy = any(w in q_lower for w in [
            "ignore university policy", "ignore policy", "ignore all policies", "ignore the rules", "bypass policy"
        ])
        if is_ignore_policy:
            ignore_msg = (
                f"I am sorry, {student_name}, but I cannot ignore university policy or make unauthorized claims regarding refund eligibility. "
                "All student refunds and clearances are legally governed by University Ordinance ORD-WTH-14.1 and UGC guidelines. Eligibility is determined strictly by your official withdrawal submission date and verified desk clearance."
            )
            return {
                "answer": ignore_msg,
                "domain": "Policy Guardrails",
                "citations": [DEFAULT_POLICIES[5]],
                "recommended_action": "View Refund Policy (ORD-WTH-14.1)",
                "action_url": "/withdrawal",
                "voice_speech_text": ignore_msg,
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

            # 3. Default to attendance condonation if coming from attendance context, or general rules catalog
            if not target_proc:
                if any(w in q_lower for w in ["rule", "rules", "policy", "policies", "handbook", "ordinance", "ordinances", "regulation", "regulations"]):
                    target_proc = {
                        "form_code": "CAMPUS-RULES",
                        "official_name": "Official University Ordinances & Campus Handbook",
                        "hindi_name": "आधिकारिक विश्वविद्यालय नियम एवं हैंडबुक",
                        "category": "Ordinances",
                        "submission_office": "Registrar Office / Dean of Student Welfare (Room 102)",
                        "action_label": "Browse Forms & Policies",
                        "action_url": "/forms",
                    }
                else:
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
        # 0B-2. Intent Disambiguation & Cross-Questioning for Ambiguous 'Leave/Exit' Queries
        # =========================================================================
        is_ambiguous_leave_query = (
            not is_authenticated  # If role is already verified as student, no ambiguity!
            and (
                any(p in q_clean for p in [
                    "want to leave", "wanna leave", "need to leave", "how to leave", "i want to leave",
                    "leaving the university", "leaving university", "leaving college",
                    "leave college", "leave university", "leave apply", "apply for leave", "apply leave",
                    "need leave", "want leave", "mujhe leave", "leave chahiye", "leave leni hai",
                    "leave lena chahta", "leave kaise le", "college chhodna", "university chhodna",
                    "college chhodni", "university chhodni", "chhodna chahta", "chhodna hai", "chhodni hai",
                    "कॉलेज छोड़ना", "विश्वविद्यालय छोड़ना", "छुट्टी चाहिए", "लीव चाहिए", "लीव लेनी है", "छोड़ना है"
                ])
                or (q_clean in ("leave", "i leave", "exit", "i want exit", "exit university", "college exit"))
            )
            and not any(spec in q_clean for spec in [
                "hostel", "room", "mess", "हॉस्टल",
                "admission cancel", "cancel admission", "fee refund", "tuition refund", "daakhila",
                "casual leave", "earned leave", "duty leave", "form 23", "professor", "faculty", "student",
                "medical", "sick", "class", "classes", "debar", "debarred", "attendance", "beemar", "बीमार",
                "form", "certificate", "bonafide", "document", "download", "scholarship", "grievance",
                "exam", "backpaper", "supplementary", "result", "grade", "marks", "id card", "fees"
            ])
        )

        if is_ambiguous_leave_query:
            if language == "hi-IN":
                clarify_ans = (
                    "कृपया स्पष्ट करें: क्या आप एक छात्र (Student) हैं जो विश्वविद्यालय से विड्रॉल और फीस रिफंड चाहते हैं, "
                    "या फैकल्टी/स्टाफ सदस्य हैं जो अवकाश (Leave - Form 23) अथवा कार्यमुक्ति (Resignation) के लिए आवेदन कर रहे हैं?"
                )
                v_ans = "कृपया स्पष्ट करें कि आप छात्र विड्रॉल के लिए पूछ रहे हैं, या फैकल्टी लीव अथवा हॉस्टल खाली करने के लिए?"
            elif language == "hi-Latn":
                clarify_ans = (
                    "Please clarify karein: Kya aap Student hain jo university se Withdrawal aur Fee Refund chahte hain, "
                    "ya Faculty/Staff member hain jo Leave (Form 23) ya Resignation ke liye apply kar rahe hain?"
                )
                v_ans = "Please batayein: Kya aap student withdrawal, faculty leave application, ya hostel vacate ke baare me pooch rahe hain?"
            else:
                clarify_ans = (
                    "Please clarify: Are you a Student looking to withdraw from the university and claim fee refund, "
                    "or a Faculty / Staff member applying for official leave (Form 23) or employment resignation?"
                )
                v_ans = "Are you a student looking to withdraw, or a faculty member applying for leave?"

            return {
                "status": "trigger_cross_question",
                "is_ambiguous": True,
                "domain": "Clarification Required",
                "answer": clarify_ans,
                "voice_speech_text": v_ans,
                "engine": "UniAssist Intent Disambiguator",
                "recommended_action": "Select Option Below",
                "action_url": "/withdrawal",
                "clarification_options": [
                    {
                        "label": "🧑‍🎓 Student Withdrawal & Fee Refund",
                        "value": "student_withdrawal",
                        "action_url": "/withdrawal",
                    },
                    {
                        "label": "👨‍🏫 Faculty Leave Application (Form 23)",
                        "value": "faculty_leave",
                        "action_url": "/forms",
                    },
                    {
                        "label": "🏢 Hostel Vacating & Handover",
                        "value": "hostel_vacate",
                        "action_url": "/services",
                    },
                ],
            }

        # Faculty Leave Application (Form 23)
        is_faculty_leave = (
            (
                any(fl in q_lower for fl in ["faculty leave", "emergency leave", "form 23", "फैकल्टी लीव", "संकाय अवकाश"])
                or ("faculty" in q_lower and "leave" in q_lower)
                or q_clean in (
                    "2", "option 2", "faculty", "i am a faculty", "i am faculty", "im a faculty", "im faculty",
                    "faculty_leave", "faculty leave", "i am a faculty member", "i am faculty member",
                    "फैकल्टी", "संकाय", "2 नंबर", "दो"
                )
                or (any(f_kw in q_clean for f_kw in ["i am a faculty", "i am faculty", "main faculty", "mein faculty"])
                    and not any(st_kw in q_clean for st_kw in ["student", "classes", "class", "debar", "attendance"]))
            )
            and not any(st in q_clean for st in ["missed class", "missed classes", "debar", "debarred", "attendance", "ac-04", "student"])
        )
        if is_faculty_leave:
            if language == "hi-IN":
                f_ans = (
                    "फैकल्टी एवं शिक्षण स्टाफ के लिए अवकाश आवेदन (Form 23) प्रक्रिया:\n"
                    "1. आकस्मिक (Casual), अर्जित (Earned), ड्यूटी (Duty), अथवा आपातकालीन अवकाश के लिए Form 23 भरें।\n"
                    "2. कक्षा व्यवस्था प्रपत्र (Class Arrangement Sheet - Form 03) पर संबंधित शिक्षक साथी की सहमति के हस्ताक्षर करवाएं।\n"
                    "3. योजनाबद्ध अवकाश से कम से कम 48 घंटे पूर्व विभागाध्यक्ष (HOD) की संस्तुति सहित प्रशासनिक ब्लॉक स्थित HR डेस्क (कमरा 103) में जमा करें।"
                )
                f_voice = "फैकल्टी लीव के लिए Form 23 और क्लास अरेंजमेंट शीट भरकर HOD संस्तुति के साथ HR डेस्क कमरा 103 में जमा करें।"
            elif language == "hi-Latn":
                f_ans = (
                    "Faculty & Teaching Staff ke liye Leave Application (Form 23) workflow:\n"
                    "1. Casual, Earned, Duty ya Medical leave ke liye Form 23 fill karein.\n"
                    "2. Class Arrangement Sheet (Form 03) par substitute teacher ke agreement signatures lein.\n"
                    "3. Planned leave se at least 48 hours pehle HOD recommendation ke saath HR Administration Desk (Room 103) me submit karein."
                )
                f_voice = "Faculty leave ke liye Form 23 aur Class Arrangement sheet fill karke HR Desk Room 103 me submit karein."
            else:
                f_ans = (
                    "Faculty and Academic Staff Leave Application (Form 23) procedure:\n"
                    "1. Complete Form 23 specifying leave category (Casual, Earned, Duty, Medical, or Emergency).\n"
                    "2. Attach signed Class Arrangement Sheet (Form 03) confirming substitute teacher coverage.\n"
                    "3. Submit with HOD recommendation to HR Administration Desk (Room 103, Administrative Block) at least 48 hours in advance."
                )
                f_voice = "For faculty leave, submit Form 23 with Class Arrangement Sheet to HR Desk in Room 103."

            return {
                "answer": f_ans,
                "domain": "HR & Staff",
                "citations": [],
                "recommended_action": "Download Form 23 (Leave Application)",
                "action_url": "/forms",
                "voice_speech_text": f_voice,
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
        substantive_topics = [
            "admit card", "admit", "hall ticket", "error", "mistake", "library", "fine", "lost", "found",
            "attendance", "marksheet", "hostel", "fee", "refund", "withdrawal", "withdraw", "exam", "grade",
            "revaluation", "rechecking", "address", "phone", "mobile", "placement", "ordinance", "rule",
            "degree", "bonafide", "id card", "scholarship", "debar", "condonation", "medical", "cgpa", "sgpa"
        ]
        is_substantive = any(st in q_lower for st in substantive_topics)

        is_ambient_navigation = not is_form_inquiry and not is_substantive and (
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

            # Try generating dynamic counselor advice via Ollama only if explicitly enabled
            ai_counselor_reply = None
            ai_engine_name = "SQLite FTS5 (Local Offline)"
            if settings.is_ollama_enabled:
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
                if primary_act and primary_act.lower() not in ai_counselor_reply.lower():
                    v_speech = f"{ai_counselor_reply} To proceed, click '{primary_act}'."
                else:
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

        # 4-Custom. Dynamic Procedures Configured in Procedure Wizard
        try:
            from .procedure_service import ProcedureService
            custom_procs = ProcedureService.list_procedures(active_only=True)
            for cp in custom_procs:
                cp_title = cp.get("title", "").strip().lower()
                cp_words = [w for w in re.sub(r"[^\w\s]", " ", cp_title).split() if len(w) > 3]
                distinctive_words = [w for w in cp_words if w not in ("hostel", "room", "student", "form", "application", "procedure", "request")]
                is_custom_match = (
                    cp_title in q_lower
                    or (cp_words and sum(1 for w in cp_words if w in q_lower) >= max(2, len(cp_words) - 1)
                        and (not distinctive_words or any(dw in q_lower for dw in distinctive_words)))
                )
                if cp_title and is_custom_match:
                    st_lines = []
                    for s in cp.get("steps", []):
                        st_lines.append(f"• Step {s['step_number']}: {s['title']} ({s.get('responsible_desk', 'Desk')} • SLA: {s.get('sla_days', 2)} days)")
                    st_str = "\n".join(st_lines) if st_lines else "Standard sequential departmental verification."
                    docs_str = ", ".join(cp.get("required_docs", [])) if cp.get("required_docs") else "None (100% digital process)"

                    if language == "hi-IN":
                        c_ans = (
                            f"{student_name}, विश्वविद्यालय पोर्टल पर '{cp['title']}' के लिए आधिकारिक प्रक्रिया:\n\n"
                            f"विभाग: {cp.get('department', 'विश्वविद्यालय कार्यालय')} | श्रेणी: {cp.get('category', 'General')}\n"
                            f"अनुमानित समय सीमा (SLA): {cp.get('sla_days', 7)} कार्य दिवस\n\n"
                            f"आधिकारिक चरण (Workflow Steps):\n{st_str}\n\n"
                            f"आवश्यक दस्तावेज: {docs_str}"
                        )
                        c_speech = f"{student_name}, {cp['title']} के लिए {len(cp.get('steps', []))} आधिकारिक चरण निर्धारित हैं।"
                    elif language == "hi-Latn":
                        c_ans = (
                            f"{student_name}, '{cp['title']}' ke liye official university workflow:\n\n"
                            f"Department: {cp.get('department', 'University Desk')} | Category: {cp.get('category', 'General')}\n"
                            f"Turnaround SLA: {cp.get('sla_days', 7)} working days\n\n"
                            f"Workflow Steps:\n{st_str}\n\n"
                            f"Required Documents: {docs_str}"
                        )
                        c_speech = f"{student_name}, {cp['title']} ke liye {len(cp.get('steps', []))} configured workflow steps hain."
                    else:
                        c_ans = (
                            f"{student_name}, official procedure details for '{cp['title']}':\n\n"
                            f"Department: {cp.get('department', 'University Office')} | Category: {cp.get('category', 'General')}\n"
                            f"Estimated SLA: {cp.get('sla_days', 7)} working days\n\n"
                            f"Configured Workflow Steps:\n{st_str}\n\n"
                            f"Required Documents: {docs_str}"
                        )
                        c_speech = f"{student_name}, the procedure for {cp['title']} has {len(cp.get('steps', []))} configured steps."

                    return {
                        "answer": c_ans,
                        "domain": f"Procedure: {cp['title']}",
                        "citations": [],
                        "recommended_action": f"View {cp['title']}",
                        "action_url": "/procedures",
                        "voice_speech_text": c_speech,
                        "engine": "UniAssist Dynamic Procedure Engine",
                    }
        except Exception:
            pass

        # 4A-0. Lost ID Card during Withdrawal / Refund (W10 & Caution Deposit Deduction)
        is_lost_id_refund_query = (
            (
                any(w in q_lower for w in ["id card", "id", "identity card", "पहचान पत्र", "आईडी कार्ड", "आईडी"])
                and any(w in q_lower for w in ["lost", "kho", "gum", "dont have", "don't have", "missing", "bina", "without", "no id", "खो", "गुम", "नहीं है", "खोया", "खोई"])
            )
            and any(w in q_lower for w in [
                "refund", "refundl", "withdrawal", "withdraw", "caution deposit", "security deposit", "leave",
                "रिफंड", "विड्रॉल", "डिपॉजिट", "कॉलेज छोड़ना"
            ])
        )

        # 4A. Student ID Card Re-issue (Duplicate ID Card)
        is_id_card_query = (
            not is_lost_id_refund_query
            and (
                any(w in q_lower for w in ["id card", "duplicate id", "lost id", "lost my id", "identity card", "पहचान पत्र", "आईडी कार्ड"])
                or (any(w in q_lower for w in ["id", "आईडी"]) and any(w in q_lower for w in ["kho gaya", "gum", "lost", "duplicate", "naya", "bane", "banega", "kho gya", "खो", "गुम", "डुप्लिकेट", "नया"]))
            )
            and not any(w in q_lower for w in ["offset", "caution deposit", "ऑफसेट", "कट सकता", "कट सकती", "काट सकते"])
        )

        # 4A-1. Day Scholar vs Hosteller Clearance (ORD-HST-5.1)
        is_day_scholar_hostel_query = (
            any(w in q_lower for w in ["day scholar", "dayscholar", "non-hosteller", "non hosteller", "डे-स्कॉलर", "डे स्कॉलर", "डेस्कॉलर"])
            and any(w in q_lower for w in ["hostel", "clearance", "हॉस्टल", "क्लीयरेंस", "हॉस्टलर"])
        ) or (
            "hostel" in q_lower and "clearance" in q_lower and any(w in q_lower for w in ["need", "required", "mandatory", "bypassed", "skip", "zarurat", "zaroorat", "padega", "jaana", "जाना", "जरूरत", "लागू"])
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
            or q_clean in ("3", "option 3", "hostel_vacate", "hostel vacate", "hostel vacating", "hostel", "हॉस्टल")
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

        # 4G-1. Student Grievance & Request Ticket Progress Tracking (F15)
        is_ticket_status_query = (
            any(w in q_lower for w in [
                "ticket status", "grievance status", "my ticket", "my tickets",
                "ticket progress", "grievance progress", "status of my ticket", "status of ticket",
                "check my ticket", "check ticket", "track ticket", "track my ticket", "track grievance",
                "complaint status", "complaint progress", "my complaint", "status of my complaint",
                "active ticket", "active tickets", "konsi ticket", "kaunsi ticket", "meri ticket", "meri tickets",
                "tickets active", "active konsi", "ticket list", "list tickets",
                "टिकट स्टेटस", "शिकायत स्टेटस", "मेरी शिकायत", "टिकट का स्टेटस", "टिकट ट्रैक", "सक्रिय टिकट",
                "check my request", "status of my request", "track request", "withdrawal status"
            ])
            or ("ticket" in q_lower and any(w in q_lower for w in ["status", "progress", "update", "check", "track", "kya hua", "kahan tak", "active", "konsi", "kaunsi", "list", "dekhna"]))
            or ("grievance" in q_lower and any(w in q_lower for w in ["status", "progress", "update", "track", "check", "active", "list"]))
            or ("complaint" in q_lower and any(w in q_lower for w in ["status", "progress", "update", "track", "check", "active", "list"]))
            or re.search(r"\bgrv[-\s]?\d{4}[-\s]?\d+\b", q_lower) is not None
        )

        # 4G-2. Student Grievance & Anti-Ragging (Filing)
        is_grievance_query = (
            not is_ticket_status_query
            and any(w in q_lower for w in [
                "ragging", "complaint", "harassment", "grievance", "shikayat", "proctor", "ragging complaint",
                "रैगिंग", "शिकायत", "प्रताड़ना", "धमकी"
            ])
        )

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
            or q_clean in (
                "1", "option 1", "student_withdrawal", "student withdrawal", "student",
                "i am a student", "i am student", "im a student", "im student", "छात्र", "विद्यार्थी"
            )
            or (is_authenticated and any(p in q_clean for p in [
                "want to leave", "wanna leave", "leave college", "leave university", "leaving college",
                "college chhodna", "university chhodna", "college chhodni", "chhodna chahta", "chhodna hai", "कॉलेज छोड़ना"
            ]))
        )

        # 4K. Attendance & Condonation (Including Medical Leave & Missed Classes)
        is_attendance_query = (
            any(w in q_lower for w in [
                "attendance", "condonation", "debar", "debarred", "absent", "shortage",
                "sick", "fell sick", "medical leave", "missed class", "missed classes",
                "missed my classes", "medical certificate", "ac-04", "ac04",
                "अटेंडेंस", "उपस्थिति", "हाजिरी", "कंडोनेशन", "कम अटेंडेंस", "बीमार", "मेडिकल लीव"
            ])
            or (any(w in q_lower for w in ["missed", "leave", "chhutti", "absent"]) and any(c in q_lower for c in ["class", "classes", "lecture", "lectures", "debar", "debarred"]))
        )

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

        # 4N. Academic Curriculum & Course Syllabus Roadmap
        is_syllabus_query = (
            any(w in q_lower for w in [
                "syllabus", "curriculum", "course structure", "subjects", "subject list",
                "semester wise", "btech cse", "computer science", "cse syllabus", "cse subject",
                "सिलबस", "सिलेबस", "पाठ्यक्रम", "विषय"
            ])
            and not any(w in q_lower for w in ["withdrawal", "refund", "bunk", "leave college", "caution deposit"])
        ) or any(w in q_lower for w in ["syllabus", "curriculum", "सिलेबस", "सिलबस"])

        # 4O. Grading System, CGPA, SGPA & Evaluation Ordinance
        is_grading_cgpa_query = any(w in q_lower for w in [
            "grading", "cgpa", "sgpa", "grading system", "passing marks", "pass marks",
            "grade point", "credit system", "relative grading", "grade scale", "ग्रेजिंग", "सीजीपीए"
        ]) and not any(w in q_lower for w in ["withdrawal", "refund", "caution deposit", "scholarship", "scholarships", "छात्रवृत्ति", "स्कॉलरशिप"])

        # 4P. Placements, Internships & Training
        is_placement_query = any(w in q_lower for w in [
            "placement", "placements", "internship", "internships", "training and placement", "t&p",
            "recruiter", "recruiters", "job campus", "प्लेसमेंट", "इंटर्नशिप"
        ]) and not any(w in q_lower for w in ["withdrawal", "refund", "caution deposit"])

        # 4Q. Library Services, Timings & Catalog
        is_library_info_query = any(w in q_lower for w in [
            "library timing", "library time", "library hours", "issue book", "return book",
            "library books", "library access", "e-resources", "लाइब्रेरी", "पुस्तकालय"
        ]) and not any(w in q_lower for w in ["fine", "offset", "deposit", "withdrawal", "caution deposit"])

        # 4R. Campus Facilities, Health Center & Medical Emergency
        is_campus_facility_query = any(w in q_lower for w in [
            "health center", "medical center", "hospital", "dispensary", "emergency contact",
            "doctor", "campus facility", "sports complex", "gym", "ambulance",
            "स्वास्थ्य केंद्र", "चिकित्सा", "अस्पताल"
        ]) and not any(w in q_lower for w in ["attendance", "condonation", "medical leave", "ac-04", "caution deposit", "wifi"])

        res = None


        if is_lost_id_refund_query:
            wth_policy = next((p for p in policies if p["doc_id"] == "POL-WTH-01"), DEFAULT_POLICIES[1])
            fin_policy = next((p for p in policies if p["doc_id"] == "POL-FIN-01"), DEFAULT_POLICIES[2] if len(DEFAULT_POLICIES) > 2 else DEFAULT_POLICIES[0])
            citations = [wth_policy, fin_policy]

            if language == "hi-IN":
                answer = (
                    f"{student_name}, यदि आपका छात्र पहचान पत्र (Student ID Card) खो गया है, तब भी आपको आपका रिफंड अवश्य मिलेगा और आपकी विड्रॉल प्रक्रिया पूरी तरह डिजिटल रूप से आगे बढ़ेगी!\n\n"
                    "विश्वविद्यालय क्लीयरेंस एवं कॉशन डिपॉजिट नियमावली (ORD-FIN-14.4 एवं ORD-WTH-14.1) के तहत आधिकारिक डिजिटल प्रक्रिया:\n\n"
                    "1. **रिफंड रुकेगा नहीं**: आईडी कार्ड न होने से आपका विड्रॉल या रिफंड कैंसिल या रिजेक्ट नहीं होता।\n"
                    "2. **सिक्योरिटी डिपॉजिट से ₹200 की स्मार्ट कटौती**: फिजिकल आईडी कार्ड सरेंडर न करने के एवज में ₹200 का रिप्लेसमेंट शुल्क आपके ₹10,000 रिफंडेबल कॉशन डिपॉजिट से कियोस्क पर ही 1-टैप स्मार्ट ऑफसेट द्वारा सीधे काट लिया जाएगा (किसी कैश काउंटर या ऑफिस जाने की आवश्यकता नहीं है)।\n"
                    "3. **डिजिटल 4-गेट क्लीयरेंस**: आपकी विड्रॉल फाइल लाइब्रेरी, हॉस्टल (यदि आप हॉस्टलर हैं; डे-स्कॉलर हेतु स्वतः बायपास), और अकाउंट्स के माध्यम से डिजिटल रूप से प्रोसेस होगी। विड्रॉल फॉर्म (Form WTH) के साथ बस एक साधारण 'Lost ID Declaration' संलग्न करें।\n"
                    "4. **डिजिटल स्लिप एवं नेट रिफंड**: रजिस्ट्रार नोटशीट डिजिटल अप्रूवल के बाद आप अपनी आधिकारिक क्लीयरेंस स्लिप (PDF) इसी कियोस्क से डाउनलोड कर सकते हैं। शेष बची ₹9,800 कॉशन डिपॉजिट और लागू ट्यूशन फीस सीधे आपके बैंक खाते में RTGS/NEFT द्वारा ट्रांसफर कर दी जाएगी।"
                )
                voice_text = f"{student_name}, आईडी कार्ड खो जाने पर भी आपका रिफंड नहीं रुकेगा। आपके ₹10,000 कॉशन डिपॉजिट से ₹200 स्मार्ट ऑफसेट द्वारा कट जाएंगे और 4 डिजिटल क्लीयरेंस गेट्स पूरे होकर बची राशि ₹9,800 एवं ट्यूशन रिफंड सीधे आपके बैंक खाते में भेज दी जाएगी।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, agar aapka student ID card kho gaya hai tab bhi aapko refund bilkul milega aur aapki withdrawal process 100% digitally aage proceed hogi!\n\n"
                    "University Clearance & Caution Deposit Rules (ORD-FIN-14.4 & ORD-WTH-14.1):\n\n"
                    "1. **Refund Block Nahi Hoga**: ID card kho jane se withdrawal ya fee refund cancel nahi hota.\n"
                    "2. **Security Deposit se ₹200 Smart Offset**: Physical card surrender na hone par ₹200 ka replacement charge aapke ₹10,000 caution/security deposit se kiosk screen par 1-tap smart offset se direct deduct ho jayega (kisi cash window par jane ki zarurat nahi).\n"
                    "3. **Digital 4-Gate Pipeline**: Application Library, Hostel (sirf agar aap resident hain; day-scholars ke liye automatically bypassed), aur Accounts me digitally check hoti hai. Form WTH ke sath bas ek simple Lost ID Declaration attach karein.\n"
                    "4. **Digital Slip & Net Disbursal**: Registrar digital sign-off ke baad aap official Clearance Slip (PDF) kiosk se download kar sakte hain. Bacha hua balance (₹9,800 deposit + applicable tuition fee) aapke verified bank account me RTGS/NEFT se transfer ho jayega."
                )
                voice_text = f"{student_name}, haan refund bilkul milega! Lost ID ke liye 200 rupees caution deposit se smart offset ho jayenge. 4 digital clearance gates complete hone ke baad net balance 9,800 rupees aur tuition refund direct aapke bank account me aa jayega."
            else:
                answer = (
                    f"{student_name}, yes! Even if your student ID card is lost, you will still receive your refund and your withdrawal will proceed 100% digitally without interruption.\n\n"
                    "Under University Clearance & Smart Offsetting Regulations (ORD-FIN-14.4 & ORD-WTH-14.1):\n\n"
                    "2. **₹200 Deduction via Smart Caution Deposit Offsetting**: Since you cannot physically surrender the ID card, a ₹200 lost ID replacement fee is automatically deducted from your ₹10,000 refundable caution/security deposit directly on screen via 1-tap Smart Offsetting (no physical cash counter or window visits needed).\n"
                    "3. **Digital 4-Gate Clearance**: Your clearance moves seamlessly across Central Library, Hostel (verified conditionally: automatically bypassed for day-scholars, digital sign-off for hostellers), Finance ledger audit, and Registrar review. Simply attach a standard Lost ID Declaration with your Form WTH.\n"
                    "4. **Digital Slip & Net Disbursal**: Upon Registrar digital notesheet approval, download your official Clearance Slip & No-Dues PDF right from this kiosk. The net caution deposit (₹9,800) plus applicable tuition fee refund under UGC slabs will be credited directly to your registered bank account via RTGS/NEFT."
                )
                voice_text = f"{student_name}, yes, you will get your refund! Losing your ID card will not block your withdrawal. A 200 Rupees lost card fee will be deducted from your 10,000 Rupees caution deposit via smart offsetting, and your remaining 9,800 Rupees plus applicable tuition refund will be credited directly to your bank account."

            res = {
                "answer": answer,
                "domain": "Withdrawal & Caution Deposit Refund",
                "citations": citations,
                "recommended_action": "Proceed with Withdrawal (Form WTH)",
                "action_url": "/withdrawal",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_syllabus_query:
            curriculum_policy = next((p for p in policies if p.get("clause_code") == "ORD-ACAD-01"), DEFAULT_POLICIES[0])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, विश्वविद्यालय B.Tech कंप्यूटर साइंस एंड इंजीनियरिंग (CSE) का 8-सेमेस्टर AICTE क्रेडिट-बेस्ड पाठ्यक्रम संरचना निम्नलिखित है:\n\n"
                    "• **सेमेस्टर 1 और 2 (फाउंडेशन)**: इंजीनियरिंग गणित (I & II), प्रोग्रामिंग फॉर प्रॉब्लम सॉल्विंग (C/Python), बेसिक इलेक्ट्रॉनिक्स, और इंजीनियरिंग फिजिक्स/केमिस्ट्री।\n"
                    "• **सेमेस्टर 3 और 4 (कोर कंप्यूटिंग)**: डेटा स्ट्रक्चर्स एंड एल्गोरिदम्स (DSA), ऑब्जेक्ट-ओरिएंटेड प्रोग्रामिंग (Java/C++), कंप्यूटर आर्किटेक्चर (COA), ऑपरेटिंग सिस्टम (OS), और डेटाबेस मैनेजमेंट सिस्टम (DBMS)।\n"
                    "• **सेमेस्टर 5 और 6 (एडवांस्ड कंप्यूटिंग)**: कंप्यूटर नेटवर्क्स (CN), थ्योरी ऑफ कंप्यूटेशन (TOC), सॉफ्टवेयर इंजीनियरिंग, आर्टिफिशियल इंटेलिजेंस (AI) एवं मशीन लर्निंग (ML), और वेब टेक्नोलॉजीज।\n"
                    "• **सेमेस्टर 7 और 8 (स्पेशलाइजेशन एवं इंडस्ट्री)**: क्लाउड कंप्यूटिंग, साइबर सिक्योरिटी, बिग डेटा एनालिटिक्स, कैपस्टोन मेजर प्रोजेक्ट (Capstone Project) और फुल-सेमेस्टर इंडस्ट्री इंटर्नशिप।\n\n"
                    "कुल डिग्री आवश्यकता: 160 क्रेडिट्स और न्यूनतम 75% उपस्थिति अनिवार्य है। विस्तृत विषय सूची छात्र पोर्टल पर उपलब्ध है।"
                )
                voice_text = f"{student_name}, B.Tech Computer Science ke 8 semesters me pehle saal foundation, dusre saal DSA, OS aur DBMS jaise core subjects, teesre saal AI, Networks aur Web, tatha aakhri saal me Capstone Project aur Internship shaamil hain."
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, University B.Tech Computer Science & Engineering (CSE) ka AICTE-aligned 8-semester curriculum roadmap yeh hai:\n\n"
                    "• **Semester 1 & 2 (Foundation)**: Engineering Mathematics I & II, Programming for Problem Solving (C/Python), Basic Electrical & Electronics, Engineering Physics.\n"
                    "• **Semester 3 & 4 (Core Computing)**: Data Structures & Algorithms (DSA), Object-Oriented Programming (Java/C++), Computer Organization & Architecture (COA), Operating Systems (OS), Database Management Systems (DBMS).\n"
                    "• **Semester 5 & 6 (Advanced Computing)**: Computer Networks (CN), Design & Analysis of Algorithms (DAA), Theory of Computation, Artificial Intelligence & Machine Learning (AI/ML), Full-Stack Web Development.\n"
                    "• **Semester 7 & 8 (Specialization & Capstone)**: Cloud Computing, Cyber Security, Major Capstone Project, aur Full-Semester Mandatory Industry Internship.\n\n"
                    "Total Degree Requirement: 160 Credits aur minimum 75% attendance mandatory hai. Aap student dashboard se detailed syllabus PDF download kar sakte hain."
                )
                voice_text = f"{student_name}, B.Tech CSE ke curriculum me 8 semesters hain: pehle foundation, fir core DSA, OS aur DBMS, third year me AI, ML aur Networks, aur final year me Major Project tatha Industry Internship hoti hai."
            else:
                answer = (
                    f"{student_name}, here is the official 8-Semester AICTE-aligned curriculum roadmap for B.Tech Computer Science & Engineering (CSE):\n\n"
                    "• **Semesters 1 & 2 (Foundation)**: Engineering Mathematics I & II, Programming for Problem Solving (C/Python), Basic Electrical & Electronics, Engineering Physics.\n"
                    "• **Semesters 3 & 4 (Core Computing)**: Data Structures & Algorithms (DSA), Object-Oriented Programming (Java/C++), Computer Organization & Architecture (COA), Operating Systems (OS), Database Management Systems (DBMS).\n"
                    "• **Semesters 5 & 6 (Advanced Systems)**: Computer Networks (CN), Design & Analysis of Algorithms (DAA), Theory of Computation, Artificial Intelligence & Machine Learning (AI/ML), Web Technologies.\n"
                    "• **Semesters 7 & 8 (Specialization & Capstone)**: Cloud Computing, Information & Cyber Security, Elective Tracks, Year-long Capstone Major Project, and Full-Semester Industry Internship.\n\n"
                    "Degree Criteria: Total 160 credits with minimum 75% attendance. Complete detailed syllabus PDF can be accessed directly on the Student Portal."
                )
                voice_text = f"{student_name}, B.Tech Computer Science comprises 8 semesters: first-year foundations, second-year core systems like DSA, OS, and DBMS, third-year AI, Networks, and Web development, and final-year capstone project with industry internship."

            res = {
                "answer": answer,
                "domain": "Academics & Curriculum",
                "citations": [curriculum_policy],
                "recommended_action": "View Syllabus & Course Catalog",
                "action_url": "/dashboard",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_grading_cgpa_query:
            grading_policy = next((p for p in policies if p.get("clause_code") == "ORD-EXM-01"), DEFAULT_POLICIES[0])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, विश्वविद्यालय 10-पॉइंट यूजीसी चॉइस-बेस्ड क्रेडिट सिस्टम (CBCS) रिलेटिव ग्रेडिंग प्रणाली का पालन करता है:\n\n"
                    "• **ग्रेड स्केल**: O (आउटस्टैंडिंग: 10), A+ (एक्सीलेंट: 9), A (वेरी गुड: 8), B+ (गुड: 7), B (एबव एवरेज: 6), C (एवरेज: 5), P (पास: 4), F (फेल: 0)।\n"
                    "• **न्यूनतम पासिंग अंक**: थ्योरी और प्रैक्टिकल दोनों में अलग-अलग न्यूनतम 40% अंक (P ग्रेड) प्राप्त करना अनिवार्य है।\n"
                    "• **SGPA & CGPA गणना**: SGPA = कुल (कोर्स क्रेडिट्स × प्राप्त ग्रेड पॉइंट्स) ÷ कुल सेमेस्टर क्रेडिट्स। सभी सेमेस्टरों का संचयी औसत CGPA कहलाता है।\n"
                    "• **डिग्री वर्गीकरण**: 7.5 CGPA और ऊपर - प्रथम श्रेणी डिस्टिंक्शन के साथ; 6.5 से 7.49 - प्रथम श्रेणी।"
                )
                voice_text = f"{student_name}, विश्वविद्यालय में 10-पॉइंट रिलेटिव ग्रेडिंग सिस्टम लागू है। न्यूनतम पासिंग ग्रेड P यानी 40% है, और 7.5 या अधिक CGPA पर फर्स्ट क्लास विद डिस्टिंक्शन मिलती है।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, University UGC Choice-Based Credit System (CBCS) 10-point relative grading scale follow karti hai:\n\n"
                    "• **Grade Scale**: O (Outstanding: 10), A+ (Excellent: 9), A (Very Good: 8), B+ (Good: 7), B (Above Average: 6), C (Average: 5), P (Pass: 4), F (Fail: 0).\n"
                    "• **Passing Criteria**: Har subject me theory aur practical component me minimum 40% marks (Grade P) score karna mandatory hai.\n"
                    "• **SGPA & CGPA Formula**: SGPA = Total (Credits × Grade Points) ÷ Total Semester Credits. Sabhi semesters ka cumulative average CGPA hota hai.\n"
                    "• **Degree Classification**: 7.5 CGPA aur above par First Class with Distinction, aur 6.5 se 7.49 par First Class award hoti hai."
                )
                voice_text = f"{student_name}, university 10-point grading system follow karti hai. Passing marks 40% ya P grade hain, aur 7.5 CGPA par distinction milti hai."
            else:
                answer = (
                    f"{student_name}, the university follows the official UGC 10-point Choice-Based Credit System (CBCS) relative grading structure:\n\n"
                    "• **Grade Scale**: O (Outstanding: 10), A+ (Excellent: 9), A (Very Good: 8), B+ (Good: 7), B (Above Average: 6), C (Average: 5), P (Pass: 4), F (Fail: 0).\n"
                    "• **Passing Threshold**: Minimum 40% aggregate in both internal assessments and end-term examinations independently.\n"
                    "• **SGPA & CGPA Calculation**: SGPA = Sum of (Course Credits × Grade Points Earned) ÷ Total Credits Registered in that semester. Cumulative across all completed terms is your CGPA.\n"
                    "• **Degree Honors**: ≥ 7.5 CGPA awards First Class with Distinction; 6.5 to 7.49 awards First Class."
                )
                voice_text = f"{student_name}, the university uses a 10-point UGC relative grading scale. Minimum passing requirement is 40% or P grade, and 7.5 CGPA confers First Class with Distinction."

            res = {
                "answer": answer,
                "domain": "Grading & Examination",
                "citations": [grading_policy],
                "recommended_action": "View Examination Ordinances",
                "action_url": "/exams",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_placement_query:
            placement_policy = next((p for p in policies if p.get("clause_code") == "ORD-TNP-01"), DEFAULT_POLICIES[0])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, विश्वविद्यालय ट्रेनिंग एंड प्लेसमेंट (T&P) सेल ब्लॉक 2 (कक्ष 204) में स्थित है:\n\n"
                    "• **पात्रता मानदंड**: 6वें/7वें सेमेस्टर के छात्र जिनका संचयी CGPA 6.5 या अधिक है और कोई सक्रिय बैकलाग नहीं है, कैंपस प्लेसमेंट ड्राइव के लिए पात्र हैं।\n"
                    "• **प्रमुख रिक्रूटर्स**: माइक्रोसॉफ्ट, गूगल, अमेज़ॉन, टीसीएस, इंफोसिस, विप्रो, एक्सेंचर एवं कोर इंजीनियरिंग कंपनियां कैंपस में आती हैं।\n"
                    "• **इंटर्नशिप अनापत्ति प्रमाण पत्र (NOC)**: 8वें सेमेस्टर या ग्रीष्मकालीन इंडस्ट्री इंटर्नशिप हेतु छात्र फॉर्म 18 भरकर टी&पी सेल से ऑनलाइन NOC प्राप्त कर सकते हैं।\n"
                    "• **रजिस्ट्रेशन**: ट्रेनिंग एवं प्लेसमेंट पोर्टल पर प्रोफाइल अपडेट करें और रिज्यूमे अपलोड करें।"
                )
                voice_text = f"{student_name}, ट्रेनिंग एंड प्लेसमेंट सेल ब्लॉक 2 में है। 6.5 से अधिक CGPA और बिना बैकलाग वाले छात्र कैंपस ड्राइव के लिए पात्र हैं, और इंटर्नशिप NOC फॉर्म 18 द्वारा मिलती है।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, University Training & Placement (T&P) Cell Block 2 (Room 204) me functional hai:\n\n"
                    "• **Eligibility Criteria**: 6th/7th semester ke students jinka CGPA 6.5+ hai aur koi active backlog nahi hai, campus placement drives ke liye eligible hain.\n"
                    "• **Key Recruiters**: Top tech leaders, product firms, IT majors, aur core engineering companies campus hiring conduct karti hain.\n"
                    "• **Internship NOC (Form 18)**: Semester internship ya summer training ke liye students Form 18 portal se download karke online NOC approve kara sakte hain.\n"
                    "• **Registration**: T&P portal par verified resume upload karke mandatory placement registration complete karein."
                )
                voice_text = f"{student_name}, placement cell Block 2 me hai. 6.5 CGPA aur zero backlog wale students eligible hote hain. Internship ke liye Form 18 se online NOC milti hai."
            else:
                answer = (
                    f"{student_name}, the University Training & Placement (T&P) Division is located in Block 2, Room 204:\n\n"
                    "• **Eligibility Criteria**: Students entering 6th/7th semester with a cumulative CGPA of 6.5 or higher and zero active backlogs are eligible for on-campus placement drives.\n"
                    "• **Top Hiring Partners**: Global tech leaders, software product companies, consulting firms, and core engineering enterprises.\n"
                    "• **Internship NOC (Form 18)**: Students undertaking mandatory 8th-semester or summer corporate internships must secure an official Departmental NOC using Form 18.\n"
                    "• **Support**: Resume building, mock interviews, and technical coding rounds are regularly organized."
                )
                voice_text = f"{student_name}, the Training and Placement Cell is in Block 2. Students with 6.5 CGPA or higher and no backlogs are eligible for campus recruitment drives, and internship NOC is issued via Form 18."

            res = {
                "answer": answer,
                "domain": "Training & Placements",
                "citations": [placement_policy],
                "recommended_action": "Download Internship NOC Form (Form 18)",
                "action_url": "/forms",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_library_info_query:
            lib_policy = next((p for p in policies if p.get("clause_code") == "ORD-LIB-01"), DEFAULT_POLICIES[0])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, केंद्रीय विश्वविद्यालय पुस्तकालय (Central Library) की समय सारिणी एवं नियम:\n\n"
                    "• **समय**: सामान्य दिनों में सुबह 8:00 बजे से रात 10:00 बजे तक; मिड-टर्म एवं एंड-टर्म परीक्षा अवधि के दौरान 24×7 रीडिंग हॉल खुला रहता है।\n"
                    "• **पुस्तक जारी करने की सीमा**: अंडरग्रेजुएट (B.Tech) छात्र अपने स्मार्ट आईडी कार्ड पर एक समय में अधिकतम 3 पुस्तकें 14 दिनों के लिए जारी करा सकते हैं।\n"
                    "• **नवीनीकरण एवं डिजिटल कैटलॉग**: छात्र कियोस्क या ऑनलाइन OPAC पोर्टल से घर बैठे पुस्तक 1 बार रिन्यू कर सकते हैं।\n"
                    "• **विलंब शुल्क**: देय तिथि के बाद प्रति पुस्तक ₹5 प्रति दिन का विलंब शुल्क लागू होता है जिसे कियोस्क पर कॉशन डिपॉजिट से 1-टैप स्मार्ट ऑफसेट किया जा सकता है।"
                )
                voice_text = f"{student_name}, सेंट्रल लाइब्रेरी सामान्य दिनों में सुबह 8 से रात 10 बजे तक और परीक्षाओं में 24 घंटे खुली रहती है। छात्र 3 पुस्तकें 14 दिनों के लिए जारी करा सकते हैं।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, Central University Library timings aur borrowing policies:\n\n"
                    "• **Timings**: Regular days me subah 8:00 AM se raat 10:00 PM tak open rehti hai; exam periods me 24×7 Reading Hall accessible rehta hai.\n"
                    "• **Book Loan Limit**: Undergraduates smart student ID card par ek samay me 3 books 14 din ke liye issue kara sakte hain.\n"
                    "• **Online OPAC & Renewal**: Library portal ya OPAC terminal se 1 time online renewal available hai.\n"
                    "• **Overdue Fine**: Due date ke baad ₹5 per day per book fine lagti hai, jise caution deposit se smart offset kiya ja sakta hai."
                )
                voice_text = f"{student_name}, library subah 8 se raat 10 baje tak aur exams me 24 ghante khuli rehti hai. Students 3 books 14 din ke liye issue kara sakte hain."
            else:
                answer = (
                    f"{student_name}, Central University Library operational guidelines and circulation rules:\n\n"
                    "• **Operating Hours**: Monday to Saturday 8:00 AM to 10:00 PM; 24×7 Reading Hall access during mid-term and end-term examinations.\n"
                    "• **Borrowing Quota**: Undergraduate students may issue up to 3 books simultaneously for a duration of 14 days using their Biometric Student ID.\n"
                    "• **Digital Resources & OPAC**: Full access to IEEE Xplore, ScienceDirect, Springer, and remote journal access via university VPN.\n"
                    "• **Overdue Policy**: Overdue fine of ₹5/day per book applies after the grace period, settable via 1-tap Caution Deposit Offsetting."
                )
                voice_text = f"{student_name}, the Central Library is open from 8 AM to 10 PM daily, and 24 hours during exams. Undergraduate students can borrow up to 3 books for 14 days."

            res = {
                "answer": answer,
                "domain": "Library & Learning Resources",
                "citations": [lib_policy],
                "recommended_action": "Check Library Dues & Clearance",
                "action_url": "/withdrawal",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_campus_facility_query:
            health_policy = next((p for p in policies if p.get("clause_code") == "ORD-HLT-01"), DEFAULT_POLICIES[0])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, विश्वविद्यालय परिसर की प्रमुख छात्र कल्याण एवं चिकित्सा सुविधाएं:\n\n"
                    "• **स्वास्थ्य केंद्र (Health Center)**: ब्लॉक 1 के ग्राउंड फ्लोर पर 24×7 खुला है। इसमें रेजिडेंट मेडिकल ऑफिसर, इमरजेंसी वार्ड और निःशुल्क आवश्यक दवाइयां उपलब्ध हैं। आपातकालीन एम्बुलेंस: एक्सटेंशन 108 / 112।\n"
                    "• **कैंपस वाई-फाई**: पूरे कैंपस और हॉस्टल्स में 'UniNet-Student' हाई-स्पीड 1Gbps सुरक्षित वाई-फाई उपलब्ध है (छात्र पोर्टल क्रेडेंशियल्स से लॉगिन करें)।\n"
                    "• **खेल एवं फिटनेस**: इनडोर बैडमिंटन कोर्ट, जिम, ओलंपिक-साइज रनिंग ट्रैक और क्रिकेट ग्राउंड सुबह 6:00 से रात 9:00 बजे तक खुले रहते हैं।\n"
                    "• **छात्र सहायता डेस्क**: किसी भी प्रशासनिक सहायता हेतु एडमिन ब्लॉक रिसेप्शन (कक्ष 101) पर संपर्क करें।"
                )
                voice_text = f"{student_name}, कैंपस हेल्थ सेंटर ब्लॉक 1 में 24 घंटे खुला रहता है जहां निःशुल्क डॉक्टर और दवाइयां मिलती हैं। इसके अतिरिक्त हाई-स्पीड वाई-फाई और स्पोर्ट्स कॉम्प्लेक्स सभी छात्रों के लिए उपलब्ध हैं।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, University Campus Student Welfare & Medical Facilities:\n\n"
                    "• **24×7 Health Center**: Block 1 ground floor par round-the-clock doctors, emergency ward, basic diagnostics, aur free primary medicines available hain. Ambulance hotline: Ext 108.\n"
                    "• **Campus Wi-Fi**: Pure academic buildings aur hostels me 'UniNet-Student' high-speed 1Gbps secure internet active hai (Student Roll No. login).\n"
                    "• **Sports Complex**: Indoor badminton, gym, athletics track, aur football ground daily 6:00 AM se 9:00 PM tak students ke liye accessible hain.\n"
                    "• **Student Care**: Kisi bhi emergency ya administrative guidance ke liye Room 101 visit karein."
                )
                voice_text = f"{student_name}, Block 1 me 24 ghante Health Center open hai jahan free checkup aur medicines milti hain. Pure campus me high speed Wi-Fi aur sports facilities accessible hain."
            else:
                answer = (
                    f"{student_name}, key University Student Welfare and Campus Amenities:\n\n"
                    "• **24×7 Campus Health Center**: Located in Block 1 (Ground Floor), offering round-the-clock emergency medical response, qualified resident physicians, ambulance, and complimentary generic medicines.\n"
                    "• **Campus-Wide Wi-Fi**: High-speed gigabit Wi-Fi network ('UniNet-Student') accessible across all academic departments, libraries, and student hostels.\n"
                    "• **Sports & Recreation Complex**: Modern gymnasium, Olympic running track, basketball courts, and indoor sports arena open daily from 6:00 AM to 9:00 PM.\n"
                    "• **Administrative Helpdesk**: Front office support available in Room 101, Main Administrative Building."
                )
                voice_text = f"{student_name}, the Campus Health Center in Block 1 is open 24 hours with free doctors and ambulance services. High-speed student Wi-Fi and comprehensive sports facilities are available campus-wide."

            res = {
                "answer": answer,
                "domain": "Campus Facilities & Welfare",
                "citations": [health_policy],
                "recommended_action": "View Campus Services Directory",
                "action_url": "/services",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_id_card_query:
            id_policy = next((p for p in policies if p["doc_id"] == "PROC-FORM-STUDENT-ID"), DEFAULT_POLICIES[11] if len(DEFAULT_POLICIES) > 11 else DEFAULT_POLICIES[0])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, यदि आपका छात्र पहचान पत्र (Student ID Card) खो गया है, तो आप 48 घंटे में नया बायोमेट्रिक आईडी कार्ड प्राप्त कर सकते हैं:\n\n"
                    "1. कियोस्क से छात्र आईडी कार्ड पुनः जारी फॉर्म (Form 28) डाउनलोड करके डिजिटल भरें।\n"
                    "2. ₹200 का पुनः जारी शुल्क स्क्रीन पर 1-टैप स्मार्ट ऑफसेट (कॉशन डिपॉजिट) से सीधे चुकाएं।\n"
                    "3. एक पासपोर्ट साइज फोटो और पुलिस गुमशुदगी रिपोर्ट (GD/NCR) की डिजिटल कॉपी संलग्न करें।\n"
                    "4. आवेदन कियोस्क पोर्टल (/forms) या छात्र सहायता डेस्क (कक्ष 101 / Room 101) पर जमा करें। आपका नया कार्ड 48 घंटे में तैयार हो जाएगा।"
                )
                voice_text = f"{student_name}, डुप्लिकेट आईडी कार्ड के लिए फॉर्म 28 कियोस्क से भरें, ₹200 शुल्क स्मार्ट ऑफसेट से चुकाएं और डिजिटल सबमिट करें। नया कार्ड 48 घंटे में मिल जाएगा।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, agar aapka student ID card kho gaya hai toh aap 48 ghante me duplicate ID card prapt kar sakte hain:\n\n"
                    "1. Kiosk se Student ID Card Re-issue Form (Form 28) download karke digitally fill karein.\n"
                    "2. ₹200 fee kiosk screen par 1-tap smart caution deposit offset se direct settle karein.\n"
                    "3. 1 passport size photo aur police lost report (GD/NCR copy) attach karein.\n"
                    "4. Application kiosk portal (/forms) ya Student Support Desk (Room 101) par submit karein. 48 hours me naya smart card ready ho jayega."
                )
                voice_text = f"{student_name}, duplicate ID card ke liye Form 28 kiosk se bhar kar 200 rupees caution deposit se smart offset karein. 48 ghante me card ready ho jayega."
            else:
                answer = (
                    f"{student_name}, if your student ID card is lost, you can obtain a duplicate biometric smart card within 48 hours:\n\n"
                    "1. Download and fill the Student ID Card Re-issue Form (Form 28) directly on this kiosk.\n"
                    "2. Settle the ₹200 re-issue fee via 1-tap Smart Caution Deposit Offsetting directly on screen (no cash queues).\n"
                    "3. Attach 1 passport photograph and a copy of your police lost report / NCR.\n"
                    "4. Submit your application digitally on this kiosk portal (/forms) or at Student Support Desk (Room 101). Turnaround SLA is 48 hours for biometric card collection."
                )
                voice_text = f"{student_name}, for a duplicate ID card, fill Form 28 on this kiosk, settle the 200 Rupees fee via smart caution deposit offset, and submit digitally. It will be ready in 48 hours."

            res = {
                "answer": answer,
                "domain": "Student ID Services",
                "citations": [id_policy],
                "recommended_action": "Download Duplicate ID Form (Form 28)",
                "action_url": "/forms",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_day_scholar_hostel_query:
            hostel_policy = next((p for p in policies if p["clause_code"] == "ORD-HST-5.1"), DEFAULT_POLICIES[5])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, विश्वविद्यालय अध्यादेश ORD-HST-5.1 के अनुसार हॉस्टल क्लीयरेंस नियमावली:\n\n"
                    "1. **डे-स्कॉलर (गैर-हॉस्टलर छात्र)**: आपको हॉस्टल जाने या वार्डन से क्लीयरेंस लेने की बिल्कुल आवश्यकता नहीं है। डिजिटल 4-गेट क्लीयरेंस पाइपलाइन में गेट 2 (हॉस्टल एवं मेस) आपके लिए स्वतः **BYPASSED / लागू नहीं** चिह्नित हो जाता है।\n"
                    "2. **हॉस्टल निवासी छात्र**: केवल कैंपस हॉस्टल में रहने वाले छात्रों को वार्डन के साथ डिजिटल रूम इन्वेंट्री सत्यापन पूरा करना होता है।\n"
                    "3. **100% डिजिटल पाइपलाइन**: किसी भौतिक कार्यालय जाने की आवश्यकता नहीं है; आप कियोस्क पोर्टल ('/withdrawal') पर अपनी लाइव क्लीयरेंस सीधे ट्रैक कर सकते हैं।"
                )
                voice_text = f"{student_name}, यदि आप डे-स्कॉलर हैं, तो आपको हॉस्टल क्लीयरेंस की बिल्कुल जरूरत नहीं है, यह गेट स्वतः बायपास हो जाता है। केवल हॉस्टल निवासियों को वार्डन से डिजिटल क्लीयरेंस चाहिए होती है।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, University Ordinance ORD-HST-5.1 ke mutabiq Hostel Clearance rules:\n\n"
                    "1. **Day-Scholars (Non-Hostellers)**: Aapko hostel jane ya warden se clearance lene ki koi zarurat nahi hai. Digital 4-Gate pipeline me Gate 2 (Hostel & Mess) aapke liye automatically **BYPASSED / NOT APPLICABLE** mark ho jata hai.\n"
                    "2. **Hostel Residents**: Sirf campus hostel me rehne wale students ko Warden ke sath digital room inventory sign-off karna hota hai.\n"
                    "3. **Digital Pipeline**: Kisi physical office jane ki zarurat nahi hai; aap '/withdrawal' par live status track kar sakte hain."
                )
                voice_text = f"{student_name}, day scholars ke liye hostel clearance automatically bypass ho jata hai, hostel jane ki koi zarurat nahi hai. Yeh sirf hostel me rehne wale students ke liye applicable hai."
            else:
                answer = (
                    f"{student_name}, under University Ordinance ORD-HST-5.1, hostel clearance criteria are as follows:\n\n"
                    "1. **Day-Scholars (Non-Hostellers)**: You do NOT need to visit the hostel or obtain warden clearance. In the digital 4-Gate clearance pipeline, Gate 2 (Hostel & Mess) is automatically marked as **BYPASSED / NOT APPLICABLE** for day scholars.\n"
                    "2. **Residential Hostellers**: Only registered students who resided in university hostels must complete room inventory handover with the Warden.\n"
                    "3. **100% Digital Pipeline**: No physical visits required. You can view your live clearance status directly on this kiosk under '/withdrawal'."
                )
                voice_text = f"{student_name}, as a day scholar, you do not need hostel clearance at all; Gate 2 is automatically bypassed. It only applies to students residing in university hostels."

            res = {
                "answer": answer,
                "domain": "Hostel & Accommodation",
                "citations": [hostel_policy],
                "recommended_action": "View Clearance Status",
                "action_url": "/withdrawal",
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_hostel_vacate_query:
            hostel_policy = next((p for p in policies if p["doc_id"] in ("POL-HSTL-01", "PROC-FORM-HOSTEL-CLR")), DEFAULT_POLICIES[5])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, हॉस्टल कमरा खाली करने और सिक्योरिटी डिपॉजिट वापस प्राप्त करने की आधिकारिक प्रक्रिया:\n\n"
                    "1. कियोस्क से हॉस्टल वेकेशन एवं हैंडओवर क्लीयरेंस फॉर्म डाउनलोड करें।\n"
                    "2. कमरा छोड़ने से 24 घंटे पहले सहायक वार्डन के साथ डिजिटल इन्वेंट्री सत्यापन कराएं।\n"
                    "3. कमरे और अलमारी की चाबियां हॉस्टल प्रशासन डेस्क (कक्ष 102 / Room 102) को डिजिटल रसीद के साथ सौंपें।\n"
                    "4. वार्डन डिजिटल क्लीयरेंस के बाद आपकी हॉस्टल सिक्योरिटी डिपॉजिट 7 कार्य दिवसों में बैंक खाते में वापस कर दी जाएगी।"
                )
                voice_text = f"{student_name}, हॉस्टल खाली करने के लिए इन्वेंट्री जांच करवाकर चाबियां हॉस्टल प्रशासन को सौंपें। सिक्योरिटी डिपॉजिट 7 दिनों में सीधे बैंक खाते में वापस मिल जाएगी।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, hostel room vacate karne aur security deposit wapas lene ke liye verified steps yeh hain:\n\n"
                    "1. Kiosk se Hostel Vacation Clearance Form download karein.\n"
                    "2. Room chhodne se 24 ghante pehle Assistant Warden ke sath inventory check karayein.\n"
                    "3. Room aur almirah keys Hostel Administration Desk (Room 102) ko hand over karein.\n"
                    "4. Warden digital sign-off ke baad aapki refundable security deposit 7 working days me account me aa jayegi."
                )
                voice_text = f"{student_name}, hostel vacate karne ke liye Assistant Warden se inventory verify karwake keys handover karein. Deposit 7 din me direct bank account me refund hogi."
            else:
                answer = (
                    f"{student_name}, to vacate your hostel room and claim your security deposit refund under Ordinance ORD-HSTL-18.2:\n\n"
                    "1. Download the Hostel Vacation & Handover Clearance Form from this kiosk.\n"
                    "2. Complete room inventory verification with the Assistant Warden 24 hours prior to departure.\n"
                    "3. Hand over your room and almirah keys to the Hostel Administration Desk (Room 102).\n"
                    "4. Obtain the Warden's digital clearance. Your refundable security deposit will be processed within 7 working days to your bank account."
                )
                voice_text = f"{student_name}, to vacate the hostel, complete an inventory check with the Warden and hand over your keys. Your security deposit will be refunded within 7 working days directly to your bank account."

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
                    "2. निर्धारित शुल्क: ₹500 प्रति विषय/पेपर (ऑनलाइन पोर्टल या कियोस्क पर देय)।\n"
                    "3. समय सीमा: परिणाम घोषित होने के 15 दिनों के भीतर आवेदन करना अनिवार्य है।\n"
                    "4. डिजिटल सबमिशन: परीक्षा एवं पुनर्मूल्यांकन पोर्टल (/exams) पर ऑनलाइन जमा करें। संशोधित परिणाम 21 कार्य दिवसों में जारी किया जाता है।"
                )
                voice_text = f"{student_name}, रीचेकिंग के लिए परिणाम के 15 दिनों के भीतर फॉर्म 27 भरकर ₹500 प्रति पेपर के साथ परीक्षा पोर्टल पर डिजिटल सबमिट करें। SLA 21 कार्यदिवस है।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, answer script rechecking aur re-evaluation ke verified rules yeh hain:\n\n"
                    "1. Application: Kiosk se Form 27 (Rechecking Form) download karein.\n"
                    "2. Fee: ₹500 per subject paper, payable online ya kiosk portal par.\n"
                    "3. Deadline: Result declare hone ke 15 calendar days ke andar apply karna compulsory hai.\n"
                    "4. Submission: Examination Portal (/exams) par digitally submit karein. Processing SLA 21 working days hai."
                )
                voice_text = f"{student_name}, rechecking ke liye result aane ke 15 din ke andar Form 27 fill karke 500 rupees per paper ke sath Examination Portal par submit karein."
            else:
                answer = (
                    f"{student_name}, for answer script re-evaluation and rechecking under University Ordinance ORD-EXAM-12.4:\n\n"
                    "1. Application Form: Download Form 27 (Application for Rechecking of Result) from this kiosk.\n"
                    "2. Prescribed Fee: ₹500 per subject/course paper, payable online via the fee gateway.\n"
                    "3. Submission Window: You must apply within 15 calendar days of result declaration.\n"
                    "4. Submission: Examination & Rechecking Portal (/exams) or Examination Cell Window 3. The re-evaluated result SLA is 21 working days."
                )
                voice_text = f"{student_name}, for re-evaluation, submit Form 27 with 500 Rupees per paper on the Examination Portal within 15 days of result declaration."

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

        elif is_ticket_status_query:
            grievance_policy = next((p for p in policies if p["clause_code"] == "ORD-GRV-22.5"), DEFAULT_POLICIES[6])
            dept_routing = {
                "academic": "Department Academic Coordinator",
                "fee": "Finance & Accounts Office",
                "hostel": "Chief Warden & Hostel Office",
                "exam": "Controller of Examinations",
                "scholarship": "Dean of Student Welfare (Scholarships Desk)"
            }

            # 1. Parse specific ticket number from query if present
            ticket_match = re.search(r"grv[-\s]?(\d{4})[-\s]?(\d+)", q_lower)
            explicit_ticket_num = None
            if ticket_match:
                try:
                    explicit_ticket_num = int(ticket_match.group(2))
                except ValueError:
                    pass
            elif re.search(r"\bticket\s*#?(\d+)\b", q_lower):
                m = re.search(r"\bticket\s*#?(\d+)\b", q_lower)
                explicit_ticket_num = int(m.group(1))

            choice_num_match = re.search(r"\b([1-9])\b", q_clean)
            selected_option_idx = int(choice_num_match.group(1)) if (choice_num_match and len(q_clean.split()) <= 4) else None

            # 2. Guest user with no ticket ID
            if not is_authenticated and not explicit_ticket_num:
                if language == "hi-IN":
                    ans = (
                        "कियोस्क पर अपनी शिकायत (Grievance Ticket) या विड्रॉल आवेदन का स्टेटस देखने के लिए कृपया अपने Student ID से लॉगिन करें, "
                        "अथवा अपना टिकट नंबर बताएं (उदाहरण: 'status of ticket GRV-2026-0010')।"
                    )
                    v_ans = "कृपया अपनी शिकायत का स्टेटस देखने के लिए लॉगिन करें या अपना टिकट नंबर बताएं।"
                elif language == "hi-Latn":
                    ans = (
                        "Kiosk par apna Grievance Ticket ya Withdrawal request status track karne ke liye please Student ID se login karein, "
                        "ya apna specific Ticket ID batayein (jaise: 'status of ticket GRV-2026-0010')."
                    )
                    v_ans = "Apna ticket status dekhne ke liye please login karein ya ticket ID batayein."
                else:
                    ans = (
                        "To track the status of your grievance ticket or submitted request on this kiosk, "
                        "please log in with your Student ID, or provide your specific Ticket ID (e.g., 'status of ticket GRV-2026-0010')."
                    )
                    v_ans = "Please log in with your Student ID or provide your Ticket ID to check ticket status."

                res = {
                    "answer": ans,
                    "domain": "Student Grievance & Welfare",
                    "citations": [grievance_policy],
                    "recommended_action": "Log In to UniAssist",
                    "action_url": "/chat",
                    "voice_speech_text": v_ans,
                    "engine": "UniAssist Policy Engine",
                }
            else:
                # 3. Retrieve tickets from database
                student_grievances = []
                if is_authenticated:
                    cur = conn.execute(
                        "SELECT id, student_id, category, description, status, resolution, timestamp FROM grievances WHERE student_id = ? ORDER BY id DESC",
                        (student["id"],)
                    )
                    student_grievances = [dict(r) for r in cur.fetchall()]

                target_ticket = None
                if explicit_ticket_num:
                    cur = conn.execute(
                        "SELECT id, student_id, category, description, status, resolution, timestamp FROM grievances WHERE id = ?",
                        (explicit_ticket_num,)
                    )
                    row = cur.fetchone()
                    if row:
                        target_ticket = dict(row)

                # If selected from numeric choice (1, 2, 3...)
                if not target_ticket and selected_option_idx and student_grievances and 1 <= selected_option_idx <= len(student_grievances):
                    target_ticket = student_grievances[selected_option_idx - 1]

                if target_ticket:
                    t_id = target_ticket["id"]
                    t_code = f"GRV-2026-{t_id:04d}"
                    t_cat = target_ticket.get("category", "academic").title()
                    t_desc = target_ticket.get("description", "No description provided")
                    t_stat = target_ticket.get("status", "open").upper()
                    t_res = target_ticket.get("resolution") or "Under investigation by assigned coordinator. Resolution in progress."
                    t_assigned = dept_routing.get(target_ticket.get("category", "academic"), "Proctorial Board")
                    t_time = target_ticket.get("timestamp", "Recently filed")
                    sla_hrs = 48 if target_ticket.get("category") in ("academic", "fee") else 72

                    if language == "hi-IN":
                        ans = (
                            f"{student_name}, आपके टिकट **{t_code}** का सत्यापित डेटाबेस स्टेटस:\n\n"
                            f"• **विषय / श्रेणी**: {t_cat}\n"
                            f"• **वर्तमान स्थिति**: **{t_stat}**\n"
                            f"• **प्रभारी विभाग**: {t_assigned}\n"
                            f"• **विवरण**: {t_desc}\n"
                            f"• **समाधान / कार्रवाई**: {t_res}\n"
                            f"• **अनिवार्य SLA**: {sla_hrs} घंटे (अध्यादेश ORD-GRV-22.5)\n"
                            f"• **दर्ज करने की तिथि**: {t_time}"
                        )
                        v_ans = f"टिकट {t_code} वर्तमान में {t_stat} स्थिति में है और {t_assigned} द्वारा संसाधित किया जा रहा है।"
                    elif language == "hi-Latn":
                        ans = (
                            f"{student_name}, aapke ticket **{t_code}** ka verified database status:\n\n"
                            f"• **Category**: {t_cat}\n"
                            f"• **Status**: **{t_stat}**\n"
                            f"• **Assigned Coordinator**: {t_assigned}\n"
                            f"• **Description**: {t_desc}\n"
                            f"• **Resolution Progress**: {t_res}\n"
                            f"• **Resolution SLA**: {sla_hrs} hours under Ordinance ORD-GRV-22.5\n"
                            f"• **Submission Date**: {t_time}"
                        )
                        v_ans = f"Ticket {t_code} currently {t_stat} status me hai aur {t_assigned} ise review kar rahe hain."
                    else:
                        ans = (
                            f"{student_name}, here is the actual persisted status for Ticket **{t_code}** from university records:\n\n"
                            f"• **Category**: {t_cat}\n"
                            f"• **Current Status**: **{t_stat}**\n"
                            f"• **Assigned Office**: {t_assigned}\n"
                            f"• **Filed Description**: {t_desc}\n"
                            f"• **Resolution Notes**: {t_res}\n"
                            f"• **Resolution SLA**: {sla_hrs} hours under Ordinance ORD-GRV-22.5\n"
                            f"• **Submission Date**: {t_time}"
                        )
                        v_ans = f"Ticket {t_code} is currently {t_stat} and assigned to {t_assigned}."

                    res = {
                        "answer": ans,
                        "domain": "Student Grievance & Welfare",
                        "citations": [grievance_policy],
                        "recommended_action": f"Track Ticket {t_code}",
                        "action_url": "/chat",
                        "voice_speech_text": v_ans,
                        "engine": "UniAssist Policy Engine",
                    }

                elif len(student_grievances) == 1:
                    t = student_grievances[0]
                    t_id = t["id"]
                    t_code = f"GRV-2026-{t_id:04d}"
                    t_cat = t.get("category", "academic").title()
                    t_desc = t.get("description", "No description provided")
                    t_stat = t.get("status", "open").upper()
                    t_res = t.get("resolution") or "Under active review by assigned department coordinator."
                    t_assigned = dept_routing.get(t.get("category", "academic"), "Proctorial Board")
                    t_time = t.get("timestamp", "Recently filed")
                    sla_hrs = 48 if t.get("category") in ("academic", "fee") else 72

                    if language == "hi-IN":
                        ans = (
                            f"{student_name}, आपके रिकॉर्ड पर 1 सक्रिय टिकट है। **{t_code}** का स्टेटस:\n\n"
                            f"• **श्रेणी**: {t_cat}\n"
                            f"• **स्थिति**: **{t_stat}**\n"
                            f"• **प्रभारी**: {t_assigned}\n"
                            f"• **विवरण**: {t_desc}\n"
                            f"• **कार्रवाई**: {t_res}\n"
                            f"• **SLA**: {sla_hrs} घंटे"
                        )
                    else:
                        ans = (
                            f"{student_name}, you have 1 active grievance ticket on record. Here is the verified status for **{t_code}**:\n\n"
                            f"• **Category**: {t_cat}\n"
                            f"• **Status**: **{t_stat}**\n"
                            f"• **Assigned Office**: {t_assigned}\n"
                            f"• **Description**: {t_desc}\n"
                            f"• **Resolution Status**: {t_res}\n"
                            f"• **Resolution SLA**: {sla_hrs} hours under Ordinance ORD-GRV-22.5\n"
                            f"• **Submission Date**: {t_time}"
                        )

                    res = {
                        "answer": ans,
                        "domain": "Student Grievance & Welfare",
                        "citations": [grievance_policy],
                        "recommended_action": f"Track Ticket {t_code}",
                        "action_url": "/chat",
                        "voice_speech_text": f"Ticket {t_code} is currently {t_stat} under review by {t_assigned}.",
                        "engine": "UniAssist Policy Engine",
                    }

                elif len(student_grievances) > 1:
                    # Multiple tickets: ask student to choose with proper ticket names & IDs (F15 requirement)
                    options_list = []
                    chat_lines = []
                    for idx, t in enumerate(student_grievances[:5], 1):
                        t_code = f"GRV-2026-{t['id']:04d}"
                        t_cat = t.get("category", "academic").title()
                        short_desc = t.get("description", "")
                        if len(short_desc) > 40:
                            short_desc = short_desc[:37] + "..."
                        t_stat = t.get("status", "open").capitalize()
                        label = f"📋 [{t_code}] {t_cat}: '{short_desc}' ({t_stat})"
                        options_list.append({
                            "label": label,
                            "value": f"ticket {t_code}",
                            "action_url": "/chat",
                        })
                        chat_lines.append(f"   [{idx}] **{t_code}**: {t_cat} - \"{short_desc}\" (Status: **{t_stat}**)")

                    options_str = "\n".join(chat_lines)
                    if language == "hi-IN":
                        ans = (
                            f"{student_name}, आपके रिकॉर्ड पर {len(student_grievances)} शिकायत टिकट दर्ज हैं। "
                            f"कृपया बताएं कि आप किस टिकट का स्टेटस देखना चाहते हैं:\n\n"
                            f"{options_str}\n\n"
                            "कृपया विकल्प संख्या (जैसे '1') या टिकट नंबर लिखकर बताएं।"
                        )
                        v_ans = f"आपके {len(student_grievances)} टिकट दर्ज हैं। कृपया विकल्प संख्या चुनकर बताएं।"
                    elif language == "hi-Latn":
                        ans = (
                            f"{student_name}, aapke record par {len(student_grievances)} grievance tickets available hain. "
                            f"Aap kis ticket ka status track karna chahte hain? Choose karein:\n\n"
                            f"{options_str}\n\n"
                            "Reply karein option number (jaise '1') ya Ticket ID ke saath."
                        )
                        v_ans = f"Aapke {len(student_grievances)} tickets hain. Please option number ya ticket ID choose karein."
                    else:
                        ans = (
                            f"{student_name}, you have {len(student_grievances)} grievance tickets on record. "
                            f"Please select which ticket status you would like to track:\n\n"
                            f"{options_str}\n\n"
                            "Reply with the option number (e.g., '1') or Ticket ID to view full progress."
                        )
                        v_ans = f"You have {len(student_grievances)} tickets on record. Please select option 1 or reply with the ticket ID."

                    res = {
                        "status": "trigger_cross_question",
                        "is_ambiguous": True,
                        "answer": ans,
                        "domain": "Student Grievance & Welfare",
                        "citations": [grievance_policy],
                        "recommended_action": "Select Ticket",
                        "action_url": "/chat",
                        "voice_speech_text": v_ans,
                        "clarification_options": options_list,
                        "engine": "UniAssist Policy Engine",
                    }

                else:
                    if language == "hi-IN":
                        ans = (
                            f"{student_name}, आपके नाम पर वर्तमान में कोई सक्रिय शिकायत टिकट या विड्रॉल आवेदन दर्ज नहीं है। "
                            "क्या आप किसी समस्या के लिए नई शिकायत दर्ज करना चाहते हैं?"
                        )
                    else:
                        ans = (
                            f"{student_name}, you do not have any active grievance tickets or withdrawal requests on record. "
                            "Would you like to file a formal grievance ticket right now?"
                        )

                    res = {
                        "answer": ans,
                        "domain": "Student Grievance & Welfare",
                        "citations": [grievance_policy],
                        "recommended_action": "File Formal Grievance",
                        "action_url": "/chat",
                        "voice_speech_text": ans,
                        "engine": "UniAssist Policy Engine",
                    }

        elif is_grievance_query:
            grievance_policy = next((p for p in policies if p["clause_code"] == "ORD-GRV-22.5"), DEFAULT_POLICIES[6])
            if language == "hi-IN":
                answer = (
                    f"{student_name}, छात्र सुरक्षा और शिकायत निवारण अध्यादेश ORD-GRV-22.5 के तहत पूरी तरह संरक्षित हैं:\n\n"
                    "1. रैगिंग पर शून्य सहनशीलता: रैगिंग या उत्पीड़न की किसी भी शिकायत पर 24 घंटे के भीतर आपातकालीन प्रॉक्टोरियल जांच और कार्रवाई होती है।\n"
                    "2. अनिवार्य समय सीमा (SLA): सामान्य शैक्षणिक और सुविधा संबंधी शिकायतों का 48 घंटे के भीतर अनिवार्य निवारण किया जाता है।\n"
                    "3. डिजिटल शिकायत डेस्क: आप कियोस्क से सीधे ऑनलाइन शिकायत दर्ज कर सकते हैं (/chat)। यदि 48 घंटे में समाधान न हो तो टिकट स्वतः उच्च अधिकारियों को एस्केलेट हो जाता है।"
                )
                voice_text = f"{student_name}, रैगिंग या उत्पीड़न पर तुरंत 24 घंटे में आपातकालीन कार्रवाई होती है। आप सीधे इस कियोस्क से डिजिटल शिकायत दर्ज कर सकते हैं।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, campus safety aur grievance redressal Ordinance ORD-GRV-22.5 ke under guaranteed hai:\n\n"
                    "1. Zero Tolerance Anti-Ragging: Ragging ya harassment par immediate 24-hour Proctorial emergency action hoti hai Anti-Ragging Cell (Room 105) dwara.\n"
                    "2. Resolution SLA: Academic aur campus facility grievances ka mandatory 48-hour resolution SLA hai.\n"
                    "3. Digital Grievance: Aap kiosk par direct digital grievance ticket lodge kar sakte hain (/chat). 48 hours me resolve na hone par ticket automatically escalate ho jata hai."
                )
                voice_text = f"{student_name}, ragging par 24-hour emergency SLA hai. Aap direct is kiosk se digital complaint register kar sakte hain."
            else:
                answer = (
                    f"{student_name}, student safety and grievances are strictly governed under Ordinance ORD-GRV-22.5:\n\n"
                    "1. Zero Tolerance for Ragging: Any harassment or ragging allegation triggers an immediate 24-hour emergency Proctorial investigation at Anti-Ragging Cell (Room 105).\n"
                    "2. Mandatory SLA: General academic and facility grievances carry a mandatory 48-hour resolution SLA by the Department Coordinator, escalating to Dean Student Welfare.\n"
                    "3. Digital Lodge: You can lodge a formal grievance ticket right now on this kiosk (/chat) with automated SLA escalation."
                )
                voice_text = f"{student_name}, ragging carries a zero tolerance policy and an emergency 24-hour response. You can file a formal grievance directly on this kiosk."

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
                    "3. आवेदन: नया सेमेस्टर शुरू होने के 15 दिनों के भीतर फॉर्म SCH-01 और ग्रेड कार्ड छात्रवृत्ति पोर्टल (/scholarship) पर ऑनलाइन जमा करें।\n"
                    "4. वित्तीय सहायता: ₹3,00,000 से कम वार्षिक पारिवारिक आय वाले छात्र आय प्रमाण पत्र के साथ आवेदन कर सकते हैं।"
                )
                voice_text = f"{student_name}, मेरिट छात्रवृत्ति के लिए न्यूनतम 8.0 CGPA, 80% उपस्थिति और शून्य बैकपेपर होना अनिवार्य है। छात्रवृत्ति पोर्टल पर फॉर्म SCH-01 जमा करें।"
            elif language == "hi-Latn":
                answer = (
                    f"{student_name}, merit scholarship renewal criteria Ordinance ORD-SCH-16.3 ke under yeh hain:\n\n"
                    "1. Criteria: Minimum 8.0 CGPA, 80% previous semester attendance, aur zero backpapers.\n"
                    "2. Benefit: Upcoming semester tuition fee me 50% waiver.\n"
                    "3. Renewal: Semester shuru hone ke 15 days me Form SCH-01 aur grade card Scholarship Portal (/scholarship) par submit karein."
                )
                voice_text = f"{student_name}, scholarship renewal ke liye minimum 8.0 CGPA aur 80 percent attendance zaroori hai. Scholarship Portal par Form SCH-01 submit karein."
            else:
                answer = (
                    f"{student_name}, university scholarships and concessions are governed by Ordinance ORD-SCH-16.3:\n\n"
                    "1. Merit Scholarship Renewal Criteria: You must maintain a minimum CGPA of 8.0, achieve at least 80% overall attendance in the preceding semester, and have zero active backpapers.\n"
                    "2. Benefit: 50% tuition fee waiver for the upcoming academic year.\n"
                    "3. Submission: Submit Form SCH-01 with semester grade cards directly through the digital Scholarships Portal (/scholarship) or at the Scholarship & Financial Aid Cell (Room 204) within 15 calendar days of semester commencement.\n"
                    "4. Need-Based Aid: Concessions require annual submission of verified family income certificate (< ₹3 Lakh p.a.)."
                )
                voice_text = f"{student_name}, merit scholarship renewal requires a minimum 8.0 CGPA, 80 percent attendance, and zero backpapers. Submit Form SCH-01 via the Scholarship Portal."

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

            if is_staff_user:
                # Query database for current pending withdrawal requests in the review queue
                wth_rows = conn.execute(
                    """SELECT w.id, w.student_id, COALESCE(s.name, w.student_id) AS student_name, 
                              w.reason, w.status, w.reference_no, w.timestamp
                       FROM withdrawal_requests w
                       LEFT JOIN students s ON w.student_id = s.id
                       ORDER BY w.timestamp DESC"""
                ).fetchall()
                pending_wths = [dict(r) for r in wth_rows if str(r["status"]).lower() in ("pending", "under_review", "in_review", "submitted", "in_flight", "open")]
                total_wths = len(wth_rows)
                pending_count = len(pending_wths)

                if pending_count > 0:
                    summary_lines = []
                    for idx, pw in enumerate(pending_wths[:5], 1):
                        ref = pw.get("reference_no") or f"WTH-REQ-{pw['id']}"
                        sname = pw.get("student_name") or pw.get("student_id")
                        sid = pw.get("student_id")
                        stat = pw.get("status", "pending").upper()
                        summary_lines.append(f"   {idx}. **{sname}** ({sid}) — Ref: `{ref}` [{stat}]")
                    queue_text = "\n".join(summary_lines)

                    if language == "hi-IN":
                        staff_ans = (
                            f"{staff_designation}, समीक्षा कतार (Review Queue) में वर्तमान में **{pending_count} छात्र विड्रॉल आवेदन** लंबित हैं:\n\n"
                            f"{queue_text}\n\n"
                            "प्रशासनिक सत्यापन हेतु आप नीचे दिए गए **'Open Withdrawal Review Queue'** बटन पर क्लिक करके डिजिटल क्लीयरेंस गेट्स (लाइब्रेरी, हॉस्टल, अकाउंट्स) की समीक्षा व अनुमोदन कर सकते हैं।"
                        )
                        staff_v = f"{staff_designation}, वर्तमान में {pending_count} छात्र विड्रॉल आवेदन समीक्षा हेतु लंबित हैं।"
                    elif language == "hi-Latn":
                        staff_ans = (
                            f"{staff_designation}, Review Queue me filhaal **{pending_count} student withdrawal applications** pending hain:\n\n"
                            f"{queue_text}\n\n"
                            "Verification aur gate clearance review ke liye neeche **'Open Withdrawal Review Queue'** par click karein."
                        )
                        staff_v = f"{staff_designation}, review queue me {pending_count} withdrawal requests pending hain. Staff portal par clearance gates review karein."
                    else:
                        staff_ans = (
                            f"{staff_designation}, there are currently **{pending_count} pending student withdrawal request(s)** awaiting administrative review:\n\n"
                            f"{queue_text}\n\n"
                            "To audit submitted documents and sign off on clearance gates (Library, Hostel, Accounts, Registrar), please click **'Open Withdrawal Review Queue'** below."
                        )
                        staff_v = f"{staff_designation}, there are {pending_count} student withdrawal applications pending review in your administrative queue."
                else:
                    if language == "hi-IN":
                        staff_ans = (
                            f"{staff_designation}, वर्तमान में समीक्षा कतार (Review Queue) में **0 छात्र विड्रॉल आवेदन** लंबित हैं। "
                            "सभी छात्र क्लीयरेंस गेट्स पूर्णतः अद्यतन और स्वीकृत (Clear & Up to date) हैं।\n\n"
                            "यदि आप यूजीसी रिफंड स्लैब (ORD-WTH-14.1) अथवा कॉशन डिपॉजिट ऑफसेट ऑडिट नियमों की समीक्षा करना चाहते हैं, तो वे नीचे संदर्भित हैं।"
                        )
                        staff_v = f"{staff_designation}, वर्तमान में कोई विड्रॉल आवेदन लंबित नहीं है। सभी क्लीयरेंस कतारें पूर्ण हैं।"
                    elif language == "hi-Latn":
                        staff_ans = (
                            f"{staff_designation}, Review Queue me abhi **0 student withdrawal requests** pending hain. "
                            "Sabhi student clearance gates completely clear aur up-to-date hain.\n\n"
                            "UGC refund mandates (ORD-WTH-14.1) aur cautionary deposit offset rules verified hain."
                        )
                        staff_v = f"{staff_designation}, filhaal koi withdrawal application pending nahi hai. All review gates are clear."
                    else:
                        staff_ans = (
                            f"{staff_designation}, there are currently **0 pending student withdrawal applications** in the administrative review queue. "
                            "All student departure and clearance workflows are currently clear and up to date.\n\n"
                            "For reference, official UGC 2024 refund mandates (ORD-WTH-14.1) and caution deposit settlement procedures (ORD-FIN-14.4) are active."
                        )
                        staff_v = f"{staff_designation}, there are currently 0 pending student withdrawal requests. All review queues are clear."

                return {
                    "answer": staff_ans,
                    "domain": "Staff Clearance & Withdrawal Queue",
                    "citations": [wth_policy, offset_policy],
                    "recommended_action": "Open Withdrawal Review Queue",
                    "action_url": "/staff/withdrawals",
                    "voice_speech_text": staff_v,
                    "engine": "UniAssist Policy Engine",
                }

            # Dynamically fetch configured workflow steps
            try:
                from .procedure_service import ProcedureService
                live_steps = ProcedureService.get_steps("withdrawal")
            except Exception:
                live_steps = []

            if live_steps:
                num_steps = len(live_steps)
                steps_titles = ", ".join([s.get("title", "") for s in live_steps])
                steps_detail = "\n   " + "\n   ".join([f"• Step {s['step_number']}: {s['title']} ({s['department']})" for s in live_steps])
            else:
                num_steps = 4
                steps_titles = "Central Library, Hostel & Mess (Conditional), Finance & Accounts, Registrar Office"
                steps_detail = ""

            guest_note_en = (
                "\n\n💡 **Student Account Access**: To view your personalized clearance gates, verify if hostel clearance applies to your profile, and track your active refund voucher, please log in with your Student ID."
                if not is_authenticated else
                f"\n\n👤 **Active Student Session ({student_name})**: You can initiate or track your live clearance pipeline, trigger 1-tap caution deposit offsets, and download your approved clearance slip under '/withdrawal'."
            )
            guest_note_hi = (
                "\n\n💡 **छात्र खाता सूचना**: अपने व्यक्तिगत क्लीयरेंस गेट्स देखने, हॉस्टल छूट स्थिति जांचने, और वास्तविक रिफंड वाउचर ट्रैक करने हेतु कृपया अपनी छात्र आईडी से लॉगिन करें।"
                if not is_authenticated else
                f"\n\n👤 **सक्रिय सत्र ({student_name})**: आप '/withdrawal' सेक्शन में अपनी लाइव क्लीयरेंस पाइपलाइन ट्रैक कर सकते हैं और अप्रूव्ड क्लीयरेंस स्लिप डाउनलोड कर सकते हैं।"
            )
            guest_note_latn = (
                "\n\n💡 **Student Login Note**: Apne personalized clearance gates, hostel clearance applicability aur real-time refund voucher track karne ke liye Student ID se login karein."
                if not is_authenticated else
                f"\n\n👤 **Active Session ({student_name})**: Aap '/withdrawal' me jakar apni live clearance pipeline track kar sakte hain aur approved clearance slip download kar sakte hain."
            )

            if is_staff_user:
                wth_prefix = f"{staff_designation}, administrative guidelines for student withdrawal and fee refunds:\n\n"
                wth_v_prefix = f"{staff_designation}, "
                wth_prefix_hi = f"{staff_designation}, छात्र विड्रॉल एवं फीस रिफंड हेतु प्रशासनिक नियमावली:\n\n"
                wth_prefix_latn = f"{staff_designation}, student withdrawal aur fee refunds ke liye administrative guidelines:\n\n"
            elif is_authenticated:
                wth_prefix = f"{student_name}, "
                wth_v_prefix = f"{student_name}, "
                wth_prefix_hi = f"{student_name}, "
                wth_prefix_latn = f"{student_name}, "
            else:
                wth_prefix = ""
                wth_v_prefix = ""
                wth_prefix_hi = ""
                wth_prefix_latn = ""

            if language == "hi-IN":
                answer = (
                    f"{wth_prefix_hi}विश्वविद्यालय विड्रॉल और फीस रिफंड (अध्यादेश ORD-WTH-14.1 / UGC directives) की सत्यापित प्रक्रिया इस प्रकार है:\n\n"
                    "1. **यूजीसी ट्यूशन फीस रिफंड स्लैब**:\n"
                    "   • प्रवेश अंतिम तिथि से 15 दिन या अधिक पूर्व: 100% रिफंड (अधिकतम ₹1,000 प्रोसेसिंग शुल्क काटकर)\n"
                    "   • 15 दिन से कम पूर्व: 90% रिफंड\n"
                    "   • अंतिम तिथि के 15 दिनों के भीतर: 80% रिफंड\n"
                    "   • 16 से 30 दिनों के भीतर: 50% रिफंड\n"
                    "   • 30 दिनों के बाद: ट्यूशन फीस शून्य रिफंड।\n\n"
                    "2. **कॉशन डिपॉजिट (₹10,000)**: आपकी ₹10,000 की कॉशन डिपॉजिट राशि सभी तिथियों पर 100% वापस की जाती है। यदि कोई मामूली लाइब्रेरी शुल्क या खोए हुए आईडी कार्ड का ₹200 शुल्क है, तो वह कियोस्क पर 1-टैप स्मार्ट ऑफसेट से सीधे एडजस्ट हो जाता है (कैश खिड़की पर जाने की जरूरत नहीं)।\n\n"
                    "3. **4-गेट डिजिटल क्लीयरेंस पाइपलाइन**:\n"
                    "   • **गेट 1 (सेंट्रल लाइब्रेरी)**: किताबों की वापसी एवं बकाये का ऑटोमेटेड डिजिटल सत्यापन।\n"
                    "   • **गेट 2 (हॉस्टल एवं मेस - सशर्त)**: सिस्टम छात्र के आवासीय रिकॉर्ड की पुष्टि करता है। यदि आप डे-स्कॉलर हैं, तो यह गेट स्वतः BYPASSED/NOT APPLICABLE हो जाता है; यदि हॉस्टलर हैं, तो वार्डन डिजिटल इन्वेंट्री साइन-ऑफ करता है।\n"
                    "   • **गेट 3 (वित्त एवं लेखा)**: डिजिटल फीस ऑडिट एवं रिफंड लेजर गणना।\n"
                    "   • **गेट 4 (रजिस्ट्रार समीक्षा एवं नोटशीट)**: डिजिटल नोटशीट सत्यापन उपरांत आधिकारिक डिजिटल क्लीयरेंस स्लिप (PDF) जारी होती है।\n\n"
                    "4. **आवेदन एवं लाइव ट्रैकिंग**: कियोस्क पर नीचे दिए गए बटन ('/withdrawal/flow') से डिजिटल फॉर्म भरें और लाइव ट्रैकिंग करें। यदि किसी डेस्क पर 48 घंटे से अधिक का विलंब हो, तो शिकायत निवारण डेस्क ('/chat') पर तुरंत डिजिटल टिकट दर्ज करें।"
                    f"{guest_note_hi}"
                )
                voice_text = f"{wth_v_prefix}विश्वविद्यालय विड्रॉल में यूजीसी रिफंड स्लैब, 10,000 कॉशन डिपॉजिट रिटर्न और 4 क्लीयरेंस गेट शामिल हैं: लाइब्रेरी, हॉस्टल, एकाउंट्स और रजिस्ट्रार नोटशीट रिव्यू। ऑनलाइन स्टेटस ट्रैक करें।"
            elif language == "hi-Latn":
                answer = (
                    f"{wth_prefix_latn}University withdrawal aur fee refund (ORD-WTH-14.1 / UGC directives) ki verified process is prakaar hai:\n\n"
                    "1. **UGC Tuition Refund Slabs**:\n"
                    "   • 15+ days prior to admission deadline: 100% refund (minus max ₹1,000 processing fee)\n"
                    "   • Less than 15 days prior: 90% refund\n"
                    "   • Up to 15 days post deadline: 80% refund\n"
                    "   • 16 to 30 days post deadline: 50% refund\n"
                    "   • Beyond 30 days: 0% tuition refund.\n\n"
                    "2. **Caution Deposit (₹10,000)**: Aapki ₹10,000 refundable caution deposit har date par 100% safe aur refundable hai. Minor library fines ya ₹200 lost ID charges kiosk par 1-tap smart offset se direct settle ho jate hain bina cash window par line lagaye.\n\n"
                    "3. **4-Gate Digital Clearance Pipeline**:\n"
                    "   • **Gate 1 (Central Library)**: Automated digital check for returned books & dues.\n"
                    "   • **Gate 2 (Hostel & Mess - Conditional)**: System resident status verify karta hai. Day-scholars ke liye yeh gate automatically BYPASSED rehta hai; Hostellers ke liye Warden digitally inventory sign-off karta hai.\n"
                    "   • **Gate 3 (Finance & Accounts)**: Digital fee ledger audit aur refund reconciliation.\n"
                    "   • **Gate 4 (Registrar Review & Notesheet)**: Digital approval ke baad downloadable official Clearance Slip & No-Dues PDF generate hoti hai.\n\n"
                    "4. **Apply & Real-time Tracking**: Kiosk par '/withdrawal/flow' se apply karein aur real-time track karein. Agar koi desk 48 hours se zyada delay kare toh Grievance Desk (/chat) par direct SLA escalation raise karein."
                    f"{guest_note_latn}"
                )
                voice_text = f"{wth_v_prefix}University withdrawal me UGC refund slabs, 10,000 caution deposit return, aur 4 clearance gates shamil hain: Library, conditional Hostel, Accounts smart offset aur Registrar notesheet review. Bina physical office jaye live track karein."
            else:
                if is_staff_user:
                    wth_intro = f"{staff_designation}, administrative guidelines for student withdrawal and fee refunds (Ordinance ORD-WTH-14.1 & UGC directives):\n\n"
                    voice_text = f"{staff_designation}, administrative guidelines for student withdrawal include UGC tuition refund slabs, full 10,000 Rupees caution deposit return, and 4 clearance gates."
                elif is_authenticated:
                    wth_intro = f"{student_name}, the verified procedure for university withdrawal and fee refund (Ordinance ORD-WTH-14.1 & UGC directives) is:\n\n"
                    voice_text = f"{student_name}, university withdrawal includes UGC tuition refund slabs, full 10,000 Rupees caution deposit return, and 4 clearance gates: Library, conditional Hostel, Accounts audit, and Registrar notesheet review. Track your live progress online."
                else:
                    wth_intro = "The verified procedure for university withdrawal and fee refund (Ordinance ORD-WTH-14.1 & UGC directives) is:\n\n"
                    voice_text = "University withdrawal includes UGC tuition refund slabs, full 10,000 Rupees caution deposit return, and 4 clearance gates: Library, conditional Hostel, Accounts audit, and Registrar notesheet review. Track your live progress online."

                answer = (
                    f"{wth_intro}"
                    "1. **UGC Tuition Refund Slabs**:\n"
                    "   • 15+ days prior to admission deadline: 100% refund (minus max ₹1,000 processing fee)\n"
                    "   • Less than 15 days prior to deadline: 90% refund\n"
                    "   • Up to 15 days post admission deadline: 80% refund\n"
                    "   • 16 to 30 days post admission deadline: 50% refund\n"
                    "   • Beyond 30 days post deadline: 0% tuition refund.\n\n"
                    "2. **Refundable Caution Deposit (₹10,000)**: Your ₹10,000 caution deposit is 100% refundable across all calendar dates. Minor dues or ₹200 lost ID replacement fees are settled on screen via 1-tap Smart Caution Deposit Offsetting without visiting cash counters.\n\n"
                    "3. **4-Gate Digital Clearance Pipeline**:\n"
                    "   • **Gate 1 (Central Library)**: Automated digital audit for returned books and dues.\n"
                    "   • **Gate 2 (Hostel & Mess - Conditional)**: Verified automatically by system. For day-scholars, this gate is automatically marked BYPASSED / NOT APPLICABLE; for residential hostellers, the Warden completes digital inventory sign-off.\n"
                    "   • **Gate 3 (Finance & Accounts)**: Digital fee audit, UGC slab application, and deposit ledger reconciliation.\n"
                    "   • **Gate 4 (Registrar Digital Review)**: Notesheet verification and instant generation of the official Clearance Slip & No-Dues PDF (/withdrawal/{ref}/slip).\n\n"
                    "4. **Application & Real-time Tracking**: Submit your application directly on this kiosk portal (/withdrawal/flow) and track each gate in real time. If any desk exceeds the 48-hour SLA, raise an instant digital ticket via the Grievance Desk (/chat)."
                    f"{guest_note_en}"
                )

            rec_act = "Review Withdrawal Queue" if is_staff_user else ("Start Withdrawal Procedure" if is_authenticated else "Sign In to Apply")
            act_url = "/staff/withdrawals" if is_staff_user else ("/withdrawal" if is_authenticated else "/login")

            res = {
                "answer": answer,
                "domain": "Withdrawal & Refunds",
                "citations": [wth_policy, offset_policy],
                "recommended_action": rec_act,
                "action_url": act_url,
                "voice_speech_text": voice_text,
                "engine": "UniAssist Policy Engine",
            }

        elif is_attendance_query:
            matching_clause = next((p for p in policies if p["clause_code"] == "ORD-ACAD-7.2"), DEFAULT_POLICIES[0])
            is_medical_missed_query = any(mw in q_lower for mw in [
                "sick", "fell sick", "medical leave", "missed class", "missed classes",
                "missed my classes", "medical certificate", "beemar", "bimari", "bimar", "बीमार", "मेडिकल लीव",
                "dengue", "fever", "illness", "hospital", "condonation", "doctor", "disease",
                "60%", "65%", "70%", "below 75", "short of 75", "74%", "shortage"
            ])

            if is_staff_user:
                if language == "hi-IN":
                    staff_att_ans = (
                        f"{staff_designation}, विश्वविद्यालय अध्यादेश ORD-ACAD-7.2 के तहत प्रशासनिक उपस्थिति नियमावली:\n\n"
                        "1. **75% अनिवार्य सीमा**: छात्रों के परीक्षा प्रवेश पत्र (Admit Card) जारी करने हेतु न्यूनतम 75% कक्षा उपस्थिति अनिवार्य है।\n"
                        "2. **डीन मेडिकल छूट (60.0% - 74.9%)**: 60% से 74.9% उपस्थिति वाले छात्रों के लिए डीन द्वारा फॉर्म AC-04 एवं सत्यापित मेडिकल दस्तावेजों के आधार पर छूट अनुमन्य की जा सकती है।\n"
                        "3. **अनिवार्य डिबारमेंट (<60%)**: 60% से कम उपस्थिति वाले छात्रों का अनिवार्य निष्कासन (Debarment) किया जाता है।\n"
                        "4. **प्रशासनिक समीक्षा**: स्टाफ सदस्य स्टाफ एडमिन पोर्टल ('/staff') पर जाकर छात्र उपस्थिति रोस्टर, मेडिकल प्रमाणपत्रों का ऑडिट, और डिबारमेंट सूची सत्यापित कर सकते हैं।"
                    )
                    staff_att_v = f"{staff_designation}, अध्यादेश ORD-ACAD-7.2 के तहत 75% उपस्थिति अनिवार्य है। 60 से 74.9% उपस्थिति पर फॉर्म AC-04 से डीन छूट अनुमन्य है। स्टाफ पोर्टल पर रोस्टर सत्यापित करें।"
                elif language == "hi-Latn":
                    staff_att_ans = (
                        f"{staff_designation}, University Ordinance ORD-ACAD-7.2 ke mutabiq Administrative Attendance regulations:\n\n"
                        "1. **75% Mandatory Cutoff**: Semester exams admit cards issue karne ke liye minimum 75% overall attendance mandatory hai.\n"
                        "2. **Dean Condonation (60.0% - 74.9%)**: Form AC-04 aur verified hospital OPD slips ke basis par Dean medical condonation grant kar sakte hain.\n"
                        "3. **Debarment (<60%)**: 60% se kam attendance par mandatory debarment apply hota hai.\n"
                        "4. **Staff Audit**: Staff officers Staff Admin Portal ('/staff') par jakar departmental attendance rosters audit aur condonation requests sign-off kar sakte hain."
                    )
                    staff_att_v = f"{staff_designation}, Ordinance ORD-ACAD-7.2 requires 75% attendance. Dean condonation applies between 60% and 74.9%. Staff can audit rosters on Staff Portal."
                else:
                    staff_att_ans = (
                        f"{staff_designation}, administrative guidelines under Attendance Ordinance ORD-ACAD-7.2:\n\n"
                        "1. **75% Mandatory Cutoff**: Students must maintain a minimum 75% attendance in each registered course for semester exam admit card eligibility.\n"
                        "2. **Dean's Condonation (60.0% to 74.9%)**: Deans may grant medical condonation upon verification of Form AC-04 and hospital OPD records submitted at least 10 days before exams.\n"
                        "3. **Mandatory Debarment (<60%)**: Attendance below 60% requires compulsory debarment with zero exemption allowed.\n"
                        "4. **Staff Roster Audit**: Authorized staff can verify medical certificates, process condonation approvals, and audit departmental attendance registries via the Staff Portal (/staff)."
                    )
                    staff_att_v = f"{staff_designation}, Ordinance ORD-ACAD-7.2 mandates 75% attendance. Condonation applies between 60% and 74.9% via Form AC-04. Audit rosters in Staff Portal."

                return {
                    "answer": staff_att_ans,
                    "domain": "Staff Attendance Administration",
                    "citations": [matching_clause],
                    "recommended_action": "Staff Admin Portal",
                    "action_url": "/staff",
                    "voice_speech_text": staff_att_v,
                    "screen_instruction": None,
                    "highlight_target": None,
                    "engine": "UniAssist Policy Engine",
                }

            elif not is_authenticated:
                # Guest Mode / Walk-in Kiosk: Do NOT assume 75% attendance! State official ordinance rules & condonation steps.
                if language == "hi-IN":
                    if is_medical_missed_query:
                        answer = (
                            "विश्वविद्यालय अध्यादेश ORD-ACAD-7.2 के तहत मेडिकल लीव एवं उपस्थिति नियमावली:\n\n"
                            "1. **अनिवार्य 75% उपस्थिति एवं 25% मार्जिन**: अंतिम सेमेस्टर परीक्षा में बैठने के लिए न्यूनतम 75% उपस्थिति अनिवार्य है। शेष 25% अनुपस्थिति का मार्जिन विशेष रूप से मेडिकल लीव, बीमारी, और आकस्मिक व्यक्तिगत कारणों के लिए ही दिया जाता है। सामान्य बीमारी इसी 25% बफर में समाहित मानी जाती है।\n"
                            "2. **मेडिकल छूट / कंडोनेशन (60.0% से 74.9%)**: यदि गंभीर या लंबी बीमारी के कारण उपस्थिति 60% से 74.9% के बीच रह जाती है, तो छात्र फॉर्म AC-04 (Attendance Condonation Application) भरकर डीन छूट प्राप्त कर सकते हैं। इसके साथ अस्पताल की मूल ओपीडी पर्ची, डॉक्टर का प्रिस्क्रिप्शन, और मेडिकल फिटनेस सर्टिफिकेट संलग्न कर परीक्षा से 10 कार्यदिवस पूर्व जमा करें।\n"
                            "3. **अनिवार्य डिबारमेंट (<60%)**: 60% से कम उपस्थिति होने पर परीक्षा से अनिवार्य डिबारमेंट होता है और शून्य छूट अनुमन्य है।\n\n"
                            "आप फॉर्म AC-04 इसी कियोस्क स्क्रीन पर नीचे दिए गए बटन से सीधे डाउनलोड कर सकते हैं।"
                        )
                        voice_text = "अध्यादेश ORD-ACAD-7.2 के तहत 75% उपस्थिति अनिवार्य है, और 25% मार्जिन विशेष रूप से मेडिकल लीव और बीमारी के लिए ही रखा गया है। यदि गंभीर बीमारी से उपस्थिति 60 से 74.9% रह जाए तो फॉर्म AC-04 और मेडिकल पर्चे के साथ आवेदन करें। 60% से कम पर डिबारमेंट होता है."
                    else:
                        answer = (
                            "विश्वविद्यालय अध्यादेश ORD-ACAD-7.2 के तहत उपस्थिति एवं मेडिकल छूट (Condonation) नियमावली:\n\n"
                            "1. **न्यूनतम 75% आवश्यकता एवं 25% बफर**: अंतिम सेमेस्टर परीक्षा में बैठने के लिए प्रत्येक पंजीकृत विषय में 75% न्यूनतम उपस्थिति अनिवार्य है। 25% का मार्जिन बीमारी और मेडिकल कारणों के लिए ही निर्धारित है।\n"
                            "2. **डीन छूट / कंडोनेशन (60.0% से 74.9%)**: 60% से 74.9% उपस्थिति वाले छात्र गंभीर बीमारी या अधिकृत ड्यूटी के आधार पर फॉर्म AC-04 भरकर डीन शैक्षणिक मामले में परीक्षा से 10 दिन पूर्व जमा कर सकते हैं।\n"
                            "3. **अनिवार्य डिबारमेंट (<60%)**: 60% से कम उपस्थिति होने पर अध्यादेश के तहत परीक्षा में बैठना पूरी तरह वर्जित (डिबार) है।\n\n"
                            "कंडोनेशन फॉर्म AC-04 आप नीचे दिए गए बटन से तुरंत डाउनलोड कर सकते हैं।"
                        )
                        voice_text = "विश्वविद्यालय में परीक्षा के लिए 75% उपस्थिति आवश्यक है और 25% मार्जिन मेडिकल कारणों के लिए है। 60 से 74.9% उपस्थिति पर फॉर्म AC-04 जमा करें। 60% से कम पर डिबारमेंट होता है."
                elif language == "hi-Latn":
                    if is_medical_missed_query:
                        answer = (
                            "University Ordinance ORD-ACAD-7.2 ke under Medical Leave aur Attendance criteria:\n\n"
                            "1. **75% Mandatory Attendance & 25% Margin**: Semester exams ke liye minimum 75% attendance compulsory hai. Baaki 25% absence margin specifically medical leave, illness, aur emergency situations ke liye hi diya jata hai. Routine sick leaves is 25% buffer ke andar hi absorb hoti hain.\n"
                            "2. **Medical Condonation (60.0% to 74.9%)**: Agar prolonged illness ki wajah se attendance 60% se 74.9% ke beech aa jati hai, toh aap Form AC-04 fill karke Dean Condonation le sakte hain. Iske sath authentic hospital OPD slip, doctor prescription, aur medical certificate attach karke exam se 10 working days pehle submit karein.\n"
                            "3. **Mandatory Debarment (<60%)**: 60% se kam attendance par strict debarment hota hai with zero condonation permitted.\n\n"
                            "Aap Form AC-04 isi screen par niche diye gaye button se turant download kar sakte hain."
                        )
                        voice_text = "Ordinance ORD-ACAD-7.2 ke mutabiq 75% attendance compulsory hai aur 25% margin specifically medical leave ke liye hi diya gaya hai. Agar illness se attendance 60 se 74.9% ke beech ho, toh Form AC-04 aur hospital certificates ke sath condonation apply karein. 60% se kam par strict debarment hota hai."
                    else:
                        answer = (
                            "University Ordinance ORD-ACAD-7.2 ke mutabiq Attendance aur Condonation rules yeh hain:\n\n"
                            "1. **Mandatory Cutoff & 25% Margin**: Minimum 75% attendance in every course is compulsory to sit for End Term Semester Exams. The 25% absence allowance is provided specifically for medical leave and personal emergencies.\n"
                            "2. **Dean Condonation (60.0% to 74.9%)**: Students can apply for condonation on medical or university duty grounds by submitting Form AC-04 at least 10 working days before exams.\n"
                            "3. **Mandatory Debarment (<60%)**: Attendance below 60% constitutes mandatory debarment with zero condonation.\n\n"
                            "Form AC-04 can be downloaded right here on this kiosk screen."
                        )
                        voice_text = "Semester exams ke liye 75% attendance zaroori hai aur 25% buffer medical leave ke liye hota hai. 60 se 74.9% attendance wale students Form AC-04 submit karke condonation le sakte hain."
                else:
                    if is_medical_missed_query:
                        answer = (
                            "Under University Ordinance ORD-ACAD-7.2, medical leaves and attendance are governed by the following criteria:\n\n"
                            "1. **75% Mandatory Attendance & 25% Margin**: A minimum of 75% overall attendance is strictly compulsory in each registered course to be eligible for End Term Semester Examinations. The 25% absence margin is provided specifically to absorb medical leave, illness, and personal emergencies. Routine sick leaves are expected to be covered within this 25% buffer.\n"
                            "2. **Medical Condonation Range (60.0% to 74.9%)**: If prolonged or severe documented illness causes your attendance to drop into the 60.0%–74.9% range, you can apply for Dean's Medical Condonation using Form AC-04. Attach authentic hospital OPD/admission slips, doctor prescriptions, and medical fitness certificates at least 10 working days prior to exam start.\n"
                            "3. **Mandatory Debarment (<60%)**: Attendance below 60% constitutes mandatory debarment with zero condonation permitted under university statutes.\n\n"
                            "You can download Form AC-04 directly right here on this UniAssist screen using the button below."
                        )
                        voice_text = "Under Ordinance ORD-ACAD-7.2, 75% attendance is compulsory. The 25% absence margin is provided specifically to absorb medical leave and sickness. If prolonged illness drops your attendance between 60% and 74.9%, apply for Dean's condonation using Form AC-04 with hospital certificates. Below 60% is strictly debarred."
                    else:
                        answer = (
                            "Under University Ordinance ORD-ACAD-7.2, attendance and condonation are governed by the following rules:\n\n"
                            "1. **Minimum Attendance & 25% Margin**: A minimum of 75% overall attendance is mandatory in each registered course to be eligible for End Term Semester Examinations. The 25% margin is provided specifically to accommodate medical leave and personal emergencies.\n"
                            "2. **Dean's Condonation (60.0% to 74.9%)**: If overall attendance is between 60.0% and 74.9%, students may apply for condonation on genuine medical grounds by filing Form AC-04 with supporting certificates at least 10 working days prior to exams.\n"
                            "3. **Mandatory Debarment (<60%)**: Attendance below 60% constitutes mandatory debarment with zero condonation permitted under university statutes.\n\n"
                            "You can download Form AC-04 directly on this screen using the button below."
                        )
                        voice_text = "Under Ordinance ORD-ACAD-7.2, minimum attendance is 75% and the 25% margin covers medical leaves. If your attendance is between 60% and 74.9%, submit Form AC-04 for condonation. Attendance below 60% results in mandatory debarment."

                recommended_action = "Download Form AC-04 (Condonation)"
                action_url = "/forms"

            elif is_medical_missed_query:
                # Authenticated student specifically asking how to submit medical leave / condonation for missed classes
                if language == "hi-IN":
                    answer = (
                        f"{student_name}, विश्वविद्यालय अध्यादेश ORD-ACAD-7.2 के तहत मेडिकल लीव एवं उपस्थिति नियमावली:\n\n"
                        "1. **75% अनिवार्य उपस्थिति एवं 25% मार्जिन**: अंतिम सेमेस्टर परीक्षा हेतु न्यूनतम 75% उपस्थिति आवश्यक है। 25% का मार्जिन विशेष रूप से मेडिकल लीव और बीमारी के लिए ही रखा गया है।\n"
                        "2. **मेडिकल कंडोनेशन (60.0% से 74.9%)**: यदि गंभीर बीमारी के कारण आपकी उपस्थिति 60% से 74.9% के बीच है, तो आप फॉर्म AC-04 (Attendance Condonation Application) भरकर डीन छूट प्राप्त कर सकते हैं। अस्पताल की मूल ओपीडी पर्ची और मेडिकल सर्टिफिकेट संलग्न करें।\n"
                        "3. **आवेदन समय सीमा**: परीक्षा प्रारंभ होने से कम से कम 10 कार्यदिवस पूर्व आवेदन जमा करें।\n"
                        "4. **अनिवार्य डिबारमेंट (<60%)**: 60% से कम उपस्थिति होने पर परीक्षा में बैठना पूरी तरह वर्जित (डिबार) है।"
                    )
                    voice_text = f"{student_name}, कॉलेज में 75% उपस्थिति अनिवार्य है और 25% मार्जिन मेडिकल लीव के लिए है। यदि बीमारी से उपस्थिति 60 से 74.9% रह गई है तो फॉर्म AC-04 और मेडिकल सर्टिफिकेट के साथ परीक्षा से 10 दिन पूर्व आवेदन करें।"
                elif language == "hi-Latn":
                    answer = (
                        f"{student_name}, University Ordinance ORD-ACAD-7.2 ke under Medical Leave aur Attendance rules:\n\n"
                        "1. **75% Attendance & 25% Margin**: 75% attendance compulsory hai. 25% absence margin specifically medical emergencies aur sickness ke liye provide kiya gaya hai.\n"
                        "2. **Medical Condonation (60.0% to 74.9%)**: Agar severe illness ki wajah se attendance 60% se 74.9% ke beech hai, toh aap Form AC-04 submit karke Dean Condonation le sakte hain. Valid hospital OPD slips aur medical fitness certificate attach karein.\n"
                        "3. **Submission**: Exam se kam se kam 10 working days pehle apply karein.\n"
                        "4. **Mandatory Debarment (<60%)**: 60% se kam attendance par compulsory debarment hota hai."
                    )
                    voice_text = f"{student_name}, 75% attendance compulsory hai aur 25% margin medical leave ke liye diya gaya hai. Agar attendance 60 se 74.9% hai, toh Form AC-04 medical certificate ke sath submit karein."
                else:
                    answer = (
                        f"{student_name}, under University Ordinance ORD-ACAD-7.2, medical leave and attendance criteria are as follows:\n\n"
                        "1. **75% Mandatory Attendance & 25% Margin**: A minimum of 75% overall attendance is strictly required. The 25% absence margin is provided specifically to absorb medical leave, illness, and personal emergencies.\n"
                        "2. **Medical Condonation (60.0% to 74.9%)**: If prolonged or severe documented illness drops your attendance into the 60.0%–74.9% range, you can apply for Dean's Medical Condonation using Form AC-04 with authentic hospital OPD slips and doctor certificates.\n"
                        "3. **Submission Timeline**: Submit at least 10 working days prior to semester exam commencement.\n"
                        "4. **Mandatory Debarment (<60%)**: Attendance below 60% constitutes mandatory debarment with zero condonation permitted."
                    )
                    voice_text = f"{student_name}, under Ordinance ORD-ACAD-7.2, 75% attendance is mandatory and the 25% margin is specifically for medical leave. If serious illness drops your attendance between 60% and 74.9%, submit Form AC-04 with medical slips to avoid debarment."

                recommended_action = "Download Form AC-04 (Condonation)"
                action_url = "/forms"

            elif attendance >= 75.0:
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
                        "डीन छूट (Condonation) प्राप्त कर सकते हैं। यह आवेदन परीक्षा शुरू होने से 10 दिन पहले पोर्टल (/forms) पर जमा करना होता है।"
                    )
                elif language == "hi-Latn":
                    answer = (
                        f"{student_name}, aapki attendance {attendance:.1f}% hai ({shortfall:.1f}% short of 75%). "
                        "Under ORD-ACAD-7.2, aap medical grounds par Form AC-04 submit karke Dean Condonation le sakte hain portal (/forms) par. "
                        "Kya aap Form AC-04 download karna chahte hain?"
                    )
                else:
                    answer = (
                        f"{student_name}, your recorded attendance is {attendance:.1f}% ({shortfall:.1f}% short of the mandatory 75% cutoff). "
                        "Under Ordinance ORD-ACAD-7.2, you are eligible to request Dean's Condonation on medical or approved official "
                        "duty grounds by filing Form AC-04 online (/forms) before the 10-day exam deadline."
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
                "voice_speech_text": voice_text if "voice_text" in locals() else answer,
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
                p_title = proc.get("official_name") or proc.get("title") or "University Procedure"
                p_kiosk = proc.get("kiosk_access") or proc.get("kiosk_action") or "Download form directly on kiosk screen"
                p_docs = proc.get("required_documents") or proc.get("attachments_required") or ["Completed application form"]
                p_office = proc.get("submission_office") or proc.get("submission_room") or "Registrar Desk (Room 101)"
                p_sla = proc.get("deadline_sla") or proc.get("sla_working_days") or "3-5 working days"
                p_fee = proc.get("fee_details") or proc.get("fee") or "As applicable per fee schedule"
                p_docs_str = ", ".join(p_docs) if isinstance(p_docs, list) else str(p_docs)
                content_text = (
                    f"Verified Procedure for {p_title}:\n"
                    f"1. Action at Kiosk: {p_kiosk}\n"
                    f"2. Required Attachments: {p_docs_str}\n"
                    f"3. Submission Room & Window: {p_office}\n"
                    f"4. Turnaround SLA: {p_sla}\n"
                    f"5. Associated Fee: {p_fee}"
                )
                f_title = p_title
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

        if res is None:
            # Check if query matches any staff-configured custom procedure created in Setup Wizard
            matched_custom_proc = None
            try:
                from .procedure_service import ProcedureService
                active_procs = ProcedureService.list_procedures(active_only=True)
                for cp in active_procs:
                    cp_title = (cp.get("title") or "").lower()
                    words_in_title = [w for w in cp_title.split() if len(w) >= 4 and w not in ("application", "procedure", "form", "desk", "office", "hostel", "room")]
                    matched_words = [w for w in words_in_title if w in q_lower]
                    if cp_title in q_lower or (words_in_title and len(matched_words) >= max(1, len(words_in_title) // 2 + 1)):
                        matched_custom_proc = cp
                        break
            except Exception:
                matched_custom_proc = None

            if matched_custom_proc:
                cp_title = matched_custom_proc.get("title", "Configured Procedure")
                cp_dept = matched_custom_proc.get("department", "University Desk")
                cp_sla = matched_custom_proc.get("sla_days", 3)
                cp_docs = ", ".join(matched_custom_proc.get("required_docs") or ["No physical documents required (100% Digital)"])
                cp_steps = matched_custom_proc.get("steps") or []
                if cp_steps:
                    steps_str = "\n".join([f"   • Step {s.get('step_number', idx+1)}: {s.get('title')} ({s.get('responsible_desk', 'Desk')}) - SLA: {s.get('sla_days', 1)} day(s)" for idx, s in enumerate(cp_steps)])
                else:
                    steps_str = "   • Step 1: Initial Desk Review & Approval"

                if language == "hi-IN":
                    answer = (
                        f"{student_name}, विश्वविद्यालय पोर्टल पर {cp_title} ({cp_dept}) के लिए निर्धारित आधिकारिक प्रक्रिया:\n\n"
                        f"1. आवश्यक दस्तावेज: {cp_docs}\n"
                        f"2. प्रक्रिया के चरण ({len(cp_steps) or 1} स्टेप्स):\n{steps_str}\n"
                        f"3. समाधान समयसीमा (SLA): {cp_sla} कार्य दिवस।"
                    )
                    voice_text = f"{student_name}, {cp_title} की प्रक्रिया में {len(cp_steps) or 1} चरण हैं और यह {cp_sla} कार्य दिवसों में पूरी होती है।"
                elif language == "hi-Latn":
                    answer = (
                        f"{student_name}, {cp_title} ({cp_dept}) ke liye official configured procedure:\n\n"
                        f"1. Required Documents: {cp_docs}\n"
                        f"2. Process Workflow ({len(cp_steps) or 1} steps):\n{steps_str}\n"
                        f"3. SLA Timeline: {cp_sla} working days."
                    )
                    voice_text = f"{student_name}, {cp_title} ke {len(cp_steps) or 1} steps hain aur SLA {cp_sla} working days hai."
                else:
                    answer = (
                        f"{student_name}, here is the official configured procedure for {cp_title} ({cp_dept}):\n\n"
                        f"1. Required Documents: {cp_docs}\n"
                        f"2. Approval Workflow ({len(cp_steps) or 1} step(s)):\n{steps_str}\n"
                        f"3. Processing SLA: {cp_sla} working day(s)."
                    )
                    voice_text = f"{student_name}, the configured procedure for {cp_title} involves {len(cp_steps) or 1} stage(s) with an SLA of {cp_sla} working days."

                res = {
                    "answer": answer,
                    "domain": cp_dept,
                    "citations": [],
                    "recommended_action": f"View {cp_title}",
                    "action_url": "/services",
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
                        f"मुझे क्षमा करें, {student_name}, लेकिन मुझे आपके इस प्रश्न से संबंधित कोई विशिष्ट विश्वविद्यालय अध्यादेश नहीं मिला। "
                        "UniAssist सभी 31 फॉर्म, विड्रॉल रिफंड, उपस्थिति छूट (Condonation), कॉशन डिपॉजिट ऑफसेट, बैकपेपर परीक्षा, "
                        "और छात्रवृत्ति नियमों में पूरी सहायता करता है। कृपया इनमें से किसी भी विषय पर पूछें।"
                    )
                elif language == "hi-Latn":
                    fallback_msg = (
                        f"Sorry {student_name}, mujhe aapke question se matching koi specific ordinance nahi mila. "
                        "UniAssist sabhi 31 forms, Attendance Condonation, Withdrawal Refund, Caution Deposit Offsets, "
                        "Backpapers, aur Scholarships me help provide karta hai. Please inme se kisi topic par poochiye."
                    )
                else:
                    fallback_msg = (
                        f"I am sorry, {student_name}, but I could not find a specific university ordinance matching your inquiry. "
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
                "General",
                "General Policies",
                "Domain Boundary Guard",
                "Institutional Discipline Guard",
                "Policy Guardrails",
                "Academics",
                "Academics & Curriculum",
                "Grading & Examination",
                "Training & Placements",
                "Library & Learning Resources",
                "Campus Facilities & Welfare",
                "Withdrawal & Refunds",
                "Withdrawal & Caution Deposit Offset",
                "Withdrawal & Caution Deposit Refund",
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
                "Staff Clearance & Withdrawal Queue",
                "Staff Administration",
                "Admissions & Enrollment",
                "Admissions & Registrar",
                "HR & Faculty",
                "HR & Staff",
                "Conversational",
                "Navigation",
                "Screen Navigation",
            )
            # ---------------------------------------------------------------
            # OLLAMA SYNTHESIS: Route ALL campus queries through Ollama when
            # available. Ollama receives retrieved university policy facts as
            # RAG context and synthesizes a warm, grounded, clean response.
            # ---------------------------------------------------------------
            if settings.is_ollama_enabled and not is_deterministic_domain:
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
                    res["answer"] = strip_markdown_stars(text)
                    res["voice_speech_text"] = strip_markdown_stars(text)
                    res["engine"] = engine_name
            elif not is_deterministic_domain:
                # Cloud Gemini fallback when Ollama is not enabled
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
                    if "Offline" not in engine_name:
                        res["answer"] = strip_markdown_stars(text)
                        res["voice_speech_text"] = strip_markdown_stars(text)
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
            if is_staff_user:
                if not res.get("action_url") or res.get("action_url") in ("/forms", "/withdrawal", "/services"):
                    res["action_url"] = "/staff"
                if not res.get("recommended_action") or res.get("recommended_action") in ("Browse Forms & Policies", "Open Forms Catalog", "Start Withdrawal Procedure"):
                    res["recommended_action"] = "Open Staff Admin Portal"
            else:
                if not res.get("action_url"):
                    res["action_url"] = "/forms"
                if not res.get("recommended_action"):
                    res["recommended_action"] = "Open Forms Catalog"

        # Universal asterisk sanitizer - strip all raw markdown from any answer
        if res.get("answer"):
            res["answer"] = strip_markdown_stars(res["answer"])
        if res.get("voice_speech_text"):
            res["voice_speech_text"] = strip_markdown_stars(res["voice_speech_text"])

        return res
