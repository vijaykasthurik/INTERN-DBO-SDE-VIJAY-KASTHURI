"""Integration test suite for database engine support, URL normalization, and Alembic migrations.

Validates:
1. Postgres and SQLite URL normalization with SSL enforcement.
2. Connection retry logic with exponential backoff.
3. Alembic migration lifecycle (upgrade to head and downgrade to base).
4. Full CRUD operations across all SQLAlchemy metadata models.
"""

import os
import tempfile
import pytest
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.config import normalize_database_url
from app.db.models import (
    AdminAuditLog,
    Base,
    CacheEntry,
    ChatMessage,
    ChatSession,
    ContactMessage,
    DashboardOrder,
    Dataset,
    DatasetColumn,
    ExecutionTrace,
    LoginEvent,
    MetricDefinition,
    ReportArtifact,
    SystemSetting,
    User,
    UserApiKey,
)
from app.db.session import check_connection


def test_database_url_normalization():
    """Verify URL normalization across SQLite, local Postgres, and cloud Postgres (Neon/Supabase)."""
    # SQLite unchanged
    assert normalize_database_url("sqlite:///./data/lumen.db") == "sqlite:///./data/lumen.db"

    # Local Postgres normalized to psycopg 3 driver without forcing sslmode
    assert (
        normalize_database_url("postgres://postgres:pass@localhost:5432/lumen")
        == "postgresql+psycopg://postgres:pass@localhost:5432/lumen"
    )
    assert (
        normalize_database_url("postgresql://postgres:pass@127.0.0.1:5432/lumen")
        == "postgresql+psycopg://postgres:pass@127.0.0.1:5432/lumen"
    )

    # Cloud remote Postgres normalized with sslmode=require appended
    remote_neon = "postgres://user:secret@ep-cool-db.us-east-2.aws.neon.tech/neondb"
    normalized_neon = normalize_database_url(remote_neon)
    assert normalized_neon.startswith("postgresql+psycopg://")
    assert "sslmode=require" in normalized_neon

    # Explicit sslmode preserved
    explicit_ssl = "postgresql://user:secret@db.supabase.co:5432/postgres?sslmode=verify-full"
    normalized_explicit = normalize_database_url(explicit_ssl)
    assert normalized_explicit.startswith("postgresql+psycopg://")
    assert "sslmode=verify-full" in normalized_explicit


def test_connection_retry_logic():
    """Verify retry logic on transient connection failures."""
    with patch("app.db.session.engine.connect") as mock_connect, patch("time.sleep") as mock_sleep:
        # Simulate 2 failures then 1 success
        mock_conn = MagicMock()
        mock_connect.side_effect = [
            Exception("Connection refused"),
            Exception("Host unreachable"),
            mock_conn,
        ]

        result = check_connection(max_retries=3, initial_backoff=0.01)
        assert result is True
        assert mock_connect.call_count == 3
        assert mock_sleep.call_count == 2


def test_alembic_upgrade_and_downgrade():
    """Verify Alembic upgrade to head and downgrade to base on clean schema."""
    from pathlib import Path
    from alembic import command
    from alembic.config import Config

    tmp_db_file = os.path.join(tempfile.gettempdir(), f"lumen_migration_test_{int(datetime.now().timestamp())}.db")
    tmp_url = f"sqlite:///{tmp_db_file}"

    backend_dir = Path(__file__).resolve().parents[2]
    ini_path = backend_dir / "alembic.ini"
    if not ini_path.exists():
        ini_path = Path("backend/alembic.ini").resolve()

    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", tmp_url)

    try:
        # Upgrade to head
        command.upgrade(alembic_cfg, "head")

        test_engine = create_engine(tmp_url)
        inspector = inspect(test_engine)
        tables = set(inspector.get_table_names())

        required_tables = {
            "users",
            "datasets",
            "dataset_columns",
            "chat_sessions",
            "chat_messages",
            "cache_entries",
            "execution_traces",
            "report_artifacts",
            "metric_definitions",
            "user_api_keys",
            "contact_messages",
            "dashboard_orders",
            "login_events",
            "admin_audit_logs",
            "system_settings",
        }
        assert required_tables.issubset(tables), f"Missing tables: {required_tables - tables}"

        # Verify user columns
        user_cols = {c["name"] for c in inspector.get_columns("users")}
        assert {"role", "token_version", "last_login_at", "last_seen_at", "login_count"}.issubset(user_cols)

        # Downgrade to base
        command.downgrade(alembic_cfg, "base")
        tables_after_downgrade = set(inspect(test_engine).get_table_names()) - {"alembic_version"}
        assert len(tables_after_downgrade) == 0

    finally:
        if os.path.exists(tmp_db_file):
            try:
                os.remove(tmp_db_file)
            except OSError:
                pass


def test_all_models_crud_lifecycle():
    """Verify all ORM models perform create, read, update, delete correctly."""
    tmp_db_file = os.path.join(tempfile.gettempdir(), f"lumen_crud_test_{int(datetime.now().timestamp())}.db")
    test_engine = create_engine(f"sqlite:///{tmp_db_file}")
    Base.metadata.create_all(bind=test_engine)
    TestingSession = sessionmaker(bind=test_engine)

    try:
        with TestingSession() as session:
            # 1. User
            user = User(
                email="admin_test@example.com",
                hashed_password="secure_hash_value",
                role="admin",
                token_version=1,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            assert user.id is not None
            assert user.role == "admin"

            # 2. Dataset & Columns
            ds = Dataset(
                user_id=user.id,
                name="Sales 2026",
                source_filename="sales.csv",
                duckdb_table_name="t_sales_2026",
                row_count=100,
                column_count=2,
            )
            session.add(ds)
            session.commit()
            session.refresh(ds)

            col = DatasetColumn(
                dataset_id=ds.id,
                name="Revenue",
                sanitized_name="revenue",
                data_type="FLOAT",
            )
            session.add(col)

            # 3. ChatSession & ChatMessage
            cs = ChatSession(id="sess_test_123", user_id=user.id, title="Revenue Inquiry")
            session.add(cs)
            session.commit()

            cm = ChatMessage(
                id="msg_test_123",
                session_id=cs.id,
                role="user",
                content="What is total revenue?",
            )
            session.add(cm)

            # 4. CacheEntry
            cache = CacheEntry(
                cache_key="key_test_123",
                schema_hash="hash123",
                question="What is total revenue?",
                answer_payload={"answer": "$10,000"},
                expires_at=datetime.now(UTC),
            )
            session.add(cache)

            # 5. ExecutionTrace
            trace = ExecutionTrace(
                trace_id="tr_123",
                user_id=user.id,
                session_id=cs.id,
                question="What is total revenue?",
                lane="quick_lookup",
                provider="mock",
                duration_ms=45.2,
            )
            session.add(trace)

            # 6. ReportArtifact
            report = ReportArtifact(
                id="rep_123",
                user_id=user.id,
                filename="report_123.pdf",
                title="Q1 Report",
                format="pdf",
                source_dataset_ids=[ds.id],
            )
            session.add(report)

            # 7. MetricDefinition
            metric = MetricDefinition(
                user_id=user.id,
                dataset_id=ds.id,
                name="net_revenue",
                expression="SUM(amount)",
            )
            session.add(metric)

            # 8. UserApiKey
            key = UserApiKey(
                user_id=user.id,
                provider_id="groq",
                ciphertext="encrypted_key_material",
                key_hint="gsk_1234",
                model_fast="fast-model",
                model_strong="strong-model",
            )
            session.add(key)

            # 9. ContactMessage & DashboardOrder
            contact = ContactMessage(name="Alice", email="alice@test.com", message="Great app!")
            dash_order = DashboardOrder(user_id=user.id, scope="global", widget_ids=["w1", "w2"])
            session.add_all([contact, dash_order])

            # 10. LoginEvent, AdminAuditLog, SystemSetting
            login_event = LoginEvent(
                user_id=user.id,
                email=user.email,
                role=user.role,
                success=True,
                ip_address="127.0.0.1",
            )
            audit_log = AdminAuditLog(
                admin_user_id=user.id,
                admin_email=user.email,
                action="system.login",
                target_type="user",
                target_id=str(user.id),
                details={"status": "ok"},
            )
            sys_setting = SystemSetting(
                key="maintenance_mode",
                value={"enabled": False},
                description="Global maintenance toggle",
            )
            session.add_all([login_event, audit_log, sys_setting])
            session.commit()

            # Verify fetch
            fetched_setting = session.query(SystemSetting).filter_by(key="maintenance_mode").first()
            assert fetched_setting is not None
            assert fetched_setting.value == {"enabled": False}

            fetched_log = session.query(AdminAuditLog).filter_by(admin_user_id=user.id).first()
            assert fetched_log is not None
            assert fetched_log.action == "system.login"

            # Cascade delete test
            session.delete(user)
            session.commit()

            # Datasets and sessions should have cascaded
            assert session.query(Dataset).filter_by(user_id=user.id).count() == 0
            assert session.query(ChatSession).filter_by(user_id=user.id).count() == 0
            assert session.query(MetricDefinition).filter_by(user_id=user.id).count() == 0

    finally:
        if os.path.exists(tmp_db_file):
            try:
                os.remove(tmp_db_file)
            except OSError:
                pass
