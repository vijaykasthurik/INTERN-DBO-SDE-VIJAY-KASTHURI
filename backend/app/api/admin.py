"""Administrative and operational management endpoints for Lumen."""

import os
import shutil
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlglot
from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import desc, func, inspect, text
from sqlalchemy.orm import Session
from sqlglot import exp

from app.config import get_settings
from app.core.errors import (
    AuthenticationError,
    LumenException,
    NotFoundError,
    PermissionDeniedError,
    SecurityViolationError,
    ValidationError,
)
from app.core.security import create_admin_access_token, verify_password, verify_totp
from app.db.models import (
    AdminAuditLog,
    CacheEntry,
    ChatSession,
    ContactMessage,
    Dataset,
    ExecutionTrace,
    LoginEvent,
    SystemSetting,
    User,
)
from app.db.session import engine, get_db
from app.deps import get_current_admin
from app.llm.router import LLMRouter

router = APIRouter(prefix="/admin", tags=["admin"])
_llm_router = LLMRouter()

# Rate limiting for administrative authentication (5 failed attempts per 15 min per IP)
_admin_failed_attempts: dict[str, list[float]] = defaultdict(list)
LOCKOUT_WINDOW_SECONDS = 900  # 15 minutes
MAX_FAILED_ATTEMPTS = 5


def _check_ip_lockout(ip: str) -> None:
    now = time.time()
    attempts = [t for t in _admin_failed_attempts[ip] if now - t < LOCKOUT_WINDOW_SECONDS]
    _admin_failed_attempts[ip] = attempts
    if len(attempts) >= MAX_FAILED_ATTEMPTS:
        raise LumenException(
            message="Too many failed administrative login attempts. IP address is locked for 15 minutes.",
            code="ADMIN_LOCKED_OUT",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


def _record_failed_attempt(ip: str) -> None:
    _admin_failed_attempts[ip].append(time.time())


def _clear_failed_attempts(ip: str) -> None:
    if ip in _admin_failed_attempts:
        del _admin_failed_attempts[ip]


def validate_admin_select_query(sql: str) -> None:
    """Enforce strict read-only single-statement SELECT constraints on admin queries."""
    if not sql or not sql.strip():
        raise ValidationError("Query string cannot be empty.")

    try:
        parsed = sqlglot.parse(sql.strip())
    except Exception as exc:
        raise SecurityViolationError(f"SQL parsing error: {exc}")

    if not parsed or len(parsed) != 1:
        raise SecurityViolationError("Only a single SQL statement is allowed.")

    stmt = parsed[0]
    if stmt is None or not isinstance(stmt, exp.Select):
        raise SecurityViolationError("Only SELECT queries are permitted in the admin console.")

    forbidden_types = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Alter,
        exp.Command,
        exp.Create,
    )
    for node in stmt.walk():
        if isinstance(node, forbidden_types):
            raise SecurityViolationError(f"Prohibited SQL expression detected: {type(node).__name__}")


# =====================================================================
# Request / Response Models
# =====================================================================


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin: dict[str, Any]


class UserStatusUpdateRequest(BaseModel):
    is_active: bool


class SqlQueryRequest(BaseModel):
    query: str = Field(..., max_length=5000)


class DatabaseMaintenanceRequest(BaseModel):
    action: str = Field(..., pattern="^(vacuum|purge_traces|clear_cache)$")
    days: int | None = 30


class SettingUpdateRequest(BaseModel):
    key: str
    value: dict[str, Any]
    description: str | None = None


# =====================================================================
# Public Diagnostics & Auth
# =====================================================================


@router.get("/system-info")
async def get_system_info() -> dict[str, Any]:
    """Retrieve runtime environment diagnostics."""
    settings = get_settings()
    return {
        "app_env": settings.app_env,
        "llm_provider": settings.llm_provider,
        "cache_ttl": settings.cache_ttl_seconds,
        "max_upload_mb": settings.max_upload_mb,
    }


@router.get("/providers/status")
async def get_providers_status() -> dict[str, Any]:
    """Retrieve health and circuit breaker status across all configured LLM providers."""
    return _llm_router.get_provider_status()


@router.post("/login", response_model=AdminTokenResponse)
async def admin_login(
    req: AdminLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AdminTokenResponse:
    """Authenticate administrator with password, optional TOTP, and lockout tracking."""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    _check_ip_lockout(client_ip)

    email = req.email.strip().lower()
    admin = db.query(User).filter(User.email == email).first()

    # Rejection criteria
    if not admin or admin.role != "admin" or not admin.is_active:
        _record_failed_attempt(client_ip)
        db.add(
            LoginEvent(
                email=email,
                role="admin",
                success=False,
                ip_address=client_ip,
                user_agent=user_agent[:255],
                failure_reason="Invalid credentials or unauthorized role",
            )
        )
        db.commit()
        raise AuthenticationError("Invalid administrative credentials")

    if not verify_password(req.password, admin.hashed_password):
        _record_failed_attempt(client_ip)
        db.add(
            LoginEvent(
                user_id=admin.id,
                email=email,
                role="admin",
                success=False,
                ip_address=client_ip,
                user_agent=user_agent[:255],
                failure_reason="Invalid password",
            )
        )
        db.commit()
        raise AuthenticationError("Invalid administrative credentials")

    settings = get_settings()
    if settings.admin_totp_secret and settings.admin_totp_secret.strip():
        if not req.totp_code or not verify_totp(req.totp_code, settings.admin_totp_secret):
            _record_failed_attempt(client_ip)
            db.add(
                LoginEvent(
                    user_id=admin.id,
                    email=email,
                    role="admin",
                    success=False,
                    ip_address=client_ip,
                    user_agent=user_agent[:255],
                    failure_reason="Invalid TOTP authentication code",
                )
            )
            db.commit()
            raise AuthenticationError("Invalid or missing TOTP two-factor authentication code")

    # Success
    _clear_failed_attempts(client_ip)
    admin.last_login_at = datetime.now(UTC)
    admin.login_count += 1

    token = create_admin_access_token(
        {
            "sub": str(admin.id),
            "email": admin.email,
            "role": "admin",
            "ver": admin.token_version,
        }
    )

    db.add(
        LoginEvent(
            user_id=admin.id,
            email=admin.email,
            role="admin",
            success=True,
            ip_address=client_ip,
            user_agent=user_agent[:255],
        )
    )
    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            admin_email=admin.email,
            action="admin.login",
            ip_address=client_ip,
            details={"status": "authenticated"},
        )
    )
    db.commit()

    return AdminTokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.admin_jwt_expire_minutes * 60,
        admin={"id": admin.id, "email": admin.email, "role": admin.role},
    )


# =====================================================================
# Tab 1: System Dashboard
# =====================================================================


@router.get("/dashboard")
async def get_admin_dashboard(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Provide real operational aggregate metrics, provider health, and login telemetry."""
    now = datetime.now(UTC)
    d1 = now - timedelta(days=1)
    d7 = now - timedelta(days=7)
    d30 = now - timedelta(days=30)

    # Active users
    active_24h = db.query(func.count(User.id)).filter(User.last_seen_at >= d1).scalar() or 0
    active_7d = db.query(func.count(User.id)).filter(User.last_seen_at >= d7).scalar() or 0
    active_30d = db.query(func.count(User.id)).filter(User.last_seen_at >= d30).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0

    # Datasets
    total_datasets = db.query(func.count(Dataset.id)).scalar() or 0

    # Traces & Queries
    total_queries = db.query(func.count(ExecutionTrace.id)).scalar() or 0
    total_tokens = db.query(func.sum(ExecutionTrace.total_tokens)).scalar() or 0
    total_cost = float(db.query(func.sum(ExecutionTrace.cost_usd)).scalar() or 0.0)

    # Cache hit rate
    cache_hits = db.query(func.count(ExecutionTrace.id)).filter(ExecutionTrace.cache_hit.is_(True)).scalar() or 0
    cache_hit_rate = round((cache_hits / total_queries * 100.0) if total_queries > 0 else 0.0, 1)

    # LLM provider health grid
    provider_status = _llm_router.get_provider_status()

    # Recent logins (last 50)
    recent_logins = (
        db.query(LoginEvent)
        .order_by(LoginEvent.created_at.desc())
        .limit(50)
        .all()
    )
    logins_list = [
        {
            "id": evt.id,
            "email": evt.email,
            "role": evt.role,
            "success": evt.success,
            "ip_address": evt.ip_address,
            "failure_reason": evt.failure_reason,
            "created_at": evt.created_at.isoformat() if evt.created_at else None,
        }
        for evt in recent_logins
    ]

    # Daily queries over last 30 days
    traces_30d = (
        db.query(ExecutionTrace)
        .filter(ExecutionTrace.created_at >= d30)
        .all()
    )
    daily_map: dict[str, int] = defaultdict(int)
    provider_tokens_map: dict[str, int] = defaultdict(int)
    for tr in traces_30d:
        dt_str = tr.created_at.strftime("%Y-%m-%d") if tr.created_at else "unknown"
        daily_map[dt_str] += 1
        provider_tokens_map[tr.provider] += tr.total_tokens

    # Sort daily queries chronologically
    sorted_dates = sorted(daily_map.keys())
    daily_queries = [{"date": dt, "count": daily_map[dt]} for dt in sorted_dates]
    token_by_provider = [{"provider": p, "tokens": t} for p, t in provider_tokens_map.items()]

    return {
        "metrics": {
            "total_users": total_users,
            "active_users_24h": active_24h,
            "active_users_7d": active_7d,
            "active_users_30d": active_30d,
            "total_datasets": total_datasets,
            "total_queries": total_queries,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "cache_hit_rate": cache_hit_rate,
        },
        "providers": provider_status,
        "recent_logins": logins_list,
        "charts": {
            "daily_queries": daily_queries,
            "tokens_by_provider": token_by_provider,
        },
    }


# =====================================================================
# Tab 2: User Management
# =====================================================================


@router.get("/users")
async def list_users(
    search: str = Query("", description="Search by email"),
    role: str = Query("", description="Filter by user or admin"),
    active: bool | None = Query(None, description="Filter active status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve filterable, paginated user list with resource utilization metrics."""
    q = db.query(User)

    if search.strip():
        term = f"%{search.strip().lower()}%"
        q = q.filter(User.email.ilike(term))

    if role.strip():
        q = q.filter(User.role == role.strip())

    if active is not None:
        q = q.filter(User.is_active.is_(active))

    total = q.count()

    sort_attr = getattr(User, sort_by, User.created_at)
    q = q.order_by(sort_attr.desc() if order.lower() == "desc" else sort_attr.asc())
    users = q.offset((page - 1) * per_page).limit(per_page).all()

    items = []
    settings = get_settings()
    for u in users:
        ds_count = db.query(func.count(Dataset.id)).filter(Dataset.user_id == u.id).scalar() or 0
        q_count = db.query(func.count(ExecutionTrace.id)).filter(ExecutionTrace.user_id == u.id).scalar() or 0

        # Estimate DuckDB storage
        user_duckdb = os.path.join(settings.data_dir, f"duckdb_tenant_{u.id}.duckdb")
        storage_bytes = os.path.getsize(user_duckdb) if os.path.exists(user_duckdb) else 0

        items.append(
            {
                "id": u.id,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "token_version": u.token_version,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None,
                "login_count": u.login_count,
                "datasets_count": ds_count,
                "queries_count": q_count,
                "storage_bytes": storage_bytes,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/users/{user_id}/details")
async def get_user_details(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve full detail profile of a user including datasets and session activity."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found.")

    datasets = db.query(Dataset).filter(Dataset.user_id == user_id).all()
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at.desc())
        .limit(10)
        .all()
    )

    traces = (
        db.query(ExecutionTrace)
        .filter(ExecutionTrace.user_id == user_id)
        .order_by(ExecutionTrace.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "token_version": user.token_version,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
        },
        "datasets": [
            {
                "id": d.id,
                "name": d.name,
                "row_count": d.row_count,
                "column_count": d.column_count,
                "quality_score": d.quality_score,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in datasets
        ],
        "recent_sessions": [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sessions
        ],
        "recent_traces": [
            {
                "id": t.id,
                "lane": t.lane,
                "provider": t.provider,
                "duration_ms": t.duration_ms,
                "total_tokens": t.total_tokens,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in traces
        ],
    }


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    req: UserStatusUpdateRequest,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Enable or disable user account. Disabling immediately revokes existing JWTs."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found.")

    if user.id == admin.id and not req.is_active:
        raise ValidationError("Administrators cannot disable their own account.")

    old_status = user.is_active
    user.is_active = req.is_active
    if not req.is_active:
        user.token_version += 1  # Invalidate sessions immediately

    client_ip = request.client.host if request.client else "unknown"
    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            admin_email=admin.email,
            action="user.status_update",
            target_type="user",
            target_id=str(user.id),
            details={"old_status": old_status, "new_status": req.is_active},
            ip_address=client_ip,
        )
    )
    db.commit()
    return {"id": user.id, "email": user.email, "is_active": user.is_active}


@router.post("/users/{user_id}/logout")
async def force_user_logout(
    user_id: int,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Force session invalidation by incrementing token_version."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found.")

    user.token_version += 1
    client_ip = request.client.host if request.client else "unknown"
    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            admin_email=admin.email,
            action="user.force_logout",
            target_type="user",
            target_id=str(user.id),
            details={"new_token_version": user.token_version},
            ip_address=client_ip,
        )
    )
    db.commit()
    return {"id": user.id, "message": "User session revoked successfully."}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Permanently delete user and cascade across database records and disk storage."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User not found.")

    if user.id == admin.id:
        raise ValidationError("Administrators cannot delete their own account.")

    user_email = user.email
    settings = get_settings()

    # Clean up local DuckDB database file
    user_duckdb = os.path.join(settings.data_dir, f"duckdb_tenant_{user_id}.duckdb")
    if os.path.exists(user_duckdb):
        try:
            os.remove(user_duckdb)
        except OSError:
            pass

    # Clean up upload directory for tenant
    tenant_upload_dir = os.path.join(settings.data_dir, f"tenant_{user_id}")
    if os.path.exists(tenant_upload_dir):
        shutil.rmtree(tenant_upload_dir, ignore_errors=True)

    client_ip = request.client.host if request.client else "unknown"
    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            admin_email=admin.email,
            action="user.delete",
            target_type="user",
            target_id=str(user_id),
            details={"email": user_email},
            ip_address=client_ip,
        )
    )

    db.delete(user)
    db.commit()
    return {"message": f"User {user_email} and all associated data deleted successfully."}


# =====================================================================
# Tab 3: Database & SQL Console
# =====================================================================


@router.get("/database/tables")
async def list_database_tables(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List metadata database tables with row counts and schema information."""
    inspector = inspect(db.get_bind())
    table_names = inspector.get_table_names()

    tables = []
    for name in sorted(table_names):
        try:
            count = db.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar() or 0
        except Exception:
            count = 0
        columns = [
            {"name": col["name"], "type": str(col["type"])}
            for col in inspector.get_columns(name)
        ]
        tables.append({"name": name, "row_count": count, "columns": columns})

    return {"tables": tables}


@router.get("/database/browse/{table_name}")
async def browse_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    sort_by: str | None = None,
    order: str = Query("asc"),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve paginated rows for a metadata table with sensitive columns masked."""
    inspector = inspect(db.get_bind())
    if table_name not in inspector.get_table_names():
        raise NotFoundError(f"Table '{table_name}' does not exist.")

    columns = [col["name"] for col in inspector.get_columns(table_name)]

    # Validate sort_by
    if sort_by and sort_by not in columns:
        sort_by = None

    order_clause = ""
    if sort_by:
        dir_str = "DESC" if order.lower() == "desc" else "ASC"
        order_clause = f'ORDER BY "{sort_by}" {dir_str}'

    total = db.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar() or 0
    offset = (page - 1) * per_page
    query = text(f'SELECT * FROM "{table_name}" {order_clause} LIMIT :limit OFFSET :offset')
    rows = db.execute(query, {"limit": per_page, "offset": offset}).mappings().all()

    # Mask sensitive credentials
    sensitive_cols = {"hashed_password", "ciphertext"}
    result_rows = []
    for row in rows:
        row_dict = dict(row)
        for c in sensitive_cols:
            if c in row_dict and row_dict[c] is not None:
                row_dict[c] = "***"
        result_rows.append(row_dict)

    return {
        "table": table_name,
        "columns": columns,
        "rows": result_rows,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.post("/database/reveal-secret")
async def reveal_secret(
    table_name: str = Query(...),
    row_id: int = Query(...),
    column_name: str = Query(...),
    request: Request = None,  # type: ignore
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Audit and reveal a sensitive masked credential for administrative inspection."""
    if column_name not in ("hashed_password", "ciphertext"):
        raise ValidationError("Column is not a masked secret.")

    inspector = inspect(db.get_bind())
    if table_name not in inspector.get_table_names():
        raise NotFoundError("Table does not exist.")

    query = text(f'SELECT "{column_name}" FROM "{table_name}" WHERE id = :id')
    val = db.execute(query, {"id": row_id}).scalar()
    if val is None:
        raise NotFoundError("Record or column value not found.")

    client_ip = request.client.host if request and request.client else "unknown"
    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            admin_email=admin.email,
            action="secret.revealed",
            target_type=table_name,
            target_id=str(row_id),
            details={"column": column_name},
            ip_address=client_ip,
        )
    )
    db.commit()
    return {"value": str(val)}


@router.post("/database/query")
async def run_sql_query(
    req: SqlQueryRequest,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Execute a single-statement read-only SELECT query with safety enforcement and timeout."""
    validate_admin_select_query(req.query)

    # Wrap query with row limit to enforce max 500 rows returned
    wrapped_sql = f"SELECT * FROM ({req.query.strip().rstrip(';')}) AS __admin_q LIMIT 500"

    start_time = time.perf_counter()
    try:
        res = db.execute(text(wrapped_sql))
        columns = list(res.keys())
        rows_raw = res.fetchall()
    except Exception as exc:
        raise ValidationError(f"Query execution failed: {exc}") from exc

    duration_ms = (time.perf_counter() - start_time) * 1000.0

    # Mask sensitive credentials in query result
    sensitive_cols = {"hashed_password", "ciphertext"}
    result_rows = []
    for r in rows_raw:
        row_dict = dict(zip(columns, r, strict=False))
        for col in sensitive_cols:
            if col in row_dict and row_dict[col] is not None:
                row_dict[col] = "***"
        result_rows.append(row_dict)

    client_ip = request.client.host if request.client else "unknown"
    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            admin_email=admin.email,
            action="sql.query",
            details={
                "query": req.query[:500],
                "row_count": len(result_rows),
                "duration_ms": round(duration_ms, 2),
            },
            ip_address=client_ip,
        )
    )
    db.commit()

    return {
        "columns": columns,
        "rows": result_rows,
        "row_count": len(result_rows),
        "duration_ms": round(duration_ms, 2),
    }


@router.post("/database/maintenance")
async def run_maintenance(
    req: DatabaseMaintenanceRequest,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Perform database vacuum, trace pruning, or cache clearing."""
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    details: dict[str, Any] = {"action": req.action}

    if req.action == "vacuum":
        is_postgres = "postgres" in settings.normalized_database_url
        with db.get_bind().connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            if is_postgres:
                conn.execute(text("VACUUM ANALYZE"))
            else:
                conn.execute(text("VACUUM"))
        details["result"] = "Database vacuum and analyze completed successfully."

    elif req.action == "purge_traces":
        cutoff = datetime.now(UTC) - timedelta(days=req.days or 30)
        deleted = db.query(ExecutionTrace).filter(ExecutionTrace.created_at < cutoff).delete()
        db.commit()
        details["deleted_count"] = deleted

    elif req.action == "clear_cache":
        deleted = db.query(CacheEntry).delete()
        db.commit()
        details["deleted_count"] = deleted

    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            admin_email=admin.email,
            action=f"maintenance.{req.action}",
            details=details,
            ip_address=client_ip,
        )
    )
    db.commit()
    return details


# =====================================================================
# Tab 4: Operations & Configuration
# =====================================================================


@router.get("/operations/settings")
async def get_system_settings(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve operational feature flags, limits, and runtime configuration."""
    settings = get_settings()

    # Default settings dictionary
    defaults = {
        "allow_registration": {"enabled": True, "description": "Allow public user registration"},
        "allow_shared_fallback": {"enabled": True, "description": "Enable smart fallback to shared server models"},
        "maintenance_mode": {"enabled": False, "description": "Show maintenance advisory banner to regular users"},
        "max_upload_mb": {"value": settings.max_upload_mb, "description": "Global file upload size limit in MB"},
    }

    # Fetch stored dynamic settings
    db_settings = {s.key: s.value for s in db.query(SystemSetting).all()}
    merged = {**defaults, **db_settings}

    # Config overview (secrets redacted)
    config_overview = {
        "app_env": settings.app_env,
        "app_name": settings.app_name,
        "log_level": settings.log_level,
        "database_engine": "postgresql" if "postgres" in settings.normalized_database_url else "sqlite",
        "llm_provider": settings.llm_provider,
        "llm_fallback_order": settings.fallback_providers_list,
        "groq_pool_size": len(settings.groq_keys_pool),
        "shared_pool_hourly_limit": settings.shared_pool_hourly_limit,
    }

    return {"settings": merged, "config": config_overview}


@router.patch("/operations/settings")
async def update_system_setting(
    req: SettingUpdateRequest,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Update or upsert dynamic operational configuration settings."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == req.key).first()
    if setting:
        setting.value = req.value
        if req.description:
            setting.description = req.description
    else:
        setting = SystemSetting(key=req.key, value=req.value, description=req.description)
        db.add(setting)

    client_ip = request.client.host if request.client else "unknown"
    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            admin_email=admin.email,
            action="setting.update",
            target_type="system_setting",
            target_id=req.key,
            details={"value": req.value},
            ip_address=client_ip,
        )
    )
    db.commit()
    return {"key": setting.key, "value": setting.value}


@router.get("/operations/contact-messages")
async def list_contact_messages(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """List visitor contact submissions."""
    total = db.query(func.count(ContactMessage.id)).scalar() or 0
    msgs = (
        db.query(ContactMessage)
        .order_by(ContactMessage.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    items = [
        {
            "id": m.id,
            "name": m.name,
            "email": m.email,
            "message": m.message,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msgs
    ]
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.delete("/operations/contact-messages/{msg_id}")
async def delete_contact_message(
    msg_id: int,
    request: Request,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete a contact message."""
    msg = db.query(ContactMessage).filter(ContactMessage.id == msg_id).first()
    if not msg:
        raise NotFoundError("Message not found.")

    db.delete(msg)
    client_ip = request.client.host if request.client else "unknown"
    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            admin_email=admin.email,
            action="contact_message.delete",
            target_type="contact_message",
            target_id=str(msg_id),
            ip_address=client_ip,
        )
    )
    db.commit()
    return {"message": "Message deleted."}


# =====================================================================
# Tab 5: Audit Log
# =====================================================================


@router.get("/audit-logs")
async def list_audit_logs(
    action: str = Query("", description="Filter by action keyword"),
    admin_email: str = Query("", description="Filter by admin email"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve filterable audit trail of administrative actions."""
    q = db.query(AdminAuditLog)

    if action.strip():
        q = q.filter(AdminAuditLog.action.ilike(f"%{action.strip()}%"))

    if admin_email.strip():
        q = q.filter(AdminAuditLog.admin_email.ilike(f"%{admin_email.strip()}%"))

    total = q.count()
    logs = (
        q.order_by(AdminAuditLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items = [
        {
            "id": l.id,
            "admin_user_id": l.admin_user_id,
            "admin_email": l.admin_email,
            "action": l.action,
            "target_type": l.target_type,
            "target_id": l.target_id,
            "details": l.details,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]

    return {"items": items, "total": total, "page": page, "per_page": per_page}
