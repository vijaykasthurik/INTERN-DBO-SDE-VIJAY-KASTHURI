import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  KeyRound,
  RefreshCw,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Key,
  Layers,
  Gauge,
} from "lucide-react";
import { useAuthStore } from "../stores/authStore";
import { useAIConnectionStore } from "../stores/aiConnectionStore";
import { api } from "../lib/api";
import { cn } from "../lib/utils";

export const ProfilePage: React.FC = () => {
  const { user } = useAuthStore();
  const {
    connection,
    sharedPool,
    fetchConnection,
    fetchSharedStatus,
    openConnectModal,
    setFallbackPreference,
  } = useAIConnectionStore();

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    latency_ms?: number;
    model_used?: string;
  } | null>(null);

  const [removing, setRemoving] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState(false);

  useEffect(() => {
    fetchConnection();
    fetchSharedStatus();
  }, [fetchConnection, fetchSharedStatus]);

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.byok.test();
      setTestResult({
        success: true,
        message: res.message,
        latency_ms: res.latency_ms,
        model_used: res.model_used,
      });
      await fetchConnection();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Connection probe failed";
      setTestResult({
        success: false,
        message: msg,
      });
    } finally {
      setTesting(false);
    }
  };

  const handleRemoveKey = async () => {
    setRemoving(true);
    try {
      await api.byok.delete();
      await fetchConnection();
      setConfirmRemove(false);
      setTestResult(null);
    } catch (err: unknown) {
      console.error("Failed to remove key", err);
    } finally {
      setRemoving(false);
    }
  };

  const statusColor =
    connection?.status === "active"
      ? "text-emerald-700 bg-emerald-50 border-emerald-200"
      : connection?.status === "quota_exhausted" || connection?.status === "rate_limited"
      ? "text-amber-700 bg-amber-50 border-amber-200"
      : "text-rose-700 bg-rose-50 border-rose-200";

  return (
    <div className="min-h-screen bg-white pt-20 sm:pt-24 pb-24 md:pb-16 px-4 md:px-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* PAGE HEADER */}
        <div>
          <span className="text-[11px] font-semibold text-accent-indigo uppercase tracking-wider">
            User Account & Preferences
          </span>
          <h1 className="font-serif text-3xl font-medium text-ink tracking-tight mt-1">
            Account & AI Connections
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Manage your credentials, custom AI models, and shared server pool settings.
          </p>
        </div>

        {/* ACCOUNT INFO */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-6 bg-surface/50 border border-hairline rounded-24 flex items-center justify-between"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-pill bg-gradient-to-br from-indigo-100 to-violet-100 border border-hairline flex items-center justify-center text-accent-indigo font-serif text-xl font-medium">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-ink">
                {user?.full_name || "Lumen Analyst"}
              </h3>
              <p className="text-xs text-ink-muted">{user?.email}</p>
            </div>
          </div>
          <div className="text-right">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Active Member
            </span>
          </div>
        </motion.div>

        {/* AI CONNECTION CARD */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="border border-hairline rounded-24 bg-white shadow-soft-xs overflow-hidden"
        >
          <div className="p-6 border-b border-hairline bg-surface/30 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-pill bg-ink flex items-center justify-center text-white shadow-soft-xs">
                <Key className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-ink">
                  AI Provider Connection
                </h2>
                <p className="text-xs text-ink-muted">
                  Bring Your Own Key (BYOK) for unmetered data intelligence.
                </p>
              </div>
            </div>

            {connection?.connected && (
              <span
                className={cn(
                  "px-3 py-1 rounded-pill text-xs font-medium border capitalize flex items-center gap-1.5",
                  statusColor
                )}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-current" />
                {connection.status || "Active"}
              </span>
            )}
          </div>

          <div className="p-6 space-y-6">
            {connection?.connected ? (
              <>
                {/* CONNECTED KEY DETAILS */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="p-4 bg-surface/60 rounded-18 border border-hairline">
                    <span className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider block">
                      Active Provider
                    </span>
                    <span className="text-sm font-semibold text-ink mt-1 block">
                      {connection.provider_name || connection.provider_id?.toUpperCase()}
                    </span>
                    <span className="text-xs font-mono text-ink-muted mt-0.5 block">
                      Key: {connection.masked_key}
                    </span>
                  </div>

                  <div className="p-4 bg-surface/60 rounded-18 border border-hairline">
                    <span className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider block">
                      Configured Models
                    </span>
                    <div className="mt-1 space-y-0.5">
                      <p className="text-xs text-ink truncate">
                        <span className="text-ink-muted font-medium">Fast:</span>{" "}
                        <span className="font-mono">{connection.model_fast || "Default"}</span>
                      </p>
                      <p className="text-xs text-ink truncate">
                        <span className="text-ink-muted font-medium">Strong:</span>{" "}
                        <span className="font-mono">{connection.model_strong || "Default"}</span>
                      </p>
                    </div>
                  </div>

                  <div className="p-4 bg-surface/60 rounded-18 border border-hairline">
                    <span className="text-[10px] font-semibold text-ink-muted uppercase tracking-wider block">
                      Usage & Verification
                    </span>
                    <div className="mt-1 space-y-0.5">
                      <p className="text-xs text-ink">
                        <span className="text-ink-muted font-medium">Requests:</span>{" "}
                        <span className="font-semibold">{connection.request_count || 0}</span>
                      </p>
                      <p className="text-xs text-ink-muted">
                        Verified {connection.last_verified_at ? new Date(connection.last_verified_at * 1000).toLocaleTimeString() : "recently"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* FALLBACK PREFERENCE TOGGLE */}
                <div className="p-4 bg-indigo-50/40 border border-indigo-100 rounded-18 flex items-center justify-between">
                  <div className="space-y-0.5">
                    <h4 className="text-xs font-semibold text-ink">
                      Smart Fallback to Shared Server Chain
                    </h4>
                    <p className="text-[11px] text-ink-muted">
                      If your key expires or exhausts quota, smoothly transition to the shared pool (Groq / Z.AI / HF) instead of failing.
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={connection.allow_shared_fallback ?? true}
                      onChange={(e) => setFallbackPreference(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-10 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-accent-indigo"></div>
                  </label>
                </div>

                {/* TEST RESULT ALERT */}
                {testResult && (
                  <div
                    className={cn(
                      "p-3 rounded-16 border flex items-start gap-2.5 text-xs animate-fadeIn",
                      testResult.success
                        ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                        : "bg-rose-50 border-rose-200 text-rose-800"
                    )}
                  >
                    {testResult.success ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-rose-600 mt-0.5 shrink-0" />
                    )}
                    <div>
                      <p className="font-semibold">{testResult.message}</p>
                      {testResult.latency_ms && (
                        <p className="text-[11px] mt-0.5">
                          Probe round-trip: {testResult.latency_ms}ms via{" "}
                          <span className="font-mono">{testResult.model_used}</span>
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* BUTTON ACTIONS */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={testing}
                      onClick={handleTestConnection}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-ink bg-surface hover:bg-surface/80 border border-hairline rounded-pill transition-all active:scale-95"
                    >
                      <RefreshCw className={cn("w-3.5 h-3.5", testing && "animate-spin text-accent-indigo")} />
                      <span>{testing ? "Testing..." : "Test Connection"}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => openConnectModal(connection.provider_id)}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-ink bg-surface hover:bg-surface/80 border border-hairline rounded-pill transition-all active:scale-95"
                    >
                      <Layers className="w-3.5 h-3.5 text-accent-indigo" />
                      <span>Replace Key</span>
                    </button>
                  </div>

                  {!confirmRemove ? (
                    <button
                      type="button"
                      onClick={() => setConfirmRemove(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-50 rounded-pill transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      <span>Remove Key</span>
                    </button>
                  ) : (
                    <div className="flex items-center gap-2 animate-fadeIn">
                      <span className="text-xs text-rose-700 font-medium">Permanently delete?</span>
                      <button
                        type="button"
                        disabled={removing}
                        onClick={handleRemoveKey}
                        className="px-2.5 py-1 text-xs font-medium text-white bg-rose-600 hover:bg-rose-700 rounded-pill"
                      >
                        {removing ? "Deleting..." : "Confirm"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmRemove(false)}
                        className="px-2 py-1 text-xs text-ink-muted hover:text-ink"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              </>
            ) : (
              /* NO KEY CONNECTED EMPTY STATE */
              <div className="text-center py-8 px-4 space-y-4">
                <div className="w-12 h-12 rounded-pill bg-surface border border-hairline flex items-center justify-center text-ink-muted mx-auto">
                  <KeyRound className="w-6 h-6 text-emerald-700" />
                </div>
                <div className="max-w-md mx-auto space-y-1">
                  <h3 className="text-sm font-semibold text-ink">
                    No Personal Model Key Connected
                  </h3>
                  <p className="text-xs text-ink-muted leading-relaxed">
                    You are currently using Lumen&apos;s free shared model pool. Connect your personal API key (Groq, Gemini, OpenAI, Anthropic, DeepSeek, etc.) for direct private queries with zero shared rate limits.
                  </p>
                </div>
                <div>
                  <button
                    type="button"
                    onClick={() => openConnectModal()}
                    className="inline-flex items-center gap-2 px-5 py-2 text-xs font-medium text-white bg-ink rounded-pill shadow-soft-xs hover:bg-ink/90 active:scale-95 transition-all"
                  >
                    <Key className="w-3.5 h-3.5" />
                    <span>Connect your AI Key</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </motion.div>

        {/* SHARED SERVER POOL HEALTH */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="border border-hairline rounded-24 bg-white p-6 shadow-soft-xs space-y-4"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Gauge className="w-4 h-4 text-accent-indigo" />
              <h2 className="text-sm font-semibold text-ink">
                Shared Server Model Pool (Demo Mode)
              </h2>
            </div>
            <span className="text-xs text-ink-muted">
              {sharedPool?.user_hourly_remaining ?? 30} of {sharedPool?.user_hourly_limit ?? 30} free requests left this hour
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* GROQ MULTI-KEY ROTATION */}
            <div className="p-3.5 bg-surface/50 border border-hairline rounded-16 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-ink">Groq 7-Key Pool</span>
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
              </div>
              <p className="text-[11px] text-ink-muted">
                {sharedPool?.groq_active_keys ?? 7} active keys (round-robin)
              </p>
              <div className="flex items-center gap-1 pt-1">
                {[...Array(7)].map((_, i) => (
                  <span
                    key={i}
                    className="w-2 h-2 rounded-full bg-emerald-400"
                    title={`Groq Key ${i + 1} Healthy`}
                  />
                ))}
              </div>
            </div>

            {/* Z.AI GLM-4 */}
            <div className="p-3.5 bg-surface/50 border border-hairline rounded-16 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-ink">Z.AI (GLM-4)</span>
                <span
                  className={cn(
                    "w-2 h-2 rounded-full",
                    sharedPool?.zai_configured ? "bg-emerald-500" : "bg-slate-300"
                  )}
                />
              </div>
              <p className="text-[11px] text-ink-muted">
                {sharedPool?.zai_configured ? "Secondary failover configured" : "Standby"}
              </p>
            </div>

            {/* HUGGING FACE */}
            <div className="p-3.5 bg-surface/50 border border-hairline rounded-16 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-ink">Hugging Face</span>
                <span
                  className={cn(
                    "w-2 h-2 rounded-full",
                    sharedPool?.hf_configured ? "bg-emerald-500" : "bg-slate-300"
                  )}
                />
              </div>
              <p className="text-[11px] text-ink-muted">
                {sharedPool?.hf_configured ? "Qwen 2.5 7B Router Active" : "Standby"}
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};
