"""
Document management with real OCR verification (Phase 25) and fraud detection.

Phase 25 upgrade:
  - Real pytesseract OCR when Tesseract binary is available
  - Graceful mock fallback when Tesseract is not installed
  - Identity cross-check: extracted enrollment ID vs logged-in student
  - Fraud Detection: Checks for tampered signatures, mismatched names, altered text
  - Verification: Staff can manually verify or flag documents
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from pydantic import BaseModel
import hashlib
import shutil
import uuid
import json
import random
from pathlib import Path
from ..database.connection import get_connection
from ..config import settings
from ..services.ocr_service import OcrService

router = APIRouter(prefix="/api/documents", tags=["Documents"])
limiter = Limiter(key_func=get_remote_address)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}


# ── Upload Document with Real OCR Analysis (Phase 25) ─────────────────────────
@router.post("/upload")
@limiter.limit(settings.rate_limit_upload)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    student_id: str = Form(...)
):
    """
    Upload document and run real OCR text extraction + identity cross-check.
    Uses pytesseract when available, otherwise falls back to mock analysis.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, JPG, and PNG are allowed.")

    if file.filename is None:
        raise HTTPException(status_code=400, detail="A file name is required.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the permitted size.")

    secure_name = f"{student_id}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = UPLOAD_DIR / secure_name

    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    conn = get_connection()

    # Duplicate detection via SHA-256 hash comparison
    rows = conn.execute(
        "SELECT ocr_data FROM documents WHERE student_id = ? ORDER BY timestamp DESC",
        (student_id.upper().strip(),),
    ).fetchall()

    file_hash = hashlib.sha256(contents).hexdigest()
    is_duplicate = False
    for row in rows:
        if row["ocr_data"]:
            try:
                data = json.loads(row["ocr_data"])
                metadata = data.get("metadata", {})
                prior_hash = metadata.get("sha256")
                if prior_hash and prior_hash == file_hash:
                    is_duplicate = True
                    break
            except json.JSONDecodeError:
                continue

    # Phase 25: Real OCR analysis with identity cross-check
    analysis_result = OcrService.analyze(
        file_bytes=contents,
        filename=file.filename,
        student_id=student_id,
    )

    # Append duplicate flag if detected
    if is_duplicate:
        analysis_result["fraud_flags"].append("Duplicate document detected")
        analysis_result["overall_status"] = "FRAUD_DETECTED"

    ocr_identity_match = analysis_result.get("ocr_identity_match", "NOT_FOUND")
    ocr_engine = analysis_result.get("ocr_engine", "mock_fallback")

    try:
        verification_status = "fraud_detected" if analysis_result["fraud_flags"] else "pending"
        ocr_json = json.dumps(analysis_result["ocr_data"])
        fraud_notes = "; ".join(analysis_result["fraud_flags"]) if analysis_result["fraud_flags"] else None

        conn.execute(
            """INSERT INTO documents 
               (student_id, file_name, file_path, classification, ocr_data,
                verification_status, verification_notes, ocr_identity_match) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (student_id, file.filename, str(file_path),
             analysis_result["ocr_data"]["document_type"],
             ocr_json,
             verification_status,
             fraud_notes,
             ocr_identity_match)
        )
        conn.commit()
    except Exception:
        raise HTTPException(status_code=500, detail="Database error while saving document record.")

    return {
        "message": "Document uploaded successfully",
        "file_name": file.filename,
        "ocr_data": analysis_result["ocr_data"],
        "fraud_flags": analysis_result["fraud_flags"],
        "overall_status": analysis_result["overall_status"],
        "ocr_identity_match": ocr_identity_match,
        "ocr_engine": ocr_engine,
        "verification_status": verification_status,
    }


# ── Retrieve Documents for Audit ────────────────────────────────────────────────
@router.get("/list/{student_id}")
async def get_student_documents(student_id: str):
    """Get all documents uploaded by a student."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM documents WHERE student_id = ? ORDER BY timestamp DESC",
        (student_id.upper().strip(),)
    ).fetchall()
    
    result = []
    for r in rows:
        d = dict(r)
        if d["ocr_data"]:
            d["ocr_data"] = json.loads(d["ocr_data"])
        result.append(d)
    
    return result


# ── Admin: Get All Documents for Audit ───────────────────────────────────────
@router.get("/admin/audit-log")
async def get_all_documents_audit():
    """Get all documents for admin review with OCR audit data."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT d.*, s.name as student_name 
           FROM documents d 
           JOIN students s ON d.student_id = s.id 
           ORDER BY d.timestamp DESC"""
    ).fetchall()
    
    result = []
    for r in rows:
        d = dict(r)
        if d["ocr_data"]:
            d["ocr_data"] = json.loads(d["ocr_data"])
        result.append(d)
    
    return result


# ── Document Verification ───────────────────────────────────────────────────────
class DocumentVerification(BaseModel):
    status: str  # "verified", "fraud_detected", or "error"
    notes: str = None

@router.post("/verify/{doc_id}")
async def verify_document(doc_id: int, body: DocumentVerification):
    """
    Admin endpoint to verify or flag a document.
    """
    allowed_statuses = ("verified", "fraud_detected", "error")
    if body.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {', '.join(allowed_statuses)}")
    
    conn = get_connection()
    row = conn.execute("SELECT id FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    conn.execute(
        "UPDATE documents SET verification_status = ?, verification_notes = ? WHERE id = ?",
        (body.status, body.notes, doc_id)
    )
    conn.commit()
    
    return {"message": f"Document {doc_id} marked as {body.status}.", "notes": body.notes}
