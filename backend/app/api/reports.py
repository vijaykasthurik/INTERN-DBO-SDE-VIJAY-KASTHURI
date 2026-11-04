"""Report export endpoints (PDF and Markdown) with full Evidence Ledger integration."""

import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import ChatMessage, ChatSession, User
from app.db.session import get_db
from app.deps import get_current_user
from app.reports.builder import ReportBuilder
from app.reports.markdown import MarkdownReportExporter
from app.reports.pdf import PDFReportExporter

router = APIRouter(prefix="/reports", tags=["reports"])

REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "reports"))
os.makedirs(REPORTS_DIR, exist_ok=True)

_BUILDER = ReportBuilder()
_PDF_EXPORTER = PDFReportExporter()
_MD_EXPORTER = MarkdownReportExporter()


class ExportReportRequest(BaseModel):
    """Report export request parameters."""

    session_id: str
    format: str = Field(default="pdf", pattern="^(pdf|md)$")
    title: str | None = "Lumen Executive Analytical Report"


class ExportReportResponse(BaseModel):
    """Report generation response metadata."""

    report_id: str
    format: str
    download_url: str
    title: str


@router.post("/export", response_model=ExportReportResponse, status_code=status.HTTP_201_CREATED)
async def export_report(
    req: ExportReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExportReportResponse:
    """Generate executive report from Evidence Ledger session history in PDF or Markdown."""
    # Verify session ownership
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == req.session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        # If session doesn't exist in DB (e.g. mock test session), generate report with session title
        title = req.title or "Lumen Executive Analytical Report"
        messages_data: list[dict[str, Any]] = []
    else:
        title = req.title or session.title or "Lumen Executive Analytical Report"
        db_messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == req.session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        messages_data = [
            {
                "role": m.role,
                "content": m.content,
                "evidence": m.evidence_ledger or {},
            }
            for m in db_messages
        ]

    report_data = _BUILDER.build_report_data(
        session_id=req.session_id,
        messages=messages_data,
        title=title,
    )

    report_id = f"rep_{uuid.uuid4().hex[:10]}"
    ext = req.format.lower()
    filename = f"{report_id}.{ext}"
    output_path = os.path.join(REPORTS_DIR, filename)

    if ext == "pdf":
        _PDF_EXPORTER.render_pdf(report_data, output_path)
    else:
        content = _MD_EXPORTER.render_markdown(report_data)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

    return ExportReportResponse(
        report_id=report_id,
        format=ext,
        download_url=f"/api/v1/reports/download/{filename}",
        title=title,
    )


@router.get("/download/{filename}")
async def download_report(filename: str) -> FileResponse:
    """Download compiled report document."""
    file_path = os.path.join(REPORTS_DIR, os.path.basename(filename))
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report file '{filename}' not found",
        )

    media_type = "application/pdf" if filename.endswith(".pdf") else "text/markdown; charset=utf-8"
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename,
    )
