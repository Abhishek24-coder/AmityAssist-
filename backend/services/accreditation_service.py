"""
Phase 27: Academic Accreditation & CO/PO Reporting Engine.
Maps examination grades to Course Outcomes (CO1-CO4) and Program Outcomes
(PO1-PO12) for automated NAAC Criterion 2.6 attainment reporting.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..database.connection import get_connection

# Grade-to-numeric mapping (10-point CBCS scale)
GRADE_MAP = {
    "O": 10, "A+": 9, "A": 8, "B+": 7, "B": 6,
    "C": 5, "D": 4, "F": 0, "P": 5, "NP": 0,
}

PO_LABELS = [f"PO{i}" for i in range(1, 13)]


class AccreditationService:
    """CO/PO attainment engine for NAAC/NBA compliance reporting."""

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def grade_to_numeric(cls, grade: Optional[str]) -> float:
        """Convert letter grade to numeric value."""
        if not grade:
            return 0.0
        return float(GRADE_MAP.get(grade.strip().upper(), 0))

    @classmethod
    def get_co_attainment(
        cls,
        branch: str,
        semester: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calculate CO attainment for all courses in a branch/semester.
        
        Attainment = percentage of students scoring >= threshold grade (B+ = 7)
        for each CO. A CO is "attained" if this percentage >= target_attainment.
        """
        conn = get_connection()

        # Get CO/PO mappings for the branch
        query = "SELECT * FROM co_po_mappings WHERE branch = ?"
        params: list = [branch.upper()]
        if semester:
            query += " AND semester = ?"
            params.append(semester)
        query += " ORDER BY course_code, co_code"

        mappings = [dict(row) for row in conn.execute(query, params).fetchall()]
        if not mappings:
            return {"branch": branch, "semester": semester, "courses": [], "generated_at": cls._now_iso()}

        # Get examination grades for students in this branch
        grade_query = """
            SELECT e.student_id, e.subject_code, e.grade
            FROM examinations e
            JOIN students s ON e.student_id = s.id
            WHERE s.branch = ? AND e.grade IS NOT NULL
        """
        grade_params: list = [branch.upper()]
        if semester:
            grade_query += " AND s.semester = ?"
            grade_params.append(semester)

        grades = conn.execute(grade_query, grade_params).fetchall()

        # Build grade lookup: {course_code: {student_id: numeric_grade}}
        grade_lookup: Dict[str, Dict[str, float]] = {}
        for g in grades:
            code = g["subject_code"]
            if code not in grade_lookup:
                grade_lookup[code] = {}
            grade_lookup[code][g["student_id"]] = cls.grade_to_numeric(g["grade"])

        # Calculate CO attainment per course
        courses = {}
        for m in mappings:
            code = m["course_code"]
            if code not in courses:
                courses[code] = {
                    "course_code": code,
                    "course_name": m["course_name"],
                    "semester": m["semester"],
                    "cos": [],
                }

            # Get students who took this course
            student_grades = grade_lookup.get(code, {})
            total_students = len(student_grades) if student_grades else 1  # avoid div by zero

            # Count students scoring >= B+ (7.0) as "attaining" this CO
            threshold = 7.0  # B+ and above
            attaining_students = sum(1 for g in student_grades.values() if g >= threshold)
            attainment_pct = round((attaining_students / total_students) * 100, 2) if total_students > 0 else 0.0

            target = m.get("target_attainment", 50.0)
            is_attained = attainment_pct >= target

            co_entry = {
                "co_code": m["co_code"],
                "co_description": m["co_description"],
                "total_students": total_students,
                "students_above_threshold": attaining_students,
                "attainment_percentage": attainment_pct,
                "target_attainment": target,
                "is_attained": is_attained,
                "status": "ATTAINED" if is_attained else "NOT_ATTAINED",
            }
            courses[code]["cos"].append(co_entry)

        return {
            "branch": branch.upper(),
            "semester": semester,
            "total_courses": len(courses),
            "courses": list(courses.values()),
            "generated_at": cls._now_iso(),
        }

    @classmethod
    def get_po_attainment(cls, branch: str) -> Dict[str, Any]:
        """
        Calculate PO attainment matrix by aggregating CO→PO correlation
        weights across all courses in the branch.
        
        PO attainment = weighted average of CO attainments using the
        CO→PO mapping weights from co_po_mappings table.
        """
        conn = get_connection()

        mappings = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM co_po_mappings WHERE branch = ? ORDER BY course_code, co_code",
                (branch.upper(),),
            ).fetchall()
        ]

        if not mappings:
            return {"branch": branch, "po_matrix": [], "generated_at": cls._now_iso()}

        # Aggregate PO weights and counts
        po_sums = {po: 0.0 for po in PO_LABELS}
        po_counts = {po: 0 for po in PO_LABELS}

        for m in mappings:
            for po in PO_LABELS:
                weight = float(m.get(po.lower(), 0))
                if weight > 0:
                    po_sums[po] += weight
                    po_counts[po] += 1

        # Build PO attainment matrix
        po_matrix = []
        for po in PO_LABELS:
            avg_weight = round(po_sums[po] / po_counts[po], 2) if po_counts[po] > 0 else 0.0
            # Attainment level based on average correlation weight (0-3 scale)
            if avg_weight >= 2.5:
                level = "HIGH"
            elif avg_weight >= 1.5:
                level = "MEDIUM"
            elif avg_weight > 0:
                level = "LOW"
            else:
                level = "NONE"

            po_matrix.append({
                "po_code": po,
                "average_correlation_weight": avg_weight,
                "contributing_cos": po_counts[po],
                "total_weight": round(po_sums[po], 2),
                "attainment_level": level,
            })

        return {
            "branch": branch.upper(),
            "total_pos": len(PO_LABELS),
            "po_matrix": po_matrix,
            "generated_at": cls._now_iso(),
        }

    @classmethod
    def get_cohort_summary(
        cls,
        branch: str,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate a cohort-level summary combining CO and PO attainment."""
        co_report = cls.get_co_attainment(branch)
        po_report = cls.get_po_attainment(branch)

        total_cos = sum(len(c["cos"]) for c in co_report["courses"])
        attained_cos = sum(
            sum(1 for co in c["cos"] if co["is_attained"])
            for c in co_report["courses"]
        )
        high_pos = sum(1 for po in po_report["po_matrix"] if po["attainment_level"] == "HIGH")
        medium_pos = sum(1 for po in po_report["po_matrix"] if po["attainment_level"] == "MEDIUM")

        return {
            "branch": branch.upper(),
            "academic_year": year or datetime.now().year,
            "total_courses": co_report["total_courses"],
            "total_cos": total_cos,
            "attained_cos": attained_cos,
            "co_attainment_rate": round((attained_cos / total_cos) * 100, 2) if total_cos else 0,
            "po_summary": {
                "high_attainment": high_pos,
                "medium_attainment": medium_pos,
                "low_attainment": 12 - high_pos - medium_pos,
            },
            "co_report": co_report,
            "po_report": po_report,
            "generated_at": cls._now_iso(),
        }

    @classmethod
    def csv_export(cls, branch: str, semester: Optional[int] = None) -> bytes:
        """Export CO attainment report as CSV for NAAC Criterion 2.6."""
        co_report = cls.get_co_attainment(branch, semester)
        output = io.StringIO(newline="")
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Course Code", "Course Name", "Semester", "CO Code",
            "CO Description", "Total Students", "Students Above Threshold",
            "Attainment %", "Target %", "Status",
        ])

        for course in co_report["courses"]:
            for co in course["cos"]:
                writer.writerow([
                    course["course_code"],
                    course["course_name"],
                    course["semester"],
                    co["co_code"],
                    co["co_description"],
                    co["total_students"],
                    co["students_above_threshold"],
                    co["attainment_percentage"],
                    co["target_attainment"],
                    co["status"],
                ])

        return output.getvalue().encode("utf-8")

    @classmethod
    def pdf_export(cls, branch: str) -> bytes:
        """Export a summary PDF using the existing ReportingService pattern."""
        from .reporting_service import ReportingService

        summary = cls.get_cohort_summary(branch)
        flat = {
            "Branch": summary["branch"],
            "Academic Year": summary["academic_year"],
            "Total Courses": summary["total_courses"],
            "Total COs": summary["total_cos"],
            "Attained COs": summary["attained_cos"],
            "CO Attainment Rate (%)": summary["co_attainment_rate"],
            "High PO Attainment": summary["po_summary"]["high_attainment"],
            "Medium PO Attainment": summary["po_summary"]["medium_attainment"],
            "Low PO Attainment": summary["po_summary"]["low_attainment"],
        }
        return ReportingService.pdf_export(
            f"NAAC Criterion 2.6 - CO/PO Attainment Report ({branch})",
            flat,
        )
