"""Local, auditable AI service for UniAssist with Ollama (Llama 3.2) integration.

This module combines on-premise local LLM inference via Ollama (Llama 3.2)
with deterministic citation templates as a fallback. It never invents policy outcomes
and always grounds responses in the verified citation set returned by SQLite FTS5.
"""

from __future__ import annotations

import re
from typing import Any
import httpx

from ..config import settings


def _safe_title(citation: dict[str, Any]) -> str:
    return str((citation or {}).get("title") or "verified university guidance").strip()


def _safe_clause(citation: dict[str, Any]) -> str:
    return str((citation or {}).get("clause_code") or "Policy clause").strip()


def _safe_content(citation: dict[str, Any]) -> str:
    content = str((citation or {}).get("content") or "").strip()
    return content[:500]


def strip_markdown_stars(text: str) -> str:
    """Remove markdown bold asterisks and stray asterisks while preserving line breaks and structure."""
    if not text:
        return ""
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    cleaned = re.sub(r"\*([^*]+)\*", r"\1", cleaned)
    cleaned = re.sub(r"\*", "", cleaned)
    return cleaned


def clean_text_for_speech(text: str) -> str:
    """Strip markdown headers, bold asterisks, and code formatting for speech friendliness."""
    if not text:
        return ""
    cleaned = strip_markdown_stars(text)
    cleaned = re.sub(r"#{1,6}\s*", "", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"[-*]\s+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


VERIFIED_ROOMS = {"201", "103", "105", "110", "101", "102"}


def sanitize_and_verify_response(text: str) -> str:
    """Post-processing guardrails to ensure responses are concise, grounded, and free of fake rooms."""
    if not text:
        return ""
    cleaned = clean_text_for_speech(text)

    # 0. Intercept LLM meta-roleplay preambles & conversational scenario setups
    meta_patterns = [
        r"^it seems like you're trying to create a scenario[^\n.!?]*[.!?]?\s*",
        r"^i'll provide a possible response[^\n.!?]*[.!?]?\s*",
        r"^here is a possible response[^\n.!?]*[.!?]?\s*",
        r"^response:\s*(counselor:)?\s*",
        r"^counselor:\s*",
        r"^as an ai[^\n.!?]*[.!?]?\s*",
    ]
    for mp in meta_patterns:
        cleaned = re.sub(mp, "", cleaned, flags=re.IGNORECASE).strip()

    # Intercept hallucinated harassment or misconduct encouragement
    if any(p in cleaned.lower() for p in ["teacher ko pareshaan", "pareshan karna chahiye", "pareshaan karna chaahiye", "trouble the teacher", "harass"]):
        return "Sorry, main is baare me help nahi kar sakta. University Code of Conduct ke mutabiq teachers ya staff ko pareshaan karna strictly prohibited hai."

    # 1. Strip internal legalistic codes from spoken response
    cleaned = re.sub(r"\[?(ORD-[A-Z0-9.-]+|OCRM-[A-Z0-9.-]+)\]?", "university regulations", cleaned, flags=re.IGNORECASE)

    # 2. Intercept hallucinated room numbers: Room <number> or कमरा <number> or कक्ष <number>
    def _room_replacer(match: re.Match) -> str:
        prefix = match.group(1)
        num = match.group(2)
        if num in VERIFIED_ROOMS:
            return match.group(0)
        if any(term in prefix.lower() for term in ["कमरा", "कक्ष"]):
            return "विश्वविद्यालय प्रशासनिक डेस्क"
        return "the designated university desk"

    cleaned = re.sub(r"(Room|room|कमरा|कक्ष)\s*#?\s*(\d{2,4})", _room_replacer, cleaned)
    # Intercept fake service centers: सेवा केंद्र 3, Service Center 3, etc.
    cleaned = re.sub(r"(सेवा\s*केंद्र|Service\s*Center)\s*\d+", "विश्वविद्यालय कार्यालय", cleaned, flags=re.IGNORECASE)

    # 3. Hard sentence ceiling: Max 3 to 4 complete sentences without breaking abbreviations (e.g. B.Tech, Dr., 7.5)
    sentence_delimiters = re.split(r'(?<!\b[A-Za-z])(?<!\b[A-Z][a-z])(?<!\d)([.!?।])(?:\s+|$)', cleaned)
    if len(sentence_delimiters) > 1:
        reconstructed = []
        sentence_count = 0
        for i in range(0, len(sentence_delimiters) - 1, 2):
            sent = sentence_delimiters[i].strip()
            punct = sentence_delimiters[i + 1]
            if sent:
                reconstructed.append(f"{sent}{punct}")
                sentence_count += 1
                if sentence_count >= 3:
                    break
        if reconstructed:
            cleaned = " ".join(reconstructed)

    return cleaned.strip()


def check_ollama_status() -> dict[str, Any]:
    """Check connectivity to the local Ollama daemon and list available models."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                model_ready = any(settings.ollama_model in m for m in models)
                return {
                    "online": True,
                    "target_model": settings.ollama_model,
                    "model_installed": model_ready,
                    "available_models": models,
                    "base_url": settings.ollama_base_url,
                }
    except Exception as exc:
        return {
            "online": False,
            "target_model": settings.ollama_model,
            "model_installed": False,
            "available_models": [],
            "base_url": settings.ollama_base_url,
            "error": str(exc),
        }
    return {
        "online": False,
        "target_model": settings.ollama_model,
        "model_installed": False,
        "available_models": [],
        "base_url": settings.ollama_base_url,
    }


def ensure_ollama_daemon_running() -> bool:
    """Check if Ollama daemon is active; if not, automatically launch 'ollama serve' in background."""
    import os
    import sys
    import shutil
    import subprocess

    status = check_ollama_status()
    if status.get("online"):
        return True

    # Only attempt to auto-launch if explicitly enabled to prevent llama-server.exe crash dialogs on Windows
    if os.getenv("OLLAMA_AUTOSPAWN", "false").lower() not in ("true", "1", "yes"):
        return False

    ollama_path = shutil.which("ollama")
    if not ollama_path:
        local_app_data = os.getenv("LOCALAPPDATA", "")
        candidate = os.path.join(local_app_data, "Programs", "Ollama", "ollama.exe")
        if os.path.exists(candidate):
            ollama_path = candidate

    if ollama_path:
        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            subprocess.Popen(
                [ollama_path, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                shell=False,
            )
            return True
        except Exception:
            return False
    return False


def call_ollama_llama3(
    prompt: str,
    system_instruction: str,
    model: str | None = None,
    timeout: float | None = None,
    history: list[dict[str, Any]] | None = None,
) -> str | None:
    """Send an inference request to the local Ollama daemon with optional multi-turn conversation history."""
    target_model = model or settings.ollama_model
    request_timeout = timeout or settings.ollama_timeout_seconds
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_instruction}
    ]
    if history:
        # Bounded history window: last 4 turns, max 400 chars/turn to prevent context explosion and prompt injection
        for turn in history[-4:]:
            raw_role = str(turn.get("role", "user")).lower()
            role = "assistant" if raw_role in ("assistant", "model", "bot", "counselor") else "user"
            content = str(turn.get("content") or turn.get("message") or turn.get("text") or "")[:400].strip()
            if content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": target_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "num_predict": 100,
            "num_ctx": 1024,
        },
    }

    try:
        with httpx.Client(timeout=request_timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                if content and content.strip():
                    return sanitize_and_verify_response(content.strip())
    except Exception:
        return None
    return None


def generate_local_policy_answer(
    query: str,
    citations: list[dict[str, Any]],
    student: dict[str, Any] | None = None,
    page_context: dict[str, Any] | None = None,
    language: str = "en-IN",
    use_ollama: bool = True,
    history: list[dict[str, Any]] | None = None,
) -> str | None:
    """Return a concise answer using verified university clauses via Ollama or template fallback.

    If there is no verified citation set, refuses rather than fabricating.
    """
    if not query or not query.strip():
        return None
    if not citations:
        if language == "hi-IN":
            return "मुझे क्षमा करें, मैं केवल सत्यापित विश्वविद्यालय नियमों और अभिलेखों के आधार पर ही उत्तर दे सकता हूँ। इस प्रश्न के लिए कोई मेल खाता अध्यादेश नहीं मिला।"
        elif language == "hi-Latn":
            return "Sorry, main keval verified university rules ke basis par answer kar sakta hoon. Is query ke liye koi matching policy nahi mili."
        return (
            "I am sorry, but I can only provide answers grounded in verified university policy and workflow records. "
            "No matching ordinance or guidance was found for this request."
        )

    student_name = (student or {}).get("name", "Student").split()[0]
    student_attendance = (student or {}).get("attendance", "N/A")
    student_fee_status = (student or {}).get("fee_status", "N/A")
    page_name = (page_context or {}).get("screen_name") or "the current panel"

    # Step 1: Attempt local Ollama inference if enabled / requested
    if use_ollama:
        from ..data.kiosk_master_procedures import get_procedure_by_keyword

        facts_text = "\n".join(
            [
                f"- [{_safe_clause(c)}] {_safe_title(c)}: {_safe_content(c)}"
                for c in citations[:3]
            ]
        )

        matched_procedure = get_procedure_by_keyword(query)
        if not matched_procedure and history:
            combined_h = " ".join([str(h.get("content") or "").lower() for h in history[-3:]])
            matched_procedure = get_procedure_by_keyword(combined_h)

        if matched_procedure:
            req_docs = ", ".join(matched_procedure.get("required_documents") or ["None required (100% digital process)"])
            facts_text += (
                f"\nOFFICIAL MASTER PROCEDURE GROUNDING:\n"
                f"- Official Form: {matched_procedure.get('official_name', 'University Form')}\n"
                f"- Kiosk Access: Download directly right here on this UniAssist kiosk screen using the action button below ({matched_procedure.get('action_label', 'Download Form')}). Never send student to wander across campus counters to obtain it.\n"
                f"- Eligibility: {matched_procedure.get('eligibility', 'All eligible university members')}\n"
                f"- Required Attachments: {req_docs}\n"
                f"- Verified Submission Office: {matched_procedure.get('submission_office', 'UniAssist Portal / Department Desk')}\n"
                f"- Turnaround SLA: {matched_procedure.get('deadline_sla', 'Standard campus SLA')}\n"
            )

        # Dynamically inject live configured workflow steps and custom procedures into grounding
        try:
            from .procedure_service import ProcedureService
            q_lower_check = query.lower()
            if any(w in q_lower_check for w in ["withdrawal", "refund", "विड्रॉल", "रिफंड"]):
                live_wth_steps = ProcedureService.get_steps("withdrawal")
                if live_wth_steps:
                    steps_summary = "; ".join([f"Step {s['step_number']}: {s['title']} ({s['department']})" for s in live_wth_steps])
                    facts_text += f"\n- Live Clearance Workflow Steps ({len(live_wth_steps)} stages): {steps_summary}"

            active_procs = ProcedureService.list_procedures(active_only=True)
            for ap in active_procs:
                p_title = (ap.get("title") or "").lower()
                if p_title and (p_title in q_lower_check or any(w in q_lower_check for w in p_title.split() if len(w) >= 4)):
                    step_list = ap.get("steps") or []
                    s_desc = "; ".join([f"Step {s.get('step_number', idx+1)}: {s.get('title')} ({s.get('responsible_desk', 'Desk')})" for idx, s in enumerate(step_list)]) if step_list else "Standard administrative review"
                    docs_desc = ", ".join(ap.get("required_docs") or ["None"])
                    facts_text += (
                        f"\nOFFICIAL CONFIGURED PROCEDURE ({ap.get('title')}):\n"
                        f"- Department: {ap.get('department', 'University Desk')}\n"
                        f"- Total Steps ({len(step_list)}): {s_desc}\n"
                        f"- SLA: {ap.get('sla_days', 3)} working days\n"
                        f"- Required Documents: {docs_desc}\n"
                    )
                    break
        except Exception:
            pass

        lang_instruction = "Respond in warm, professional, and concise Indian English for text-to-speech."
        if language == "hi-IN":
            lang_instruction = (
                "Respond strictly in pure, natural, fluent Devanagari Hindi (हिन्दी). "
                "Use a warm campus counselor voice suitable for audio playback."
            )
        elif language == "hi-Latn":
            lang_instruction = (
                "Respond in conversational Hinglish (Hindi written in Roman script) "
                "suitable for friendly voice assistance."
            )

        system_instruction = (
            "You are UniAssist, an empathetic digital campus counselor at an official university kiosk.\n"
            f"{lang_instruction}\n"
            "STRICT RULES:\n"
            "1. CLOSED-DOMAIN DOCUMENT RULE: Answer ONLY and EXCLUSIVELY using verified information from the verified university documents provided. If any information is not present in the documents, state that no matching university record is found. NEVER guess, assume, or extrapolate.\n"
            "2. APP-SCOPE STRICT LIMITATION: Do NOT answer anything other than this university kiosk app's functionality (academics, 75% attendance rules, examinations, fee clearances, caution deposit offsets, withdrawal refunds, clearance tracking, and 31 official university forms). Politely refuse any off-topic inquiries.\n"
            "3. Never hallucinate or alter fee amounts, refund percentages, dates, or attendance minimums.\n"
            "4. Form EX-02 is EXCLUSIVELY and ONLY for Supplementary / Backpaper Examinations (INR 1,500 fee). You must NEVER state or suggest that Form EX-02 is for program withdrawal, job resignation, or refund.\n"
            "5. If a faculty member or employee asks about quitting or resigning from their job, direct them to submit resignation notice to HOD/Dean and complete HR No-Dues clearance at Room 103. Never confuse faculty with students.\n"
            "6. Never fabricate connections between unrelated questions and university forms or withdrawal procedures.\n"
            "7. Keep the answer concise (2 to 3 sentences max) so it sounds natural when spoken aloud.\n"
            "8. End with a helpful, actionable next step related ONLY to verified campus procedures.\n"
            "9. Do NOT include bullet points, bold asterisks (**), or headers.\n"
            "10. NEVER mention internal legalistic codes or clause numbers (such as ORD-..., OCRM, or clause codes) in spoken text. Speak naturally like a helpful campus counselor (e.g., 'विश्वविद्यालय के नियमों के अनुसार' or 'According to university rules').\n"
            "11. Always use full, human-friendly form names (such as 'Supplementary / Backpaper Examination Application (Form EX-02)' or 'Attendance Condonation Application (Form AC-04)'), NEVER cryptic abbreviations like 'EX-2'.\n"
            "12. Kiosk-First Policy: NEVER invent non-existent campus locations, counters, or service centers (like 'सेवा केंद्र 3'). Always clarify that forms are directly downloadable on this UniAssist kiosk screen using the action button below, and submit only to verified offices (Dean Room 201, Exam Cell Room 110, HR Room 103, Registrar Room 102)."
        )

        user_prompt = (
            f"VERIFIED UNIVERSITY ORDINANCES:\n{facts_text}\n\n"
            f"STUDENT CONTEXT:\nName: {student_name}, Attendance: {student_attendance}%, Fee Status: {student_fee_status}\n"
            f"CURRENT SCREEN: {page_name}\n\n"
            f"STUDENT QUESTION:\n{query}"
        )

        ollama_result = call_ollama_llama3(user_prompt, system_instruction, history=history)
        if ollama_result:
            return ollama_result[:1200]

    # Step 2: Deterministic Citation Template Fallback (Guaranteed Safe)
    first = citations[0]
    clause = _safe_clause(first)
    title = _safe_title(first)
    summary = _safe_content(first)

    if language == "hi-IN":
        answer = (
            f"विश्वविद्यालय के सत्यापित नियमों के अनुसार, सबसे प्रासंगिक अध्यादेश संदर्भ {clause} ({title}) है। "
            f"नियम विवरण: {summary}। "
            f"किसी भी अंतिम प्रक्रिया या आवेदन के लिए कृपया संबंधित कार्यालय से संपर्क करें। क्या आप इस विषय पर कुछ और पूछना चाहते हैं?"
        )
    elif language == "hi-Latn":
        answer = (
            f"University ke verified rules ke mutabiq, sabse relevant policy reference {clause} ({title}) hai. "
            f"Niyam detail: {summary}. "
            f"Kisi bhi official procedure ke liye please relevant desk se confirm karein. Kya aapko is baare mein aur help chahiye?"
        )
    else:
        answer = (
            f"{student_name}, UniAssist can only answer questions using verified university ordinances and forms. "
            f"The closest university ordinance reference is {clause} ({title}): {summary}. "
            f"For official clearance or submission, please visit the relevant desk on {page_name}. Would you like help with this?"
        )

    return answer[:1200]
