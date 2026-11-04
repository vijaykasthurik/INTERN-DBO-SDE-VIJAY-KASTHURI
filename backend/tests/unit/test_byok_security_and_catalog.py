"""Unit tests for BYOK AES-256-GCM encryption, SSRF protection, log scrubbing, and catalog integrity."""

import pytest

from app.core.encryption import (
    decrypt_api_key,
    encrypt_api_key,
    mask_key_hint,
    scrub_secrets_from_text,
    validate_outbound_url_ssrf,
)
from app.core.errors import SecurityViolationError
from app.llm.catalog import (
    check_key_format_hint,
    get_catalog_entry,
    get_provider_catalog,
    select_fast_and_strong_models,
)


def test_encryption_roundtrip_and_tamper_detection() -> None:
    raw_key = "gsk_secret_test_key_for_lumen_byok_9999"
    ciphertext = encrypt_api_key(raw_key, key_version="v1")

    assert ciphertext.startswith("v1:")
    assert raw_key not in ciphertext

    decrypted = decrypt_api_key(ciphertext)
    assert decrypted == raw_key

    # Tamper with ciphertext
    parts = ciphertext.split(":", 1)
    tampered = parts[0] + ":" + parts[1][:-4] + "AAAA"
    with pytest.raises(SecurityViolationError):
        decrypt_api_key(tampered)


def test_mask_key_hint() -> None:
    assert mask_key_hint("dummy_sample_key_for_testing_purposes_only_last4") == "...ast4"
    assert mask_key_hint("sk-1234") == "...1234"
    assert mask_key_hint("abc") == "...abc"


def test_log_scrubber_masks_credentials() -> None:
    sample_log = (
        "Calling endpoint with Authorization: Bearer sk-testmockcredentialvalue123456 and "
        "Groq key gsk_testmockcredentialvalue123456 and "
        "Gemini AIzaSyTestMockCredentialValue123456"
    )
    scrubbed = scrub_secrets_from_text(sample_log)
    assert "sk-test" not in scrubbed
    assert "gsk_test" not in scrubbed
    assert "AIzaSy" not in scrubbed
    assert "[REDACTED_CREDENTIAL]" in scrubbed


def test_ssrf_guard_blocks_private_and_metadata_ips() -> None:
    # Allowed HTTPS external domain
    assert "api.openai.com" in validate_outbound_url_ssrf("https://api.openai.com/v1")
    assert "api.groq.com" in validate_outbound_url_ssrf("https://api.groq.com/openai/v1")

    # Disallow plain HTTP for remote hosts
    with pytest.raises(SecurityViolationError):
        validate_outbound_url_ssrf("http://api.openai.com/v1")

    # Disallow internal cloud metadata endpoint
    with pytest.raises(SecurityViolationError):
        validate_outbound_url_ssrf("https://169.254.169.254/latest/meta-data/")


def test_catalog_integrity_and_model_heuristics() -> None:
    catalog = get_provider_catalog()
    assert len(catalog) >= 10
    provider_ids = [p["id"] for p in catalog]
    for required in ["openai", "gemini", "anthropic", "groq", "deepseek", "openrouter", "zai", "huggingface", "custom"]:
        assert required in provider_ids

    groq_entry = get_catalog_entry("groq")
    assert groq_entry is not None
    assert groq_entry.supports_tools is True

    # Test hint heuristic
    hint = check_key_format_hint("groq", "sk-proj-openai-key-candidate")
    assert hint is not None
    assert "OpenAI" in hint

    # Test model selection heuristic
    mock_groq_models = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "whisper-large-v3"]
    fast, strong = select_fast_and_strong_models("groq", mock_groq_models)
    assert fast == "llama-3.1-8b-instant"
    assert strong == "llama-3.3-70b-versatile"
