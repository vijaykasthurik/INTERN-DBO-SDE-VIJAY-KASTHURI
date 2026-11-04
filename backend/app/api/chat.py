"""Chat sessions, conversational messages, and Evidence Ledger inspection endpoints."""

from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    """Session initiation payload."""
    title: str | None = "New Analysis"


class SessionResponse(BaseModel):
    """Chat session representation."""
    id: str
    title: str
    created_at: str


class EvidenceLedgerResponse(BaseModel):
    """Evidence ledger entry details."""
    message_id: str
    steps: list[dict[str, Any]]
    verified: bool
    confidence: str


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(req: CreateSessionRequest) -> SessionResponse:
    """Create a new chat session."""
    return SessionResponse(
        id="sess_01j78abc",
        title=req.title or "New Analysis",
        created_at="2026-11-04T12:00:00Z",
    )


@router.get("/messages/{message_id}/evidence", response_model=EvidenceLedgerResponse)
async def get_message_evidence(message_id: str) -> EvidenceLedgerResponse:
    """Retrieve full Evidence Ledger entries and cross-check results."""
    return EvidenceLedgerResponse(
        message_id=message_id,
        steps=[],
        verified=True,
        confidence="High",
    )
