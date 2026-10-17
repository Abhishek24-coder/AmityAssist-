"""Official Notesheet PDF Generator.

Produces publication-grade, downloadable PDF documents for the Amity University
Digital Notesheet Cockpit with full signature seals and audit trails.
Zero external dependencies (pure PDF-1.4 vector drawing).
"""

from datetime import datetime, timezone
from typing import Any


def escape_pdf(text: str) -> str:
    """Escape text for inclusion inside PDF string literals."""
    if not text:
        return ""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def generate_notesheet_pdf(ns: dict[str, Any]) -> bytes:
    """Generate a clean, official Amity University Digital Notesheet PDF."""
    ref_no = ns.get("reference_no", "NS-UNKNOWN")
    title = ns.get("title", "Official University Notesheet")
    category = ns.get("category", "General")
    stage = ns.get("current_stage", "SUPERVISOR")
    status = ns.get("status", "IN_REVIEW")
    student_id = ns.get("student_id") or "N/A"
    created_by = ns.get("created_by", "Faculty/Staff")
    created_at = ns.get("created_at", datetime.now(timezone.utc).strftime("%Y-%m-%d"))[:10]
    content = ns.get("content") or {}
    subject = content.get("subject") or title
    body_text = content.get("body") or content.get("remarks") or "Official administrative review notesheet."
    justification = content.get("justification") or content.get("reason") or "As per university statutes and procedural standards."
    signatures = ns.get("signatures") or []

    # Page size: 612 x 792 (Letter)
    decorations = [
        # Top banner (Amity Navy / Blue)
        "q 0.05 0.15 0.35 rg 0 720 612 72 re f Q",
        # Accent gold bar
        "q 0.95 0.72 0.11 rg 0 714 612 6 re f Q",
        # Border box for the document
        "q 0.85 0.88 0.92 rg 36 40 540 655 re s Q",
        # Header background box for details
        "q 0.96 0.97 0.99 rg 48 580 516 100 re f Q",
        "q 0.85 0.88 0.92 rg 48 580 516 100 re s Q",
        # Content background box
        "q 0.98 0.98 0.99 rg 48 290 516 270 re f Q",
        "q 0.85 0.88 0.92 rg 48 290 516 270 re s Q",
        # Signatures container box
        "q 0.95 0.96 0.98 rg 48 110 516 160 re f Q",
        "q 0.85 0.88 0.92 rg 48 110 516 160 re s Q",
    ]

    text_ops = [
        # Banner Header
        "BT 1 1 1 rg /F2 18 Tf 50 755 Td (AMITY UNIVERSITY) Tj ET",
        "BT 0.95 0.72 0.11 rg /F2 11 Tf 50 735 Td (OFFICIAL ACADEMIC & ADMINISTRATIVE DIGITAL NOTESHEET) Tj ET",
        f"BT 1 1 1 rg /F1 10 Tf 410 745 Td (Ref: {escape_pdf(ref_no)}) Tj ET",

        # Header Box Details
        f"BT 0.05 0.15 0.35 rg /F2 12 Tf 60 660 Td (Subject: {escape_pdf(subject[:60])}) Tj ET",
        f"BT 0.2 0.2 0.2 rg /F1 10 Tf 60 640 Td (Category: {escape_pdf(category)}   |   Student ID: {escape_pdf(student_id)}   |   Date: {escape_pdf(created_at)}) Tj ET",
        f"BT 0.2 0.2 0.2 rg /F1 10 Tf 60 622 Td (Originator: {escape_pdf(created_by)}   |   Current Stage: {escape_pdf(stage)}   |   Status: {escape_pdf(status)}) Tj ET",
        f"BT 0.3 0.3 0.3 rg /F1 9 Tf 60 595 Td (Approval Track: Supervisor -> HOD -> HOI -> Pro-VC -> Vice Chancellor) Tj ET",

        # Body Section
        "BT 0.05 0.15 0.35 rg /F2 12 Tf 60 535 Td (I. DETAILED NOTE / OBSERVATIONS) Tj ET",
    ]

    # Split body text into wrapped lines
    words = body_text.split()
    lines = []
    curr = []
    for w in words:
        if len(" ".join(curr + [w])) < 75:
            curr.append(w)
        else:
            lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))

    y = 515
    for l in lines[:7]:
        text_ops.append(f"BT 0.15 0.15 0.15 rg /F1 10 Tf 60 {y} Td ({escape_pdf(l)}) Tj ET")
        y -= 16

    # Justification Section
    text_ops.extend([
        "BT 0.05 0.15 0.35 rg /F2 12 Tf 60 380 Td (II. STATUTORY JUSTIFICATION & RECOMMENDATION) Tj ET",
    ])
    j_words = justification.split()
    j_lines = []
    j_curr = []
    for w in j_words:
        if len(" ".join(j_curr + [w])) < 75:
            j_curr.append(w)
        else:
            j_lines.append(" ".join(j_curr))
            j_curr = [w]
    if j_curr:
        j_lines.append(" ".join(j_curr))

    jy = 360
    for jl in j_lines[:3]:
        text_ops.append(f"BT 0.25 0.25 0.25 rg /F1 10 Tf 60 {jy} Td ({escape_pdf(jl)}) Tj ET")
        jy -= 16

    # Signatures & Hierarchy Block
    text_ops.append("BT 0.05 0.15 0.35 rg /F2 11 Tf 60 250 Td (III. HIERARCHICAL DIGITAL SIGNATURES & AUDIT LOGS) Tj ET")

    if not signatures:
        text_ops.append("BT 0.4 0.4 0.4 rg /F1 9 Tf 60 220 Td (No signatures recorded yet. Currently awaiting review at SUPERVISOR stage.) Tj ET")
    else:
        sig_x = 60
        sig_y = 225
        for sig in signatures[:4]:
            role = sig.get("role", "Officer")
            name = sig.get("officer_name", "Authorized Officer")
            act = sig.get("action", "SIGNED")
            dt = str(sig.get("signed_at", ""))[:10]
            comm = sig.get("comments") or "Approved"
            text_ops.append(f"BT 0.1 0.1 0.1 rg /F2 9 Tf {sig_x} {sig_y} Td ({escape_pdf(role)}: {escape_pdf(name)}) Tj ET")
            text_ops.append(f"BT 0.2 0.5 0.2 rg /F1 8 Tf {sig_x} {sig_y - 12} Td ([{escape_pdf(act)}] on {escape_pdf(dt)}) Tj ET")
            text_ops.append(f"BT 0.3 0.3 0.3 rg /F1 8 Tf {sig_x} {sig_y - 24} Td (Note: {escape_pdf(comm[:24])}) Tj ET")
            sig_x += 125
            if sig_x > 450:
                sig_x = 60
                sig_y -= 45

    # Legal Disclaimer Footer
    text_ops.extend([
        "BT 0.5 0.5 0.5 rg /F1 8 Tf 50 65 Td (This document is digitally endorsed under Information Technology Act 2000. Tamper-evident ledger record.) Tj ET",
        f"BT 0.5 0.5 0.5 rg /F1 8 Tf 50 50 Td (Amity University Digital Governance System - Verified Reference: {escape_pdf(ref_no)}) Tj ET",
    ])

    stream_content = " ".join(decorations + text_ops)
    stream_bytes = stream_content.encode("latin-1", "replace")

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        f"<< /Length {len(stream_bytes)} >>\nstream\n{stream_content}\nendstream",
    ]

    pdf = "%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(pdf.encode("latin-1")))
        pdf += f"{index} 0 obj\n{obj}\nendobj\n"

    xref_offset = len(pdf.encode("latin-1"))
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    pdf += "".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"

    return pdf.encode("latin-1", "replace")
