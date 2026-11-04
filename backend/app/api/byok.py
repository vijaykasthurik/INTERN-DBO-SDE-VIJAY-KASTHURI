"""BYOK (Bring Your Own Key) and AI Connection Management Endpoints."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_api_key, encrypt_api_key, mask_key_hint
from app.db.models import User, UserApiKey
from app.db.session import get_db
from app.deps import get_current_user
from app.llm.catalog import get_provider_catalog
from app.llm.pool import get_user_shared_quota_remaining
from app.llm.router import LLMRouter
from app.llm.validator import validate_user_api_key

router = APIRouter(tags=["byok"])
_router_instance = LLMRouter()


class ValidateKeyRequest(BaseModel):
    provider_id: str
    api_key: str
    base_url: str | None = None
    custom_model: str | None = None


class StoreKeyRequest(BaseModel):
    provider_id: str
    api_key: str
    label: str | None = "Primary Key"
    base_url: str | None = None
    model_fast: str | None = None
    model_strong: str | None = None
    allow_shared_fallback: bool = True


class UpdateConnectionRequest(BaseModel):
    label: str | None = None
    model_fast: str | None = None
    model_strong: str | None = None
    allow_shared_fallback: bool | None = None


class AIConnectionResponse(BaseModel):
    connected: bool
    provider_id: str | None = None
    label: str | None = None
    key_hint: str | None = None
    status: str = "unconnected"
    model_fast: str | None = None
    model_strong: str | None = None
    capabilities: dict[str, Any] | None = None
    allow_shared_fallback: bool = True
    shared_quota_remaining: int = 30
    request_count: int = 0
    token_count: int = 0
    last_verified_at: str | None = None
    last_used_at: str | None = None


@router.get("/llm/providers")
async def list_providers_catalog() -> list[dict[str, Any]]:
    """Return public declarative provider catalog for the UI."""
    return get_provider_catalog()


@router.get("/llm/shared-status")
async def get_shared_chain_status() -> dict[str, Any]:
    """Return health of the shared server key pool and fallback providers (zero secrets)."""
    return _router_instance.get_shared_status()


@router.post("/me/ai-connection/validate")
async def validate_connection(
    req: ValidateKeyRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate submitted credentials against the provider without storing."""
    res = await validate_user_api_key(
        provider_id=req.provider_id,
        api_key=req.api_key,
        base_url=req.base_url,
        custom_model=req.custom_model,
        user_id=current_user.id,
    )
    return res.to_dict()


@router.put("/me/ai-connection", response_model=AIConnectionResponse)
async def store_or_replace_connection(
    req: StoreKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIConnectionResponse:
    """Validate submitted key, encrypt with AES-256-GCM, and persist for authenticated user."""
    # 1. Validate
    val_res = await validate_user_api_key(
        provider_id=req.provider_id,
        api_key=req.api_key,
        base_url=req.base_url,
        user_id=current_user.id,
    )
    if not val_res.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection validation failed: {val_res.message}",
        )

    # 2. Encrypt
    encrypted_ct = encrypt_api_key(req.api_key)
    hint = mask_key_hint(req.api_key)
    fast_model = req.model_fast or val_res.model_fast or "default"
    strong_model = req.model_strong or val_res.model_strong or "default"

    # 3. Update User fallback preference
    current_user.allow_shared_fallback = req.allow_shared_fallback

    # 4. Upsert single active connection
    existing = db.query(UserApiKey).filter(UserApiKey.user_id == current_user.id).first()
    now_utc = datetime.now(UTC)

    if existing:
        existing.provider_id = req.provider_id
        existing.label = req.label or "Primary Key"
        existing.ciphertext = encrypted_ct
        existing.key_hint = hint
        existing.base_url = req.base_url
        existing.model_fast = fast_model
        existing.model_strong = strong_model
        existing.capabilities = val_res.capabilities
        existing.status = "active"
        existing.last_verified_at = now_utc
        existing.last_error_code = None
        key_record = existing
    else:
        key_record = UserApiKey(
            user_id=current_user.id,
            provider_id=req.provider_id,
            label=req.label or "Primary Key",
            ciphertext=encrypted_ct,
            key_id="v1",
            key_hint=hint,
            base_url=req.base_url,
            model_fast=fast_model,
            model_strong=strong_model,
            capabilities=val_res.capabilities,
            status="active",
            last_verified_at=now_utc,
        )
        db.add(key_record)

    db.commit()
    db.refresh(key_record)

    remaining_quota = get_user_shared_quota_remaining(current_user.id)
    return AIConnectionResponse(
        connected=True,
        provider_id=key_record.provider_id,
        label=key_record.label,
        key_hint=key_record.key_hint,
        status=key_record.status,
        model_fast=key_record.model_fast,
        model_strong=key_record.model_strong,
        capabilities=key_record.capabilities,
        allow_shared_fallback=current_user.allow_shared_fallback,
        shared_quota_remaining=remaining_quota,
        request_count=key_record.request_count,
        token_count=key_record.token_count,
        last_verified_at=key_record.last_verified_at.isoformat() if key_record.last_verified_at else None,
        last_used_at=key_record.last_used_at.isoformat() if key_record.last_used_at else None,
    )


@router.get("/me/ai-connection", response_model=AIConnectionResponse)
async def get_connection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIConnectionResponse:
    """Retrieve masked connection state and usage metrics for the active user."""
    key_record = db.query(UserApiKey).filter(UserApiKey.user_id == current_user.id).first()
    remaining_quota = get_user_shared_quota_remaining(current_user.id)

    if not key_record:
        return AIConnectionResponse(
            connected=False,
            status="unconnected",
            allow_shared_fallback=current_user.allow_shared_fallback,
            shared_quota_remaining=remaining_quota,
        )

    return AIConnectionResponse(
        connected=True,
        provider_id=key_record.provider_id,
        label=key_record.label,
        key_hint=key_record.key_hint,
        status=key_record.status,
        model_fast=key_record.model_fast,
        model_strong=key_record.model_strong,
        capabilities=key_record.capabilities,
        allow_shared_fallback=current_user.allow_shared_fallback,
        shared_quota_remaining=remaining_quota,
        request_count=key_record.request_count,
        token_count=key_record.token_count,
        last_verified_at=key_record.last_verified_at.isoformat() if key_record.last_verified_at else None,
        last_used_at=key_record.last_used_at.isoformat() if key_record.last_used_at else None,
    )


@router.post("/me/ai-connection/test")
async def test_stored_connection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Re-test the stored encrypted key against its provider endpoint."""
    key_record = db.query(UserApiKey).filter(UserApiKey.user_id == current_user.id).first()
    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AI connection registered for current user.",
        )

    plaintext = decrypt_api_key(key_record.ciphertext)
    val_res = await validate_user_api_key(
        provider_id=key_record.provider_id,
        api_key=plaintext,
        base_url=key_record.base_url,
        user_id=current_user.id,
    )

    key_record.status = "active" if val_res.valid else val_res.status
    key_record.last_verified_at = datetime.now(UTC)
    if not val_res.valid:
        key_record.last_error_code = val_res.message[:60]
    db.commit()

    return val_res.to_dict()


@router.patch("/me/ai-connection", response_model=AIConnectionResponse)
async def update_connection_settings(
    req: UpdateConnectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIConnectionResponse:
    """Update model selections, label, or fallback toggle."""
    key_record = db.query(UserApiKey).filter(UserApiKey.user_id == current_user.id).first()
    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AI connection registered.",
        )

    if req.label:
        key_record.label = req.label
    if req.model_fast:
        key_record.model_fast = req.model_fast
    if req.model_strong:
        key_record.model_strong = req.model_strong
    if req.allow_shared_fallback is not None:
        current_user.allow_shared_fallback = req.allow_shared_fallback

    db.commit()
    db.refresh(key_record)

    remaining_quota = get_user_shared_quota_remaining(current_user.id)
    return AIConnectionResponse(
        connected=True,
        provider_id=key_record.provider_id,
        label=key_record.label,
        key_hint=key_record.key_hint,
        status=key_record.status,
        model_fast=key_record.model_fast,
        model_strong=key_record.model_strong,
        capabilities=key_record.capabilities,
        allow_shared_fallback=current_user.allow_shared_fallback,
        shared_quota_remaining=remaining_quota,
        request_count=key_record.request_count,
        token_count=key_record.token_count,
        last_verified_at=key_record.last_verified_at.isoformat() if key_record.last_verified_at else None,
        last_used_at=key_record.last_used_at.isoformat() if key_record.last_used_at else None,
    )


@router.delete("/me/ai-connection", status_code=status.HTTP_204_NO_CONTENT)
async def remove_connection(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Hard-delete encrypted user credentials from the database."""
    db.query(UserApiKey).filter(UserApiKey.user_id == current_user.id).delete()
    db.commit()
    return None
