import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  KeyRound,
  Lock,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Loader2,
  ChevronDown,
  ChevronUp,
  Cpu,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useAIConnectionStore } from "../stores/aiConnectionStore";
import {
  api,
  type ProviderCatalogEntry,
  type ValidateKeyResponse,
} from "../lib/api";
import { cn } from "../lib/utils";

// Monogram colors and labels for clean visual identification
const PROVIDER_MONOGRAMS: Record<string, { bg: string; text: string; label: string }> = {
  openai: { bg: "bg-emerald-100", text: "text-emerald-800", label: "OAI" },
  gemini: { bg: "bg-blue-100", text: "text-blue-800", label: "GEM" },
  anthropic: { bg: "bg-amber-100", text: "text-amber-800", label: "ANT" },
  groq: { bg: "bg-orange-100", text: "text-orange-800", label: "GRQ" },
  deepseek: { bg: "bg-cyan-100", text: "text-cyan-800", label: "DSK" },
  openrouter: { bg: "bg-indigo-100", text: "text-indigo-800", label: "OR" },
  mistral: { bg: "bg-rose-100", text: "text-rose-800", label: "MIS" },
  together: { bg: "bg-purple-100", text: "text-purple-800", label: "TOG" },
  xai: { bg: "bg-zinc-100", text: "text-zinc-800", label: "xAI" },
  zai: { bg: "bg-teal-100", text: "text-teal-800", label: "ZAI" },
  huggingface: { bg: "bg-yellow-100", text: "text-yellow-800", label: "HF" },
  custom: { bg: "bg-slate-100", text: "text-slate-800", label: "CUS" },
};

export const ConnectAIPopup: React.FC = () => {
  const {
    isConnectModalOpen,
    closeConnectModal,
    selectedProviderId,
    catalog,
    fetchCatalog,
    fetchConnection,
  } = useAIConnectionStore();

  const [activeProviderId, setActiveProviderId] = useState<string>("openai");
  const [apiKey, setApiKey] = useState("");
  const [customBaseUrl, setCustomBaseUrl] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const [validating, setValidating] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidateKeyResponse | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const [overrideFast, setOverrideFast] = useState("");
  const [overrideStrong, setOverrideStrong] = useState("");
  const [allowFallback, setAllowFallback] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    if (isConnectModalOpen) {
      if (catalog.length === 0) {
        fetchCatalog();
      }
      if (selectedProviderId) {
        setActiveProviderId(selectedProviderId);
      }
      setApiKey("");
      setValidationResult(null);
      setValidationError(null);
      setShowAdvanced(false);
    }
  }, [isConnectModalOpen, selectedProviderId, catalog.length, fetchCatalog]);

  const activeProvider =
    catalog.find((p) => p.id === activeProviderId) ||
    catalog[0] ||
    ({
      id: "openai",
      display_name: "OpenAI",
      protocol: "openai_compat",
      base_url: "https://api.openai.com/v1",
      auth_style: "bearer",
      models_endpoint: "https://api.openai.com/v1/models",
      key_format_hint: "^sk-[a-zA-Z0-9_-]{20,}$",
      docs_url: "https://platform.openai.com/api-keys",
      supports_tools: true,
      supports_json_mode: true,
      preferred_models: {
        fast: ["gpt-4o-mini"],
        strong: ["gpt-4o"],
      },
    } as ProviderCatalogEntry);

  const filteredProviders = catalog.filter((p) =>
    p.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleValidate = async () => {
    if (!apiKey.trim()) return;
    setValidating(true);
    setValidationError(null);
    setValidationResult(null);

    try {
      const res = await api.byok.validate({
        provider_id: activeProviderId,
        api_key: apiKey.trim(),
        base_url: activeProviderId === "custom" ? customBaseUrl.trim() : undefined,
      });

      if (res.valid) {
        setValidationResult(res);
        setOverrideFast(res.selected_fast);
        setOverrideStrong(res.selected_strong);
      } else {
        setValidationError(res.message);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Network error validating key";
      setValidationError(msg);
    } finally {
      setValidating(false);
    }
  };

  const handleConnect = async () => {
    if (!validationResult?.valid) return;
    setConnecting(true);
    try {
      await api.byok.connect({
        provider_id: activeProviderId,
        api_key: apiKey.trim(),
        base_url: activeProviderId === "custom" ? customBaseUrl.trim() : undefined,
        model_fast: overrideFast || validationResult.selected_fast,
        model_strong: overrideStrong || validationResult.selected_strong,
        allow_shared_fallback: allowFallback,
      });

      await fetchConnection();
      closeConnectModal();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to activate API key";
      setValidationError(msg);
    } finally {
      setConnecting(false);
    }
  };

  if (!isConnectModalOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 12 }}
          transition={{ duration: 0.22, ease: "easeOut" }}
          className="relative w-full max-w-2xl bg-white rounded-24 border border-hairline shadow-soft-xl overflow-hidden flex flex-col max-h-[90vh]"
        >
          {/* HEADER */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-hairline bg-surface/40">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-pill bg-ink flex items-center justify-center text-white shadow-soft-xs">
                <KeyRound className="w-4 h-4" />
              </div>
              <div>
                <h3 className="font-serif text-lg font-medium text-ink tracking-tight">
                  Connect your AI
                </h3>
                <p className="text-xs text-ink-muted">
                  Bring your own API key for unlimited queries, or rely on shared fallback models.
                </p>
              </div>
            </div>
            <button
              onClick={closeConnectModal}
              className="p-1.5 rounded-pill text-ink-muted hover:text-ink hover:bg-surface border border-transparent hover:border-hairline transition-colors"
              aria-label="Close dialog"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* BODY */}
          <div className="p-6 overflow-y-auto space-y-5">
            {/* PROVIDER SELECTION */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-semibold text-ink uppercase tracking-wider">
                  Select Provider
                </label>
                <div className="relative w-44">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-ink-muted" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search..."
                    className="w-full pl-8 pr-2 py-1 text-xs bg-surface border border-hairline rounded-pill focus:outline-none focus:ring-1 focus:ring-accent-indigo"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {filteredProviders.map((p) => {
                  const isSelected = p.id === activeProviderId;
                  const mono = PROVIDER_MONOGRAMS[p.id] || {
                    bg: "bg-surface",
                    text: "text-ink",
                    label: p.id.slice(0, 3).toUpperCase(),
                  };

                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => {
                        setActiveProviderId(p.id);
                        setApiKey("");
                        setValidationResult(null);
                        setValidationError(null);
                      }}
                      className={cn(
                        "flex items-center gap-2 p-2 rounded-16 border text-left transition-all",
                        isSelected
                          ? "border-accent-indigo bg-indigo-50/40 shadow-soft-xs"
                          : "border-hairline hover:border-hairline-dark hover:bg-surface/50"
                      )}
                    >
                      <span
                        className={cn(
                          "w-6 h-6 rounded-8 flex items-center justify-center font-bold text-[10px]",
                          mono.bg,
                          mono.text
                        )}
                      >
                        {mono.label}
                      </span>
                      <span className="text-xs font-medium text-ink truncate">
                        {p.display_name}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* CUSTOM BASE URL (IF CUSTOM PROVIDER) */}
            {activeProviderId === "custom" && (
              <div>
                <label className="block text-xs font-semibold text-ink mb-1">
                  Custom Base URL
                </label>
                <input
                  type="url"
                  value={customBaseUrl}
                  onChange={(e) => setCustomBaseUrl(e.target.value)}
                  placeholder="https://your-llm-proxy.com/v1"
                  className="w-full px-3.5 py-2 text-xs bg-surface border border-hairline rounded-12 focus:outline-none focus:ring-2 focus:ring-accent-indigo"
                />
              </div>
            )}

            {/* API KEY INPUT */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-semibold text-ink">
                  {activeProvider.display_name} API Key
                </label>
                {activeProvider.docs_url && (
                  <a
                    href={activeProvider.docs_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-[11px] font-medium text-accent-indigo hover:underline"
                  >
                    <span>Get Key</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>

              <div className="relative">
                <input
                  type={showKey ? "text" : "password"}
                  autoComplete="off"
                  value={apiKey}
                  onChange={(e) => {
                    setApiKey(e.target.value);
                    setValidationResult(null);
                    setValidationError(null);
                  }}
                  placeholder={
                    activeProvider.id === "openai"
                      ? "sk-proj-..."
                      : activeProvider.id === "groq"
                      ? "gsk_..."
                      : activeProvider.id === "gemini"
                      ? "AIzaSy..."
                      : "Paste secret API key..."
                  }
                  className="w-full px-3.5 py-2.5 pr-10 text-xs font-mono bg-surface border border-hairline rounded-16 focus:outline-none focus:ring-2 focus:ring-accent-indigo"
                />
                <button
                  type="button"
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-3 top-2.5 text-ink-muted hover:text-ink"
                  aria-label={showKey ? "Hide key" : "Show key"}
                >
                  {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>

              <p className="mt-1.5 text-[11px] text-ink-muted flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 inline" />
                <span>Encrypted at rest with AES-256-GCM. Used only for your requests. Never shown again.</span>
              </p>
            </div>

            {/* VALIDATION ACTION / PROGRESS */}
            {!validationResult && (
              <div className="flex justify-end">
                <button
                  type="button"
                  disabled={validating || !apiKey.trim()}
                  onClick={handleValidate}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 text-xs font-medium text-white rounded-pill transition-all",
                    validating || !apiKey.trim()
                      ? "bg-slate-300 cursor-not-allowed"
                      : "bg-ink text-white shadow-soft-xs hover:bg-ink/90 active:scale-95"
                  )}
                >
                  {validating ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Validating Key...</span>
                    </>
                  ) : (
                    <>
                      <Lock className="w-3.5 h-3.5" />
                      <span>Validate & Probe Models</span>
                    </>
                  )}
                </button>
              </div>
            )}

            {/* ERROR BANNER */}
            {validationError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-16 flex items-start gap-2.5 text-rose-800 text-xs">
                <AlertCircle className="w-4 h-4 text-rose-600 mt-0.5 shrink-0" />
                <div className="space-y-1">
                  <p className="font-semibold">Validation Notice</p>
                  <p className="text-[11px] leading-relaxed text-rose-700">
                    {validationError}
                  </p>
                </div>
              </div>
            )}

            {/* SUCCESS & MODEL SELECTION ACCORDION */}
            {validationResult?.valid && (
              <div className="p-4 bg-emerald-50/60 border border-emerald-200 rounded-20 space-y-3.5 animate-fadeIn">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-emerald-800 text-xs font-semibold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Key Verified & Active</span>
                  </div>
                  <span className="text-[11px] text-emerald-700">
                    {validationResult.models.length} chat models accessible
                  </span>
                </div>

                {/* DETECTED MODELS */}
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 bg-white border border-emerald-100 rounded-14">
                    <div className="flex items-center gap-1.5 text-ink-muted text-[10px] uppercase font-semibold">
                      <Cpu className="w-3 h-3 text-accent-indigo" />
                      <span>Fast Tier (Routing / Simple)</span>
                    </div>
                    <p className="font-mono text-xs font-semibold text-ink mt-0.5 truncate">
                      {overrideFast || validationResult.selected_fast}
                    </p>
                  </div>

                  <div className="p-2.5 bg-white border border-emerald-100 rounded-14">
                    <div className="flex items-center gap-1.5 text-ink-muted text-[10px] uppercase font-semibold">
                      <Cpu className="w-3 h-3 text-emerald-700" />
                      <span>Strong Tier (Planner / SQL / Voice)</span>
                    </div>
                    <p className="font-mono text-xs font-semibold text-ink mt-0.5 truncate">
                      {overrideStrong || validationResult.selected_strong}
                    </p>
                  </div>
                </div>

                {/* ADVANCED OVERRIDE TOGGLE */}
                <div>
                  <button
                    type="button"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className="flex items-center gap-1 text-[11px] font-medium text-ink-muted hover:text-ink"
                  >
                    <span>Advanced Model Selection</span>
                    {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  {showAdvanced && (
                    <div className="mt-2.5 pt-2.5 border-t border-emerald-200/60 grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] text-ink font-medium mb-1">
                          Override Fast Model
                        </label>
                        <select
                          value={overrideFast}
                          onChange={(e) => setOverrideFast(e.target.value)}
                          className="w-full text-xs font-mono bg-white border border-hairline rounded-10 px-2 py-1.5"
                        >
                          {validationResult.models.map((m) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-[11px] text-ink font-medium mb-1">
                          Override Strong Model
                        </label>
                        <select
                          value={overrideStrong}
                          onChange={(e) => setOverrideStrong(e.target.value)}
                          className="w-full text-xs font-mono bg-white border border-hairline rounded-10 px-2 py-1.5"
                        >
                          {validationResult.models.map((m) => (
                            <option key={m} value={m}>
                              {m}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  )}
                </div>

                {/* FALLBACK CHECKBOX */}
                <label className="flex items-center gap-2 pt-1 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={allowFallback}
                    onChange={(e) => setAllowFallback(e.target.checked)}
                    className="rounded border-hairline text-accent-indigo focus:ring-accent-indigo"
                  />
                  <span className="text-xs text-ink">
                    Allow fallback to shared models if my key expires or runs out of credit
                  </span>
                </label>
              </div>
            )}
          </div>

          {/* FOOTER */}
          <div className="flex items-center justify-between px-6 py-3.5 border-t border-hairline bg-surface/30">
            <button
              type="button"
              onClick={closeConnectModal}
              className="px-4 py-1.5 text-xs font-medium text-ink-muted hover:text-ink transition-colors"
            >
              Cancel
            </button>

            {validationResult?.valid && (
              <button
                type="button"
                disabled={connecting}
                onClick={handleConnect}
                className="flex items-center gap-2 px-5 py-2 text-xs font-medium text-white bg-ink rounded-pill shadow-soft-xs hover:bg-ink/90 active:scale-95 transition-all"
              >
                {connecting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Activating Connection...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Save & Connect</span>
                  </>
                )}
              </button>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
