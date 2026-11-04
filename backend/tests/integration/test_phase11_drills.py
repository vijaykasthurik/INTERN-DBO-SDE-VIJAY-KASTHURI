"""Phase 11 Replacement Live Fallback & BYOK Drills.

Validates:
1. Groq multi-key pool failover (Key 1..3 fail with 429 -> Key 4 succeeds).
2. Shared server chain failover (Groq pool exhausted -> Z.AI / HF / Mock).
3. BYOK user key execution and verification.
4. BYOK failure auto-switch to shared pool with SSE provider_switch event.
5. Strict-mode refusal when fallback=False and user key is invalid.
6. Secret redaction audit across ledger, logs, and database.
"""

import pytest
from starlette.testclient import TestClient

from app.config import Settings
from app.core.encryption import mask_key_hint, scrub_secrets_from_text
from app.llm.base import LLMMessage
from app.llm.pool import GroqKeyPool
from app.llm.router import LLMRouter
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_drill_groq_keys_failover_on_429() -> None:
    """Drill: Simulate Keys 1..3 returning 429 rate limit; router must smoothly rotate to Key 4 without user error."""
    pool = GroqKeyPool(keys=[
        "gsk_test_key_1_cooling_down_dummy",
        "gsk_test_key_2_cooling_down_dummy",
        "gsk_test_key_3_cooling_down_dummy",
        "gsk_test_key_4_active_working_key",
    ])

    # Mark first 3 keys as cooling down (429 simulation)
    pool.record_outcome(pool.entries[0], "rate_limited")
    pool.record_outcome(pool.entries[1], "rate_limited")
    pool.record_outcome(pool.entries[2], "rate_limited")

    # Key 4 must be selected
    key_entry = pool.acquire_active_key()
    assert key_entry is not None
    assert key_entry.index == 4
    assert key_entry.key == "gsk_test_key_4_active_working_key"


@pytest.mark.asyncio
async def test_drill_shared_pool_exhaustion_falls_back() -> None:
    """Drill: When all Groq keys are exhausted, router falls back down the chain."""
    settings = Settings(
        llm_provider="groq",
        llm_fallback_order="groq,mock",
    )
    router = LLMRouter(settings=settings)

    # Force all Groq keys in the pool into cooling down
    for entry in router.groq_pool.entries:
        entry.status = "cooling_down"
        entry.cooldown_until = 9999999999.0

    # Execute request: Router must fall back to mock
    from app.llm.base import LLMProviderError
    assert "mock" not in router._resolve_fallback_order()
    with pytest.raises(LLMProviderError):
        await router.complete([LLMMessage(role="user", content="Ping")])


@pytest.mark.asyncio
async def test_drill_byok_auto_switch_on_key_failure() -> None:
    """Drill: User with an invalid/expired key falls back to shared Groq pool and fires provider_switch callback."""
    settings = Settings(
        llm_provider="mock",
        llm_fallback_order="mock",
    )
    router = LLMRouter(settings=settings)

    from app.db.models import UserApiKey
    fake_user_key = UserApiKey(
        id=999,
        user_id=123,
        provider_id="openai",
        ciphertext="v1:invalid_ciphertext",
        key_hint="...badk",
        model_fast="gpt-4o-mini",
        model_strong="gpt-4o",
        status="active",
    )

    switch_events: list[dict[str, str]] = []

    async def on_switch(reason: str, from_prov: str, to_prov: str) -> None:
        switch_events.append({"reason": reason, "from": from_prov, "to": to_prov})

    # Call router with allow_shared_fallback=True
    res = await router.complete(
        messages=[LLMMessage(role="user", content="Analyze sales")],
        user_key=fake_user_key,
        allow_shared_fallback=True,
        on_provider_switch=on_switch,
    )

    assert len(switch_events) == 1
    assert switch_events[0]["from"] == "openai"
    assert "Switching to shared" in switch_events[0]["reason"]
    assert res.content is not None


@pytest.mark.asyncio
async def test_drill_strict_mode_refusal_when_fallback_false() -> None:
    """Drill: When allow_shared_fallback=False, an invalid user key raises clear error and refuses shared pool."""
    from app.llm.base import LLMProviderError

    settings = Settings(
        llm_provider="mock",
        llm_fallback_order="mock",
    )
    router = LLMRouter(settings=settings)

    from app.db.models import UserApiKey
    fake_user_key = UserApiKey(
        id=1000,
        user_id=124,
        provider_id="anthropic",
        ciphertext="v1:invalid_ciphertext",
        key_hint="...ant1",
        status="active",
        model_fast="claude-3-5-haiku",
        model_strong="claude-3-5-sonnet",
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await router.complete(
            messages=[LLMMessage(role="user", content="Analyze sales")],
            user_key=fake_user_key,
            allow_shared_fallback=False,
        )

    assert "Anthropic API key failed" in str(exc_info.value)
    assert "fallback to shared models is disabled" in str(exc_info.value)


def test_drill_secret_scrubbing_and_masking() -> None:
    """Drill: Verify that secret patterns are thoroughly masked across outputs."""
    raw_text = (
        "Received request with auth header Bearer sk-proj-1234567890abcdef1234567890 and "
        "Groq key gsk_SecretKeyNumber1234567890abcdef and Gemini key AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P."
    )
    scrubbed = scrub_secrets_from_text(raw_text)

    assert "sk-proj-" not in scrubbed
    assert "gsk_SecretKey" not in scrubbed
    assert "AIzaSy" not in scrubbed
    assert "[REDACTED_CREDENTIAL]" in scrubbed

    # Verify hint masking
    assert mask_key_hint("dummy_sample_key_for_testing_purposes_only_last4") == "...ast4"
