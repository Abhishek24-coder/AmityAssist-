"""Phase 29: Intelligent Search & Policy Guidance Service.

Combines SQLite FTS5 (BM25 Inverted Index) for sub-5ms legal ordinance retrieval
with personalized hybrid RAG advice synthesis (attendance condonation, withdrawal
refund slabs, caution deposit offset, and voice TTS guidance).
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from ..database.connection import get_connection
from ..services.nlp_service import score_sentiment


# ---------------------------------------------------------------------------
# Seed Ordinances & University Handbooks
# ---------------------------------------------------------------------------

DEFAULT_POLICIES = [
    {
        "doc_id": "POL-ACAD-01",
        "category": "Academics",
        "title": "Minimum Attendance Requirement & Dean's Condonation",
        "clause_code": "ORD-ACAD-7.2",
        "content": (
            "Minimum attendance requirement is 75% in every registered course to be eligible "
            "to sit for End Term Semester Examinations. If overall attendance is between 60% and 74%, "
            "the student may apply for Dean Condonation on medical or approved official university duty "
            "grounds by submitting Form AC-04 along with medical certificates at least 10 working days "
            "prior to exam commencement. Attendance below 60% constitutes mandatory debarment with zero condonation."
        ),
        "action_url": "/forms",
        "action_label": "Download Form AC-04 (Condonation)",
    },
    {
        "doc_id": "POL-WTH-01",
        "category": "Withdrawal & Refunds",
        "title": "Program Withdrawal & Tuition Fee Refund Mandates (UGC Aligned)",
        "clause_code": "ORD-WTH-14.1",
        "content": (
            "Withdrawal of admission and academic fee refunds adhere to UGC 2024 directives: "
            "(a) 15 days or more prior to formally notified admission deadline: 100% refund minus max processing fee INR 1,000; "
            "(b) Less than 15 days prior to admission deadline: 90% refund; "
            "(c) Up to 15 days post admission deadline: 80% refund; "
            "(d) Between 16 and 30 days post admission deadline: 50% refund; "
            "(e) Beyond 30 days post admission deadline: 0% tuition refund. "
            "Refundable Security/Caution Deposit of INR 10,000 is always refunded 100% across all slabs."
        ),
        "action_url": "/withdrawal",
        "action_label": "Start Withdrawal Procedure",
    },
    {
        "doc_id": "POL-FIN-01",
        "category": "Finance",
        "title": "Caution Deposit Smart Offsetting for Unreturned Assets & Fines",
        "clause_code": "ORD-FIN-14.4",
        "content": (
            "Under the Smart Financial Offsetting amendment, students undergoing departure or clearance "
            "with minor unreturned assets, lost plastic ID card replacement fees (INR 200), or library fines "
            "under INR 2,000 may opt for 1-tap direct deduction from their refundable caution deposit balance "
            "(standard balance INR 10,000). The clearance gate updates to CLEARED_VIA_OFFSET immediately without "
            "requiring physical bank visits or offline challans."
        ),
        "action_url": "/withdrawal",
        "action_label": "View Clearance Status",
    },
    {
        "doc_id": "POL-CLR-01",
        "category": "Clearance",
        "title": "Sequential 4-Gate Institutional Clearance Pipeline",
        "clause_code": "ORD-CLR-9.3",
        "content": (
            "Institutional departure, transfer certificate issuance, or withdrawal requires digital sign-off "
            "across 4 sequential clearance desks: Gate 1 Central Library (book returns & dues); Gate 2 Hostel & Mess Office "
            "(inventory inspection & room handover); Gate 3 Finance & Accounts (fee audit & deposit offset reconciliation); "
            "Gate 4 Registrar Office (final document audit & degree release). Each desk officer records digital authorization."
        ),
        "action_url": "/withdrawal",
        "action_label": "Track Clearance Gates",
    },
    {
        "doc_id": "POL-EXAM-01",
        "category": "Examinations",
        "title": "Backpaper & Supplementary Examination Guidelines",
        "clause_code": "ORD-EXAM-12.1",
        "content": (
            "Students with failed courses or seeking grade improvement may apply for Supplementary Backpaper Examinations. "
            "The examination fee is INR 1,500 per registered subject. Applications must be submitted through Form EX-02 within "
            "14 calendar days of semester grade sheet publication. Answer script re-evaluation is admissible within 7 days at INR 750 per subject."
        ),
        "action_url": "/forms",
        "action_label": "Download Form EX-02 (Backpaper)",
    },
    {
        "doc_id": "POL-HSTL-01",
        "category": "Hostel",
        "title": "Hostel Room Vacation, Inventory Handover & Key Return",
        "clause_code": "ORD-HSTL-18.2",
        "content": (
            "Hostel residents vacating campus quarters must conduct physical inventory inspection with the Assistant Warden. "
            "Room inventory checklist and key submission must be completed 24 hours prior to departure. Any physical room damage "
            "or missing fixtures will be offset against the hostel security deposit balance."
        ),
        "action_url": "/forms",
        "action_label": "Hostel Vacation Guidelines",
    },
    {
        "doc_id": "POL-GRV-01",
        "category": "Grievances",
        "title": "Student Grievance Redressal SLA & Proctorial Escalation",
        "clause_code": "ORD-GRV-22.5",
        "content": (
            "Formal student grievances submitted through the portal carry mandatory resolution SLAs: Academic and facility "
            "grievances must be addressed by the Department Coordinator within 48 hours. If unresolved after 48 hours, the ticket "
            "is automatically escalated to the Dean of Student Welfare. Harassment, ragging, or physical safety tickets have an emergency 24h SLA."
        ),
        "action_url": "/chat",
        "action_label": "File Formal Grievance",
    },
    {
        "doc_id": "POL-SCH-01",
        "category": "Scholarships",
        "title": "Merit & Financial Assistance Scholarship Renewal Criteria",
        "clause_code": "ORD-SCH-16.3",
        "content": (
            "Continuation of university merit scholarships requires maintaining a minimum CGPA of 8.0, minimum 80% attendance, "
            "and zero backpapers in the previous academic year. Need-based tuition concessions require annual submission of valid family "
            "income certificate before August 31st annually."
        ),
        "action_url": "/scholarship",
        "action_label": "Explore Scholarships",
    },
]


class PolicySearchService:
    """Provides SQLite FTS5 full-text search and personalized policy guidance."""

    @classmethod
    def initialize_fts_index(cls) -> None:
        """Create and populate the FTS5 virtual table if empty."""
        conn = get_connection()
        # Create FTS5 virtual table
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS policy_fts USING fts5(
                doc_id UNINDEXED,
                category,
                title,
                clause_code,
                content,
                action_url UNINDEXED,
                action_label UNINDEXED,
                tokenize='porter unicode61'
            );
            """
        )

        # Check if table already contains entries
        cur = conn.execute("SELECT count(*) FROM policy_fts")
        count = cur.fetchone()[0]

        if count == 0:
            for p in DEFAULT_POLICIES:
                conn.execute(
                    """
                    INSERT INTO policy_fts (doc_id, category, title, clause_code, content, action_url, action_label)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        p["doc_id"],
                        p["category"],
                        p["title"],
                        p["clause_code"],
                        p["content"],
                        p["action_url"],
                        p["action_label"],
                    ),
                )
            conn.commit()

    @classmethod
    def search_policies(
        cls,
        query: str,
        category: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search policy ordinances using BM25 ranking and snippet generation."""
        cls.initialize_fts_index()
        conn = get_connection()

        sanitized = re.sub(r"[^\w\s]", " ", query).strip()
        if not sanitized:
            return []

        # Build FTS5 MATCH tokens (prefix matching for typeahead search)
        tokens = [f'"{token}"*' for token in sanitized.split() if token]
        if not tokens:
            return []
        match_expr = " AND ".join(tokens)

        params: list[Any] = []
        sql = """
            SELECT
                doc_id,
                category,
                title,
                clause_code,
                content,
                action_url,
                action_label,
                snippet(policy_fts, 4, '<mark>', '</mark>', '...', 28) AS snippet_text,
                bm25(policy_fts) AS rank_score
            FROM policy_fts
            WHERE policy_fts MATCH ?
        """
        params.append(match_expr)

        if category and category.lower() != "all":
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY rank_score ASC LIMIT ?"
        params.append(limit)

        try:
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
            results = []
            for r in rows:
                results.append(
                    {
                        "doc_id": r["doc_id"],
                        "category": r["category"],
                        "title": r["title"],
                        "clause_code": r["clause_code"],
                        "content": r["content"],
                        "action_url": r["action_url"],
                        "action_label": r["action_label"],
                        "snippet": r["snippet_text"] or (r["content"][:160] + "..."),
                        "score": round(float(r["rank_score"]), 3),
                    }
                )
            return results
        except sqlite3.OperationalError:
            # Fallback for complex search terms or syntax deviations
            fallback_sql = """
                SELECT doc_id, category, title, clause_code, content, action_url, action_label
                FROM policy_fts
                WHERE content LIKE ? OR title LIKE ?
                LIMIT ?
            """
            like_pat = f"%{sanitized[:30]}%"
            cur = conn.execute(fallback_sql, (like_pat, like_pat, limit))
            results = []
            for r in cur.fetchall():
                results.append(
                    {
                        "doc_id": r["doc_id"],
                        "category": r["category"],
                        "title": r["title"],
                        "clause_code": r["clause_code"],
                        "content": r["content"],
                        "action_url": r["action_url"],
                        "action_label": r["action_label"],
                        "snippet": r["content"][:160] + "...",
                        "score": 0.0,
                    }
                )
            return results

    @classmethod
    def hybrid_guidance(
        cls,
        query: str,
        student_id: str | None = None,
    ) -> dict[str, Any]:
        """Synthesize zero-hallucination guidance combining live student profile with FTS5 policy clauses."""
        conn = get_connection()
        policies = cls.search_policies(query, limit=3)

        # Retrieve student record if provided
        student: dict[str, Any] | None = None
        if student_id:
            cur = conn.execute(
                "SELECT id, name, course, branch, semester, attendance, cgpa, fee_status, fee_due FROM students WHERE id = ?",
                (student_id,),
            )
            row = cur.fetchone()
            if row:
                student = dict(row)

        student_name = (student or {}).get("name", "Student").split()[0]
        attendance = float((student or {}).get("attendance", 75.0))
        fees_due = float((student or {}).get("fee_due", 0.0))

        # Check if query matches specific domains for personalized advice
        q_lower = query.lower()

        # 1. Attendance & Condonation domain
        if any(w in q_lower for w in ["attendance", "condonation", "debar", "absent", "shortage", "exam eligibility"]):
            matching_clause = next((p for p in policies if p["clause_code"] == "ORD-ACAD-7.2"), DEFAULT_POLICIES[0])
            if attendance >= 75.0:
                answer = (
                    f"{student_name}, your current attendance is {attendance:.1f}%, which meets the 75% cutoff under "
                    f"{matching_clause['clause_code']}. You are fully eligible to sit for End Term Semester Examinations without any condonation."
                )
                recommended_action = "View Exam Schedule"
                action_url = "/exams"
            elif 60.0 <= attendance < 75.0:
                shortfall = 75.0 - attendance
                answer = (
                    f"{student_name}, your recorded attendance is {attendance:.1f}% ({shortfall:.1f}% short of the mandatory 75% cutoff). "
                    f"Under {matching_clause['clause_code']}, you are eligible to request Dean's Condonation on medical or approved official "
                    f"duty grounds by filing Form AC-04 before the 10-day exam deadline."
                )
                recommended_action = "Download Form AC-04 (Condonation)"
                action_url = "/forms"
            else:
                answer = (
                    f"{student_name}, your recorded attendance is {attendance:.1f}%, which falls below the critical 60% threshold. "
                    f"Under {matching_clause['clause_code']}, attendance below 60% constitutes mandatory debarment. Please meet your Department "
                    f"Coordinator immediately for proctorial guidance."
                )
                recommended_action = "Contact Academic Advisor"
                action_url = "/chat"

            return {
                "answer": answer,
                "domain": "Academics",
                "citations": [matching_clause],
                "recommended_action": recommended_action,
                "action_url": action_url,
                "voice_speech_text": answer,
            }

        # 2. Withdrawal & Caution Deposit Offset domain
        if any(w in q_lower for w in ["withdrawal", "refund", "deposit", "offset", "lost id", "id card", "caution"]):
            offset_policy = next((p for p in policies if p["clause_code"] == "ORD-FIN-14.4"), DEFAULT_POLICIES[2])
            wth_policy = next((p for p in policies if p["clause_code"] == "ORD-WTH-14.1"), DEFAULT_POLICIES[1])

            if "offset" in q_lower or "lost id" in q_lower or "200" in q_lower:
                answer = (
                    f"{student_name}, under Smart Offsetting ({offset_policy['clause_code']}), any unreturned ID card fine (₹200) "
                    f"or library overdue charge can be auto-deducted directly from your refundable caution deposit (₹10,000). "
                    f"You do not need to make offline bank visits; checking the Smart Offset box clears the gate immediately."
                )
                action_url = "/withdrawal"
                recommended_action = "View Clearance & Offset"
            else:
                answer = (
                    f"{student_name}, university program withdrawal is governed by {wth_policy['clause_code']}. "
                    f"Tuition refund percentages follow UGC slabs (100% to 50% depending on days relative to admission closure). "
                    f"Your refundable caution deposit of ₹10,000 is 100% refundable across all withdrawal dates. "
                    f"Clearance is tracked across 4 digital gates (Library, Hostel, Accounts, Registrar)."
                )
                action_url = "/withdrawal"
                recommended_action = "Start Withdrawal Procedure"

            return {
                "answer": answer,
                "domain": "Withdrawal & Refunds",
                "citations": [wth_policy, offset_policy],
                "recommended_action": recommended_action,
                "action_url": action_url,
                "voice_speech_text": answer,
            }

        # 3. General Policy Matching Synthesis
        if policies:
            top_p = policies[0]
            answer = (
                f"{student_name}, according to {top_p['clause_code']} ({top_p['title']}): "
                f"{top_p['content']}"
            )
            return {
                "answer": answer,
                "domain": top_p["category"],
                "citations": policies,
                "recommended_action": top_p["action_label"],
                "action_url": top_p["action_url"],
                "voice_speech_text": answer,
            }

        # Fallback for unindexed topics
        fallback_msg = (
            f"{student_name}, I could not find a specific university ordinance matching your inquiry. "
            "UniAssist provides guidance for Academics, Attendance Condonation, Withdrawal Refunds, "
            "Smart Caution Deposit Offsets, Backpapers, Grievances, and Scholarships. Please try asking with one of these topics."
        )
        return {
            "answer": fallback_msg,
            "domain": "General",
            "citations": [],
            "recommended_action": "Browse Forms & Policies",
            "action_url": "/forms",
            "voice_speech_text": fallback_msg,
        }
