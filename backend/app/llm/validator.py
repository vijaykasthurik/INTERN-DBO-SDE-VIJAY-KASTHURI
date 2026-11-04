"""Live API key validation, outcome classification, and capability probing."""

import time
from typing import Any

import httpx

from app.core.encryption import validate_outbound_url_ssrf
from app.llm.catalog import (
    check_key_format_hint,
    get_catalog_entry,
    select_fast_and_strong_models,
)

# In-memory validation rate-limiter: user_id -> list of timestamps
_VALIDATION_ATTEMPTS: dict[int, list[float]] = {}
MAX_VALIDATIONS_PER_WINDOW = 15
WINDOW_SECONDS = 600.0  # 10 minutes


class ValidationResult:
    """Detailed result of an API key validation attempt."""

    def __init__(
        self,
        valid: bool,
        status: str,
        message: str,
        models: list[str] | None = None,
        model_fast: str | None = None,
        model_strong: str | None = None,
        capabilities: dict[str, Any] | None = None,
        advisory_hint: str | None = None,
    ) -> None:
        self.valid = valid
        self.status = status
        self.message = message
        self.models = models or []
        self.model_fast = model_fast
        self.model_strong = model_strong
        self.capabilities = capabilities or {"tools": True, "json_mode": True, "streaming": True}
        self.advisory_hint = advisory_hint

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "status": self.status,
            "message": self.message,
            "models": self.models,
            "model_fast": self.model_fast,
            "model_strong": self.model_strong,
            "capabilities": self.capabilities,
            "advisory_hint": self.advisory_hint,
        }


def check_validation_rate_limit(user_id: int) -> bool:
    """Enforce maximum validation attempts per user in sliding window."""
    now = time.time()
    history = _VALIDATION_ATTEMPTS.get(user_id, [])
    active = [t for t in history if now - t < WINDOW_SECONDS]
    if len(active) >= MAX_VALIDATIONS_PER_WINDOW:
        return False
    active.append(now)
    _VALIDATION_ATTEMPTS[user_id] = active
    return True


async def validate_user_api_key(
    provider_id: str,
    api_key: str,
    base_url: str | None = None,
    custom_model: str | None = None,
    user_id: int = 0,
) -> ValidationResult:
    """Perform cheap live probe to validate user-submitted API key."""
    # 0. Rate limit check
    if user_id and not check_validation_rate_limit(user_id):
        return ValidationResult(
            valid=False,
            status="rate_limited",
            message="Too many validation attempts. Please wait a few minutes before retrying.",
        )

    # 1. Input normalization
    clean_key = api_key.strip().strip("'\"")
    if not clean_key:
        return ValidationResult(
            valid=False,
            status="invalid_key",
            message="API Key cannot be blank.",
        )

    entry = get_catalog_entry(provider_id)
    if not entry:
        return ValidationResult(
            valid=False,
            status="provider_error",
            message=f"Unsupported provider identifier: {provider_id}",
        )

    hint = check_key_format_hint(provider_id, clean_key)

    # Determine Base URL
    effective_url = base_url.strip() if base_url and base_url.strip() else entry.base_url
    if not effective_url and provider_id == "custom":
        return ValidationResult(
            valid=False,
            status="invalid_key",
            message="Custom provider requires a valid Base URL.",
        )

    # SSRF verification on outbound URL
    try:
        validate_outbound_url_ssrf(effective_url)
    except Exception as exc:
        return ValidationResult(
            valid=False,
            status="network_blocked",
            message=f"Invalid target URL: {exc}",
        )

    # 2. Protocol-specific validation
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Case A: Google Gemini Native
            if entry.protocol == "gemini_native":
                url = f"{effective_url.rstrip('/')}/models?key={clean_key}"
                resp = await client.get(url)
                return _classify_gemini_response(resp, provider_id, hint)

            # Case B: Anthropic Claude Native
            elif entry.protocol == "anthropic_native":
                url = f"{effective_url.rstrip('/')}/messages"
                headers = {
                    "x-api-key": clean_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                }
                body = {
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                }
                resp = await client.post(url, json=body, headers=headers)
                return _classify_anthropic_response(resp, provider_id, hint)

            # Case C: OpenAI-Compatible (OpenAI, Groq, DeepSeek, Mistral, Together, OpenRouter, ZAI, HF, Custom)
            else:
                return await _validate_openai_compat(
                    client=client,
                    base_url=effective_url,
                    api_key=clean_key,
                    entry=entry,
                    custom_model=custom_model,
                    hint=hint,
                )

    except httpx.TimeoutException:
        return ValidationResult(
            valid=False,
            status="timeout",
            message=f"Connection to {entry.display_name} timed out after 10 seconds. Check server accessibility.",
            advisory_hint=hint,
        )
    except httpx.RequestError as exc:
        return ValidationResult(
            valid=False,
            status="network_blocked",
            message=f"Network request to {entry.display_name} failed: {exc}",
            advisory_hint=hint,
        )


async def _validate_openai_compat(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    entry: Any,
    custom_model: str | None,
    hint: str | None,
) -> ValidationResult:
    """Validate OpenAI-compatible endpoint via GET /models or 1-token probe."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if entry.id == "openrouter":
        headers["HTTP-Referer"] = "https://lumen.ai"
        headers["X-Title"] = "Lumen AI Data Analyst"

    models_url = f"{base_url.rstrip('/')}/models"
    models_list: list[str] = []

    try:
        resp = await client.get(models_url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            raw_models = data.get("data", [])
            if isinstance(raw_models, list):
                for m in raw_models:
                    if isinstance(m, dict) and "id" in m:
                        models_list.append(str(m["id"]))
                    elif isinstance(m, str):
                        models_list.append(m)

            fast_model, strong_model = select_fast_and_strong_models(entry.id, models_list)
            return ValidationResult(
                valid=True,
                status="active",
                message=f"Successfully authenticated with {entry.display_name}. Found {len(models_list)} models.",
                models=models_list[:50],  # Return top 50
                model_fast=fast_model,
                model_strong=strong_model,
                capabilities={
                    "tools": entry.supports_tools,
                    "json_mode": entry.supports_json_mode,
                    "streaming": True,
                },
                advisory_hint=hint,
            )
        elif resp.status_code in (401, 403):
            return ValidationResult(
                valid=False,
                status="invalid_key",
                message=f"Authentication failed (HTTP {resp.status_code}). Key is invalid or expired.",
                advisory_hint=hint,
            )
        elif resp.status_code == 402:
            return ValidationResult(
                valid=False,
                status="quota_exhausted",
                message=f"Authentication succeeded, but your {entry.display_name} balance or quota is exhausted.",
                advisory_hint=hint,
            )
        elif resp.status_code == 429:
            return ValidationResult(
                valid=False,
                status="rate_limited",
                message=f"{entry.display_name} rate limit reached. Key is valid, but currently throttled.",
                advisory_hint=hint,
            )
    except Exception:
        pass  # Fall through to 1-token completion check

    # If /models is unavailable or custom provider, try 1-token completion
    test_model = (
        custom_model
        or (entry.preferred_models.get("fast") or ["gpt-4o-mini"])[0]
    )
    chat_url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": test_model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    }

    resp = await client.post(chat_url, json=payload, headers=headers)
    if resp.status_code == 200:
        fast_model = test_model
        strong_model = (
            (entry.preferred_models.get("strong") or [test_model])[0]
        )
        return ValidationResult(
            valid=True,
            status="active",
            message=f"Successfully connected to {entry.display_name} via {test_model}.",
            models=[test_model],
            model_fast=fast_model,
            model_strong=strong_model,
            capabilities={
                "tools": entry.supports_tools,
                "json_mode": entry.supports_json_mode,
                "streaming": True,
            },
            advisory_hint=hint,
        )
    elif resp.status_code in (401, 403):
        return ValidationResult(
            valid=False,
            status="invalid_key",
            message=f"Authentication rejected by {entry.display_name}. Key is invalid or inactive.",
            advisory_hint=hint,
        )
    elif resp.status_code == 402:
        return ValidationResult(
            valid=False,
            status="quota_exhausted",
            message=f"Insufficient quota or credit on {entry.display_name} account.",
            advisory_hint=hint,
        )
    elif resp.status_code == 429:
        return ValidationResult(
            valid=False,
            status="rate_limited",
            message=f"{entry.display_name} rate limit hit.",
            advisory_hint=hint,
        )
    else:
        return ValidationResult(
            valid=False,
            status="provider_error",
            message=f"Provider returned HTTP {resp.status_code}: {resp.text[:200]}",
            advisory_hint=hint,
        )


def _classify_gemini_response(resp: httpx.Response, provider_id: str, hint: str | None) -> ValidationResult:
    """Classify Google Gemini API status."""
    if resp.status_code == 200:
        data = resp.json()
        models = [
            m.get("name", "").replace("models/", "")
            for m in data.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ]
        fast, strong = select_fast_and_strong_models(provider_id, models)
        return ValidationResult(
            valid=True,
            status="active",
            message=f"Successfully authenticated with Google Gemini. Found {len(models)} accessible models.",
            models=models[:40],
            model_fast=fast,
            model_strong=strong,
            capabilities={"tools": True, "json_mode": True, "streaming": True},
            advisory_hint=hint,
        )
    elif resp.status_code in (400, 401, 403):
        return ValidationResult(
            valid=False,
            status="invalid_key",
            message="Invalid Google Gemini API key.",
            advisory_hint=hint,
        )
    elif resp.status_code == 429:
        return ValidationResult(
            valid=False,
            status="rate_limited",
            message="Gemini free quota / rate limit exceeded.",
            advisory_hint=hint,
        )
    return ValidationResult(
        valid=False,
        status="provider_error",
        message=f"Gemini API returned status {resp.status_code}",
        advisory_hint=hint,
    )


def _classify_anthropic_response(resp: httpx.Response, provider_id: str, hint: str | None) -> ValidationResult:
    """Classify Anthropic Claude response."""
    if resp.status_code == 200:
        entry = get_catalog_entry(provider_id)
        fast = entry.preferred_models["fast"][0] if entry else "claude-3-5-haiku-20241022"
        strong = entry.preferred_models["strong"][0] if entry else "claude-3-7-sonnet-20250219"
        return ValidationResult(
            valid=True,
            status="active",
            message="Successfully verified Anthropic Claude credentials.",
            models=[fast, strong],
            model_fast=fast,
            model_strong=strong,
            capabilities={"tools": True, "json_mode": True, "streaming": True},
            advisory_hint=hint,
        )
    elif resp.status_code in (401, 403):
        return ValidationResult(
            valid=False,
            status="invalid_key",
            message="Anthropic API key is invalid or inactive.",
            advisory_hint=hint,
        )
    elif resp.status_code == 429:
        return ValidationResult(
            valid=False,
            status="rate_limited",
            message="Anthropic rate limit reached.",
            advisory_hint=hint,
        )
    return ValidationResult(
        valid=False,
        status="provider_error",
        message=f"Anthropic returned HTTP {resp.status_code}: {resp.text[:200]}",
        advisory_hint=hint,
    )
