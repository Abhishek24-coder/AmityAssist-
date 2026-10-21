"""
Keyword-based NLP intent classifier + polarity sentiment scorer.

Design rationale: Deterministic keyword matching instead of a heavy ML model because:
  - Full auditability — every decision is traceable to explicit keywords
  - Zero external runtime dependencies
  - Sub-millisecond latency on any hardware
  - Easy to extend: add keywords, adjust weights, or swap the engine behind the same interface

Intent categories:
  financial | academic | personal | health | career | unclear
"""

from __future__ import annotations

import re
from typing import Literal

Intent = Literal["financial", "academic", "personal", "health", "career", "unclear"]
Sentiment = Literal["positive", "neutral", "negative"]
RouterIntent = Literal[
    "academics",
    "scholarships",
    "exams",
    "grievances",
    "withdrawals",
    "notices",
    "fees",
    "hostel",
    "documents",
    "internships",
    "request_status",
    "help",
    "unknown",
]
Language = Literal["english", "hinglish", "hindi"]

# ---------------------------------------------------------------------------
# Keyword tables (all lower-case; substring matching used for partial words)
# ---------------------------------------------------------------------------

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "financial": [
        "fee", "fees", "money", "cost", "afford", "financial", "payment",
        "scholarship", "debt", "loan", "broke", "expense", "tuition", "fund",
        "poverty", "income", "salary", "economics", "budget", "bursary",
        "credit card", "installment", "due", "overdue", "refund",
    ],
    "academic": [
        "fail", "failing", "grade", "marks", "exam", "course", "study",
        "professor", "teacher", "curriculum", "assignment", "thesis",
        "academic", "performance", "cgpa", "gpa", "semester", "credit",
        "difficult", "hard", "understand", "class", "lecture", "dropout",
        "repeat", "retake", "plagiarism", "suspension",
    ],
    "personal": [
        "family", "personal", "home", "parent", "relative", "marriage",
        "relationship", "mental", "anxiety", "stress", "depression",
        "move", "relocat", "immigrat", "visa", "abroad", "country",
        "divorce", "separation", "grief", "loss",
    ],
    "health": [
        "health", "sick", "ill", "disease", "hospital", "surgery",
        "chronic", "mental health", "therapy", "treatment", "disability",
        "injury", "cancer", "diagnos", "medical", "medication", "recover",
    ],
    "career": [
        "job", "career", "work", "employ", "company", "internship",
        "opportunity", "offer", "business", "startup", "entrepreneur",
        "promotion", "full-time", "hired", "appointment",
    ],
}

_POSITIVE_WORDS = frozenset({
    "thank", "thanks", "appreciate", "good", "great", "okay", "yes",
    "sure", "confirm", "agree", "resolve", "help", "support", "better",
    "wonderful", "excellent", "perfect", "love", "happy", "pleased",
})

_NEGATIVE_WORDS = frozenset({
    "no", "not", "never", "cant", "cannot", "difficult", "hard",
    "fail", "bad", "worst", "hate", "terrible", "awful", "hopeless",
    "struggle", "impossible", "refuse", "won't", "wont", "disagree",
    "frustrated", "desperate", "overwhelmed",
})

_ROUTER_KEYWORDS: dict[str, list[str]] = {
    "academics": [
        "academic", "academics", "cgpa", "gpa", "attendance", "performance",
        "semester", "course", "subject", "marks", "kitna cgpa", "attendance bata",
        "padhai", "class", "profile", "student info", "my info", "student details",
    ],
    "scholarships": [
        "scholarship", "fellowship", "merit", "fee waiver", "eligible",
        "apply scholarship", "scholarship ke liye", "chatravriti",
    ],
    "exams": [
        "exam", "exams", "admit card", "backpaper", "back paper", "result",
        "grade", "datesheet", "paper", "arrear", "reappear",
    ],
    "grievances": [
        "grievance", "complaint", "complain", "issue", "problem", "hostel issue",
        "file complaint", "shikayat", "samasya", "pareshani",
    ],
    "notices": [
        "notice", "notices", "announcement", "announcements", "circular",
        "updates", "news", "deadline", "deadlines", "portal update",
    ],
    "fees": [
        "fee", "fees", "dues", "due", "payment", "outstanding", "paid",
        "pending fee", "fee status", "kitni fees", "fees kitni",
    ],
    "hostel": [
        "hostel", "room", "allocation", "allocated", "day scholar",
        "hostel status", "hostel allotment", "accommodation",
    ],
    "documents": [
        "document", "documents", "upload", "ocr", "verification", "verify document",
        "certificate", "id proof", "medical certificate", "fraud",
    ],
    "internships": [
        "internship", "internships", "placement", "placements", "campus drive",
        "job drive", "company", "stipend", "eligible internship",
    ],
    "request_status": [
        "request status", "status of withdrawal", "withdrawal status", "kahan tak pahuncha",
        "kahan tak pahucha", "mera status", "track request", "track withdrawal",
        "clearance status", "status kya hai", "application status", "check status",
        "withdrawal process", "where has it reached", "status of my request", "stage",
        "track", "status", "pahuncha", "pahucha",
    ],
    "withdrawals": [
        "withdraw", "withdrawal", "leave university", "drop out", "dropout",
        "refund", "cancel admission", "quit", "programme chhod", "college chhod",
    ],
    "help": [
        "help", "support", "menu", "options", "what can you do", "assist",
        "madad", "sahayata",
    ],
    
}


def _tokenize(text: str) -> list[str]:
    """Lower-case, strip punctuation, split into tokens."""
    return re.sub(r"[^\w\s]", " ", text.lower(), flags=re.UNICODE).split()


def classify_intent(text: str) -> Intent:
    """
    Classify the dominant withdrawal intent from free-text input.

    Algorithm:
      1. Tokenise input
      2. Count keyword hits per intent category
      3. Return highest-scoring category; 'unclear' if all scores are 0
    """
    lower_text = text.lower()
    tokens = set(_tokenize(text))

    scores: dict[str, int] = {}
    for intent, keywords in _INTENT_KEYWORDS.items():
        count = 0
        for kw in keywords:
            # Match whole-word tokens OR substring inside longer words
            if kw in tokens or kw in lower_text:
                count += 1
        scores[intent] = count

    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "unclear"  # type: ignore[return-value]


def route_intent(text: str) -> RouterIntent:
    """Route a general assistant message to a student-lifecycle capability."""
    lower_text = text.lower()
    tokens = set(_tokenize(text))

    # Priority disambiguation: if tracking signals are present alongside withdrawal keywords
    status_signals = {
        "status", "track", "tracking", "pahuncha", "pahucha", "kahan", "stage",
        "progress", "where", "reached", "check", "कहाँ", "कहा", "स्थिति", "स्टेटस",
        "अपडेट", "पहुँचा", "पहुंचा"
    }
    withdrawal_signals = {"withdraw", "withdrawal", "विथड्रॉल", "वापसी"}
    if any(s in lower_text or s in tokens for s in status_signals):
        if any(w in lower_text or w in tokens for w in withdrawal_signals):
            return "request_status"

    scores: dict[str, int] = {}
    for intent, keywords in _ROUTER_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in tokens or kw in lower_text:
                score += len(kw.split())
        scores[intent] = score

    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "unknown"  # type: ignore[return-value]


def detect_language(text: str) -> Language:
    """Detect English, Hinglish, or Hindi using deterministic text signals."""
    if re.search(r"[\u0900-\u097F]", text):
        return "hindi"

    indic_roman_markers = frozenset({
        # Interrogatives
        "kya", "kaise", "kahan", "kaha", "kab", "kyun", "kyu", "kis", "kise", "kisko",
        "kitna", "kitni", "kitne", "kaun", "kaunsa", "kaunsi",
        # Pronouns
        "mera", "meri", "mere", "mujhe", "mujhko", "main", "hum", "hume", "humein",
        "aap", "aapka", "aapki", "aapke", "tum", "tumhara", "tumhari", "tumhare",
        "tera", "teri", "tere", "uska", "uski", "uske", "unka", "unki", "unke",
        # Verbs & Conjugations
        "hai", "hain", "hoon", "hun",
        "karna", "karein", "kare", "karo", "karun", "karta", "karti", "karte",
        "hoga", "hogi", "hoge", "hona", "hote", "hoti", "hota",
        "chahiye", "chaho", "chahta", "chahti",
        "bata", "batao", "bataiye", "batana", "bol", "bolo", "boliye", "bolna",
        "dekh", "dekho", "dekhiye", "dekhna", "suno", "suniye",
        "dijiye", "dunga", "dungi", "lijiye", "lunga",
        "milega", "milegi", "milege", "milna", "milta", "milti",
        "sakta", "sakti", "sakte", "sako",
        "lagta", "lagti", "lagte", "lagega", "lagegi",
        "raha", "rahi", "rahe", "raho",
        "jaana", "jana", "jayega", "jayegi", "jaunga",
        "chhodna", "chhodani", "chhodne", "chhod",
        "karwana", "karwani", "karwane",
        "pucha", "pucho", "poocho", "poochna",
        # Negation, Particles & Connectors
        "nahi", "nahin", "mat",
        "bhi", "toh", "lekin", "magar",
        "mein", "ka", "ke", "ki", "ko", "se",
        "kuch", "kuchh", "sabhi", "koi",
        # Domain terms & Vocatives
        "wapas", "paise", "shikayat", "pareshani", "samasya", "padhai", "chhutti",
        "bhai", "sahab", "sirji", "madad", "sahayata", "bunk", "debar",
    })

    tokens = set(_tokenize(text))
    if tokens & indic_roman_markers:
        return "hinglish"
    return "english"


def is_voice_command(text: str) -> bool:
    """Return True when the message looks like speech-transcription input."""
    lower_text = text.lower().strip()
    return lower_text.startswith(("voice:", "spoken:", "mic:")) or any(
        phrase in lower_text
        for phrase in ("hey amity", "ok amity", "voice command", "bol kar")
    )


def score_sentiment(text: str) -> Sentiment:
    """
    Simple polarity scorer.

    Returns 'positive' if positive signals outweigh negative,
    'negative' if vice versa, or 'neutral' when balanced/absent.
    """
    tokens = set(_tokenize(text))
    pos = len(tokens & _POSITIVE_WORDS)
    neg = len(tokens & _NEGATIVE_WORDS)

    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"
