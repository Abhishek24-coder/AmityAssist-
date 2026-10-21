"""
Chat message endpoint.

Rate-limited to 20 requests/minute per IP.
Session validity is checked before every message is processed.
"""

from fastapi import APIRouter, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..models.schemas import ChatRequest, ChatResponse
from ..services.chat_service import get_session, process_message, create_session, _sessions

router = APIRouter(prefix="/api/chat", tags=["Chat"])
limiter = Limiter(key_func=get_remote_address)


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
@router.post("/message", response_model=ChatResponse)
@limiter.limit("60/minute")
async def send_message(request: Request, body: ChatRequest) -> ChatResponse:
    """Accept a student message and advance the conversation FSM."""
    session_id = body.session_id
    if session_id:
        if get_session(session_id) is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired session. Please re-verify your identity.",
            )
    elif body.student_id:
        for sid, sdata in _sessions.items():
            if sdata.get("student_id") == body.student_id:
                session_id = sid
                break
        if not session_id:
            session_id = create_session(body.student_id)
    else:
        session_id = create_session("GUEST")

    return process_message(session_id, body.message)
