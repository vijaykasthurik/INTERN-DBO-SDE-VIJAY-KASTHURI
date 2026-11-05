"""Initial database schema with multi-tenant tables and admin models.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-05
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('allow_shared_fallback', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('role', sa.String(length=16), nullable=False, server_default='user'),
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('login_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Postgres functional unique index for case-insensitive email
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_lower ON users (LOWER(email));"))

    # 2. datasets
    op.create_table(
        'datasets',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('source_filename', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('duckdb_table_name', sa.String(length=128), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('column_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quality_score', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('quality_summary', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_datasets_id'), 'datasets', ['id'], unique=False)
    op.create_index(op.f('ix_datasets_user_id'), 'datasets', ['user_id'], unique=False)
    op.create_index('ix_dataset_user_name', 'datasets', ['user_id', 'name'], unique=True)

    # 3. dataset_columns
    op.create_table(
        'dataset_columns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('sanitized_name', sa.String(length=128), nullable=False),
        sa.Column('data_type', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('profile_stats', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_dataset_columns_id'), 'dataset_columns', ['id'], unique=False)
    op.create_index(op.f('ix_dataset_columns_dataset_id'), 'dataset_columns', ['dataset_id'], unique=False)

    # 4. chat_sessions
    op.create_table(
        'chat_sessions',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False, server_default='New Analysis'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_sessions_id'), 'chat_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_user_id'), 'chat_sessions', ['user_id'], unique=False)

    # 5. chat_messages
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('evidence_ledger', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_messages_id'), 'chat_messages', ['id'], unique=False)
    op.create_index(op.f('ix_chat_messages_session_id'), 'chat_messages', ['session_id'], unique=False)

    # 6. cache_entries
    op.create_table(
        'cache_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('cache_key', sa.String(length=128), nullable=False),
        sa.Column('schema_hash', sa.String(length=64), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer_payload', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.String(length=32), nullable=False, server_default='High'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_cache_entries_id'), 'cache_entries', ['id'], unique=False)
    op.create_index(op.f('ix_cache_entries_cache_key'), 'cache_entries', ['cache_key'], unique=True)
    op.create_index(op.f('ix_cache_entries_schema_hash'), 'cache_entries', ['schema_hash'], unique=False)

    # 7. execution_traces
    op.create_table(
        'execution_traces',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trace_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('lane', sa.String(length=32), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('duration_ms', sa.Float(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cost_usd', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('cache_hit', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('verifier_confidence', sa.String(length=32), nullable=False, server_default='High'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_execution_traces_id'), 'execution_traces', ['id'], unique=False)
    op.create_index(op.f('ix_execution_traces_trace_id'), 'execution_traces', ['trace_id'], unique=True)
    op.create_index(op.f('ix_execution_traces_user_id'), 'execution_traces', ['user_id'], unique=False)
    op.create_index(op.f('ix_execution_traces_session_id'), 'execution_traces', ['session_id'], unique=False)

    # 8. report_artifacts
    op.create_table(
        'report_artifacts',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('format', sa.String(length=8), nullable=False),
        sa.Column('source_session_id', sa.String(length=64), nullable=True),
        sa.Column('source_dataset_ids', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('filename'),
    )
    op.create_index(op.f('ix_report_artifacts_user_id'), 'report_artifacts', ['user_id'], unique=False)

    # 9. metric_definitions
    op.create_table(
        'metric_definitions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('expression', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_metric_definitions_id'), 'metric_definitions', ['id'], unique=False)
    op.create_index(op.f('ix_metric_definitions_user_id'), 'metric_definitions', ['user_id'], unique=False)
    op.create_index(op.f('ix_metric_definitions_dataset_id'), 'metric_definitions', ['dataset_id'], unique=False)
    op.create_index('ix_metric_user_name', 'metric_definitions', ['user_id', 'name'], unique=True)

    # 10. user_api_keys
    op.create_table(
        'user_api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.String(length=64), nullable=False),
        sa.Column('label', sa.String(length=128), nullable=False, server_default='Primary Key'),
        sa.Column('ciphertext', sa.Text(), nullable=False),
        sa.Column('key_id', sa.String(length=32), nullable=False, server_default='v1'),
        sa.Column('key_hint', sa.String(length=16), nullable=False),
        sa.Column('base_url', sa.String(length=512), nullable=True),
        sa.Column('model_fast', sa.String(length=128), nullable=False),
        sa.Column('model_strong', sa.String(length=128), nullable=False),
        sa.Column('capabilities', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='active'),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error_code', sa.String(length=64), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_api_keys_id'), 'user_api_keys', ['id'], unique=False)
    op.create_index(op.f('ix_user_api_keys_user_id'), 'user_api_keys', ['user_id'], unique=False)
    op.create_index('ix_user_api_key_user_provider', 'user_api_keys', ['user_id', 'provider_id'], unique=False)

    # 11. contact_messages
    op.create_table(
        'contact_messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # 12. dashboard_orders
    op.create_table(
        'dashboard_orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('scope', sa.String(length=128), nullable=False),
        sa.Column('widget_ids', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_dashboard_orders_user_id'), 'dashboard_orders', ['user_id'], unique=False)

    # 13. login_events
    op.create_table(
        'login_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False, server_default='user'),
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('failure_reason', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_login_events_user_id'), 'login_events', ['user_id'], unique=False)
    op.create_index(op.f('ix_login_events_email'), 'login_events', ['email'], unique=False)

    # 14. admin_audit_logs
    op.create_table(
        'admin_audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('admin_user_id', sa.Integer(), nullable=True),
        sa.Column('admin_email', sa.String(length=255), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('target_type', sa.String(length=64), nullable=True),
        sa.Column('target_id', sa.String(length=64), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_admin_audit_logs_admin_user_id'), 'admin_audit_logs', ['admin_user_id'], unique=False)
    op.create_index(op.f('ix_admin_audit_logs_admin_email'), 'admin_audit_logs', ['admin_email'], unique=False)

    # 15. system_settings
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute(sa.text("DROP INDEX IF EXISTS ix_users_email_lower;"))

    op.drop_table('system_settings')
    op.drop_table('admin_audit_logs')
    op.drop_table('login_events')
    op.drop_table('dashboard_orders')
    op.drop_table('contact_messages')
    op.drop_table('user_api_keys')
    op.drop_table('metric_definitions')
    op.drop_table('report_artifacts')
    op.drop_table('execution_traces')
    op.drop_table('cache_entries')
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
    op.drop_table('dataset_columns')
    op.drop_table('datasets')
    op.drop_table('users')
