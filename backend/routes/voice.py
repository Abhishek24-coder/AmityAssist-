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
    language: str = Field("en-IN", description="BCP 47 language tag e.g. en-IN, hi-IN")
    page_context: Optional[dict[str, Any]] = Field(None, description="Active client screen context")
    conversation_history: Optional[list[dict[str, Any]]] = Field(None, description="Recent conversation turns")


@router.post("/query")
async def process_voice_query(body: VoiceQueryRequest, request: Request) -> dict[str, Any]:
    """Process a voice-command inquiry and return voice-optimized speech response and action shortcuts."""
    effective_sid = body.student_id
    if not effective_sid:
        auth_hdr = request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr.split(" ", 1)[1].strip()
            try:
                from ..security.jwt import decode_access_token
                payload = decode_access_token(token)
                effective_sid = payload.get("sub")
            except Exception:
                pass

    guidance = PolicySearchService.hybrid_guidance(
        query=body.spoken_text,
        student_id=effective_sid,
        page_context=body.page_context,
        language=body.language,
        history=body.conversation_history,
    )

    clean_speech = guidance.get("voice_speech_text") or guidance.get("answer", "")
    # Strip complex marks/citations for natural text-to-speech cadence
    if body.language == "hi-IN":
        clean_speech = clean_speech.replace("₹", "रुपये ").replace("INR ", "रुपये ").replace("ORD-", "अध्यादेश ")
    elif body.language == "hi-Latn":
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
        "speech_params": {
            "lang": body.language,
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
