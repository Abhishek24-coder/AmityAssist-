"""
Tests for dynamic multi-language voice and policy search adaptation.
Verifies that:
- English query produces English response with speech_params lang = 'en-IN'
- Hinglish query produces Hinglish response with speech_params lang = 'hi-Latn'
- Hindi query produces Hindi response with speech_params lang = 'hi-IN'
"""

from fastapi.testclient import TestClient
from backend.main import app
from backend.services.nlp_service import detect_language

client = TestClient(app)


def test_detect_language_accuracy():
    # English queries
    assert detect_language("What is the fee refund policy if I withdraw?") == "english"
    assert detect_language("Can I check my attendance status and exam eligibility?") == "english"
    assert detect_language("Where is the Central Library located?") == "english"

    # Hinglish queries
    assert detect_language("hostel chhodna hai to security deposit kaise milega") == "hinglish"
    assert detect_language("bhai attendance kam hai to kya exam de sakte hain") == "hinglish"
    assert detect_language("mujhe withdrawal form submit karna hai process batao") == "hinglish"
    assert detect_language("library ki book kho gayi kitna fine lagega") == "hinglish"

    # Hindi queries (Devanagari)
    assert detect_language("मुझे हॉस्टल फीस रिफंड और विथड्रॉल की प्रक्रिया जाननी है") == "hindi"
    assert detect_language("उपस्थिति कम होने पर क्या मैं परीक्षा दे सकता हूँ?") == "hindi"
    assert detect_language("लाइब्रेरी नो ड्यूज सर्टिफिकेट कैसे मिलेगा?") == "hindi"


def test_voice_query_speaks_english_when_asked_in_english():
    response = client.post("/api/voice/query", json={
        "spoken_text": "What is the fee refund policy if I withdraw from university?",
        "student_id": "STU001",
        "language": "en-IN",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["detected_language"] == "en-IN"
    assert data["speech_params"]["lang"] == "en-IN"
    assert "refund" in data["response_text"].lower()
    # Confirm it did not hallucinate Hindi Devanagari in English mode
    assert not any('\u0900' <= char <= '\u097f' for char in data["response_text"][:50])


def test_voice_query_speaks_hinglish_when_asked_in_hinglish():
    response = client.post("/api/voice/query", json={
        "spoken_text": "hostel chhodna hai to security deposit wapas kaise milega",
        "student_id": "STU001",
        "language": "en-IN",  # Client sent default en-IN, but query is Hinglish
    })
    assert response.status_code == 200
    data = response.json()
    assert data["detected_language"] == "hi-Latn"
    assert data["speech_params"]["lang"] == "hi-Latn"
    res_lower = data["response_text"].lower()
    # Check Hinglish keywords in answer
    assert any(w in res_lower for w in ["deposit", "hostel", "warden", "refund", "clearance", "gate", "rupaye"])


def test_voice_query_speaks_hindi_when_asked_in_hindi():
    response = client.post("/api/voice/query", json={
        "spoken_text": "मुझे हॉस्टल फीस रिफंड और विथड्रॉल की जानकारी चाहिए",
        "student_id": "STU001",
        "language": "en-IN",  # Client sent default en-IN, but spoken text is Hindi
    })
    assert response.status_code == 200
    data = response.json()
    assert data["detected_language"] == "hi-IN"
    assert data["speech_params"]["lang"] == "hi-IN"
    # Hindi response must contain Devanagari script
    assert any('\u0900' <= char <= '\u097f' for char in data["response_text"])
