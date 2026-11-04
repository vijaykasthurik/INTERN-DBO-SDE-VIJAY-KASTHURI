"""SQLAlchemy 2 database models for Lumen.

Manages User, Dataset, DatasetColumn, ChatSession, ChatMessage,
CacheEntry, ExecutionTrace, and MetricDefinition with strict tenant isolation.
"""

from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base declarative class for all metadata models."""

    pass


class User(Base):
    """User account entity for tenant boundary enforcement."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    datasets: Mapped[list["Dataset"]] = relationship(
        "Dataset", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )
    metrics: Mapped[list["MetricDefinition"]] = relationship(
        "MetricDefinition", back_populates="user", cascade="all, delete-orphan"
    )


class Dataset(Base):
    """Uploaded tabular dataset metadata and catalog reference."""

    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    duckdb_table_name: Mapped[str] = mapped_column(String(128), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    column_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    quality_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="datasets")
    columns: Mapped[list["DatasetColumn"]] = relationship(
        "DatasetColumn", back_populates="dataset", cascade="all, delete-orphan"
    )
    metrics: Mapped[list["MetricDefinition"]] = relationship(
        "MetricDefinition", back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetColumn(Base):
    """Column schema, profile statistics, and semantic annotations."""

    __tablename__ = "dataset_columns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sanitized_name: Mapped[str] = mapped_column(String(128), nullable=False)
    data_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_stats: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="columns")


class ChatSession(Base):
    """Conversation session grouping turns and memory."""

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), default="New Analysis", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    """Individual conversational turn with Evidence Ledger reference."""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ledger: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")


class CacheEntry(Base):
    """Verified-answer cache entry keyed by question and schema hash."""

    __tablename__ = "cache_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    schema_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="High", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExecutionTrace(Base):
    """Observability trace per question execution."""

    __tablename__ = "execution_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    lane: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verifier_confidence: Mapped[str] = mapped_column(String(32), default="High", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MetricDefinition(Base):
    """User-defined or system-inferred business metric calculation."""

    __tablename__ = "metric_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    dataset_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    expression: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # e.g. SUM(quantity * unit_price * (1 - discount))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="metrics")
    dataset: Mapped[Optional["Dataset"]] = relationship("Dataset", back_populates="metrics")


# Compound Indexes for tenant lookup performance
Index("ix_dataset_user_name", Dataset.user_id, Dataset.name, unique=True)
Index("ix_metric_user_name", MetricDefinition.user_id, MetricDefinition.name, unique=True)
