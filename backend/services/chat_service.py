"""
Conversation state-machine (FSM) service.

States:
  ASK_REASON  → Prompt student for withdrawal reason
  SUGGEST     → Classify intent, offer alternatives
  CONFIRM     → Request explicit CONFIRM / CANCEL
  DONE        → Withdrawal submitted; session closed
  RESOLVED    → Student chose an alternative; session closed gracefully

Session state is stored in-process (dict). The persistent record of every
message and every submitted request is written to SQLite via parameterised
queries — never raw string interpolation.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import Optional

from ..database.connection import get_connection
from ..models.schemas import ChatResponse
from .nlp_service import (
    classify_intent,
    detect_language,
    is_voice_command,
    route_intent,
    score_sentiment,
)
from .advanced_ai_service import advanced_reply, remember_turn, summarize_memory
from .withdrawal_workflow import create_withdrawal_request

# ---------------------------------------------------------------------------
# In-memory session registry  {session_id: SessionData}
# ---------------------------------------------------------------------------

_sessions: dict[str, dict] = {}


def create_session(student_id: str) -> str:
    """Register a new verified student session and return a secure session token."""
    session_id = secrets.token_urlsafe(32)
    _sessions[session_id] = {
        "student_id": student_id,
        "state": "ASK_REASON",
        "intent": None,
        "reason": None,
        "grievance_category": None,
        "grievance_description": None,
        "pending_scholarship_id": None,
        "pending_exam_id": None,
        "recent_turns": [],
        "memory_summary": "No prior context in this session.",
        "created_at": datetime.utcnow(),
    }
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """Retrieve session data or None if expired/invalid."""
    return _sessions.get(session_id)


def invalidate_session(session_id: str) -> None:
    """Remove session — called after withdrawal submitted or resolved."""
    _sessions.pop(session_id, None)


# ---------------------------------------------------------------------------
# Per-intent suggestion templates
# ---------------------------------------------------------------------------

_SUGGESTIONS: dict[str, str] = {
    "financial": (
        "💡 **We understand financial pressure can be overwhelming.**\n\n"
        "Before proceeding, please consider these options available to you:\n"
        "- **Emergency Bursary Fund** — up to $500 for eligible students\n"
        "- **Deferred Payment Plan** — spread tuition across 12 monthly instalments\n"
        "- **Part-Time Scholarship** — apply through the Financial Aid portal\n\n"
        "Would any of these help you continue your studies? *(yes / no / tell me more)*"
    ),
    "academic": (
        "📚 **Academic challenges affect many students — you are not alone.**\n\n"
        "Before you decide, please explore these alternatives:\n"
        "- **Academic Counselling** — one-on-one sessions with a dedicated advisor\n"
        "- **Programme Transfer** — switch to a course that suits you better\n"
        "- **Leave of Absence** — pause your studies for one semester without penalty\n\n"
        "Would you like to explore any of these? *(yes / no)*"
    ),
    "personal": (
        "❤️ **Personal circumstances can be incredibly difficult.**\n\n"
        "Please know these support options exist for you:\n"
        "- **Compassionate Leave** — up to 6 months pause with full reinstatement rights\n"
        "- **Remote Study Mode** — complete your coursework fully online\n"
        "- **Student Counselling Service** — free, confidential, and always available\n\n"
        "Can any of these help you continue? *(yes / no)*"
    ),
    "health": (
        "🏥 **Your health and wellbeing come first.**\n\n"
        "Before withdrawing, consider these health-sensitive options:\n"
        "- **Medical Leave of Absence** — pause studies without academic penalty\n"
        "- **Reduced Course Load** — carry fewer credits this semester\n"
        "- **Campus Health Services** — specialist support at no cost\n\n"
        "Would a medical leave of absence work for your situation? *(yes / no)*"
    ),
    "career": (
        "🚀 **An exciting opportunity shouldn't mean leaving your degree behind.**\n\n"
        "Consider these flexible pathways:\n"
        "- **Co-operative Education Programme** — earn academic credits while working\n"
        "- **Part-Time Enrolment** — balance your career and studies simultaneously\n"
        "- **Industry Project Elective** — real work experience built into your degree\n\n"
        "Would any of these allow you to stay enrolled? *(yes / no)*"
    ),
    "unclear": (
        "Thank you for sharing that with me. To make sure I give you the best support, "
        "could you tell me a little more about why you're considering withdrawal?\n\n"
        "For example, is it related to:\n"
        "- 💰 **Finances** (fees, costs)\n"
        "- 📚 **Academics** (grades, workload)\n"
        "- ❤️ **Personal** (family, circumstances)\n"
        "- 🏥 **Health** (medical reasons)\n"
        "- 💼 **Career** (job opportunity)\n\n"
        "Please describe your situation in your own words."
    ),
}

_POSITIVE_SIGNALS = {
    "yes",
    "yeah",
    "yep",
    "sure",
    "ok",
    "okay",
    "agree",
    "please",
    "try",
    "interested",
    "help",
}
_NEGATIVE_SIGNALS = {
    "no",
    "nope",
    "nah",
    "none",
    "still",
    "withdraw",
    "proceed",
    "want to leave",
    "decided",
}
_GRIEVANCE_CATEGORIES = {"academic", "fee", "hostel", "exam", "scholarship"}
_GREETING_SIGNALS = {
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "namaste",
}
_GREETING_SIGNALS = {
    "hello",
    "hi",
    "hey",
    "hii",
    "good morning",
    "good afternoon",
    "good evening",
    "namaste",
    "namaskar",
    "hola",
}


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _log_message(
    student_id: str,
    message: str,
    sender: str,
    intent: Optional[str] = None,
    sentiment: Optional[str] = None,
) -> None:
    """Persist a single conversation turn to SQLite."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO conversations (student_id, message, sender, detected_intent, sentiment) "
            "VALUES (?, ?, ?, ?, ?)",
            (student_id, message, sender, intent, sentiment),
        )
        conn.commit()
    except Exception:
        pass


def _submit_withdrawal(student_id: str, reason: str, intent: str) -> str:
    """Create a structured withdrawal request and generated checklist."""
    return create_withdrawal_request(student_id, reason, intent)


def _fetch_student(student_id: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    return dict(row) if row else None


def _is_greeting(raw_message: str) -> bool:
    lower = raw_message.lower().strip()
    cleaned = lower.strip(" .,!?\t\r\n")
    return cleaned in _GREETING_SIGNALS or any(
        cleaned.startswith(f"{item} ") for item in _GREETING_SIGNALS
    )


def _handle_greeting(session: dict, language: str, voice: bool) -> ChatResponse:
    student_id = session["student_id"]
    student = _fetch_student(student_id)
    prefix = _language_prefix(language, voice)
    name = student["name"].split()[0] if student else "there"
    reply = (
        f"{prefix}Hello {name}. I can help with your CGPA, attendance, exams, "
        "scholarships, grievances, documents, hostel, fee status, notices, "
        "internships, or withdrawal/refund questions."
    )
    _log_message(student_id, reply, "bot", "help", "positive")
    return ChatResponse(
        reply=reply, state="ROUTED", intent="help", sentiment="positive"
    )


def _handle_out_of_scope(session: dict, language: str, voice: bool) -> ChatResponse:
    student_id = session["student_id"]
    prefix = _language_prefix(language, voice)
    reply = (
        f"{prefix}I am designed for AmityAssist student portal support, so I cannot help much with that topic here. "
        "Ask me about CGPA, attendance, exams, backpapers, scholarships, grievances, documents, hostel, fee dues, notices, internships, or withdrawal support."
    )
    _log_message(student_id, reply, "bot", "unknown", "neutral")
    return ChatResponse(
        reply=reply, state="ROUTED", intent="unknown", sentiment="neutral"
    )


def _fetch_exam_summary(student_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM examinations WHERE student_id = ? ORDER BY exam_date ASC",
        (student_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def _fetch_scholarship_summary(student_id: str, cgpa: float) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM scholarships ORDER BY eligibility_cgpa DESC"
    ).fetchall()
    applied = conn.execute(
        "SELECT scholarship_id, status FROM scholarship_applications WHERE student_id = ?",
        (student_id,),
    ).fetchall()
    statuses = {row["scholarship_id"]: row["status"] for row in applied}

    result = []
    for row in rows:
        item = dict(row)
        item["eligible"] = cgpa >= row["eligibility_cgpa"]
        item["application_status"] = statuses.get(row["id"])
        result.append(item)
    return result


def _fetch_notices(student: dict) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM notices
           WHERE (target_branch = 'ALL' OR target_branch = ?)
             AND (target_semester = 0 OR target_semester = ?)
           ORDER BY timestamp DESC, id DESC
           LIMIT 5""",
        (student["branch"], student["semester"]),
    ).fetchall()
    return [dict(row) for row in rows]


def _fetch_internships(cgpa: float) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM internships ORDER BY deadline ASC").fetchall()
    internships = []
    for row in rows:
        item = dict(row)
        item["eligible"] = cgpa >= row["required_cgpa"]
        internships.append(item)
    return internships


def _find_named_item(
    items: list[dict], raw_message: str, name_key: str = "name"
) -> Optional[dict]:
    lower = raw_message.lower()
    for item in items:
        name = str(item.get(name_key, "")).lower()
        compact_words = [word for word in name.split() if len(word) > 2]
        if name and (name in lower or any(word in lower for word in compact_words)):
            return item
    return None


def _apply_scholarship(student_id: str, scholarship: dict) -> str:
    conn = get_connection()
    existing = conn.execute(
        "SELECT status FROM scholarship_applications WHERE student_id = ? AND scholarship_id = ?",
        (student_id, scholarship["id"]),
    ).fetchone()
    if existing:
        return f"You have already applied for {scholarship['name']}. Current status: {existing['status']}."

    conn.execute(
        "INSERT INTO scholarship_applications (student_id, scholarship_id, status) VALUES (?, ?, 'pending')",
        (student_id, scholarship["id"]),
    )
    conn.commit()
    return f"Application submitted for {scholarship['name']}. Status: pending review."


def _register_backpaper(exam_id: int) -> str:
    conn = get_connection()
    row = conn.execute("SELECT * FROM examinations WHERE id = ?", (exam_id,)).fetchone()
    if not row:
        return "I could not find that back-paper record."
    if row["grade"] not in ("F", "D", None):
        return f"Back-paper registration is not applicable for {row['subject_name']}."
    if row["backpaper_status"] in ("registered", "paid"):
        return f"{row['subject_name']} is already {row['backpaper_status']} for back-paper processing."

    conn.execute(
        "UPDATE examinations SET backpaper_status = 'registered' WHERE id = ?",
        (exam_id,),
    )
    conn.commit()
    return f"Back-paper registration created for {row['subject_name']}. Fee payment is pending."


def _calculate_refund(student: dict) -> dict:
    enrolled = datetime.fromisoformat(student["enrolled_date"])
    days_enrolled = max((datetime.utcnow() - enrolled).days, 0)
    annual_tuition = 240000.0

    if days_enrolled <= 15:
        percent = 1.0
    elif days_enrolled <= 30:
        percent = 0.8
    elif days_enrolled <= 60:
        percent = 0.5
    elif days_enrolled <= 90:
        percent = 0.25
    else:
        percent = 0.0

    gross_refund = annual_tuition * percent
    fee_due = float(student.get("fee_due") or 0)
    return {
        "days_enrolled": days_enrolled,
        "percent": percent,
        "gross_refund": gross_refund,
        "fee_due": fee_due,
        "net_refund": max(gross_refund - fee_due, 0.0),
    }


def _language_prefix(language: str, voice: bool) -> str:
    if voice and language == "hindi":
        return "Voice command received. Hindi mode active.\n\n"
    if voice and language == "hinglish":
        return "Voice command received. Hinglish mode active.\n\n"
    if language == "hindi":
        return "Hindi mode: "
    if language == "hinglish":
        return "Hinglish mode: "
    if voice:
        return "Voice command received.\n\n"
    return ""


def _is_stop_command(raw_message: str) -> bool:
    text = raw_message.strip().lower()
    stop_tokens = (
        "stop", "stop response", "stop the response", "cancel response",
        "abort", "abort response", "end chat", "close chat", "halt",
        "mute", "pause", "cancel voice", "stop voice"
    )
    return text in stop_tokens or any(token in text for token in ("stop response", "stop the response", "cancel response", "abort response"))


def _is_lifecycle_query(raw_message: str, voice: bool) -> bool:
    lower = raw_message.lower()
    command_markers = (
        "show",
        "which",
        "eligible",
        "status",
        "file",
        "register",
        "apply",
        "admit card",
        "datesheet",
        "backpaper",
        "back paper",
        "cgpa",
        "attendance",
        "bata",
        "batao",
        "help",
        "complaint",
        "grievance",
        "result",
        "notice",
        "fee",
        "fees",
        "hostel",
        "document",
        "upload",
        "internship",
        "placement",
        "apply",
        "room",
        "dues",
        "track",
        "pahuncha",
        "pahucha",
        "kahan",
        "stage",
        "स्टेटस",
        "पहुंचा",
        "कहाँ",
        "स्थिति",
        "अपडेट",
        "विथड्रॉल",
    )
    return voice or any(marker in lower for marker in command_markers)


def _route_lifecycle_message(
    session: dict, raw_message: str, language: str, voice: bool
) -> Optional[ChatResponse]:
    student_id = session["student_id"]
    routed_intent = route_intent(raw_message)
    sentiment = score_sentiment(raw_message)
    student = _fetch_student(student_id)
    prefix = _language_prefix(language, voice)

    if routed_intent in {"unknown", "withdrawals"}:
        return None
    if not _is_lifecycle_query(raw_message, voice):
        return None
    if routed_intent == "fees":
        lower = raw_message.lower()
        withdrawal_fee_markers = (
            "cannot afford",
            "can't afford",
            "cant afford",
            "unable to pay",
            "withdraw",
            "withdrawal",
            "leave",
            "quit",
            "drop out",
        )
        if any(marker in lower for marker in withdrawal_fee_markers):
            return None

    if routed_intent == "help":
        reply = (
            f"{prefix}I can help with academics, exams, scholarships, grievances, "
            "withdrawals, refund estimates, notices, fee dues, hostel status, "
            "internships, and document support. I can also file grievances, apply "
            "for eligible scholarships, and register eligible back papers after confirmation."
        )
        _log_message(student_id, reply, "bot", routed_intent, sentiment)
        return ChatResponse(
            reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
        )

    if routed_intent == "academics" and student:
        reply = (
            f"{prefix}{student['name']}, your academic snapshot is: CGPA {student['cgpa']}, "
            f"attendance {student['attendance']}%, semester {student['semester']}, "
            f"performance: {student['academic_performance']}. "
            "For back papers or admit cards, ask about exams."
        )
        _log_message(student_id, reply, "bot", routed_intent, sentiment)
        return ChatResponse(
            reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
        )

    if routed_intent == "exams":
        exams = _fetch_exam_summary(student_id)
        if not exams:
            reply = f"{prefix}I could not find exam records for your profile yet."
        else:
            upcoming = [exam for exam in exams if exam["grade"] is None]
            backpapers = [exam for exam in exams if exam["grade"] in ("F", "D")]
            selected = _find_named_item(backpapers, raw_message, "subject_name")
            wants_register = any(
                word in raw_message.lower()
                for word in ("register", "apply", "book", "submit")
            )
            if selected and wants_register:
                session["pending_exam_id"] = selected["id"]
                session["state"] = "BACKPAPER_CONFIRM"
                reply = (
                    f"{prefix}I can register your back paper for {selected['subject_name']} "
                    f"({selected['subject_code']}). Type CONFIRM to register it, or CANCEL."
                )
                _log_message(student_id, reply, "bot", routed_intent, sentiment)
                return ChatResponse(
                    reply=reply,
                    state="CONFIRM",
                    intent=routed_intent,
                    sentiment=sentiment,
                )

            lines = []
            if upcoming:
                next_exam = upcoming[0]
                lines.append(
                    f"Next exam: {next_exam['subject_name']} on {next_exam['exam_date']}."
                )
            if backpapers:
                names = ", ".join(exam["subject_name"] for exam in backpapers[:3])
                lines.append(
                    f"Back-paper eligible subjects: {names}. Say 'register backpaper for subject name' to start."
                )
            if not lines:
                lines.append(
                    "All listed exam records are completed with no pending back-paper action."
                )
            reply = prefix + " ".join(lines)
        _log_message(student_id, reply, "bot", routed_intent, sentiment)
        return ChatResponse(
            reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
        )

    if routed_intent == "scholarships" and student:
        schemes = _fetch_scholarship_summary(student_id, float(student["cgpa"]))
        eligible = [scheme for scheme in schemes if scheme["eligible"]]
        wants_apply = any(
            word in raw_message.lower() for word in ("apply", "submit", "register")
        )
        selected = _find_named_item(eligible, raw_message)
        if wants_apply and selected:
            reply = prefix + _apply_scholarship(student_id, selected)
            _log_message(student_id, reply, "bot", routed_intent, sentiment)
            return ChatResponse(
                reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
            )
        if wants_apply and len(eligible) == 1:
            reply = prefix + _apply_scholarship(student_id, eligible[0])
            _log_message(student_id, reply, "bot", routed_intent, sentiment)
            return ChatResponse(
                reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
            )
        if wants_apply and len(eligible) > 1:
            names = ", ".join(scheme["name"] for scheme in eligible)
            reply = f"{prefix}You are eligible for multiple schemes: {names}. Please say which one you want to apply for."
            _log_message(student_id, reply, "bot", routed_intent, sentiment)
            return ChatResponse(
                reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
            )
        if eligible:
            names = ", ".join(scheme["name"] for scheme in eligible)
            reply = (
                f"{prefix}Based on CGPA {student['cgpa']}, you are eligible for: {names}. "
                "Say 'apply for scheme name' and I can submit it from chat."
            )
        else:
            minimum = (
                min(scheme["eligibility_cgpa"] for scheme in schemes) if schemes else 0
            )
            reply = (
                f"{prefix}Your current CGPA is {student['cgpa']}. "
                f"The lowest listed scholarship threshold is {minimum}."
            )
        _log_message(student_id, reply, "bot", routed_intent, sentiment)
        return ChatResponse(
            reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
        )

    if routed_intent == "fees" and student:
        due = float(student.get("fee_due") or 0)
        if due > 0:
            reply = (
                f"{prefix}Your fee status is {student['fee_status']} with outstanding dues of "
                f"INR {due:,.0f}. Clearing dues may be required for admit card or withdrawal processing."
            )
        else:
            reply = f"{prefix}Your fee status is {student['fee_status']}. There are no outstanding dues on your profile."
        _log_message(student_id, reply, "bot", routed_intent, sentiment)
        return ChatResponse(
            reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
        )

    if routed_intent == "hostel" and student:
        reply = (
            f"{prefix}Hostel status: {student['hostel_status']}. "
            "If this is incorrect or you need a room change, say 'file hostel complaint' and I will file a grievance."
        )
        _log_message(student_id, reply, "bot", routed_intent, sentiment)
        return ChatResponse(
            reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
        )

    if routed_intent == "notices" and student:
        notices = _fetch_notices(student)
        if notices:
            lines = [
                f"{notice['title']} ({notice['category']}): {notice['content']}"
                for notice in notices[:3]
            ]
            reply = (
                prefix
                + "Here are your latest targeted notices:\n- "
                + "\n- ".join(lines)
            )
        else:
            reply = f"{prefix}No targeted notices are currently available for your branch and semester."
        _log_message(student_id, reply, "bot", routed_intent, sentiment)
        return ChatResponse(
            reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
        )

    if routed_intent == "internships" and student:
        internships = _fetch_internships(float(student["cgpa"]))
        eligible = [item for item in internships if item["eligible"]]
        pool = eligible or internships
        if pool:
            label = "eligible internships" if eligible else "available internships"
            lines = [
                f"{item['title']} at {item['company']} - stipend {item['stipend']}, deadline {item['deadline']}"
                for item in pool[:3]
            ]
            reply = (
                prefix
                + f"Based on CGPA {student['cgpa']}, these {label} match your profile:\n- "
                + "\n- ".join(lines)
            )
        else:
            reply = f"{prefix}I could not find internship postings right now."
        _log_message(student_id, reply, "bot", routed_intent, sentiment)
        return ChatResponse(
            reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
        )

    if routed_intent == "documents":
        reply = (
            f"{prefix}You can upload ID proof, medical certificates, and withdrawal support files in the Document Center. "
            "After upload, Document AI simulation checks OCR fields, image quality, duplicate risk, signature/stamp presence, and fraud flags."
        )
        _log_message(student_id, reply, "bot", routed_intent, sentiment)
        return ChatResponse(
            reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
        )

    if routed_intent == "request_status":
        from .withdrawal_workflow import get_latest_withdrawal_status
        w_status = get_latest_withdrawal_status(student_id)
        if not w_status.get("has_request"):
            if language == "hi":
                reply = f"{prefix}Aapke account par abhi koi active withdrawal request nahi hai. Aap Procedures tab se Withdrawal initiate kar sakte hain."
            elif language == "hinglish":
                reply = f"{prefix}Aapka koi active withdrawal request abhi exist nahi karta. Aap Procedures tab se request shuru kar sakte hain."
            else:
                reply = f"{prefix}You do not have any active withdrawal request on file. You can initiate one under the Procedures tab."
        else:
            req = w_status["request"]
            gates = w_status.get("gates", [])
            cleared_gates = [g["department"] for g in gates if g.get("status") == "CLEARED"]
            pending_gates = [g["department"] for g in gates if g.get("status") != "CLEARED"]
            status_text = (req.get("status") or "pending").upper()
            ref = req.get("reference_no", "N/A")

            events = w_status.get("events", [])
            staff_msgs = [e for e in events if e.get("actor") in ("staff", "admin", "officer")]
            latest_note = staff_msgs[-1]["description"] if staff_msgs else "Clearance desks are actively processing your request."

            if language in ("hi", "hindi"):
                cleared_str = ', '.join(cleared_gates) if cleared_gates else 'Koyi nahi'
                pending_str = ', '.join(pending_gates) if pending_gates else 'Sabhi clear'
                reply = (
                    f"{prefix}Aapki withdrawal request (Ref: {ref}) vartaman me {status_text} hai. "
                    f"Cleared Desks: {cleared_str}. "
                    f"Pending Clearance: {pending_str}. "
                    f"Staff Update: {latest_note}"
                )
            elif language == "hinglish":
                cleared_str = ', '.join(cleared_gates) if cleared_gates else 'None yet'
                pending_str = ', '.join(pending_gates) if pending_gates else 'All cleared'
                reply = (
                    f"{prefix}Aapki withdrawal application (Ref: {ref}) abhi {status_text} stage par hai. "
                    f"Approved desks: {cleared_str}. "
                    f"Pending clearance: {pending_str}. "
                    f"Office Note: {latest_note}"
                )
            else:
                cleared_str = ', '.join(cleared_gates) if cleared_gates else 'None yet'
                pending_str = ', '.join(pending_gates) if pending_gates else 'All cleared'
                reply = (
                    f"{prefix}Your withdrawal application ({ref}) is currently in {status_text} stage. "
                    f"Cleared desks: {cleared_str}. "
                    f"Pending gates: {pending_str}. "
                    f"Latest Staff Update: {latest_note}"
                )
        _log_message(student_id, reply, "bot", routed_intent, sentiment)
        return ChatResponse(
            reply=reply, state="ROUTED", intent=routed_intent, sentiment=sentiment
        )

    if routed_intent == "grievances":
        session["state"] = "GRIEVANCE_CATEGORY"
        reply = (
            f"{prefix}I can file a grievance for you. "
            "Choose one category: academic, fee, hostel, exam, or scholarship."
        )
        _log_message(student_id, reply, "bot", routed_intent, sentiment)
        return ChatResponse(
            reply=reply,
            state="GRIEVANCE_CATEGORY",
            intent=routed_intent,
            sentiment=sentiment,
        )

    return None


def _handle_grievance_state(session: dict, raw_message: str) -> ChatResponse:
    student_id = session["student_id"]
    state = session["state"]
    sentiment = score_sentiment(raw_message)
    normalised = raw_message.lower().strip()

    if state == "GRIEVANCE_CATEGORY":
        category = next(
            (item for item in _GRIEVANCE_CATEGORIES if item in normalised), None
        )
        if category is None:
            reply = "Please choose one category: academic, fee, hostel, exam, or scholarship."
            _log_message(student_id, reply, "bot", "grievances", sentiment)
            return ChatResponse(
                reply=reply,
                state="GRIEVANCE_CATEGORY",
                intent="grievances",
                sentiment=sentiment,
            )
        session["grievance_category"] = category
        session["state"] = "GRIEVANCE_DESCRIPTION"
        reply = (
            f"Got it: {category}. Please describe the issue in one or two sentences."
        )
        _log_message(student_id, reply, "bot", "grievances", sentiment)
        return ChatResponse(
            reply=reply,
            state="GRIEVANCE_DESCRIPTION",
            intent="grievances",
            sentiment=sentiment,
        )

    if state == "GRIEVANCE_DESCRIPTION":
        if len(raw_message.strip()) < 5:
            reply = "Please add a little more detail so the right office can act on it."
            _log_message(student_id, reply, "bot", "grievances", sentiment)
            return ChatResponse(
                reply=reply,
                state="GRIEVANCE_DESCRIPTION",
                intent="grievances",
                sentiment=sentiment,
            )
        session["grievance_description"] = raw_message.strip()
        session["state"] = "GRIEVANCE_CONFIRM"
        reply = "I have the grievance details. Type CONFIRM to file it, or CANCEL to discard it."
        _log_message(student_id, reply, "bot", "grievances", sentiment)
        return ChatResponse(
            reply=reply,
            state="GRIEVANCE_CONFIRM",
            intent="grievances",
            sentiment=sentiment,
        )

    if state == "GRIEVANCE_CONFIRM":
        if raw_message.strip().upper() == "CONFIRM":
            conn = get_connection()
            conn.execute(
                "INSERT INTO grievances (student_id, category, description) VALUES (?, ?, ?)",
                (
                    student_id,
                    session["grievance_category"],
                    session["grievance_description"],
                ),
            )
            conn.commit()
            session["state"] = "ASK_REASON"
            session["grievance_category"] = None
            session["grievance_description"] = None
            reply = "Your grievance has been filed successfully. You will receive a response within 3 working days."
            _log_message(student_id, reply, "bot", "grievances", sentiment)
            return ChatResponse(
                reply=reply, state="RESOLVED", intent="grievances", sentiment=sentiment
            )
        if raw_message.strip().upper() == "CANCEL":
            session["state"] = "ASK_REASON"
            session["grievance_category"] = None
            session["grievance_description"] = None
            reply = "Grievance filing cancelled. No record was created."
            _log_message(student_id, reply, "bot", "grievances", sentiment)
            return ChatResponse(
                reply=reply,
                state="ASK_REASON",
                intent="grievances",
                sentiment=sentiment,
            )
        reply = "Please type CONFIRM to file the grievance, or CANCEL to discard it."
        _log_message(student_id, reply, "bot", "grievances", sentiment)
        return ChatResponse(
            reply=reply,
            state="GRIEVANCE_CONFIRM",
            intent="grievances",
            sentiment=sentiment,
        )

    return ChatResponse(
        reply="Invalid grievance state.",
        state="INVALID",
        intent="grievances",
        sentiment=sentiment,
    )


def _handle_backpaper_state(session: dict, raw_message: str) -> ChatResponse:
    student_id = session["student_id"]
    sentiment = score_sentiment(raw_message)
    normalised = raw_message.strip().upper()

    if normalised == "CONFIRM":
        exam_id = session.get("pending_exam_id")
        reply = (
            _register_backpaper(exam_id)
            if exam_id
            else "I could not find a pending back-paper registration."
        )
        session["pending_exam_id"] = None
        session["state"] = "ASK_REASON"
        _log_message(student_id, reply, "bot", "exams", sentiment)
        return ChatResponse(
            reply=reply, state="ASK_REASON", intent="exams", sentiment=sentiment
        )

    if normalised == "CANCEL":
        session["pending_exam_id"] = None
        session["state"] = "ASK_REASON"
        reply = "Back-paper registration cancelled. No exam record was changed."
        _log_message(student_id, reply, "bot", "exams", sentiment)
        return ChatResponse(
            reply=reply, state="ASK_REASON", intent="exams", sentiment=sentiment
        )

    reply = "Please type CONFIRM to register the back paper, or CANCEL to discard it."
    _log_message(student_id, reply, "bot", "exams", sentiment)
    return ChatResponse(
        reply=reply, state="CONFIRM", intent="exams", sentiment=sentiment
    )


# ---------------------------------------------------------------------------
# Core FSM
# ---------------------------------------------------------------------------


def process_message(session_id: str, raw_message: str) -> ChatResponse:
    """
    Process one student message through the conversation FSM.

    Each call advances the session state machine one step and returns
    the bot's reply along with metadata for the frontend to consume.
    """
    session = get_session(session_id)
    if session is None:
        return ChatResponse(
            reply=(
                "Your session has expired. For your security, sessions end after "
                "a period of inactivity. Please refresh the page and verify your identity again."
            ),
            state="INVALID",
        )

    student_id: str = session["student_id"]
    state: str = session["state"]
    language = detect_language(raw_message)
    voice = is_voice_command(raw_message)

    # Persist student's raw message
    _log_message(student_id, raw_message, "student")
    remember_turn(session, "student", raw_message)

    if _is_stop_command(raw_message):
        session["state"] = "ASK_REASON"
        session["intent"] = None
        session["reason"] = None
        reply = "Response stopped. You can ask a new question or continue with the assistant from the start."
        _log_message(student_id, reply, "bot", "help", "neutral")
        return ChatResponse(reply=reply, state="ASK_REASON", intent="help", sentiment="neutral")

    if state in {"GRIEVANCE_CATEGORY", "GRIEVANCE_DESCRIPTION", "GRIEVANCE_CONFIRM"}:
        return _handle_grievance_state(session, raw_message)

    if state == "BACKPAPER_CONFIRM":
        return _handle_backpaper_state(session, raw_message)

    routed_response = _route_lifecycle_message(
        session, raw_message, language, voice
    )
    if routed_response is not None:
        return routed_response

    if state == "ASK_REASON" and _is_greeting(raw_message):
        reply = (
            "Hello! I am here to help with your student activities. "
            "You can ask about CGPA, attendance, exams, scholarships, grievances, "
            "documents, fees, hostel status, internships, or withdrawals."
        )
        _log_message(student_id, reply, "bot", "help", "positive")
        return ChatResponse(
            reply=reply, state="ASK_REASON", intent="help", sentiment="positive"
        )

    # ── State: ASK_REASON ────────────────────────────────────────────────────
    if state == "ASK_REASON":

        intent = classify_intent(raw_message)
        routed_intent = route_intent(raw_message)
        sentiment = score_sentiment(raw_message)

        if intent == "unclear" and routed_intent == "unknown":
            student = _fetch_student(student_id)
            ai = advanced_reply(raw_message, student, session, language, voice)
            _log_message(student_id, ai["reply"], "bot", "help", ai["sentiment"])
            remember_turn(session, "bot", ai["reply"])
            return ChatResponse(
                reply=ai["reply"],
                state="ASK_REASON",
                intent="help",
                sentiment=ai["sentiment"],
                ai_source=ai["source"],
                memory_summary=ai["memory_summary"],
                escalation_recommended=ai["escalation_recommended"],
            )

        session["intent"] = intent
        session["reason"] = raw_message
        session["state"] = "SUGGEST"

        bot_reply = _SUGGESTIONS[intent]
        if route_intent(raw_message) == "withdrawals":
            student = _fetch_student(student_id)
            if student:
                refund = _calculate_refund(student)
                bot_reply += (
                    "\n\n"
                    f"Official refund guidance: your current enrollment age is {refund['days_enrolled']} days, "
                    f"which maps to the {int(refund['percent'] * 100)}% policy band before finance verification. "
                    f"Recorded outstanding dues are INR {refund['fee_due']:,.0f}. "
                    "The Finance Office confirms final eligibility and amount after clearances; UNIASSIST does not predict outcomes."
                )
        _log_message(student_id, bot_reply, "bot", intent, sentiment)

        return ChatResponse(
            reply=bot_reply,
            state="SUGGEST",
            intent=intent,
            sentiment=sentiment,
            memory_summary=summarize_memory(session),
        )

    # ── State: SUGGEST ───────────────────────────────────────────────────────
    elif state == "SUGGEST":
        intent = session.get("intent") or "unclear"
        sentiment = score_sentiment(raw_message)
        routed_intent = route_intent(raw_message)
        withdrawal_intent = classify_intent(raw_message)
        tokens = set(raw_message.lower().split())

        wants_alternative = bool(tokens & _POSITIVE_SIGNALS) and not bool(
            tokens & {"withdraw", "still", "proceed", "leave", "quit"}
        )
        explicit_decline = bool(tokens & _NEGATIVE_SIGNALS)

        if (
            routed_intent == "unknown"
            and withdrawal_intent == "unclear"
            and not wants_alternative
            and not explicit_decline
        ):
            bot_reply = (
                "I am not able to help with that topic yet. "
                "Please ask about student workflows like academics, scholarships, grievances, "
                "documents, fees, hostel, internships, or withdrawal support."
            )
            _log_message(student_id, bot_reply, "bot", "help", sentiment)
            return ChatResponse(
                reply=bot_reply, state="SUGGEST", intent="help", sentiment=sentiment
            )

        if wants_alternative:
            invalidate_session(session_id)
            bot_reply = (
                "That's great to hear! 🎉\n\n"
                "Please visit the **Student Services Portal** or speak directly with your "
                "academic advisor to arrange your chosen option. They will guide you through "
                "the next steps.\n\n"
                "Is there anything else I can help you with today?"
            )
            _log_message(student_id, bot_reply, "bot", intent, sentiment)
            return ChatResponse(
                reply=bot_reply, state="RESOLVED", intent=intent, sentiment=sentiment
            )

        else:
            session["state"] = "CONFIRM"
            bot_reply = (
                "I understand, and I respect your decision.\n\n"
                "Please note: submitting this request will initiate the official withdrawal workflow "
                "for your programme. UNIASSIST will generate your document checklist, form links, "
                "departments involved, and official timeline bands. The Registrar and Finance offices "
                "make final decisions according to university policy.\n\n"
                "To proceed, type **CONFIRM**.\n"
                "To cancel and go back, type **CANCEL**."
            )
            student = _fetch_student(student_id)
            if student:
                refund = _calculate_refund(student)
                bot_reply += (
                    "\n\n"
                    f"Refund policy band: {int(refund['percent'] * 100)}% before final finance verification. "
                    f"Recorded outstanding dues: INR {refund['fee_due']:,.0f}. "
                    "Finance processing generally takes 7-10 working days after all required clearances."
                )
            _log_message(student_id, bot_reply, "bot", intent, sentiment)
            return ChatResponse(
                reply=bot_reply, state="CONFIRM", intent=intent, sentiment=sentiment
            )

    # ── State: CONFIRM ───────────────────────────────────────────────────────
    elif state == "CONFIRM":
        intent = session.get("intent") or "unclear"
        sentiment = score_sentiment(raw_message)
        normalised = raw_message.strip().upper()

        if normalised == "CONFIRM":
            ref = _submit_withdrawal(student_id, session.get("reason", ""), intent)
            invalidate_session(session_id)
            bot_reply = (
                f"**Your withdrawal workflow has been submitted.**\n\n"
                f"**Reference:** `{ref}`\n\n"
                "Next, open Request Status to review the generated checklist, official forms, "
                "departments involved, and timeline guidance. According to the official procedure, "
                "initial verification generally takes 1-2 working days after submission."
            )
            _log_message(student_id, bot_reply, "bot", intent, sentiment)
            return ChatResponse(
                reply=bot_reply,
                state="DONE",
                intent=intent,
                sentiment=sentiment,
                withdrawal_submitted=True,
            )

        elif normalised == "CANCEL":
            session["state"] = "ASK_REASON"
            session["reason"] = None
            session["intent"] = None
            bot_reply = (
                "Your withdrawal request has been cancelled. "
                "No changes have been made to your enrolment.\n\n"
                "Is there anything else I can help you with today?"
            )
            _log_message(student_id, bot_reply, "bot", intent, sentiment)
            return ChatResponse(
                reply=bot_reply, state="ASK_REASON", intent=intent, sentiment=sentiment
            )

        else:
            bot_reply = (
                "I need a clear response to proceed.\n\n"
                "Please type **CONFIRM** to submit your withdrawal request, "
                "or **CANCEL** to abort."
            )
            _log_message(student_id, bot_reply, "bot")
            return ChatResponse(
                reply=bot_reply, state="CONFIRM", intent=intent, sentiment=sentiment
            )

    # ── Guard: session already closed ────────────────────────────────────────
    else:
        return ChatResponse(
            reply=(
                "Your request has already been processed. "
                "Please contact the Registrar's office directly for further assistance."
            ),
            state="DONE",
        )
