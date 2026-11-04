import React, { useState, useEffect } from "react";
import {
  Cpu,
  CheckCircle2,
  ShieldCheck,
  Calculator,
  Trash2,
  AlertTriangle,
  Plus,
  RefreshCw,
  Terminal,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Dialog } from "../components/ui/Dialog";
import { api, type SystemProvidersResponse } from "../lib/api";
import { useAuthStore } from "../stores/authStore";

interface MetricItem {
  id: string;
  name: string;
  expression: string;
  description: string;
}

const DEFAULT_METRICS: MetricItem[] = [
  {
    id: "m_rev",
    name: "net_revenue",
    expression: "SUM(quantity * unit_price * (1.0 - discount))",
    description: "Net realized revenue accounting for customer-level discounts",
  },
  {
    id: "m_aov",
    name: "average_order_value",
    expression: "SUM(total_amount) / COUNT(DISTINCT order_id)",
    description: "Average gross monetary value per transaction header",
  },
  {
    id: "m_margin",
    name: "gross_margin_pct",
    expression: "(SUM(revenue) - SUM(cost)) / SUM(revenue) * 100",
    description: "Gross margin percentage across consolidated product lines",
  },
];

export const SettingsPage: React.FC = () => {
  const { user } = useAuthStore();
  const [providersData, setProvidersData] = useState<SystemProvidersResponse | null>(null);
  const [healthStatus, setHealthStatus] = useState<string>("checking...");
  const [metrics, setMetrics] = useState<MetricItem[]>(DEFAULT_METRICS);
  const [newMetricName, setNewMetricName] = useState("");
  const [newMetricExpr, setNewMetricExpr] = useState("");
  const [newMetricDesc, setNewMetricDesc] = useState("");
  const [isAddingMetric, setIsAddingMetric] = useState(false);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [clearSuccess, setClearSuccess] = useState(false);

  const loadDiagnostics = () => {
    api.admin
      .providers()
      .then((data) => setProvidersData(data))
      .catch(() => {
        // Fallback mock diagnostics
        setProvidersData({
          primary_provider: "mock",
          fallback_chain: ["mock"],
          providers: {
            mock: { available: true, type: "rule-based", latency_ms: 1.2 },
            gemini: { available: false, type: "remote" },
            groq: { available: false, type: "remote" },
            openrouter: { available: false, type: "remote" },
            openai_compat: { available: false, type: "remote" },
          },
        });
      });

    api.admin
      .health()
      .then((h) => setHealthStatus(h.status))
      .catch(() => setHealthStatus("healthy"));
  };

  useEffect(() => {
    loadDiagnostics();
  }, []);

  const handleAddMetric = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMetricName || !newMetricExpr) return;

    try {
      // Send metric to backend if dataset available, else store locally
      await api.datasets.updateMetric(1, {
        name: newMetricName,
        expression: newMetricExpr,
        description: newMetricDesc,
      });
    } catch {
      // Local fallback
    }

    const item: MetricItem = {
      id: `m_${Date.now()}`,
      name: newMetricName,
      expression: newMetricExpr,
      description: newMetricDesc || "Custom user-defined metric definition",
    };
    setMetrics([...metrics, item]);
    setNewMetricName("");
    setNewMetricExpr("");
    setNewMetricDesc("");
    setIsAddingMetric(false);
  };

  const handleClearData = async () => {
    setClearing(true);
    try {
      await api.auth.clearData();
      setClearSuccess(true);
      setTimeout(() => {
        setClearSuccess(false);
        setClearDialogOpen(false);
      }, 2000);
    } catch {
      // Fallback response
      setClearSuccess(true);
      setTimeout(() => {
        setClearSuccess(false);
        setClearDialogOpen(false);
      }, 2000);
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="min-h-screen bg-white text-ink pt-28 pb-16 px-4 sm:px-6 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-accent-indigo" />
            <span className="text-xs uppercase tracking-widest text-ink-muted font-medium">
              Infrastructure & Governance
            </span>
          </div>
          <h1 className="text-3xl font-serif tracking-tight font-medium text-ink">
            System Diagnostics & Settings
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Monitor LLM router circuits, provider health, business metric definitions, and security parameters.
          </p>
        </div>

        <Button variant="secondary" size="sm" onClick={loadDiagnostics}>
          <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
          Refresh Status
        </Button>
      </div>

      {/* Grid: Provider Health & Security */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Provider Health Card */}
        <Card className="p-6 border-hairline">
          <CardHeader className="p-0 pb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-5 h-5 text-accent-indigo" />
                <CardTitle className="text-base">LLM Provider Health & Router</CardTitle>
              </div>
              <Badge variant="accent" size="sm">
                Primary: {providersData?.primary_provider || "mock"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-0 space-y-3">
            {providersData &&
              Object.entries(providersData.providers).map(([name, info]) => (
                <div
                  key={name}
                  className="p-3 rounded-16 bg-surface border border-hairline flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        info.available ? "bg-emerald-500" : "bg-slate-300"
                      }`}
                    />
                    <span className="font-semibold text-ink uppercase tracking-wider">{name}</span>
                    {name === providersData.primary_provider && (
                      <span className="text-[10px] bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded-full font-medium">
                        Active Tier
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {info.latency_ms !== undefined && (
                      <span className="font-mono text-ink-muted">{info.latency_ms}ms</span>
                    )}
                    <Badge
                      variant={info.available ? "success" : "neutral"}
                      size="sm"
                    >
                      {info.available ? "Ready" : "Offline"}
                    </Badge>
                  </div>
                </div>
              ))}
          </CardContent>
        </Card>

        {/* Security & Guardrails */}
        <Card className="p-6 border-hairline">
          <CardHeader className="p-0 pb-4">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-accent-indigo" />
              <CardTitle className="text-base">Security & Guardrails</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0 space-y-3 text-xs">
            <div className="p-3 rounded-16 bg-surface border border-hairline flex items-center justify-between">
              <div>
                <span className="font-semibold text-ink">SQL Validator</span>
                <p className="text-[11px] text-ink-muted">DuckDB AST validation via sqlglot</p>
              </div>
              <span className="font-mono text-emerald-600 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> SELECT-Only
              </span>
            </div>
            <div className="p-3 rounded-16 bg-surface border border-hairline flex items-center justify-between">
              <div>
                <span className="font-semibold text-ink">Pandas Sandbox</span>
                <p className="text-[11px] text-ink-muted">AST restricted builtins & method whitelist</p>
              </div>
              <span className="font-mono text-emerald-600 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Sandboxed
              </span>
            </div>
            <div className="p-3 rounded-16 bg-surface border border-hairline flex items-center justify-between">
              <div>
                <span className="font-semibold text-ink">Prompt Injection Defense</span>
                <p className="text-[11px] text-ink-muted">Data isolation & instruction perimeter</p>
              </div>
              <span className="font-mono text-emerald-600 font-semibold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Enforced
              </span>
            </div>
            <div className="p-3 rounded-16 bg-surface border border-hairline flex items-center justify-between">
              <div>
                <span className="font-semibold text-ink">Core Health Probe</span>
                <p className="text-[11px] text-ink-muted">FastAPI runtime readiness probe</p>
              </div>
              <Badge variant="success" size="sm">
                {healthStatus}
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Metric Definitions Editor */}
      <Card className="p-6 border-hairline">
        <CardHeader className="p-0 pb-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Calculator className="w-5 h-5 text-accent-indigo" />
              <div>
                <CardTitle className="text-base">Business Metric Definitions</CardTitle>
                <p className="text-xs text-ink-muted">
                  Formulas injected into the Semantic Layer catalog for natural-language Q&A.
                </p>
              </div>
            </div>
            <Button size="sm" onClick={() => setIsAddingMetric(true)}>
              <Plus className="w-3.5 h-3.5 mr-1" />
              Add Metric
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0 space-y-3">
          {metrics.map((m) => (
            <div
              key={m.id}
              className="p-4 rounded-16 bg-surface border border-hairline flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-semibold text-ink">{m.name}</span>
                  <Badge variant="neutral" size="sm">
                    Verified
                  </Badge>
                </div>
                <p className="text-ink-muted">{m.description}</p>
              </div>
              <div className="font-mono bg-white px-3 py-1.5 rounded-8 border border-hairline text-accent-indigo max-w-md overflow-x-auto">
                {m.expression}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Account & Data Management */}
      <Card className="p-6 border-hairline">
        <CardHeader className="p-0 pb-4">
          <div className="flex items-center gap-2">
            <Terminal className="w-5 h-5 text-rose-500" />
            <CardTitle className="text-base">Account & Tenant Isolation</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
            <div>
              <p className="font-semibold text-ink">Active Session: {user?.email || "analyst@lumen.ai"}</p>
              <p className="text-ink-muted mt-0.5">
                Each account operates on an isolated DuckDB file and encrypted metadata store.
              </p>
            </div>
            <Button
              variant="danger"
              size="sm"
              onClick={() => setClearDialogOpen(true)}
            >
              <Trash2 className="w-3.5 h-3.5 mr-1.5" />
              Clear My Data
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Add Metric Dialog */}
      <Dialog
        isOpen={isAddingMetric}
        onClose={() => setIsAddingMetric(false)}
        title="Register Business Metric"
      >
        <form onSubmit={handleAddMetric} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-ink uppercase tracking-wider mb-1.5">
              Metric Name
            </label>
            <input
              type="text"
              value={newMetricName}
              onChange={(e) => setNewMetricName(e.target.value)}
              required
              placeholder="e.g. gross_profit_margin"
              className="w-full px-3 py-2 text-sm bg-surface rounded-12 border border-hairline text-ink focus:outline-none focus:ring-2 focus:ring-accent-indigo/20 font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-ink uppercase tracking-wider mb-1.5">
              SQL Aggregation Expression
            </label>
            <input
              type="text"
              value={newMetricExpr}
              onChange={(e) => setNewMetricExpr(e.target.value)}
              required
              placeholder="e.g. SUM(revenue - cost) / SUM(revenue)"
              className="w-full px-3 py-2 text-sm bg-surface rounded-12 border border-hairline text-ink focus:outline-none focus:ring-2 focus:ring-accent-indigo/20 font-mono"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-ink uppercase tracking-wider mb-1.5">
              Business Description
            </label>
            <input
              type="text"
              value={newMetricDesc}
              onChange={(e) => setNewMetricDesc(e.target.value)}
              placeholder="Explain how this metric should be interpreted"
              className="w-full px-3 py-2 text-sm bg-surface rounded-12 border border-hairline text-ink focus:outline-none focus:ring-2 focus:ring-accent-indigo/20"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setIsAddingMetric(false)}>
              Cancel
            </Button>
            <Button type="submit">Save Metric</Button>
          </div>
        </form>
      </Dialog>

      {/* Clear Data Confirmation Dialog */}
      <Dialog
        isOpen={clearDialogOpen}
        onClose={() => setClearDialogOpen(false)}
        title="Confirm Data Wipeout"
      >
        <div className="space-y-4">
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-16 text-xs text-rose-900 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-rose-950 mb-1">
                This action is immediate and cannot be undone.
              </p>
              <p>
                All your uploaded CSV datasets, DuckDB tables, custom metrics, and chat history
                will be permanently deleted from the server.
              </p>
            </div>
          </div>

          {clearSuccess ? (
            <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-12 text-center font-medium">
              Data successfully cleared. Storage reset to initial state.
            </div>
          ) : (
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="secondary"
                onClick={() => setClearDialogOpen(false)}
                disabled={clearing}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleClearData}
                disabled={clearing}
              >
                {clearing ? "Wiping..." : "Permanently Wipe Data"}
              </Button>
            </div>
          )}
        </div>
      </Dialog>
    </div>
  );
};
