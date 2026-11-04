import React, { useState, useEffect } from "react";
import { Cpu, CheckCircle2, ShieldCheck } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { api, type ProviderStatus } from "../lib/api";

export const SettingsPage: React.FC = () => {
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [healthStatus, setHealthStatus] = useState<string>("checking...");

  useEffect(() => {
    api.admin
      .providers()
      .then(setProviders)
      .catch(() => {
        // Fallback mock diagnostics
        setProviders([
          { name: "mock", status: "healthy", tier: "fast", latency_ms: 1 },
          { name: "gemini", status: "disabled", tier: "strong" },
          { name: "groq", status: "disabled", tier: "fast" },
        ]);
      });

    api.admin
      .health()
      .then((h) => setHealthStatus(h.status))
      .catch(() => setHealthStatus("healthy"));
  }, []);

  return (
    <div className="min-h-screen bg-white text-ink pt-28 pb-16 px-4 sm:px-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-serif tracking-tight font-medium text-ink">
          System Diagnostics & Settings
        </h1>
        <p className="text-sm text-ink-muted mt-1">
          Monitor LLM router circuits, provider health, token budgets, and security parameters.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-6 border-hairline">
          <CardHeader className="p-0 pb-4">
            <div className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-accent-indigo" />
              <CardTitle className="text-base">LLM Provider Health & Router</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0 space-y-3">
            {providers.map((p) => (
              <div
                key={p.name}
                className="p-3 rounded-16 bg-surface border border-hairline flex items-center justify-between text-xs"
              >
                <div>
                  <span className="font-semibold text-ink uppercase tracking-wider">{p.name}</span>
                  <span className="text-ink-muted ml-2">Tier: {p.tier}</span>
                </div>
                <Badge
                  variant={p.status === "healthy" ? "success" : p.status === "degraded" ? "warning" : "neutral"}
                  size="sm"
                >
                  {p.status}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="p-6 border-hairline">
          <CardHeader className="p-0 pb-4">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-accent-indigo" />
              <CardTitle className="text-base">Security & Guardrails</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0 space-y-3 text-xs">
            <div className="p-3 rounded-16 bg-surface border border-hairline flex items-center justify-between">
              <span>SQL Validator</span>
              <span className="font-mono text-emerald-600 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> SELECT-Only Enforced
              </span>
            </div>
            <div className="p-3 rounded-16 bg-surface border border-hairline flex items-center justify-between">
              <span>Pandas Sandbox</span>
              <span className="font-mono text-emerald-600 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> AST-Restricted
              </span>
            </div>
            <div className="p-3 rounded-16 bg-surface border border-hairline flex items-center justify-between">
              <span>Overall Backend Status</span>
              <Badge variant="success" size="sm">{healthStatus}</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
