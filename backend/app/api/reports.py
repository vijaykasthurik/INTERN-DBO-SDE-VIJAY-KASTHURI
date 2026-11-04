"""Report export endpoints (PDF and Markdown)."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

router = APIRouter(prefix="/reports", tags=["reports"])


class ExportReportRequest(BaseModel):
    """Report export request parameter."""
    session_id: str
    format: str = "pdf"  # pdf or md


@router.post("/export")
async def export_report(req: ExportReportRequest) -> dict[str, Any]:
    """Generate executive report from Evidence Ledger session history."""
    return {
        "report_id": "rep_01",
        "format": req.format,
        "download_url": f"/api/v1/reports/download/rep_01.{req.format}",
    }


@router.get("/download/{filename}")
async def download_report(filename: str) -> PlainTextResponse:
    """Download compiled report."""
    return PlainTextResponse(f"# Lumen Report\nGenerated file: {filename}")
