"""Phase 29: Voice Functionality Router.

Enables push-to-talk voice processing and text-to-speech (TTS) synthesis
parameters for the UniAssist kiosk and web frontend.
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..services.policy_search_service import PolicySearchService


router = APIRouter(prefix="/api/voice", tags=["Voice Functionality & TTS"])


class VoiceQueryRequest(BaseModel):
    spoken_text: str = Field(..., min_length=1, max_length=500, description="Transcribed voice text from microphone")
    student_id: Optional[str] = Field(None, description="Optional student ID for personalization")
    language: str = Field("en-IN", description="BCP 47 language tag e.g. en-IN, hi-IN")


@router.post("/query")
async def process_voice_query(body: VoiceQueryRequest) -> dict[str, Any]:
    """Process a voice-command inquiry and return voice-optimized speech response and action shortcuts."""
    guidance = PolicySearchService.hybrid_guidance(
        query=body.spoken_text,
        student_id=body.student_id,
    )

    clean_speech = guidance.get("voice_speech_text") or guidance.get("answer", "")
    # Strip complex marks/citations for natural text-to-speech cadence
    clean_speech = clean_speech.replace("₹", "Rupees ").replace("ORD-", "Ordinance ")

    return {
        "transcription": body.spoken_text,
        "response_text": guidance["answer"],
        "speech_text": clean_speech,
        "speech_params": {
            "lang": body.language,
            "rate": 0.95,  # Measured cadence for kiosks
            "pitch": 1.0,
            "volume": 1.0,
        },
        "citations": guidance.get("citations", []),
        "recommended_action": guidance.get("recommended_action"),
        "action_url": guidance.get("action_url"),
    }
