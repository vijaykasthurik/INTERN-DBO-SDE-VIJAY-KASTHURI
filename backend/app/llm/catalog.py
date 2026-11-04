"""Declarative LLM Provider Catalog and Automatic Model Selection Engine.

Provides verified configurations for major AI providers, protocols, key format hints,
and heuristic model auto-adaptation algorithms.
"""

import re
from typing import Any

from pydantic import BaseModel, Field


class ProviderCatalogEntry(BaseModel):
    """Declarative specification of an LLM provider and its protocol parameters."""

    id: str
    display_name: str
    protocol: str = "openai_compat"  # openai_compat | gemini_native | anthropic_native
    base_url: str
    auth_style: str = "bearer"  # bearer | x-api-key | query
    models_endpoint: str | None = "/models"
    key_format_hint: str | None = None
    key_format_regex: str | None = None
    docs_url: str
    supports_tools: bool = True
    supports_json_mode: bool = True
    preferred_models: dict[str, list[str]] = Field(default_factory=dict)
    icon_monogram: str = "AI"


# Official Provider Registry with verified Base URLs and model lists
PROVIDER_CATALOG: list[ProviderCatalogEntry] = [
    ProviderCatalogEntry(
        id="openai",
        display_name="OpenAI",
        protocol="openai_compat",
        base_url="https://api.openai.com/v1",
        auth_style="bearer",
        models_endpoint="https://api.openai.com/v1/models",
        key_format_hint="Starts with 'sk-' (e.g. sk-proj-...)",
        key_format_regex=r"^sk-[a-zA-Z0-9_-]{20,}$",
        docs_url="https://platform.openai.com/api-keys",
        supports_tools=True,
        supports_json_mode=True,
        preferred_models={
            "fast": ["gpt-4o-mini", "gpt-3.5-turbo"],
            "strong": ["gpt-4o", "chatgpt-4o-latest", "gpt-4-turbo"],
        },
        icon_monogram="OA",
    ),
    ProviderCatalogEntry(
        id="gemini",
        display_name="Google Gemini",
        protocol="gemini_native",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        auth_style="query",
        models_endpoint="https://generativelanguage.googleapis.com/v1beta/models",
        key_format_hint="Starts with 'AIzaSy' (39 chars)",
        key_format_regex=r"^AIzaSy[0-9A-Za-z-_]{33}$",
        docs_url="https://aistudio.google.com/app/apikey",
        supports_tools=True,
        supports_json_mode=True,
        preferred_models={
            "fast": ["gemini-2.0-flash", "gemini-1.5-flash"],
            "strong": ["gemini-2.0-flash-thinking-exp-01-21", "gemini-1.5-pro"],
        },
        icon_monogram="GE",
    ),
    ProviderCatalogEntry(
        id="anthropic",
        display_name="Anthropic Claude",
        protocol="anthropic_native",
        base_url="https://api.anthropic.com/v1",
        auth_style="x-api-key",
        models_endpoint=None,  # Anthropic doesn't have a public GET /models endpoint on all plans
        key_format_hint="Starts with 'sk-ant-' (e.g. sk-ant-api03-...)",
        key_format_regex=r"^sk-ant-[a-zA-Z0-9_-]{20,}$",
        docs_url="https://console.anthropic.com/settings/keys",
        supports_tools=True,
        supports_json_mode=True,
        preferred_models={
            "fast": ["claude-3-5-haiku-20241022", "claude-3-haiku-20240307"],
            "strong": ["claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022"],
        },
        icon_monogram="CL",
    ),
    ProviderCatalogEntry(
        id="groq",
        display_name="Groq Cloud (LPU)",
        protocol="openai_compat",
        base_url="https://api.groq.com/openai/v1",
        auth_style="bearer",
        models_endpoint="https://api.groq.com/openai/v1/models",
        key_format_hint="Starts with 'gsk_' (56 chars)",
        key_format_regex=r"^gsk_[a-zA-Z0-9]{48,}$",
        docs_url="https://console.groq.com/keys",
        supports_tools=True,
        supports_json_mode=True,
        preferred_models={
            "fast": ["llama-3.1-8b-instant", "llama3-8b-8192"],
            "strong": ["llama-3.3-70b-versatile", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"],
        },
        icon_monogram="GQ",
    ),
    ProviderCatalogEntry(
        id="deepseek",
        display_name="DeepSeek",
        protocol="openai_compat",
        base_url="https://api.deepseek.com/v1",
        auth_style="bearer",
        models_endpoint="https://api.deepseek.com/models",
        key_format_hint="Starts with 'sk-' (e.g. sk-...)",
        key_format_regex=r"^sk-[a-zA-Z0-9]{32,}$",
        docs_url="https://platform.deepseek.com/api_keys",
        supports_tools=True,
        supports_json_mode=True,
        preferred_models={
            "fast": ["deepseek-chat"],
            "strong": ["deepseek-reasoner", "deepseek-chat"],
        },
        icon_monogram="DS",
    ),
    ProviderCatalogEntry(
        id="openrouter",
        display_name="OpenRouter",
        protocol="openai_compat",
        base_url="https://openrouter.ai/api/v1",
        auth_style="bearer",
        models_endpoint="https://openrouter.ai/api/v1/models",
        key_format_hint="Starts with 'sk-or-v1-'",
        key_format_regex=r"^sk-or-v1-[a-f0-9]{64}$",
        docs_url="https://openrouter.ai/keys",
        supports_tools=True,
        supports_json_mode=True,
        preferred_models={
            "fast": ["google/gemini-2.0-flash-001", "meta-llama/llama-3.1-8b-instruct"],
            "strong": ["anthropic/claude-3.5-sonnet", "meta-llama/llama-3.3-70b-instruct"],
        },
        icon_monogram="OR",
    ),
    ProviderCatalogEntry(
        id="mistral",
        display_name="Mistral AI",
        protocol="openai_compat",
        base_url="https://api.mistral.ai/v1",
        auth_style="bearer",
        models_endpoint="https://api.mistral.ai/v1/models",
        key_format_hint="Mistral 32-character key",
        key_format_regex=r"^[a-zA-Z0-9]{32}$",
        docs_url="https://console.mistral.ai/api-keys/",
        supports_tools=True,
        supports_json_mode=True,
        preferred_models={
            "fast": ["mistral-small-latest", "open-mistral-7b"],
            "strong": ["mistral-large-latest", "pixtral-large-latest"],
        },
        icon_monogram="MS",
    ),
    ProviderCatalogEntry(
        id="together",
        display_name="Together AI",
        protocol="openai_compat",
        base_url="https://api.together.xyz/v1",
        auth_style="bearer",
        models_endpoint="https://api.together.xyz/v1/models",
        key_format_hint="Together AI hex key (64 chars)",
        key_format_regex=r"^[a-f0-9]{64}$",
        docs_url="https://api.together.xyz/settings/api-keys",
        supports_tools=True,
        supports_json_mode=True,
        preferred_models={
            "fast": ["meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"],
            "strong": ["meta-llama/Meta-Llama-3.3-70B-Instruct-Turbo", "deepseek-ai/DeepSeek-V3"],
        },
        icon_monogram="TG",
    ),
    ProviderCatalogEntry(
        id="xai",
        display_name="xAI (Grok)",
        protocol="openai_compat",
        base_url="https://api.x.ai/v1",
        auth_style="bearer",
        models_endpoint="https://api.x.ai/v1/models",
        key_format_hint="Starts with 'xai-'",
        key_format_regex=r"^xai-[a-zA-Z0-9]{40,}$",
        docs_url="https://console.x.ai/",
        supports_tools=True,
        supports_json_mode=True,
        preferred_models={
            "fast": ["grok-2-mini", "grok-beta"],
            "strong": ["grok-2", "grok-2-latest"],
        },
        icon_monogram="XA",
    ),
    ProviderCatalogEntry(
        id="zai",
        display_name="Z.AI (GLM)",
        protocol="openai_compat",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        auth_style="bearer",
        models_endpoint="https://open.bigmodel.cn/api/paas/v4/models",
        key_format_hint="Z.AI API Key format '<id>.<secret>'",
        key_format_regex=r"^[a-zA-Z0-9]+\.[a-zA-Z0-9]+$",
        docs_url="https://bigmodel.cn/usercenter/apikeys",
        supports_tools=True,
        supports_json_mode=True,
        preferred_models={
            "fast": ["glm-4-flash", "glm-4"],
            "strong": ["glm-4-plus", "glm-4"],
        },
        icon_monogram="ZA",
    ),
    ProviderCatalogEntry(
        id="huggingface",
        display_name="Hugging Face",
        protocol="openai_compat",
        base_url="https://router.huggingface.co/v1",
        auth_style="bearer",
        models_endpoint="https://router.huggingface.co/v1/models",
        key_format_hint="Starts with 'hf_' (e.g. hf_...)",
        key_format_regex=r"^hf_[a-zA-Z0-9]{30,}$",
        docs_url="https://huggingface.co/settings/tokens",
        supports_tools=False,  # Wrapped with JSON-repair and schema validation
        supports_json_mode=False,
        preferred_models={
            "fast": ["Qwen/Qwen2.5-7B-Instruct"],
            "strong": ["Qwen/Qwen2.5-7B-Instruct", "meta-llama/Llama-3.1-8B-Instruct"],
        },
        icon_monogram="HF",
    ),
    ProviderCatalogEntry(
        id="custom",
        display_name="Custom (OpenAI-compatible)",
        protocol="openai_compat",
        base_url="",  # Provided by user
        auth_style="bearer",
        models_endpoint="/models",
        key_format_hint="Any valid API key or Bearer token",
        docs_url="https://platform.openai.com/docs/api-reference",
        supports_tools=True,
        supports_json_mode=True,
        preferred_models={
            "fast": [],
            "strong": [],
        },
        icon_monogram="CU",
    ),
]

_CATALOG_INDEX: dict[str, ProviderCatalogEntry] = {entry.id: entry for entry in PROVIDER_CATALOG}


def get_provider_catalog() -> list[dict[str, Any]]:
    """Return serialized list of supported providers for client consumption (zero secrets)."""
    return [entry.model_dump() for entry in PROVIDER_CATALOG]


def get_catalog_entry(provider_id: str) -> ProviderCatalogEntry | None:
    """Find catalog entry by provider identifier."""
    return _CATALOG_INDEX.get(provider_id.lower().strip())


def check_key_format_hint(provider_id: str, key_candidate: str) -> str | None:
    """Provide a friendly advisory hint if a user pastes a key that appears to belong to another provider."""
    entry = get_catalog_entry(provider_id)
    cand = key_candidate.strip()

    # Friendly heuristics for cross-pasted keys
    if provider_id != "openai" and cand.startswith("sk-") and not cand.startswith("sk-ant-") and not cand.startswith("sk-or-"):
        return "This key looks like an OpenAI key ('sk-...'). Did you select the correct provider?"
    if provider_id != "anthropic" and cand.startswith("sk-ant-"):
        return "This key looks like an Anthropic Claude key ('sk-ant-...'). Did you select Anthropic?"
    if provider_id != "groq" and cand.startswith("gsk_"):
        return "This key looks like a Groq key ('gsk_...'). Did you select Groq?"
    if provider_id != "gemini" and cand.startswith("AIzaSy"):
        return "This key looks like a Google Gemini key ('AIzaSy...'). Did you select Gemini?"
    if provider_id != "huggingface" and cand.startswith("hf_"):
        return "This key looks like a Hugging Face token ('hf_...'). Did you select Hugging Face?"

    # Check provider's own hint regex if provided
    if entry and entry.key_format_regex and not re.match(entry.key_format_regex, cand):
        return f"Note: expected format for {entry.display_name} is: {entry.key_format_hint}"

    return None


def select_fast_and_strong_models(
    provider_id: str,
    available_models: list[str],
) -> tuple[str, str]:
    """Auto-select the FAST and STRONG models by intersecting catalog preferences with accessible models.

    Falls back to intelligent heuristics if preferred candidates are not listed.
    """
    entry = get_catalog_entry(provider_id)
    if not available_models:
        # Default catalog candidates
        if entry:
            fast = entry.preferred_models.get("fast", ["default"])[0] if entry.preferred_models.get("fast") else "default"
            strong = entry.preferred_models.get("strong", ["default"])[0] if entry.preferred_models.get("strong") else "default"
            return fast, strong
        return "default", "default"

    avail_set = set(available_models)
    fast_choice: str | None = None
    strong_choice: str | None = None

    if entry:
        # 1. Match fast preference
        for candidate in entry.preferred_models.get("fast", []):
            if candidate in avail_set:
                fast_choice = candidate
                break

        # 2. Match strong preference
        for candidate in entry.preferred_models.get("strong", []):
            if candidate in avail_set:
                strong_choice = candidate
                break

    # 3. Fallback heuristics for available models
    chat_models = [
        m for m in available_models
        if not any(token in m.lower() for token in ["embedding", "whisper", "tts", "dall-e", "moderation", "vision-preview", "bge-"])
    ]
    if not chat_models:
        chat_models = available_models

    if not fast_choice:
        # Prefer smaller/cheaper indicators: mini, flash, 8b, 7b, small, instant
        fast_candidates = [
            m for m in chat_models
            if any(token in m.lower() for token in ["mini", "flash", "8b", "7b", "small", "instant", "turbo"])
        ]
        fast_choice = fast_candidates[0] if fast_candidates else chat_models[0]

    if not strong_choice:
        # Prefer flagship indicators: 70b, pro, large, plus, 4o, sonnet
        strong_candidates = [
            m for m in chat_models
            if any(token in m.lower() for token in ["70b", "pro", "large", "plus", "4o", "sonnet", "reasoner"])
        ]
        strong_choice = strong_candidates[0] if strong_candidates else chat_models[-1]

    return fast_choice, strong_choice
