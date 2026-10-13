"""Phase 32: Unit tests for On-Premise Local AI Engine (Ollama / Llama 3.2)."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.services.local_llm_service import (
    clean_text_for_speech,
    check_ollama_status,
    call_ollama_llama3,
    generate_local_policy_answer,
)
from backend.services.advanced_ai_service import synthesize_guidance_with_gemini


@pytest.fixture
def client():
    return TestClient(app)


def test_clean_text_for_speech():
    """Verify that speech text is stripped of markdown syntax that sounds awkward on TTS."""
    raw = "**Warning:** Please submit ### Form AC-04 *immediately*. `code` [Link](http://a.com) - Item 1"
    cleaned = clean_text_for_speech(raw)
    assert "**" not in cleaned
    assert "###" not in cleaned
    assert "`" not in cleaned
    assert "[" not in cleaned
    assert "Warning: Please submit Form AC-04 immediately. code Link Item 1" in cleaned


def test_check_ollama_status_offline():
    """Verify check_ollama_status returns offline dictionary when daemon is unreachable."""
    with patch("httpx.Client.get", side_effect=Exception("Connection refused")):
        status = check_ollama_status()
        assert status["online"] is False
        assert status["target_model"] == "llama3.2"
        assert status["model_installed"] is False


def test_check_ollama_status_online():
    """Verify check_ollama_status recognizes model when Ollama returns tags."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "models": [{"name": "llama3.2:latest"}, {"name": "mistral:latest"}]
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        status = check_ollama_status()
        assert status["online"] is True
        assert status["model_installed"] is True
        assert "llama3.2:latest" in status["available_models"]


def test_call_ollama_llama3_success():
    """Verify call_ollama_llama3 parses message content from Ollama response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "Aisha, you can apply for Dean condonation using **Form AC-04**.",
        }
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        reply = call_ollama_llama3("attendance query", "system instructions")
        assert reply is not None
        assert "Aisha, you can apply for Dean condonation using Form AC-04." in reply
        # Bold markers stripped
        assert "**" not in reply


def test_call_ollama_llama3_network_failure():
    """Verify call_ollama_llama3 gracefully returns None on connection error without raising."""
    with patch("httpx.Client.post", side_effect=Exception("Timeout")):
        reply = call_ollama_llama3("query", "system instructions")
        assert reply is None


def test_generate_local_policy_answer_with_ollama_mock():
    """Verify generate_local_policy_answer uses Ollama output when available."""
    citations = [
        {
            "clause_code": "ORD-ACAD-7.2",
            "title": "Attendance Policy",
            "content": "75% required; 60-74% dean condonation.",
        }
    ]

    with patch(
        "backend.services.local_llm_service.call_ollama_llama3",
        return_value="Yes, you qualify for Dean condonation under Ordinance ACAD 7.2.",
    ):
        ans = generate_local_policy_answer(
            query="Can I sit for exam?",
            citations=citations,
            student={"name": "Aisha Malik", "attendance": 68.0},
            language="en-IN",
            use_ollama=True,
        )
        assert ans == "Yes, you qualify for Dean condonation under Ordinance ACAD 7.2."


def test_generate_local_policy_answer_fallback_when_ollama_offline():
    """Verify generate_local_policy_answer falls back to deterministic template when Ollama fails."""
    citations = [
        {
            "clause_code": "ORD-WTH-14.1",
            "title": "Tuition Refund",
            "content": "100% refund 15 days before deadline.",
        }
    ]

    with patch("backend.services.local_llm_service.call_ollama_llama3", return_value=None):
        ans_en = generate_local_policy_answer(
            query="How much refund do I get?",
            citations=citations,
            student={"name": "Aisha Malik"},
            language="en-IN",
            use_ollama=True,
        )
        assert "Aisha" in ans_en
        assert "ORD-WTH-14.1" in ans_en
        assert "Tuition Refund" in ans_en

        ans_hi = generate_local_policy_answer(
            query="रिफंड कितना मिलेगा?",
            citations=citations,
            student={"name": "Aisha Malik"},
            language="hi-IN",
            use_ollama=True,
        )
        assert "अध्यादेश संदर्भ ORD-WTH-14.1" in ans_hi


def test_synthesize_guidance_waterfall_ollama_priority():
    """Verify synthesize_guidance_with_gemini routes to Ollama when provider is ollama."""
    citations = [
        {
            "clause_code": "ORD-FIN-14.4",
            "title": "Smart Offsetting",
            "content": "Unreturned assets offset from caution deposit.",
        }
    ]

    object.__setattr__(settings, "llm_provider", "ollama")

    with patch(
        "backend.services.local_llm_service.call_ollama_llama3",
        return_value="You can offset your fine directly from your deposit.",
    ):
        text, source = synthesize_guidance_with_gemini(
            query="Can I offset library fine?",
            citations=citations,
            return_source=True,
        )
        assert "You can offset your fine directly" in text
        assert source == "Ollama Local AI (Llama 3.2)"


def test_api_policy_llm_status_endpoint(client):
    """Verify GET /api/policy/llm/status returns health metrics."""
    resp = client.get("/api/policy/llm/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_provider" in data
    assert "is_ollama_enabled" in data
    assert "ollama" in data
    assert "target_model" in data["ollama"]


def test_ambient_situational_awareness_what_page_next():
    """Verify PolicySearchService answers what page are we on and what to do next."""
    from backend.services.policy_search_service import PolicySearchService

    page_ctx = {
        "screen_name": "Program Withdrawal Portal",
        "route": "/withdrawal",
        "primary_action": "Initiate Withdrawal Request",
        "available_actions": [
            "Initiate Withdrawal Request",
            "Review Refund Policy",
            "Download Clearance Checklist",
        ],
    }

    # Test with Ollama mocked
    with patch(
        "backend.services.local_llm_service.call_ollama_llama3",
        return_value="We are currently on the Program Withdrawal Portal. Your next step is to click Initiate Withdrawal Request.",
    ):
        res = PolicySearchService.hybrid_guidance(
            query="what page are we on and what should i do next",
            student_id="STU001",
            page_context=page_ctx,
            language="en-IN",
        )
        assert res["domain"] == "Screen Navigation"
        assert res["recommended_action"] == "Initiate Withdrawal Request"
        assert res["action_url"] == "/withdrawal"
        assert "Program Withdrawal Portal" in res["answer"]
        assert "Initiate Withdrawal Request" in res["answer"]

    # Test fallback template in Hindi
    with patch("backend.services.local_llm_service.call_ollama_llama3", return_value=None):
        res_hi = PolicySearchService.hybrid_guidance(
            query="हम किस पेज पर हैं और आगे क्या करना चाहिए",
            student_id="STU001",
            page_context=page_ctx,
            language="hi-IN",
        )
        assert res_hi["domain"] == "Screen Navigation"
        assert "Program Withdrawal Portal" in res_hi["answer"]
        assert "Initiate Withdrawal Request" in res_hi["answer"]


def test_call_ollama_llama3_multi_turn_history():
    history = [
        {"role": "user", "content": "What is the attendance policy?"},
        {"role": "assistant", "content": "You need 75% attendance under ORD-ACAD-7.2."},
    ]
    with patch("httpx.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_instance
        mock_instance.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"message": {"content": "You can apply for condonation with Form AC-04."}},
        )

        reply = call_ollama_llama3(
            prompt="Where do I submit that?",
            system_instruction="You are UniAssist.",
            history=history,
        )
        assert reply == "You can apply for condonation with Form AC-04."

        # Verify payload messages contains system + 2 history turns + user turn
        call_args = mock_instance.post.call_args
        sent_payload = call_args.kwargs.get("json", {})
        messages = sent_payload.get("messages", [])
        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "What is the attendance policy?"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "You need 75% attendance under ORD-ACAD-7.2."
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "Where do I submit that?"


@pytest.mark.asyncio
async def test_voice_query_multi_turn_history_forwarding():
    from httpx import AsyncClient, ASGITransport
    from backend.main import app

    history = [
        {"role": "user", "content": "What page are we on?"},
        {"role": "assistant", "content": "We are on the Dashboard."},
    ]
    with patch(
        "backend.services.local_llm_service.call_ollama_llama3",
        return_value="You can proceed to submit Form AC-04 at the Academic Desk.",
    ) as mock_ollama:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/voice/query",
                json={
                    "spoken_text": "What should I do next?",
                    "student_id": "STU001",
                    "language": "en-IN",
                    "conversation_history": history,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "Form AC-04" in data["response_text"]
            # Verify mock_ollama was called with history
            assert mock_ollama.called
            assert mock_ollama.call_args.kwargs.get("history") == history

