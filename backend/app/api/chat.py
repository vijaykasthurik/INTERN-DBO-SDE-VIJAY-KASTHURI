"""Chat sessions, conversational messages, SSE streaming, and Evidence Ledger inspection endpoints."""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.agent.engine import AgentEngine
from app.agent.memory import AgentMemory
from app.core.errors import NotFoundError
from app.data.ingestion import DataIngestionPipeline
from app.db.models import ChatMessage, ChatSession, Dataset, User, UserApiKey
from app.db.session import get_db
from app.deps import get_current_user
from app.safety.sql_validator import SQLSecurityError
from app.tools.sql_tool import SQLExecutionError, SQLTool

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory session memory storage keyed by session_id
_SESSION_MEMORIES: dict[str, AgentMemory] = {}
_AGENT_ENGINE = AgentEngine()


def get_or_create_memory(session_id: str) -> AgentMemory:
    """Retrieve or create active working memory for a session."""
    if session_id not in _SESSION_MEMORIES:
        _SESSION_MEMORIES[session_id] = AgentMemory(session_id=session_id)
    return _SESSION_MEMORIES[session_id]


class CreateSessionRequest(BaseModel):
    """Session initiation payload."""

    title: str | None = "New Analysis"


class SessionResponse(BaseModel):
    """Chat session representation."""

    id: str
    title: str
    created_at: str


class SendMessageRequest(BaseModel):
    """User message submission payload."""

    content: str


class ExecuteSQLRequest(BaseModel):
    """Read-only SQL rerun request for code shown in the Evidence drawer."""

    sql: str


class EvidenceLedgerResponse(BaseModel):
    """Evidence ledger inspection payload."""

    message_id: str
    steps: list[dict[str, Any]]
    verified: bool
    confidence: str


@router.post("/execute")
async def execute_sql(
    req: ExecuteSQLRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Re-run exact SQL through the same SELECT-only table allow-list and read-only DuckDB tool."""
    datasets = db.query(Dataset).filter(Dataset.user_id == current_user.id).all()
    if not datasets:
        raise HTTPException(status_code=409, detail="Upload a dataset before running SQL.")
    pipeline = DataIngestionPipeline()
    tool = SQLTool(
        db_path=pipeline.get_user_db_path(current_user.id),
        allowed_tables=[dataset.duckdb_table_name for dataset in datasets],
        enforce_relationships=True,
    )
    try:
        return tool.execute(req.sql)
    except SQLSecurityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLExecutionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class ExecutePandasRequest(BaseModel):
    code: str


@router.post("/execute-pandas")
async def execute_pandas(body: ExecutePandasRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    import asyncio
    import time

    from app.safety.pandas_sandbox import SandboxViolationError
    from app.tools.pandas_tool import PandasTool
    datasets = db.query(Dataset).filter(Dataset.user_id == current_user.id).all()
    if not datasets:
        raise HTTPException(status_code=409,detail="Upload a dataset before running Pandas.")
    start = time.perf_counter()
    tool = PandasTool()
    try:
        frames = tool.load_dataframes(DataIngestionPipeline().get_user_db_path(current_user.id),[dataset.duckdb_table_name for dataset in datasets])
        result = await asyncio.to_thread(tool.execute_script,body.code,frames)
        columns,rows = tool.result_rows(result)
    except (SandboxViolationError,ValueError) as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    return {"columns":columns,"rows":rows,"row_count":len(rows),"runtime_ms":round((time.perf_counter()-start)*1000,2),"executed_code":body.code}


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    req: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionResponse:
    """Create a new chat session scoped to authenticated user."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    new_session = ChatSession(
        id=session_id,
        user_id=current_user.id,
        title=req.title or "New Analysis",
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return SessionResponse(
        id=new_session.id,
        title=new_session.title,
        created_at=new_session.created_at.isoformat(),
    )


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SessionResponse]:
    """List all chat sessions belonging to the authenticated user."""
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return [
        SessionResponse(
            id=s.id,
            title=s.title,
            created_at=s.created_at.isoformat(),
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve full conversation history for a given session."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise NotFoundError(f"Chat session '{session_id}' not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "confidence": m.confidence,
                "created_at": m.created_at.isoformat(),
                "has_evidence": m.evidence_ledger is not None,
            }
            for m in messages
        ],
    }


@router.post("/sessions/{session_id}/messages")
async def send_message_stream(
    session_id: str,
    req: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventSourceResponse:
    """Execute PEVN agent pipeline and stream real-time reasoning timeline via SSE."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise NotFoundError(f"Chat session '{session_id}' not found")

    # Record user message in DB
    user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    user_msg = ChatMessage(
        id=user_msg_id,
        session_id=session_id,
        role="user",
        content=req.content,
    )
    db.add(user_msg)
    db.commit()

    trace_id = f"trc_{uuid.uuid4().hex[:12]}"
    memory = get_or_create_memory(session_id)
    asst_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    user_id = current_user.id

    user_key = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == current_user.id, UserApiKey.status == "active")
        .first()
    )
    allow_fallback = current_user.allow_shared_fallback

    async def _sse_generator() -> AsyncGenerator[dict[str, str], None]:
        captured_narrative: dict[str, Any] = {}
        captured_ledger_entries: list[dict[str, Any]] = []
        captured_verification: dict[str, Any] = {}

        async for event in _AGENT_ENGINE.run(
            question=req.content,
            session_id=session_id,
            user_id=user_id,
            trace_id=trace_id,
            memory=memory,
            user_key=user_key,
            allow_shared_fallback=allow_fallback,
        ):
            if event.event_type == "final":
                captured_narrative = event.payload
            if event.event_type == "step_result":
                captured_ledger_entries.append(event.payload)
            if event.event_type == "verify":
                captured_verification = event.payload

            # Yield SSE frame
            yield {
                "event": event.event_type,
                "data": event.model_dump_json(),
            }

        # Persist assistant turn and Evidence Ledger in DB
        try:
            content_text = captured_narrative.get("direct_answer", "Analysis completed.")
            confidence = captured_narrative.get("confidence", "High")
            ledger_dict = {"entries": captured_ledger_entries, "verification": captured_verification}

            asst_msg = ChatMessage(
                id=asst_msg_id,
                session_id=session_id,
                role="assistant",
                content=content_text,
                evidence_ledger=ledger_dict,
                confidence=confidence,
            )
            db.add(asst_msg)
            db.commit()
        except Exception:
            db.rollback()

    return EventSourceResponse(_sse_generator())


@router.get("/messages/{message_id}/evidence", response_model=EvidenceLedgerResponse)
async def get_message_evidence(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvidenceLedgerResponse:
    """Retrieve full Evidence Ledger entries and cross-check results for a specific message."""
    msg = (
        db.query(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .filter(ChatMessage.id == message_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not msg:
        raise NotFoundError(f"Message '{message_id}' not found or inaccessible")

    ledger_data = msg.evidence_ledger or {}
    steps = ledger_data.get("entries", [])

    return EvidenceLedgerResponse(
        message_id=message_id,
        steps=steps,
        verified=msg.confidence in {"High", "Medium"} and bool(ledger_data.get("verification")),
        confidence=msg.confidence or "High",
    )
