"""Phase 29: Voice Functionality Router.

Enables push-to-talk voice processing and text-to-speech (TTS) synthesis
parameters for the UniAssist kiosk and web frontend.
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from ..services.policy_search_service import PolicySearchService


router = APIRouter(prefix="/api/voice", tags=["Voice Functionality & TTS"])


class VoiceQueryRequest(BaseModel):
    spoken_text: str = Field(..., min_length=1, max_length=500, description="Transcribed voice text from microphone")
    student_id: Optional[str] = Field(None, description="Optional student ID for personalization")
    is_staff: Optional[bool] = Field(False, description="Whether the requester is an authorized staff member")
    staff_role: Optional[str] = Field(None, description="Staff role e.g. Registrar, Hostel, Accounts")
    staff_username: Optional[str] = Field(None, description="Staff username")
    language: str = Field("en-IN", description="BCP 47 language tag e.g. en-IN, hi-IN")
    page_context: Optional[dict[str, Any]] = Field(None, description="Active client screen context")
    conversation_history: Optional[list[dict[str, Any]]] = Field(None, description="Recent conversation turns")


@router.post("/query")
async def process_voice_query(body: VoiceQueryRequest, request: Request) -> dict[str, Any]:
    """Process a voice-command inquiry and return voice-optimized speech response and action shortcuts."""
    is_staff = body.is_staff or False
    staff_role = body.staff_role
    effective_sid = body.student_id
    if effective_sid and str(effective_sid).strip().upper() in ("GUEST", "PUBLIC", "NONE", "NULL", ""):
        effective_sid = None

    # Check page_context for staff indicators or public kiosk routes
    route_name = ""
    if body.page_context and isinstance(body.page_context, dict):
        route_name = str(body.page_context.get("route", "")).lower().strip()
        if body.page_context.get("is_staff") or "/staff" in route_name:
            is_staff = True
            staff_role = staff_role or body.page_context.get("staff_role") or "Registrar Staff"
            effective_sid = None

    is_public_page = bool(route_name and route_name in ("/", "/services", "/login", "/welcome"))

    auth_hdr = request.headers.get("Authorization", "")
    if auth_hdr.startswith("Bearer "):
        token = auth_hdr.split(" ", 1)[1].strip()
        try:
            from ..security.jwt import decode_access_token
            payload = decode_access_token(token)
            if payload.get("role") == "staff":
                is_staff = True
                staff_role = staff_role or payload.get("staff_role") or "Registrar Staff"
                effective_sid = None
            elif not is_staff and not is_public_page and body.student_id is not None and payload.get("role") == "student":
                effective_sid = payload.get("sub")
        except Exception:
            pass

    # Never attach student record if on a public screen or if caller explicitly sent null student_id
    if is_public_page or body.student_id is None:
        effective_sid = None

    # Dynamic language adaptation: English -> en-IN, Hinglish -> hi-Latn, Hindi -> hi-IN
    from ..services.nlp_service import detect_language
    detected_lang_type = detect_language(body.spoken_text)
    if detected_lang_type == "hindi":
        effective_language = "hi-IN"
    elif detected_lang_type == "hinglish":
        effective_language = "hi-Latn"
    else:
        effective_language = "en-IN"

    guidance = PolicySearchService.hybrid_guidance(
        query=body.spoken_text,
        student_id=effective_sid,
        page_context=body.page_context,
        language=effective_language,
        history=body.conversation_history,
        is_staff=is_staff,
        staff_role=staff_role,
    )

    clean_speech = guidance.get("voice_speech_text") or guidance.get("answer", "")
    # Strip complex marks/citations for natural text-to-speech cadence in the detected language
    if effective_language == "hi-IN":
        clean_speech = clean_speech.replace("₹", "रुपये ").replace("INR ", "रुपये ").replace("ORD-", "अध्यादेश ")
    elif effective_language == "hi-Latn":
        clean_speech = clean_speech.replace("₹", "rupaye ").replace("INR ", "rupaye ").replace("ORD-", "Ordinance ")
    else:
        clean_speech = clean_speech.replace("₹", "Rupees ").replace("INR ", "Rupees ").replace("ORD-", "Ordinance ")

    return {
        "status": guidance.get("status"),
        "is_ambiguous": guidance.get("is_ambiguous", False),
        "clarification_options": guidance.get("clarification_options", []),
        "domain": guidance.get("domain"),
        "transcription": body.spoken_text,
        "response_text": guidance["answer"],
        "speech_text": clean_speech,
        "engine": guidance.get("engine", "Gemini Hybrid AI"),
        "detected_language": effective_language,
        "language": effective_language,
        "speech_params": {
            "lang": effective_language,
            "rate": 0.95,  # Measured cadence for kiosks
            "pitch": 1.0,
            "volume": 1.0,
        },
        "citations": guidance.get("citations", []),
        "recommended_action": guidance.get("recommended_action"),
        "action_url": guidance.get("action_url"),
        "highlight_target": guidance.get("highlight_target"),
        "screen_instruction": guidance.get("screen_instruction"),
    }

