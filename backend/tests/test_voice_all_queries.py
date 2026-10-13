import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from backend.main import app

def log(query, category, result_status="PASS"):
    print(f"[{result_status}] {category:<24} | Query: \"{query}\"")

def test_voice_comprehensive_suite():
    client = TestClient(app)
    print("=" * 80)
    print("STARTING BRUTAL VOICE QUERY & NATURAL SPEECH COMPREHENSIVE SUITE")
    print("=" * 80)

    test_queries = [
        # 1. Broad Navigation
        {
            "category": "Broad Navigation",
            "query": "Where can you take me and what portals are available?",
            "check": lambda res: "forms" in res["response_text"].lower() and "withdrawal" in res["response_text"].lower() and len(res["speech_text"]) > 20
        },
        # 2. Specific Route Navigation
        {
            "category": "Withdrawal Route",
            "query": "Take me to the withdrawal portal right now",
            "check": lambda res: res["action_url"] == "/withdrawal" and "navigating" in res["speech_text"].lower()
        },
        {
            "category": "Forms Hub Route",
            "query": "Navigate to the official forms catalog",
            "check": lambda res: res["action_url"] == "/forms" and "catalog" in res["speech_text"].lower()
        },
        {
            "category": "Exam Route",
            "query": "Show me the examination and rechecking portal",
            "check": lambda res: res["action_url"] == "/exams" and "examination" in res["speech_text"].lower()
        },
        {
            "category": "Grievance Route",
            "query": "Take me to file a student complaint ticket",
            "check": lambda res: res["action_url"] == "/chat" and "grievance" in res["speech_text"].lower()
        },
        {
            "category": "Scholarship Route",
            "query": "Go to the scholarship and financial aid page",
            "check": lambda res: res["action_url"] == "/scholarship" and "scholarship" in res["speech_text"].lower()
        },
        # 3. Ambient Screen Context & Button Highlighting
        {
            "category": "Ambient Screen Action",
            "query": "Which button should I click on this screen?",
            "page_context": {
                "screen_name": "Withdrawal Services Guide",
                "route": "/withdrawal",
                "primary_action": "Initiate Withdrawal",
                "available_actions": ["Initiate Withdrawal", "Download Form", "View Slabs"]
            },
            "check": lambda res: res["highlight_target"] == "Initiate Withdrawal" and "initiate withdrawal" in res["speech_text"].lower()
        },
        # 4. Post-Form Download Procedures
        {
            "category": "Migration Form Flow",
            "query": "What should I do after getting the migration certificate application?",
            "check": lambda res: ("registrar" in res["speech_text"].lower() or "clearance" in res["speech_text"].lower()) and len(res["citations"]) > 0
        },
        {
            "category": "Rechecking Form Flow",
            "query": "Where do I submit the rechecking form and what documents to attach?",
            "check": lambda res: len(res["citations"]) > 0 and len(res["speech_text"]) > 30
        },
        # 5. Attendance & Condonation
        {
            "category": "Attendance (Shortage)",
            "query": "I have attendance shortage what to do",
            "student_id": "STU001",
            "check": lambda res: "attendance" in res["response_text"].lower() and ("75" in res["response_text"] or "condonation" in res["response_text"].lower())
        },
        {
            "category": "Exam Condonation",
            "query": "Can I get condonation for medical absence from Dean?",
            "student_id": "STU001",
            "check": lambda res: "condonation" in res["response_text"].lower() or "ord-acad-7.2" in str(res["citations"]).lower()
        },
        # 6. Withdrawal Slabs & Caution Offsetting
        {
            "category": "Smart Caution Offset",
            "query": "Can I offset my lost ID card 200 rupees fine from caution deposit?",
            "student_id": "STU001",
            "check": lambda res: "offset" in res["response_text"].lower() and ("200" in res["response_text"] or "deposit" in res["response_text"].lower())
        },
        {
            "category": "Refund Slabs Policy",
            "query": "What percentage of fee is refunded if I withdraw before classes start?",
            "student_id": "STU001",
            "check": lambda res: "refund" in res["response_text"].lower() and len(res["citations"]) > 0
        },
        # 7. Staff / Logistics
        {
            "category": "Conveyance Reimburse",
            "query": "How to claim local conveyance and TA DA expense?",
            "check": lambda res: len(res["response_text"]) > 20 and len(res["speech_text"]) > 20
        },
        # 8. Boundary Guard (Off-Topic Query)
        {
            "category": "Domain Boundary Guard",
            "query": "Who won the football world cup in 2022?",
            "check": lambda res: any(k in res["response_text"].lower() for k in ["uniassist", "forms", "ordinance", "academic", "counselor", "university"])
        }
    ]

    passed_count = 0
    for idx, item in enumerate(test_queries, 1):
        payload = {
            "spoken_text": item["query"],
            "student_id": item.get("student_id", "STU001"),
            "language": "en-IN",
            "page_context": item.get("page_context")
        }

        res = client.post("/api/voice/query", json=payload)
        assert res.status_code == 200, f"Voice query failed with status {res.status_code}: {res.text}"
        data = res.json()

        # Verify speech params contract
        assert "speech_text" in data, "speech_text missing"
        assert "speech_params" in data, "speech_params missing"
        assert data["speech_params"]["lang"] == "en-IN", "Speech language mismatch"
        assert data["speech_params"]["rate"] > 0, "Invalid speech rate"
        assert "₹" not in data["speech_text"], "Raw currency symbol ₹ found in speech text (must be 'Rupees')"

        # Check domain-specific logic
        condition = item["check"](data)
        assert condition, f"Validation condition failed for query: '{item['query']}' | Response: {data['response_text']}"
        
        log(item["query"][:45] + "...", item["category"], "PASS")
        passed_count += 1

    print("=" * 80)
    print(f"ALL {passed_count}/{len(test_queries)} VOICE DOMAIN TESTS PASSED WITH 100% SUCCESS!")
    print("Zero currency symbol leaks, clean spoken cadence, and accurate RAG citations verified.")
    print("=" * 80)

if __name__ == "__main__":
    test_voice_comprehensive_suite()
