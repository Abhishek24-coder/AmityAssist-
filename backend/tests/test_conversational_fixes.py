"""Test suite validating fixes for all 5 conversational and guidance issues.

Covers:
1. Math & Programming Domain Boundary Guard (clean refusal without withdrawal/cartridge hijack)
2. Faculty Resignation Separation (routes to HR Desk Room 103, never student Form EX-02)
3. Vague Form Disambiguation (prompts for specific form instead of hallucinating)
4. Multi-Turn Affirmative Follow-Up (advances to Form AC-04 instructions instead of looping)
"""

from backend.services.policy_search_service import PolicySearchService


def test_math_query_refusal_no_withdrawal_leak():
    res = PolicySearchService.hybrid_guidance("can you tell me whats 2+2")
    assert res["domain"] == "Domain Boundary Guard"
    assert "2+2" not in res["answer"].lower() or "counselor" in res["answer"].lower()
    assert res["citations"] == []
    assert res.get("screen_instruction") is None
    assert "withdrawal" not in res["answer"].lower()


def test_python_query_refusal_no_citations():
    res = PolicySearchService.hybrid_guidance("can you tell me what are the arithmatic operators in python")
    assert res["domain"] == "Domain Boundary Guard"
    assert res["citations"] == []
    assert res.get("screen_instruction") is None


def test_faculty_resignation_routes_to_hr_never_ex02():
    query = "math faculty aur mujhe naa job chhodani hai apni toh mein kaise uski process ko mere guide kar sakte ho"
    res = PolicySearchService.hybrid_guidance(query, language="hi-Latn")
    assert res["domain"] == "HR & Faculty"
    assert "ex-02" not in res["answer"].lower()
    assert "backpaper" not in res["answer"].lower()
    assert "103" in res["answer"]  # HR Room 103
    assert "hod" in res["answer"].lower()
    assert res["recommended_action"] == "Download Faculty Exit Format"
    assert res["citations"][0]["clause_code"] == "ORD-HR-24.1"


def test_vague_form_request_asks_clarification():
    query = "mujhe naa form bharana hai madad chaahiye kya aap meri madad kar sakte"
    res = PolicySearchService.hybrid_guidance(query, language="hi-Latn")
    assert res["domain"] == "Forms Navigation"
    assert "31" in res["answer"]
    assert "kaunsa form" in res["answer"].lower() or "which form" in res["answer"].lower()
    # Ensure it offers options rather than assuming EX-02 is the answer
    assert res["recommended_action"] == "Browse All 31 Forms"


def test_multiturn_affirmative_followup_advances_ac04():
    history = [
        {"role": "user", "content": "meri attendance kam hai kya mai exam de sakta hu?"},
        {
            "role": "assistant",
            "content": "Aapko exam dene ke liye 75% attendance chahiye. Agar 60-74% hai toh aap Form AC-04 submit karke Dean Condonation le sakte hain. Kya aapko yeh form bharna hai?"
        }
    ]
    res = PolicySearchService.hybrid_guidance("mujhe chaahiye", language="hi-Latn", history=history)
    assert res["domain"] == "Academics"
    assert "ac-04" in res["answer"].lower()
    # It must give the actionable submission steps (10 days / Room 201) and not loop
    assert "10 working days" in res["answer"].lower() or "room 201" in res["answer"].lower()
    assert res["recommended_action"] == "Download Form AC-04 (Condonation)"


def test_all_three_languages_faculty_resignation():
    # 1. English
    res_en = PolicySearchService.hybrid_guidance("I am a computer science faculty member and I need to resign from my job, how to proceed?", language="en-IN")
    assert res_en["domain"] == "HR & Faculty"
    assert "ex-02" not in res_en["answer"].lower()
    assert "room 103" in res_en["answer"].lower()
    assert res_en["recommended_action"] == "Download Faculty Exit Format"

    # 2. Hindi (Devanagari)
    res_hi = PolicySearchService.hybrid_guidance("मैं गणित फैकल्टी हूँ और मुझे नौकरी छोड़नी है, इस्तीफा देने की प्रक्रिया क्या है?", language="hi-IN")
    assert res_hi["domain"] == "HR & Faculty"
    assert "ex-02" not in res_hi["answer"].lower()
    assert "103" in res_hi["answer"]
    assert "डीन" in res_hi["answer"] or "HOD" in res_hi["answer"]

    # 3. Hinglish
    res_latn = PolicySearchService.hybrid_guidance("Main professor hoon aur mujhe job chhodani hai, resignation process kya hai?", language="hi-Latn")
    assert res_latn["domain"] == "HR & Faculty"
    assert "ex-02" not in res_latn["answer"].lower()
    assert "103" in res_latn["answer"]


def test_all_three_languages_vague_form_request():
    # 1. English
    res_en = PolicySearchService.hybrid_guidance("I need to fill out a form, can you help me?", language="en-IN")
    assert res_en["domain"] == "Forms Navigation"
    assert "31" in res_en["answer"]
    assert "which form" in res_en["answer"].lower() or "specify" in res_en["answer"].lower()

    # 2. Hindi
    res_hi = PolicySearchService.hybrid_guidance("मुझे फॉर्म भरना है कृपया सहायता करें", language="hi-IN")
    assert res_hi["domain"] == "Forms Navigation"
    assert "31" in res_hi["answer"]
    assert "फॉर्म" in res_hi["answer"]

    # 3. Hinglish
    res_latn = PolicySearchService.hybrid_guidance("mujhe form bharna hai", language="hi-Latn")
    assert res_latn["domain"] == "Forms Navigation"
    assert "31" in res_latn["answer"]
    assert "kaunsa form" in res_latn["answer"].lower()


def test_text_chat_api_endpoint_non_voice():
    """Verify that the standard non-voice text endpoint /api/policy/guide functions perfectly across 3 languages."""
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)

    # English non-voice text query
    resp_en = client.post("/api/policy/guide", json={"query": "What is the attendance condonation rule?", "language": "en-IN"})
    data_en = resp_en.json()
    assert "75%" in data_en["answer"] or "AC-04" in data_en["answer"]
    assert len(data_en["citations"]) > 0

    # Hindi non-voice text query
    resp_hi = client.post("/api/policy/guide", json={"query": "अटेंडेंस 75% से कम है क्या करें?", "language": "hi-IN"})
    assert resp_hi.status_code == 200
    data_hi = resp_hi.json()
    assert "75%" in data_hi["answer"] or "उपस्थिति" in data_hi["answer"]

    # Hinglish non-voice text query
    resp_latn = client.post("/api/policy/guide", json={"query": "attendance 65 percent hai exam de sakta hu?", "language": "hi-Latn"})
    assert resp_latn.status_code == 200
    data_latn = resp_latn.json()
    assert "AC-04" in data_latn["answer"] or "75%" in data_latn["answer"]


def test_where_to_get_form_kiosk_first_retrieval():
    """Verify exact Screenshot 1 scenario: User asks 'अरे मतलब वो कहाँ से लूँगा यहाँ कहाँ से मिलेगा?'"""
    history = [
        {"role": "user", "content": "मेरी अटेंडेंस 65% है क्या मुझे परीक्षा देने मिलेगी?"},
        {"role": "assistant", "content": "आप फॉर्म AC-04 भरकर डीन छूट ले सकते हैं।"}
    ]
    query = "अरे मतलब वो कहाँ से लूँगा यहाँ कहाँ से मिलेगा?"
    res = PolicySearchService.hybrid_guidance(query, language="hi-IN", history=history)

    # Must give Kiosk-First direct download and real room 201
    assert "भटकने की ज़रूरत नहीं" in res["answer"]
    assert "Download Form AC-04" in res["recommended_action"]
    assert res["action_url"] == "/forms"
    assert "201" in res["answer"]  # Room 201 Dean Office

    # Must NEVER contain fake hallucinations
    assert "सेवा केंद्र 3" not in res["answer"]
    assert "सेवा केंद्र" not in res["answer"]
    assert "cartridge" not in str(res["citations"]).lower()
    assert "Attendance Condonation" in res["citations"][0]["title"]


def test_ollama_prompt_grounding_and_negative_rules():
    """Verify Step 3: Ollama is fed Master Procedural Grounding and negative rules."""
    from unittest.mock import patch
    from backend.services.advanced_ai_service import synthesize_guidance_with_gemini
    from backend.services.local_llm_service import generate_local_policy_answer

    captured_prompts = []
    captured_sys_instructions = []

    def fake_call_ollama(prompt, system_instruction, **kwargs):
        captured_prompts.append(prompt)
        captured_sys_instructions.append(system_instruction)
        return "Test response grounded in facts."

    citations = [
        {
            "clause_code": "ORD-ACAD-7.2",
            "title": "Attendance Policy",
            "content": "75% required; 60-74% dean condonation via Form AC-04.",
        }
    ]

    with patch("backend.services.local_llm_service.call_ollama_llama3", side_effect=fake_call_ollama):
        # Test in advanced_ai_service
            synthesize_guidance_with_gemini(
                query="kahan se milega form AC-04 attendance condonation",
                citations=citations,
                language="hi-IN"
            )

            # Test in local_llm_service
            generate_local_policy_answer(
                query="attendance condonation process and submission room",
                citations=citations,
                language="en-IN",
                use_ollama=True
            )

    # Verify both callers injected Master Procedure Facts
    assert len(captured_prompts) == 2
    for p in captured_prompts:
        assert "Attendance Condonation Application (Form AC-04)" in p
        assert "Room 201" in p
        assert "Kiosk Access" in p

    # Verify anti-hallucination rules in system instructions
    for s in captured_sys_instructions:
        assert "सेवा केंद्र 3" in s
        assert "Kiosk-First" in s
        assert "EX-2" in s


# =============================================================================
# Multi-Persona Stress Battery Tests (Hinglish, British English, Hindi)
# =============================================================================

def test_lost_id_card_routing_all_languages():
    # 1. Hinglish
    res_latn = PolicySearchService.hybrid_guidance("bhai mera student ID card kho gaya hai duplicate kaise banega", language="hi-Latn")
    assert res_latn["domain"] == "Student ID Services"
    assert "200" in res_latn["answer"]
    assert "101" in res_latn["answer"]
    assert "48" in res_latn["answer"]
    assert "withdrawal" not in res_latn["answer"].lower()
    assert "form 28" in res_latn["recommended_action"].lower()

    # 2. British / International English
    res_en = PolicySearchService.hybrid_guidance("I have misplaced my student identity card, what is the procedure to obtain a duplicate?", language="en-IN")
    assert res_en["domain"] == "Student ID Services"
    assert "200" in res_en["answer"]
    assert "101" in res_en["answer"]
    assert "48 hours" in res_en["answer"].lower()

    # 3. Hindi Devanagari
    res_hi = PolicySearchService.hybrid_guidance("मेरा छात्र पहचान पत्र खो गया है नया आईडी कार्ड कैसे बनेगा?", language="hi-IN")
    assert res_hi["domain"] == "Student ID Services"
    assert "200" in res_hi["answer"]
    assert "101" in res_hi["answer"]


def test_hostel_vacate_and_security_deposit_routing():
    # 1. Hinglish
    res_latn = PolicySearchService.hybrid_guidance("hostel chhodna hai security deposit wapas kaise milega", language="hi-Latn")
    assert res_latn["domain"] == "Hostel & Accommodation"
    assert "102" in res_latn["answer"]
    assert "warden" in res_latn["answer"].lower()
    assert "program withdrawal" not in res_latn["answer"].lower()

    # 2. British English
    res_en = PolicySearchService.hybrid_guidance("I wish to vacate my campus hostel room and request the refund of my security deposit", language="en-IN")
    assert res_en["domain"] == "Hostel & Accommodation"
    assert "102" in res_en["answer"]
    assert "warden" in res_en["answer"].lower()

    # 3. Hindi
    res_hi = PolicySearchService.hybrid_guidance("हॉस्टल खाली करना है और सिक्योरिटी डिपॉजिट वापस चाहिए", language="hi-IN")
    assert res_hi["domain"] == "Hostel & Accommodation"
    assert "102" in res_hi["answer"]


def test_rechecking_and_reevaluation_routing():
    # 1. British English
    res_en = PolicySearchService.hybrid_guidance("Could you inform me of the fee and timeline for answer script re-evaluation?", language="en-IN")
    assert res_en["domain"] == "Examinations"
    assert "500" in res_en["answer"]
    assert "15" in res_en["answer"]
    assert "window 3" in res_en["answer"].lower()
    assert "ex-02" not in res_en["answer"].lower()  # Must NOT be backpaper

    # 2. Hinglish
    res_latn = PolicySearchService.hybrid_guidance("marks recheck karwane hain copy dobara check hogi kya procedure hai", language="hi-Latn")
    assert res_latn["domain"] == "Examinations"
    assert "500" in res_latn["answer"]
    assert "rechecking form" in res_latn["recommended_action"].lower()

    # 3. Hindi
    res_hi = PolicySearchService.hybrid_guidance("उत्तर पुस्तिका के पुनर्मूल्यांकन और रीचेकिंग का शुल्क क्या है?", language="hi-IN")
    assert res_hi["domain"] == "Examinations"
    assert "500" in res_hi["answer"]


def test_degree_certificate_routing():
    # 1. Hindi Devanagari
    res_hi = PolicySearchService.hybrid_guidance("डिग्री प्रमाण पत्र के लिए आवेदन कैसे करें?", language="hi-IN")
    assert res_hi["domain"] == "Academic Records"
    assert "22" in res_hi["answer"]
    assert "रजिस्ट्रार" in res_hi["answer"]
    assert "leave" not in res_hi["answer"].lower()  # Must NOT match Faculty Leave

    # 2. British English
    res_en = PolicySearchService.hybrid_guidance("How do I apply for the formal conferral and dispatch of my degree certificate?", language="en-IN")
    assert res_en["domain"] == "Academic Records"
    assert "window 2" in res_en["answer"].lower()
    assert "7 to 10" in res_en["answer"].lower()


def test_migration_certificate_routing():
    res = PolicySearchService.hybrid_guidance("migration certificate kaise milega kitna time lagta hai", language="hi-Latn")
    assert res["domain"] == "Academic Records"
    assert "15" in res["answer"]
    assert "300" in res["answer"]
    assert "3 se 5" in res["answer"].lower() or "3 to 5" in res["answer"].lower()


def test_grievance_and_anti_ragging_routing():
    # 1. Hinglish
    res_latn = PolicySearchService.hybrid_guidance("ragging ki complaint kahan karni hai", language="hi-Latn")
    assert res_latn["domain"] == "Student Grievance & Welfare"
    assert "24" in res_latn["answer"]  # 24-hour emergency SLA
    assert "105" in res_latn["answer"]  # Room 105
    assert "conveyance" not in res_latn["answer"].lower()

    # 2. British English
    res_en = PolicySearchService.hybrid_guidance("What is the formal procedure to submit an urgent grievance regarding campus harassment?", language="en-IN")
    assert res_en["domain"] == "Student Grievance & Welfare"
    assert "24-hour" in res_en["answer"].lower() or "48-hour" in res_en["answer"].lower()


def test_scholarship_renewal_criteria_routing():
    res_en = PolicySearchService.hybrid_guidance("What are the minimum CGPA and attendance requirements for merit scholarship renewal?", language="en-IN")
    assert res_en["domain"] == "Scholarships"
    assert "8.0" in res_en["answer"]
    assert "80%" in res_en["answer"]
    assert "204" in res_en["answer"]  # Room 204


def test_caution_deposit_offsetting_routing():
    res = PolicySearchService.hybrid_guidance("library ki book kho gayi kya fine caution deposit se cut sakta hai", language="hi-Latn")
    assert res["domain"] == "Finance & Accounts"
    assert "10,000" in res["answer"]
    assert "offset" in res["answer"].lower()
    assert "program withdrawal is governed" not in res["answer"].lower()


def test_program_withdrawal_routing():
    res = PolicySearchService.hybrid_guidance("I wish to withdraw from my degree program and request a tuition fee refund", language="en-IN")
    assert res["domain"] == "Withdrawal & Refunds"
    assert "ugc" in res["answer"].lower()
    assert "10,000" in res["answer"]
    assert "100%" in res["answer"]


def test_conversational_negation_did_not_ask_no_policy_dump():
    """Verify 'I did not ask.' never dumps faculty resignation or legal ordinances."""
    res_en = PolicySearchService.hybrid_guidance("I did not ask.", language="en-IN")
    assert res_en["domain"] == "Conversational"
    assert res_en["citations"] == []
    assert "faculty" not in res_en["answer"].lower()
    assert "resignation" not in res_en["answer"].lower()

    res_latn = PolicySearchService.hybrid_guidance("maine nahi pucha", language="hi-Latn")
    assert res_latn["domain"] == "Conversational"
    assert res_latn["citations"] == []
    assert "faculty" not in res_latn["answer"].lower()

    res_hi = PolicySearchService.hybrid_guidance("मैंने यह नहीं पूछा", language="hi-IN")
    assert res_hi["domain"] == "Conversational"
    assert res_hi["citations"] == []


def test_conversational_greetings_and_small_talk():
    """Verify pure greetings, gratitude, and help questions return conversational responses."""
    # Greetings
    for greeting in ["hello", "hi", "hey"]:
        res = PolicySearchService.hybrid_guidance(greeting, language="en-IN")
        assert res["domain"] == "Conversational"
        assert res["citations"] == []

    # Gratitude
    res_thanks = PolicySearchService.hybrid_guidance("thank you so much", language="en-IN")
    assert res_thanks["domain"] == "Conversational"
    assert res_thanks["citations"] == []

    # Identity
    res_who = PolicySearchService.hybrid_guidance("who are you", language="en-IN")
    assert res_who["domain"] == "Conversational"
    assert "UniAssist" in res_who["answer"]

    # Negation / nothing
    res_nothing = PolicySearchService.hybrid_guidance("kuch nahi", language="hi-Latn")
    assert res_nothing["domain"] == "Conversational"
    assert res_nothing["citations"] == []


def test_sanitize_and_verify_response_guardrails():
    """Verify that sanitize_and_verify_response intercepts hallucinated rooms, strips fake service centers, and caps sentences."""
    from backend.services.local_llm_service import sanitize_and_verify_response

    # 1. Fake room intercept
    fake_room_en = "Please submit your file at Room 404 immediately."
    cleaned = sanitize_and_verify_response(fake_room_en)
    assert "Room 404" not in cleaned
    assert "the designated university desk" in cleaned

    # 2. Verified room preserved
    real_room = "Dean office is located in Room 201 and Exam Cell is in Room 110."
    cleaned_real = sanitize_and_verify_response(real_room)
    assert "Room 201" in cleaned_real
    assert "Room 110" in cleaned_real

    # 3. Hindi fake room and fake service center
    fake_hindi = "कृपया फॉर्म कमरा 808 या सेवा केंद्र 3 में जमा करें।"
    cleaned_hi = sanitize_and_verify_response(fake_hindi)
    assert "808" not in cleaned_hi
    assert "सेवा केंद्र 3" not in cleaned_hi
    assert "विश्वविद्यालय प्रशासनिक डेस्क" in cleaned_hi or "विश्वविद्यालय कार्यालय" in cleaned_hi

    # 4. Hard sentence ceiling (truncates past 3 sentences)
    rambling = "Sentence one. Sentence two! Sentence three? Sentence four should be dropped. Sentence five should be dropped."
    cleaned_sentences = sanitize_and_verify_response(rambling)
    assert "Sentence one." in cleaned_sentences
    assert "Sentence two!" in cleaned_sentences
    assert "Sentence three?" in cleaned_sentences
    assert "Sentence four" not in cleaned_sentences
    assert "Sentence five" not in cleaned_sentences


def test_intent_disambiguation_cross_questioning_and_role_mapping():
    """Verify ambiguous 'I want to leave' triggers cross-questions for guest and direct withdrawal for student."""
    # 1. Guest trigger
    res_guest = PolicySearchService.hybrid_guidance("I want to leave", student_id="GUEST")
    assert res_guest.get("status") == "trigger_cross_question"
    assert res_guest.get("is_ambiguous") is True
    assert len(res_guest.get("clarification_options", [])) == 3

    # 2. Authenticated student bypass
    res_stu = PolicySearchService.hybrid_guidance("I want to leave", student_id="STU001")
    assert res_stu.get("domain") == "Withdrawal & Refunds"
    assert res_stu.get("recommended_action") == "Start Withdrawal Procedure"
    assert res_stu.get("status") is None

    # 3. Multi-turn follow-up resolution
    history = [
        {"role": "user", "content": "I want to leave"},
        {"role": "assistant", "content": res_guest.get("answer")},
    ]
    # Reply 'student'
    res_stu_follow = PolicySearchService.hybrid_guidance("student", student_id="GUEST", history=history)
    assert res_stu_follow.get("domain") == "Withdrawal & Refunds"

    # Reply 'faculty'
    res_fac_follow = PolicySearchService.hybrid_guidance("faculty", student_id="GUEST", history=history)
    assert res_fac_follow.get("domain") == "HR & Staff"

    # Reply 'hostel'
    res_hstl_follow = PolicySearchService.hybrid_guidance("hostel", student_id="GUEST", history=history)
    assert "Hostel" in res_hstl_follow.get("domain")

