"""Phase 18 advanced conversational AI helpers.

The service keeps UniAssist useful without a paid LLM key by using local,
auditable context memory and domain guardrails. If a Gemini API key is
configured, the same interface can call Gemini for a concise answer.
"""

from __future__ import annotations

import textwrap
from typing import Any

import httpx

from ..config import settings
from .local_llm_service import (
    generate_local_policy_answer,
    call_ollama_llama3,
    clean_text_for_speech,
    sanitize_and_verify_response,
    strip_markdown_stars,
)
from .nlp_service import route_intent, score_sentiment


_DOMAIN_SCOPE = (
    "academics, attendance, exams, backpapers, scholarships, grievances, "
    "documents, hostel, fee dues, notices, internships, withdrawal procedure, "
    "refund guidance, and request status"
)

_ESCALATION_MARKERS = {
    "urgent",
    "emergency",
    "harassment",
    "unsafe",
    "suicide",
    "self harm",
    "legal",
    "medical emergency",
    "threat",
    "discrimination",
}


def remember_turn(session: dict[str, Any], role: str, message: str) -> None:
    """Store a bounded conversational memory in the in-process session."""
    turns = session.setdefault("recent_turns", [])
    turns.append(
        {
            "role": role,
            "message": message.strip()[:500],
            "intent": route_intent(message),
            "sentiment": score_sentiment(message),
        }
    )
    del turns[:-8]
    session["memory_summary"] = summarize_memory(session)


def summarize_memory(session: dict[str, Any]) -> str:
    """Return a compact summary suitable for display or LLM prompting."""
    turns = session.get("recent_turns", [])
    if not turns:
        return "No prior context in this session."

    intents = [
        turn["intent"]
        for turn in turns
        if turn.get("intent") and turn["intent"] != "unknown"
    ]
    sentiments = [turn.get("sentiment") for turn in turns if turn.get("sentiment")]
    last_student_turn = next(
        (turn["message"] for turn in reversed(turns) if turn.get("role") == "student"),
        "",
    )
    intent_summary = ", ".join(dict.fromkeys(intents)) or "general support"
    sentiment_summary = sentiments[-1] if sentiments else "neutral"
    return (
        f"Recent topics: {intent_summary}. "
        f"Latest sentiment: {sentiment_summary}. "
        f"Latest student message: {last_student_turn[:120]}"
    )


def escalation_recommended(message: str, sentiment: str, memory_summary: str) -> bool:
    """Flag conversations that should move to a human staff member."""
    lower = f"{message} {memory_summary}".lower()
    return sentiment == "negative" and any(marker in lower for marker in _ESCALATION_MARKERS)


def build_local_contextual_reply(
    message: str,
    student: dict[str, Any] | None,
    memory_summary: str,
    language: str,
    voice: bool,
) -> str:
    """Domain-specific fallback when no external LLM is configured."""
    first_name = (student or {}).get("name", "student").split()[0]
    prefix = ""
    if voice:
        prefix = "Voice command received. "
    if language == "hindi":
        prefix += "Hindi mode: "
    elif language == "hinglish":
        prefix += "Hinglish mode: "

    return (
        f"{prefix}{first_name}, I can only answer inside UniAssist service workflows and student workflow support right now. "
        f"Supported areas are {_DOMAIN_SCOPE}. "
        "Tell me which service you want, for example: withdrawal checklist, fee status, "
        "document verification, grievance filing, scholarship eligibility, notices, or exam results.\n\n"
        f"Context I will keep for this session: {memory_summary}"
    )


def try_gemini_reply(
    message: str,
    student: dict[str, Any] | None,
    memory_summary: str,
) -> str | None:
    """Call Gemini only when explicitly configured; otherwise return None."""
    if not settings.llm_enabled:
        return None

    prompt = textwrap.dedent(
        f"""
        You are UniAssist, a university student-service assistant.
        Stay inside this domain: {_DOMAIN_SCOPE}.
        Do not invent approval decisions, refund outcomes, legal advice, or medical advice.
        Give a concise next-step answer and suggest staff escalation for urgent cases.

        Student context: {student or {}}
        Conversation memory: {memory_summary}
        Student message: {message}
        """
    ).strip()

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = httpx.post(
            url,
            json=payload,
            timeout=settings.llm_timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text")
        )
    except Exception:
        return None


def synthesize_guidance_with_gemini(
    query: str,
    citations: list[dict[str, Any]],
    student: dict[str, Any] | None = None,
    page_context: dict[str, Any] | None = None,
    language: str = "en-IN",
    return_source: bool = False,
    history: list[dict[str, Any]] | None = None,
) -> Any:
    """Synthesize concise spoken voice response from retrieved university policy/form citations.

    Implements a multi-tier waterfall router:
    Tier 1 (Local): Ollama (Llama 3.2) on-premise inference
    Tier 2 (Cloud): Google Gemini 1.5 Flash (if configured)
    Tier 3 (Offline): Deterministic SQLite FTS5 Citation Formatter
    """
    from .local_llm_service import call_ollama_llama3, clean_text_for_speech
    from ..data.kiosk_master_procedures import get_procedure_by_keyword

    facts = "\n".join(
        [
            f"- [{c.get('clause_code', 'ORD')}] {c.get('title', '')}: {c.get('content', '')}"
            for c in citations[:3]
        ]
    )

    # Master Procedural Grounding (Pillar 1 & 3): Eliminate hallucinations like 'सेवा केंद्र 3'
    matched_procedure = get_procedure_by_keyword(query)
    if not matched_procedure and history:
        combined_h = " ".join([str(h.get("content") or "").lower() for h in history[-3:]])
        matched_procedure = get_procedure_by_keyword(combined_h)

    if matched_procedure:
        req_docs = ", ".join(matched_procedure.get("required_documents") or ["None required (100% digital process)"])
        proc_grounding = (
            f"\nOFFICIAL MASTER PROCEDURE GROUNDING:\n"
            f"- Official Form: {matched_procedure.get('official_name', 'University Form')}\n"
            f"- Kiosk Access: Download directly right here on this UniAssist kiosk screen using the action button below ({matched_procedure.get('action_label', 'Download Form')}). Never send student to wander across campus counters to obtain it.\n"
            f"- Eligibility: {matched_procedure.get('eligibility', 'All eligible university members')}\n"
            f"- Required Attachments: {req_docs}\n"
            f"- Verified Submission Office: {matched_procedure.get('submission_office', 'UniAssist Portal / Department Desk')}\n"
            f"- Turnaround SLA: {matched_procedure.get('deadline_sla', 'Standard campus SLA')}\n"
        )
        facts += proc_grounding

    lang_instruction = ""
    if language == "hi-IN":
        lang_instruction = (
            "\nCRITICAL LANGUAGE INSTRUCTION: The user has chosen HINDI (हिन्दी).\n"
            "You MUST generate your entire answer and speech text ONLY in pure, natural, fluent Hindi "
            "using Devanagari script (e.g. 'हाँ, आप 71% उपस्थिति के साथ परीक्षा दे सकते हैं, लेकिन आपको डीन छूट के लिए फॉर्म AC-04 जमा करना होगा...'). "
            "Keep official form names (like Form AC-04) intact. Do NOT output English sentences.\n"
        )
    elif language == "hi-Latn":
        lang_instruction = (
            "\nCRITICAL LANGUAGE INSTRUCTION: The user has chosen HINGLISH.\n"
            "You MUST generate your response in conversational Hinglish (Hindi written in Roman English alphabet, "
            "e.g. 'Haan, aap 71% attendance ke sath exam de sakte hain, lekin aapko Dean condonation ke liye Form AC-04 submit karna hoga...').\n"
        )

    history_context = ""
    if history:
        turns_summary = []
        for t in history[-4:]:
            r = "Student" if t.get("role") in ("user", "student") else "Counselor"
            msg = str(t.get("content") or t.get("message") or "")[:200].strip()
            if msg:
                turns_summary.append(f"{r}: {msg}")
        if turns_summary:
            history_context = "\nRecent Conversation History:\n" + "\n".join(turns_summary) + "\n"

    prompt = textwrap.dedent(
        f"""
        You are UniAssist, the official university digital counselor and voice guide.
        {lang_instruction}
        Answer the user query concisely, warmly, and empathetically using ONLY the verified university policy/form facts provided below.

        Strict Rules:
        1. CLOSED-DOMAIN DOCUMENT RULE: Answer ONLY and EXCLUSIVELY using verified information from the verified university documents provided. If any information is not present in the documents, state that no matching university record is found. NEVER guess, assume, or extrapolate.
        2. ZERO CODE & NO PROGRAMMING: NEVER output programming code (Python, C++, Java, JavaScript, etc.), algorithms, or homework solutions. If asked about programming or non-campus subjects, politely state you only assist with university campus procedures and forms.
        3. ZERO FOREIGN UNIASSIST HALLUCINATION: You are the on-campus Amity university kiosk counselor. You have ZERO connection to German or Australian uni-assist portals. NEVER mention Germany, Australia, or foreign admissions.
        4. APP-SCOPE STRICT LIMITATION: Do NOT answer anything other than this university kiosk app's functionality (academics, 75% attendance rules, examinations, fee clearances, caution deposit offsets, withdrawal refunds, clearance tracking, and 31 official university forms). Politely refuse any off-topic inquiries.
        5. Never contradict or invent fees, room numbers, deadlines, or SLAs.
        6. KIOSK-FIRST RULE: Whenever a user asks how or where to get an official document or form, ALWAYS state that they can download it directly right here on this UniAssist kiosk screen using the action button below. NEVER tell them to wander or find physical counters to obtain the form.
        7. ZERO FAKE ROOMS: NEVER invent non-existent campus locations, counters, or centers (such as 'सेवा केंद्र 3' or 'Service Center 3'). Physical submission is ONLY to verified rooms stated in the facts (e.g. Dean Room 201, Exam Cell Room 110, HR Room 103, Registrar Room 102).
        8. FORM NAMING: Always use the proper official name of the form (e.g., 'Supplementary / Backpaper Examination Application (Form EX-02)' or 'Attendance Condonation Application (Form AC-04)'), NEVER cryptic abbreviations like 'EX-2'.
        9. FORM EX-02 IS SOLELY FOR BACKPAPERS: Form EX-02 is strictly for supplementary/backpaper exams (INR 1,500 fee). Never suggest it for withdrawal, resignation, or refund.
        10. NO LEGAL CODES IN SPEECH: Never recite internal legal codes (such as ORD-..., OCRM, or clause codes) in spoken text. Speak naturally like a warm, helpful campus counselor (e.g. 'विश्वविद्यालय के नियमों के अनुसार' or 'According to university rules').
        11. FACULTY EXIT: If a faculty member asks about resignation or leaving job, direct them to HOD/Dean notice and HR Desk (Room 103). Never confuse faculty with students.
        12. Sound like an attentive, helpful campus counselor (like ChatGPT Voice), not a dry legal statute.
        13. Keep your answer under 3 to 4 clear spoken sentences suitable for text-to-speech reading. Absolutely NO markdown bolding, NO asterisks (** or *), and NO rigid bullet lists.
        14. End with a warm, natural follow-up or next-step offer (for example in English: "Would you like help starting this form?" or in Hindi: "क्या आप इस प्रक्रिया में और सहायता चाहते हैं?").

        Verified University Knowledge:
        {facts}

        Active Student Context:
        {student or 'Guest / Public Visitor'}

        Active Screen:
        {page_context or {}}
        {history_context}
        User Query:
        {query}
        """
    ).strip()

    # --- Priority 1: Ollama Llama 3.2 Local (only when explicitly configured as provider) ---
    if settings.is_ollama_enabled:
        system_instruction = (
            "You are UniAssist, an empathetic digital campus counselor at this university kiosk (Amity).\n"
            + (f"Respond in pure Devanagari Hindi (हिन्दी).\n" if language == "hi-IN" else (f"Respond in conversational Hinglish.\n" if language == "hi-Latn" else "Respond in warm, spoken English.\n"))
            + "STRICT RULES:\n"
            "- Answer in 2-3 natural sentences max strictly using the verified facts provided.\n"
            "- ZERO HALLUCINATION: You have zero connection to German or Australian uni-assist portals. Never mention Germany or Australia.\n"
            "- NO CODE / NO PROGRAMMING: Never write code or answer programming/homework questions. Politely state you only assist with university campus procedures.\n"
            "- Kiosk-First: Always instruct the user to download forms directly on this screen via the action button.\n"
            "- ZERO FAKE ROOMS: NEVER invent non-existent campus locations or counters like 'सेवा केंद्र 3'. Submissions go ONLY to verified rooms (Dean Room 201, Exam Cell Room 110, HR Room 103, Registrar Room 102).\n"
            "- Never mention internal clause codes (ORD-..., OCRM) in speech.\n"
            "- Use full official form names, not 'EX-2'.\n"
            "- NO ASTERISKS: Never output markdown asterisks (** or *), bold tags, or hash headings."
        )
        ollama_reply = call_ollama_llama3(prompt, system_instruction, history=history)
        if ollama_reply and ollama_reply.strip():
            clean_reply = sanitize_and_verify_response(ollama_reply.strip())
            clean_reply = strip_markdown_stars(clean_reply)
            return (clean_reply, "Ollama Local AI (Llama 3.2)") if return_source else clean_reply

    # --- Priority 2: Gemini Cloud Hybrid Fallback ---
    if settings.llm_enabled:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }

        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=max(settings.llm_timeout_seconds, 10.0),
            )
            response.raise_for_status()
            data = response.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text")
            )
            if text and text.strip():
                clean_text = sanitize_and_verify_response(text.strip())
                return (clean_text, "Gemini Hybrid AI") if return_source else clean_text
        except Exception:
            pass

    # --- Priority 3: Deterministic SQLite FTS5 Citation Formatter (100% Offline) ---
    local_answer = generate_local_policy_answer(
        query, citations, student, page_context, language=language, use_ollama=False
    )
    if local_answer:
        return (local_answer, "SQLite FTS5 (Local Offline)") if return_source else local_answer
    return None


def advanced_reply(
    message: str,
    student: dict[str, Any] | None,
    session: dict[str, Any],
    language: str,
    voice: bool,
) -> dict[str, Any]:
    """Return an advanced AI reply with safe local fallback metadata."""
    memory_summary = summarize_memory(session)
    sentiment = score_sentiment(message)
    llm_reply = try_gemini_reply(message, student, memory_summary)

    if llm_reply:
        source = "gemini"
        reply = llm_reply
    else:
        source = "local-context"
        reply = build_local_contextual_reply(
            message, student, memory_summary, language, voice
        )

    return {
        "reply": reply,
        "source": source,
        "memory_summary": memory_summary,
        "sentiment": sentiment,
        "escalation_recommended": escalation_recommended(
            message, sentiment, memory_summary
        ),
    }
