# ADDENDUM: "Bring Your Own Key" (BYOK) + Smart Provider Fallback

Companion to `MASTER_PROMPT_Lumen_AI_Data_Analyst.md`.
It overrides and extends the master prompt wherever the two differ.

## 1. PRODUCT BEHAVIOUR
There is NO restriction on which provider a user may choose. Reviewers must be able to use their own key from any major provider.

Key resolution order for every LLM request, per user:
  (a) The user's own active key (if they connected one).
  (b) If (a) fails (401/403 invalid or expired, quota exhausted, repeated 5xx, network error) AND the
      user has "Allow fallback to shared models" enabled (default ON): the SHARED server chain
      groq (round-robin key pool, keys 1..N) -> zai -> huggingface.
  (c) If everything fails: a friendly, specific error in the UI with a "Fix connection" button.

When a key stops working:
  1. Mark it with precise status
  2. Switch silently to shared chain if allowed
  3. Show non-blocking banner: "Your <Provider> key expired or ran out of credit. Using shared model for now. [Update key]"
  4. Emit SSE event `provider_switch` so the Reasoning Timeline shows it honestly.

## 2. PROVIDER CATALOG (`backend/app/llm/catalog.py`)
Registry where each provider is one declarative entry:
  id, display_name, protocol ("openai_compat" | "gemini_native" | "anthropic_native"), base_url,
  auth_style (bearer | x-api-key | query), models_endpoint, key_format_hint, docs_url, supports_tools,
  supports_json_mode, preferred_models: {fast: [...], strong: [...]}.

Catalog includes: OpenAI, Google Gemini, Anthropic, Groq, DeepSeek, OpenRouter, Mistral, Together AI,
xAI, Z.AI (GLM), Hugging Face, and Custom OpenAI-compatible.

## 3. SECURITY REQUIREMENTS
- AES-256-GCM encryption at rest with KEY_ENCRYPTION_SECRET.
- Never return stored keys to browser (mask as ...a1b2).
- Global log scrubber masking keys and patterns.
- SSRF protection on Custom provider URLs and outbound calls.
- Strict per-user isolation.
- Keys exist only in ephemeral request context.

## 4. NEW PHASE 11 (REPLACEMENT)
Live validation using server shared pool (Groq 1..N, Z.AI, Hugging Face) and BYOK flow.
