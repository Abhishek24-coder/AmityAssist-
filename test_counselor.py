"""
UniAssist AI Counselor Interactive Test Suite
Allows testing both Text Chat and Voice Speech features directly without running the Flutter frontend.
Supports:
  - Single queries or batch queries separated by ';' or '||'
  - Guest Mode vs Authenticated Student Mode (/guest, /student)
  - Interactive Cross-Questioning & Option Selection (1, 2, 3 or keywords)
  - Multi-Turn Conversation Memory with automatic context carry-over
  - Speech Audio Playback on Windows native TTS (/audio)
  - Multilingual Testing: English (/en), Hindi (/hi), Hinglish (/hinglish)
  - Procedure inspection (/steps)
"""

from __future__ import annotations

import os
import sys
import re
import subprocess
import argparse
from typing import Optional, List, Dict, Any

def sanitize_batch_input(text: str) -> List[str]:
    """Split input queries while guarding against common contraction typos like 'don; t'."""
    # Fix accidental semicolon instead of apostrophe in contractions: don; t -> don't, can; t -> can't, etc.
    cleaned = re.sub(r"\b([a-zA-Z]+);\s*([a-zA-Z]+)\b", r"\1'\2", text)
    if "||" in cleaned:
        return [part.strip() for part in cleaned.split("||") if part.strip()]
    if ";" in cleaned:
        return [part.strip() for part in cleaned.split(";") if part.strip()]
    return [cleaned.strip()]

# Ensure stdout handles UTF-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.services.policy_search_service import PolicySearchService
from backend.services.procedure_service import ProcedureService


def speak_windows(text: str):
    """Speak text using Windows native SpeechSynthesizer without requiring extra libraries."""
    try:
        clean_text = text.replace('"', ' ').replace("'", " ").replace("\n", " ")[:350]
        ps_cmd = f'Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Rate = 0; $s.Speak("{clean_text}")'
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def run_query(
    query: str,
    language: str = "en-IN",
    student_id: str = "GUEST",
    play_audio: bool = False,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Execute a query through the full AI Counselor pipeline and display Chat & Voice outputs."""
    print("\n" + "=" * 75)
    role_label = "Authenticated Student (STU001)" if student_id != "GUEST" else "Walk-in Guest / Kiosk User"
    print(f"QUERY    : \"{query}\"")
    print(f"SETTINGS : Language: {language} | Role: {role_label}")
    print("=" * 75)

    res = PolicySearchService.hybrid_guidance(
        query=query,
        student_id=student_id,
        language=language,
        history=history,
    )

    status = res.get("status")
    is_ambiguous = res.get("is_ambiguous", False)
    options = res.get("clarification_options", [])
    answer = res.get("answer", "")
    voice_speech = res.get("voice_speech_text") or answer
    engine = res.get("engine", "UniAssist Policy Engine")
    domain = res.get("domain", "General")
    action_label = res.get("recommended_action") or "None"
    action_url = res.get("action_url") or "None"
    citations = res.get("citations") or []

    print(f"\n[ENGINE]   : {engine}")
    print(f"[DOMAIN]   : {domain}")
    print(f"[ACTION]   : {action_label} -> {action_url}")
    if citations:
        c_codes = [c.get("clause_code") or c.get("doc_id") or "Citation" for c in citations if isinstance(c, dict)]
        print(f"[CITATIONS]: {', '.join(c_codes)}")

    if status == "trigger_cross_question" or is_ambiguous:
        print("\n⚡ [DISAMBIGUATION REQUIRED / CROSS-QUESTION TRIGGERED] ⚡")
        print("The AI detected an ambiguous intent and requires clarification before database access:")
        for idx, opt in enumerate(options, 1):
            print(f"   [{idx}] {opt.get('label')}  (Reply '{idx}' or '{opt.get('value')}')")

    print("\n--- [1. CHAT RESPONSE (Text Display)] ---")
    print(answer)

    print("\n--- [2. VOICE SPEECH OUTPUT (Spoken TTS Audio)] ---")
    print(voice_speech)

    if play_audio:
        print("\n🔊 [AUDIO] Playing voice speech through speakers...")
        speak_windows(voice_speech)

    print("=" * 75)
    return res


def run_batch_queries(
    queries: List[str],
    language: str = "en-IN",
    student_id: str = "GUEST",
    play_audio: bool = False,
):
    """Run multiple queries in sequence and print distinct responses for each."""
    total = len(queries)
    print(f"\n🚀 Running Batch of {total} Questions...")
    history: List[Dict[str, Any]] = []
    for idx, q in enumerate(queries, 1):
        clean_q = q.strip()
        if not clean_q:
            continue
        print(f"\n>>> [Question {idx} of {total}]")
        res = run_query(clean_q, language=language, student_id=student_id, play_audio=play_audio, history=history)
        history.append({"role": "user", "content": clean_q})
        history.append({"role": "assistant", "content": res.get("answer", "")})
        if len(history) > 8:
            history = history[-8:]


def interactive_loop():
    current_lang = "en-IN"
    current_student_id = "GUEST"  # Default to Kiosk Guest to observe disambiguation
    play_audio = False
    history: List[Dict[str, Any]] = []

    print("\n" + "*" * 75)
    print("      UNIASSIST AI COUNSELOR - INTERACTIVE TEST CONSOLE")
    print("*" * 75)
    print("Commands:")
    print("  /guest     - Switch to Guest / Kiosk mode (Observe Disambiguation)")
    print("  /student   - Switch to Authenticated Student mode (STU001)")
    print("  /en        - Switch language to English (en-IN)")
    print("  /hi        - Switch language to Hindi (hi-IN, Devanagari)")
    print("  /hinglish  - Switch language to Hinglish (hi-Latn)")
    print("  /audio     - Toggle speaker voice playback (currently " + ("ON" if play_audio else "OFF") + ")")
    print("  /reset     - Clear conversation history")
    print("  /steps     - View all live procedure steps currently in Database")
    print("  /exit      - Exit tester")
    print("\nTip: You can ask multiple questions at once separated by ';' (e.g. 'I want to leave ; what is 75% attendance rule')\n")

    while True:
        lang_label = "English" if current_lang == "en-IN" else ("Hindi" if current_lang == "hi-IN" else "Hinglish")
        role_label = "Student" if current_student_id != "GUEST" else "Guest"
        audio_label = "ON" if play_audio else "OFF"
        turns_label = f"Turns:{len(history)//2}" if history else "Fresh"
        try:
            prompt = f"\n[{lang_label} | {role_label} | Audio:{audio_label} | {turns_label}] Ask > "
            user_input = input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting UniAssist AI Counselor Tester.")
            break

        if not user_input:
            continue

        cmd = user_input.lower()
        if cmd in ("/exit", "exit", "quit", "q"):
            print("Exiting UniAssist AI Counselor Tester.")
            break
        elif cmd == "/guest":
            current_student_id = "GUEST"
            print("-> Switched to Guest / Kiosk Walk-in user.")
            continue
        elif cmd == "/student":
            current_student_id = "STU001"
            print("-> Switched to Authenticated Student (STU001).")
            continue
        elif cmd == "/en":
            current_lang = "en-IN"
            print("-> Language switched to English.")
            continue
        elif cmd == "/hi":
            current_lang = "hi-IN"
            print("-> Language switched to Hindi (हिन्दी).")
            continue
        elif cmd in ("/hinglish", "/latn"):
            current_lang = "hi-Latn"
            print("-> Language switched to Hinglish.")
            continue
        elif cmd == "/audio":
            play_audio = not play_audio
            print(f"-> Speaker audio playback is now {'ENABLED (ON)' if play_audio else 'DISABLED (OFF)'}.")
            continue
        elif cmd in ("/reset", "/clear"):
            history.clear()
            print("-> Conversation history reset.")
            continue
        elif cmd == "/steps":
            print("\n--- Current Procedure Steps in Database ---")
            steps = ProcedureService.get_steps("withdrawal")
            print(f"Withdrawal Steps ({len(steps)}):")
            for s in steps:
                print(f"  Step {s['step_number']}: {s['title']} ({s['department']} • {s.get('timeline_text', '1-2 days')})")
            custom_procs = ProcedureService.list_procedures()
            print(f"\nCustom Procedures ({len(custom_procs)}):")
            for cp in custom_procs:
                print(f"  [{cp['id']}] {cp['title']} ({cp['department']}) - {len(cp.get('steps', []))} steps")
            continue

        # Check for multiple questions separated by ';' or '||'
        batch = sanitize_batch_input(user_input)
        if len(batch) > 1:
            run_batch_queries(batch, language=current_lang, student_id=current_student_id, play_audio=play_audio)
            continue
        elif batch:
            user_input = batch[0]

        # Execute single query with conversation history
        res = run_query(
            user_input,
            language=current_lang,
            student_id=current_student_id,
            play_audio=play_audio,
            history=history,
        )

        # Update history
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": res.get("answer", "")})
        if len(history) > 8:
            history = history[-8:]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test UniAssist AI Counselor Chat and Voice")
    parser.add_argument("query", nargs="?", help="Optional single or batch query (use ';' for multiple questions)")
    parser.add_argument("--guest", action="store_true", help="Run in Guest / Walk-in Kiosk mode")
    parser.add_argument("--student", default="STU001", help="Student ID (default STU001)")
    parser.add_argument("--lang", choices=["en-IN", "hi-IN", "hi-Latn"], default="en-IN", help="Language tag")
    parser.add_argument("--audio", action="store_true", help="Play audio speech output through speakers")
    args = parser.parse_args()

    active_student_id = "GUEST" if args.guest else args.student

    if args.query:
        batch = sanitize_batch_input(args.query)
        if len(batch) > 1:
            run_batch_queries(batch, language=args.lang, student_id=active_student_id, play_audio=args.audio)
        elif batch:
            run_query(batch[0], language=args.lang, student_id=active_student_id, play_audio=args.audio)
    else:
        interactive_loop()
