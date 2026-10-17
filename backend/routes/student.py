"""
Student lifecycle API endpoints.

Provides personalized data for dashboard, academics, scholarships,
notices, grievances, internships, and back-paper registration.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Request
from ..database.connection import get_connection
from ..models.schemas import BackpaperRequest, GrievanceCreate, ScholarshipApply
from ..security.rbac import require_student_access

router = APIRouter(prefix="/api/student", tags=["Student"])


def _normalise_student_id(student_id: str) -> str:
    return student_id.upper().strip()


# ── Profile ───────────────────────────────────────────────────────────────────
def _fetch_profile(student_id: str):
    """Return full student profile for dashboard personalization."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE id = ?", (_normalise_student_id(student_id),)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found.")
    return dict(row)


@router.get("/profile")
async def get_profile(student_id: str = Query(..., min_length=3, max_length=20), request: Request = None):
    """Return full student profile for dashboard personalization."""
    require_student_access(request, student_id)
    return _fetch_profile(student_id)


@router.get("/profile/{student_id}")
async def get_profile_by_path(student_id: str, request: Request = None):
    """Compatibility route for existing callers that use path parameters."""
    require_student_access(request, student_id)
    return _fetch_profile(student_id)


# ── Personalized Notices ───────────────────────────────────────────────────────
def _fetch_notices(student_id: str):
    """Return notices personalized to student's branch and semester."""
    conn = get_connection()
    student = conn.execute(
        "SELECT branch, semester FROM students WHERE id = ?",
        (_normalise_student_id(student_id),)
    ).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    branch = student["branch"]
    semester = student["semester"]

    rows = conn.execute(
        """SELECT * FROM notices
           WHERE (target_branch = 'ALL' OR target_branch = ?)
             AND (target_semester = 0 OR target_semester = ?)
           ORDER BY timestamp DESC""",
        (branch, semester)
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/notices")
async def get_notices(student_id: str = Query(..., min_length=3, max_length=20), request: Request = None):
    """Return notices personalized to student's branch and semester."""
    require_student_access(request, student_id)
    return _fetch_notices(student_id)


@router.get("/notices/{student_id}")
async def get_notices_by_path(student_id: str, request: Request = None):
    """Compatibility route for existing callers that use path parameters."""
    require_student_access(request, student_id)
    return _fetch_notices(student_id)


# ── Examinations & Results ─────────────────────────────────────────────────────
def _fetch_exams(student_id: str):
    """Return exam schedule, grades, and back-paper status for a student."""
    conn = get_connection()
    student = conn.execute(
        "SELECT id FROM students WHERE id = ?",
        (_normalise_student_id(student_id),),
    ).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    rows = conn.execute(
        "SELECT * FROM examinations WHERE student_id = ? ORDER BY exam_date ASC",
        (_normalise_student_id(student_id),)
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/exams")
async def get_exams(student_id: str = Query(..., min_length=3, max_length=20), request: Request = None):
    """Return exam schedule, grades, and back-paper status for a student."""
    require_student_access(request, student_id)
    return _fetch_exams(student_id)


@router.get("/exams/{student_id}")
async def get_exams_by_path(student_id: str, request: Request = None):
    """Compatibility route for existing callers that use path parameters."""
    require_student_access(request, student_id)
    return _fetch_exams(student_id)


# ── Back Paper Registration ────────────────────────────────────────────────────
def _register_backpaper(body: BackpaperRequest):
    """Register a student for a back-paper exam."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM examinations WHERE id = ? AND student_id = ?",
        (body.exam_id, body.student_id)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Exam record not found.")
    if row["grade"] not in (None, "F", "D"):
        raise HTTPException(status_code=400, detail="Back paper not applicable for this exam.")
    conn.execute(
        "UPDATE examinations SET backpaper_status = 'registered' WHERE id = ?",
        (body.exam_id,)
    )
    conn.commit()
    return {"message": f"Back paper registered for {row['subject_name']}. Fee payment pending."}


@router.post("/backpaper")
async def register_backpaper(body: BackpaperRequest):
    """Register a student for a back-paper exam."""
    return _register_backpaper(body)


@router.post("/backpaper/register")
async def register_backpaper_compat(body: BackpaperRequest):
    """Compatibility route for existing callers."""
    return _register_backpaper(body)


# ── Scholarships ───────────────────────────────────────────────────────────────
def _fetch_scholarships(student_id: str):
    """Return all scholarships and eligibility status for the student."""
    conn = get_connection()
    student = conn.execute(
        "SELECT cgpa FROM students WHERE id = ?",
        (_normalise_student_id(student_id),)
    ).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    schemes = conn.execute("SELECT * FROM scholarships").fetchall()
    applied = conn.execute(
        "SELECT scholarship_id, status FROM scholarship_applications WHERE student_id = ?",
        (_normalise_student_id(student_id),)
    ).fetchall()
    applied_map = {r["scholarship_id"]: r["status"] for r in applied}

    result = []
    for s in schemes:
        eligible = student["cgpa"] >= s["eligibility_cgpa"]
        result.append({
            **dict(s),
            "eligible": eligible,
            "application_status": applied_map.get(s["id"], None)
        })
    return result


@router.get("/scholarships")
async def get_scholarships(student_id: str = Query(..., min_length=3, max_length=20), request: Request = None):
    """Return all scholarships and eligibility status for the student."""
    require_student_access(request, student_id)
    return _fetch_scholarships(student_id)


@router.get("/scholarships/{student_id}")
async def get_scholarships_by_path(student_id: str, request: Request = None):
    """Compatibility route for existing callers that use path parameters."""
    require_student_access(request, student_id)
    return _fetch_scholarships(student_id)


# ── Apply for Scholarship ──────────────────────────────────────────────────────
@router.post("/scholarships/apply")
async def apply_scholarship(body: ScholarshipApply):
    """Auto-apply student for a scholarship if eligible."""
    conn = get_connection()
    student = conn.execute(
        "SELECT cgpa FROM students WHERE id = ?",
        (body.student_id,)
    ).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    scheme = conn.execute(
        "SELECT * FROM scholarships WHERE id = ?", (body.scholarship_id,)
    ).fetchone()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scholarship not found.")

    if student["cgpa"] < scheme["eligibility_cgpa"]:
        raise HTTPException(
            status_code=400,
            detail=f"Not eligible. Required CGPA: {scheme['eligibility_cgpa']}, Your CGPA: {student['cgpa']}"
        )

    existing = conn.execute(
        "SELECT id FROM scholarship_applications WHERE student_id = ? AND scholarship_id = ?",
        (body.student_id, body.scholarship_id)
    ).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="Already applied for this scholarship.")

    conn.execute(
        "INSERT INTO scholarship_applications (student_id, scholarship_id, status) VALUES (?, ?, 'pending')",
        (body.student_id, body.scholarship_id)
    )
    conn.commit()
    return {"message": f"Application submitted for '{scheme['name']}'. Under review."}


# ── Grievances ────────────────────────────────────────────────────────────────
@router.post("/grievances")
async def file_grievance(body: GrievanceCreate):
    """File a new student grievance."""
    allowed = ("academic", "fee", "hostel", "exam", "scholarship")
    if body.category not in allowed:
        raise HTTPException(status_code=400, detail=f"Category must be one of: {', '.join(allowed)}")
    conn = get_connection()
    # Check for recent duplicate submission from the same student to prevent duplicate submissions (F07)
    recent = conn.execute(
        """
        SELECT id, timestamp FROM grievances 
        WHERE student_id = ? AND category = ? AND description = ? AND status = 'open'
        ORDER BY timestamp DESC LIMIT 1
        """,
        (body.student_id, body.category, body.description)
    ).fetchone()
    if recent:
        existing_id = recent["id"]
        year = datetime.now(timezone.utc).year
        ticket_id = f"GRV-{year}-{existing_id:04d}"
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate submission prevented. An identical grievance is already registered as Ticket {ticket_id}."
        )

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO grievances (student_id, category, description) VALUES (?, ?, ?)",
        (body.student_id, body.category, body.description)
    )
    conn.commit()
    grievance_id = cursor.lastrowid
    year = datetime.now(timezone.utc).year
    ticket_id = f"GRV-{year}-{grievance_id:04d}"

    dept_routing = {
        "academic": "Department Academic Coordinator",
        "fee": "Finance & Accounts Office",
        "hostel": "Chief Warden & Hostel Office",
        "exam": "Controller of Examinations",
        "scholarship": "Dean of Student Welfare (Scholarships Desk)"
    }.get(body.category, "Proctorial Board")

    return {
        "message": "Grievance registered and assigned to department coordinator.",
        "ticket_id": ticket_id,
        "id": grievance_id,
        "category": body.category,
        "assigned_to": dept_routing,
        "sla_hours": 48 if body.category in ("academic", "fee") else 72,
        "status": "open",
    }

def _fetch_grievances(student_id: str):
    """Return all grievances for a student."""
    conn = get_connection()
    norm_id = _normalise_student_id(student_id)
    if norm_id != "GUEST":
        student = conn.execute(
            "SELECT id FROM students WHERE id = ?",
            (norm_id,),
        ).fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found.")
    rows = conn.execute(
        "SELECT * FROM grievances WHERE student_id = ? ORDER BY timestamp DESC",
        (norm_id,)
    ).fetchall()
    
    dept_routing = {
        "academic": "Department Academic Coordinator",
        "fee": "Finance & Accounts Office",
        "hostel": "Chief Warden & Hostel Office",
        "exam": "Controller of Examinations",
        "scholarship": "Dean of Student Welfare (Scholarships Desk)"
    }
    
    res = []
    for r in rows:
        d = dict(r)
        gid = d.get("id", 0)
        d["ticket_id"] = f"GRV-2026-{gid:04d}"
        cat = d.get("category", "academic")
        d["assigned_to"] = dept_routing.get(cat, "Proctorial Board")
        d["sla_hours"] = 48 if cat in ("academic", "fee") else 72
        res.append(d)
    return res


@router.get("/grievances")
async def get_grievances(student_id: str = Query(..., min_length=3, max_length=20), request: Request = None):
    """Return all grievances for a student."""
    require_student_access(request, student_id)
    return _fetch_grievances(student_id)


@router.get("/grievances/{student_id}")
async def get_grievances_by_path(student_id: str, request: Request = None):
    """Compatibility route for existing callers that use path parameters."""
    require_student_access(request, student_id)
    return _fetch_grievances(student_id)


# ── Internships ───────────────────────────────────────────────────────────────
def _fetch_internships(student_id: str):
    """Return internship opportunities relevant to a student's CGPA."""
    conn = get_connection()
    student = conn.execute(
        "SELECT cgpa FROM students WHERE id = ?",
        (_normalise_student_id(student_id),)
    ).fetchone()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    rows = conn.execute(
        "SELECT * FROM internships ORDER BY deadline ASC"
    ).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        d["eligible"] = student["cgpa"] >= r["required_cgpa"]
        result.append(d)
    return result


@router.get("/internships")
async def get_internships(student_id: str = Query(..., min_length=3, max_length=20)):
    """Return internship opportunities relevant to a student's CGPA."""
    return _fetch_internships(student_id)


@router.get("/internships/{student_id}")
async def get_internships_by_path(student_id: str):
    """Compatibility route for existing callers that use path parameters."""
    return _fetch_internships(student_id)
