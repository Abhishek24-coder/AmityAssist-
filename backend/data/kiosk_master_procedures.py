"""Master Procedural & Grounding Knowledge Base for UniAssist Kiosk AI.

This authoritative document is fed directly into Ollama Llama 3.2 and the Policy Engine.
It establishes zero-hallucination ground truth for all official university procedures:
1. Human-friendly official form names (no cryptic codes like 'EX-2' or legal jargon).
2. Kiosk-First access: How to get the form directly on this kiosk/screen.
3. Eligibility criteria and required attachments.
4. Exact verified campus submission rooms (No fake 'Seva Kendra 3').
5. Turnaround SLAs and actionable on-screen buttons.
"""

from __future__ import annotations
from typing import Any

MASTER_PROCEDURES: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # 1. ACADEMIC & ATTENDANCE PROCEDURES
    # -------------------------------------------------------------------------
    "attendance_condonation": {
        "form_code": "AC-04",
        "official_name": "Attendance Condonation Application (Form AC-04)",
        "hindi_name": "उपस्थिति छूट आवेदन (फॉर्म AC-04)",
        "category": "Academics",
        "kiosk_access": (
            "You do not need to wander anywhere on campus to get this form. "
            "You can download it directly right here on this UniAssist screen using the button below, "
            "or open the Forms Catalog (/forms)."
        ),
        "kiosk_access_hindi": (
            "आपको इस फॉर्म के लिए कैंपस में कहीं भी भटकने की ज़रूरत नहीं है। "
            "आप इसी स्क्रीन पर नीचे दिए गए 'Download Form AC-04' बटन पर क्लिक करके इसे तुरंत यहीं से प्राप्त कर सकते हैं।"
        ),
        "kiosk_access_hinglish": (
            "Aapko is form ke liye campus me kahin bhatakne ki zaroorat nahi hai. "
            "Aap yahin UniAssist screen par niche diye gaye 'Download Form AC-04' button par click karke turant prapt kar sakte hain."
        ),
        "eligibility": "Attendance between 60.0% and 74.9% (below 60% constitutes mandatory debarment).",
        "required_documents": [
            "Authentic medical certificate with doctor prescription and hospital OPD slip",
            "Or approved official university duty certificate signed by event coordinator"
        ],
        "submission_office": "Dean of Academic Affairs (Room 201, Academic Block)",
        "deadline_sla": "Submit at least 10 working days prior to exam start. Admit card is unblocked within 48 hours of Dean approval.",
        "action_label": "Download Form AC-04 (Condonation)",
        "action_url": "/forms",
    },

    # -------------------------------------------------------------------------
    # 2. EXAMINATION PROCEDURES
    # -------------------------------------------------------------------------
    "backpaper_exam": {
        "form_code": "EX-02",
        "official_name": "Supplementary / Backpaper Examination Application (Form EX-02)",
        "hindi_name": "बैकपेपर पूरक परीक्षा आवेदन (फॉर्म EX-02)",
        "category": "Examinations",
        "kiosk_access": (
            "You can download Form EX-02 directly right here on this UniAssist screen using the action button below, "
            "or access it from the Forms Catalog (/forms)."
        ),
        "kiosk_access_hindi": (
            "आप Form EX-02 इसी स्क्रीन पर नीचे दिए गए बटन पर क्लिक करके तुरंत यहीं से डाउनलोड कर सकते हैं।"
        ),
        "kiosk_access_hinglish": (
            "Aap Form EX-02 yahin screen par niche diye gaye button par click karke turant download kar sakte hain."
        ),
        "eligibility": "Students with failed subjects or seeking grade improvement in previous semester courses.",
        "fee_details": "INR 1,500 per registered subject paper.",
        "required_documents": [
            "Copy of semester grade sheet showing failed / improvement course codes",
            "INR 1,500 per subject fee challan / payment receipt"
        ],
        "submission_office": "Examination Cell (Block 3, Room 110)",
        "deadline_sla": "Must submit within 14 calendar days of semester grade sheet publication.",
        "action_label": "Download Form EX-02 (Backpaper)",
        "action_url": "/forms",
    },

    "rechecking_reevaluation": {
        "form_code": "PROC-FORM-27",
        "official_name": "Application for Rechecking & Re-evaluation of Result",
        "hindi_name": "परीक्षा परिणाम पुनर्मूल्यांकन आवेदन (फॉर्म 27)",
        "category": "Examinations",
        "kiosk_access": "Download directly right here on this screen via the button below or Forms Catalog (/forms).",
        "kiosk_access_hindi": "इसी स्क्रीन पर नीचे दिए गए बटन से तुरंत डाउनलोड करें।",
        "kiosk_access_hinglish": "Yahin screen par niche diye gaye button se turant download karein.",
        "eligibility": "Any enrolled student seeking re-evaluation of theory examination answer sheets.",
        "fee_details": "INR 500 per subject paper (rechecking) / INR 750 (re-evaluation).",
        "required_documents": [
            "Semester grade card copy",
            "Accounts fee payment slip"
        ],
        "submission_office": "Controller of Examinations (Examination Cell Window 3)",
        "deadline_sla": "Submit within 15 calendar days of result declaration. Processing turnaround is 21 working days.",
        "action_label": "Download Rechecking Form",
        "action_url": "/forms",
    },

    "degree_application": {
        "form_code": "PROC-FORM-22",
        "official_name": "Degree Application & Convocation Format",
        "hindi_name": "डिग्री एवं दीक्षांत समारोह आवेदन प्रपत्र",
        "category": "Examinations",
        "kiosk_access": "Download directly right here on this UniAssist screen or from Forms Catalog (/forms).",
        "kiosk_access_hindi": "इसी स्क्रीन पर नीचे दिए गए बटन से तुरंत डाउनलोड करें।",
        "kiosk_access_hinglish": "Yahin screen par niche diye gaye button se turant download karein.",
        "eligibility": "Graduating students who have passed all semesters and cleared institutional dues.",
        "fee_details": "INR 1,500 convocation & degree processing fee.",
        "required_documents": [
            "Attested photocopies of cumulative grade sheet (all semesters passed)",
            "10th passing certificate for date of birth verification",
            "University No-Dues Clearance slip"
        ],
        "submission_office": "Controller of Examinations (Degree Cell Window 1)",
        "deadline_sla": "Turnaround SLA is 15 working days for provisional degree and convocation roll inclusion.",
        "action_label": "Download Degree Application",
        "action_url": "/forms",
    },

    # -------------------------------------------------------------------------
    # 3. WITHDRAWAL & REFUND PROCEDURES
    # -------------------------------------------------------------------------
    "program_withdrawal": {
        "form_code": "PROC-FORM-WTH",
        "official_name": "Program Withdrawal & Tuition Refund Application Form",
        "hindi_name": "प्रवेश विड्रॉल एवं शुल्क रिफंड आवेदन प्रपत्र",
        "category": "Withdrawal & Refunds",
        "kiosk_access": (
            "You do not need to run to any offices to get this form. "
            "You can initiate digital clearance and download the form directly on this UniAssist kiosk via the button below."
        ),
        "kiosk_access_hindi": (
            "आपको कहीं जाने की आवश्यकता नहीं है। आप इसी कियोस्क पर नीचे दिए गए 'Start Withdrawal Procedure' बटन से डिजिटल क्लियरेंस और फॉर्म शुरू कर सकते हैं।"
        ),
        "kiosk_access_hinglish": (
            "Aapko kahin jane ki zaroorat nahi hai. Aap yahin kiosk par 'Start Withdrawal Procedure' button par tap karke digital clearance aur form turant shuru kar sakte hain."
        ),
        "eligibility": "Any student requesting departure or admission cancellation under UGC refund guidelines.",
        "refund_slabs": [
            "15+ days prior to admission deadline: 100% refund (minus max INR 1,000 processing fee)",
            "Less than 15 days prior: 90% refund",
            "Up to 15 days post admission deadline: 80% refund",
            "16 to 30 days post deadline: 50% refund",
            "Beyond 30 days: 0% tuition refund",
            "Refundable Caution Deposit (INR 10,000): Always 100% refunded across all slabs."
        ],
        "required_documents": [
            "Parent / guardian consent letter",
            "Student ID card",
            "Cancelled bank cheque or passbook copy showing IFSC code for NEFT refund transfer"
        ],
        "submission_office": "Registrar Office (Room 102, Administrative Block) after 4-gate digital sign-off.",
        "deadline_sla": "Refund credited to bank account within 14 working days of document verification.",
        "action_label": "Start Withdrawal Procedure",
        "action_url": "/withdrawal",
    },

    "smart_deposit_offset": {
        "form_code": "ORD-FIN-14.4",
        "official_name": "Smart Caution Deposit Offsetting Procedure",
        "hindi_name": "कॉशन डिपॉजिट स्मार्ट ऑफसेट प्रक्रिया",
        "category": "Finance",
        "kiosk_access": "Available 100% digitally on this kiosk on the Withdrawal & Clearance portal (/withdrawal).",
        "kiosk_access_hindi": "इसी कियोस्क पर विड्रॉल और क्लियरेंस पोर्टल (/withdrawal) पर 1-टैप में उपलब्ध।",
        "kiosk_access_hinglish": "Yahin kiosk par Withdrawal portal (/withdrawal) par 1-tap me available.",
        "eligibility": "Students with pending dues under INR 2,000 (such as library fines or lost ID replacement fee of INR 200).",
        "details": "Directly deducts fine from INR 10,000 refundable caution deposit balance without physical bank visits or challans.",
        "submission_office": "100% Automated Digital Clearance Gate on UniAssist.",
        "deadline_sla": "Gate updates to CLEARED immediately.",
        "action_label": "View Clearance Status",
        "action_url": "/withdrawal",
    },

    # -------------------------------------------------------------------------
    # 4. REGISTRAR & STUDENT SERVICES
    # -------------------------------------------------------------------------
    "migration_certificate": {
        "form_code": "PROC-FORM-15",
        "official_name": "Migration Certificate Application Form",
        "hindi_name": "माइग्रेशन प्रमाणपत्र आवेदन प्रपत्र",
        "category": "Academics",
        "kiosk_access": "Download directly right here on this UniAssist screen or from the Forms Catalog (/forms).",
        "kiosk_access_hindi": "इसी स्क्रीन पर नीचे दिए गए बटन से तुरंत डाउनलोड करें।",
        "kiosk_access_hinglish": "Yahin screen par niche diye gaye button se turant download karein.",
        "eligibility": "Outgoing students enrolling in another university.",
        "required_documents": [
            "All semester grade sheet photocopies",
            "Provisional degree or bonafide certificate",
            "University No-Dues clearance slip"
        ],
        "submission_office": "Registrar Office Window 2 (Room 102, Administrative Block)",
        "deadline_sla": "Processing SLA is 3 to 5 working days. Can collect at Window 2 or receive via speed post.",
        "action_label": "Download Migration Form",
        "action_url": "/forms",
    },

    "student_id_reissue": {
        "form_code": "PROC-FORM-28",
        "official_name": "Student Identity Card Re-issue & Duplicate Form",
        "hindi_name": "छात्र पहचान पत्र डुप्लिकेट पुनः जारी आवेदन",
        "category": "Admissions & Registrar",
        "kiosk_access": "Download directly right here on this UniAssist screen or from Forms Catalog (/forms).",
        "kiosk_access_hindi": "इसी स्क्रीन पर नीचे दिए गए बटन से तुरंत डाउनलोड करें।",
        "kiosk_access_hinglish": "Yahin screen par niche diye gaye button se turant download karein.",
        "eligibility": "Students with damaged, lost, or defaced smart ID cards.",
        "fee_details": "INR 200 re-issue fee (eligible for 1-tap Smart Caution Deposit Offsetting).",
        "required_documents": [
            "1 recent passport photograph with white background",
            "Police lost report / NCR copy (if lost)",
            "INR 200 fee receipt or Smart Offset authorization"
        ],
        "submission_office": "Student Services / Registrar Desk (Room 101)",
        "deadline_sla": "SLA is 48 hours for biometric smart card collection.",
        "action_label": "Download Student ID Form",
        "action_url": "/forms",
    },

    "new_admission": {
        "form_code": "ADM-01",
        "official_name": "New Student Admission & Document Verification Dossier (Form ADM-01)",
        "hindi_name": "नवीन छात्र प्रवेश एवं दस्तावेज सत्यापन आवेदन (फॉर्म ADM-01)",
        "category": "Admissions & Registrar",
        "kiosk_access": "Download Form ADM-01 directly right here on this UniAssist screen via the action button below, or access it from the Forms Catalog (/forms).",
        "kiosk_access_hindi": "इसी स्क्रीन पर नीचे दिए गए बटन से Form ADM-01 तुरंत डाउनलोड करें, या फॉर्म्स कैटलॉग (/forms) से प्राप्त करें।",
        "kiosk_access_hinglish": "Yahin screen par niche diye gaye button se Form ADM-01 turant download karein, ya Forms Catalog (/forms) se lein.",
        "eligibility": "Candidates seeking fresh enrollment in undergraduate, postgraduate, or diploma programs.",
        "fee_details": "First semester tuition fee plus INR 10,000 refundable caution deposit.",
        "required_documents": [
            "Original 10th and 12th marksheets with attested photocopies",
            "Qualifying entrance examination rank scorecard (JEE / CUET / State CET / University Test)",
            "Transfer Certificate (TC) and Migration Certificate",
            "Character Certificate from head of previous institution",
            "4 recent passport-size photographs (white background)",
            "Category / Caste certificate (if applicable)"
        ],
        "submission_office": "Directorate of Admissions (Room 101, Central Block)",
        "deadline_sla": "Document verification and provisional enrollment completed within 24 hours of seat allotment.",
        "action_label": "Download Form ADM-01 (Admission)",
        "action_url": "/forms",
    },

    # -------------------------------------------------------------------------
    # 5. FACULTY & STAFF HR PROCEDURES
    # -------------------------------------------------------------------------
    "faculty_resignation": {
        "form_code": "ORD-HR-24.1",
        "official_name": "Faculty & Staff Resignation & Relieving Clearance Procedure",
        "hindi_name": "संकाय एवं स्टाफ त्यागपत्र एवं रिलीविंग क्लियरेंस प्रक्रिया",
        "category": "HR & Faculty",
        "kiosk_access": "Download the Faculty Clearance Dossier right here on this UniAssist screen via the button below.",
        "kiosk_access_hindi": "फैकल्टी क्लियरेंस डोजियर इसी स्क्रीन पर नीचे दिए गए बटन से डाउनलोड करें।",
        "kiosk_access_hinglish": "Faculty Clearance Dossier yahin screen par niche diye gaye button se download karein.",
        "eligibility": "Faculty members or staff resigning from university service.",
        "procedure_steps": [
            "1. Submit formal written resignation notice to Department HOD and Dean of Faculty.",
            "2. Complete 4-counter No-Dues Clearance: (a) Department HOD (handover course dossiers and lab keys), (b) Central Library (book returns), (c) Stores & IT (laptop, printer assets, and biometric deactivation), (d) Finance & Accounts (salary & PF reconciliation).",
            "3. Submit completed dossier to HR Administration Desk (Room 103, Administrative Block)."
        ],
        "submission_office": "HR Administration Desk (Room 103, Administrative Block)",
        "deadline_sla": "Relieving letter and experience certificate issued within 15 working days.",
        "action_label": "Download Faculty Exit Format",
        "action_url": "/forms",
    },

    "faculty_leave": {
        "form_code": "PROC-FORM-23",
        "official_name": "Faculty Leave Application & Emergency Leave Proforma",
        "hindi_name": "संकाय अवकाश आवेदन प्रपत्र",
        "category": "HR & Staff",
        "kiosk_access": "Download directly right here on this screen or from Forms Catalog (/forms).",
        "kiosk_access_hindi": "इसी स्क्रीन पर नीचे दिए गए बटन से तुरंत डाउनलोड करें।",
        "kiosk_access_hinglish": "Yahin screen par niche diye gaye button se download karein.",
        "eligibility": "Academic teaching faculty applying for Casual, Earned, Duty, Medical, or Emergency leave.",
        "required_documents": [
            "Class Arrangement Sheet (PROC-FORM-03) with substitute colleague teacher agreement"
        ],
        "submission_office": "HR Administration Desk (Room 103, Administrative Block)",
        "deadline_sla": "Submit at least 48 hours prior to planned leave (or 24 hours post-return for emergency leave).",
        "action_label": "Download Leave Application",
        "action_url": "/forms",
    },
}


def get_procedure_by_keyword(query: str) -> dict[str, Any] | None:
    """Match student voice or text query against official procedural ground truth."""
    q_low = query.lower()

    if any(w in q_low for w in ["ac-04", "ac04", "condonation", "medical leave", "medical application", "sick leave", "illness leave", "कंडोनेशन", "अटेंडेंस कम", "कम हाजिरी", "मेडिकल लीव", "बीमारी"]):
        return MASTER_PROCEDURES["attendance_condonation"]

    if any(w in q_low for w in ["ex-02", "ex02", "backpaper", "supplementary", "बैकपेपर", "बैक"]):
        return MASTER_PROCEDURES["backpaper_exam"]

    if any(w in q_low for w in ["rechecking", "re-evaluation", "reevaluation", "पुनर्मूल्यांकन"]):
        return MASTER_PROCEDURES["rechecking_reevaluation"]

    if any(w in q_low for w in ["degree", "convocation", "डिग्री", "दीक्षांत"]):
        return MASTER_PROCEDURES["degree_application"]

    if any(w in q_low for w in ["withdrawal", "refund", "विड्रॉल", "रिफंड", "फीस वापसी"]):
        return MASTER_PROCEDURES["program_withdrawal"]

    if any(w in q_low for w in ["offset", "caution deposit", "कॉशन", "कौशन", "सिक्योरिटी"]):
        return MASTER_PROCEDURES["smart_deposit_offset"]

    if any(w in q_low for w in ["migration", "माइग्रेशन"]):
        return MASTER_PROCEDURES["migration_certificate"]

    if any(w in q_low for w in ["student id", "id card", "पहचान पत्र", "आईडी कार्ड"]):
        return MASTER_PROCEDURES["student_id_reissue"]

    if any(w in q_low for w in ["resignation", "job chhod", "istifa", "इस्तीफा", "नौकरी छोड़ना"]):
        return MASTER_PROCEDURES["faculty_resignation"]

    if any(w in q_low for w in ["faculty leave", "emergency leave", "फैकल्टी लीव"]):
        return MASTER_PROCEDURES["faculty_leave"]

    if any(w in q_low for w in ["admission", "admissions", "daakhila", "dakhila", "एडमिशन", "दाखिला", "प्रवेश"]):
        if not any(w in q_low for w in ["withdraw", "withdrawal", "cancel", "refund"]):
            return MASTER_PROCEDURES["new_admission"]

    return None
