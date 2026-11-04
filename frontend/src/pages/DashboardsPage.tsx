import { useLocation } from "react-router-dom";
import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Plus,
  Activity,
  Maximize2,
  TrendingUp,
  AlertTriangle,
  MoveUp,
  MoveDown,
  FileDown,
  Layers,
  Check,
} from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Dialog } from "../components/ui/Dialog";
import { NumberCountUp } from "../components/ui/NumberCountUp";
import { ChartRenderer } from "../features/workspace/ChartRenderer";
import { api, type DashboardResponse, type DashboardWidget } from "../lib/api";

interface AnomalyItem {
  id: string;
  severity: string;
  detail: string;
}

interface PieSlice {
  name: string;
  value: number;
  share?: string;
}

interface DashboardScope { id: string; title: string }

export const DashboardsPage: React.FC = () => {
  const location = useLocation();
  const uploadWarnings = (location.state as {uploadWarnings?:string[]}|null)?.uploadWarnings || [];
  const [savingOrder,setSavingOrder]=useState(false);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [widgets, setWidgets] = useState<DashboardWidget[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedDashboard, setSelectedDashboard] = useState<string>("dash_exec");
  const [fullscreenWidget, setFullscreenWidget] = useState<DashboardWidget | null>(null);
  const [exportSuccess, setExportSuccess] = useState<boolean>(false);
  const [exportError, setExportError] = useState<string | null>(uploadWarnings.length ? uploadWarnings.join("; ") : null);
  const [scopes, setScopes] = useState<DashboardScope[]>([{ id: "combined", title: "All files (combined)" }]);

  const fetchDashboard = useCallback(async (title?: string, scope = "combined") => {
    setLoading(true);
    try {
      const res = await api.dashboards.generate(title || "Executive Sales & Operations Overview", scope);
      setDashboard(res);
      setWidgets(res.widgets || []);
    } catch (err: unknown) {
      setDashboard(null);
      setWidgets([]);
      setExportError(err instanceof Error ? err.message : "Dashboard generation failed.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    api.datasets.list().then((datasets) => {
      const groups = new Map<string,typeof datasets>();
      for(const dataset of datasets){const source=dataset.source_filename||dataset.name;groups.set(source,[...(groups.get(source)||[]),dataset]);}
      const available = [{id:"combined",title:"All files (combined)"},...Array.from(groups.entries()).map(([source,items])=>({id:items.length===1?String(items[0].id):`file:${source}`,title:items.length===1?items[0].name:source}))];
      setScopes(available);
      return fetchDashboard(undefined, "combined");
    }).catch((err: unknown) => {
      setExportError(err instanceof Error ? err.message : "Unable to load dashboard scopes.");
    });
  }, [fetchDashboard]);

  const moveWidget = async (index: number, direction: "up" | "down") => {
    if(savingOrder)return;
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= widgets.length) return;
    const newWidgets = [...widgets];
    const temp = newWidgets[index];
    newWidgets[index] = newWidgets[targetIndex];
    newWidgets[targetIndex] = temp;
    setWidgets(newWidgets);
    if(dashboard) {
      setSavingOrder(true);
      try {await api.dashboards.reorder(dashboard.id,newWidgets.map(widget=>widget.id));}
      catch(error) {setWidgets(widgets);setExportError(error instanceof Error?error.message:"Widget order could not be saved.");}
      finally {setSavingOrder(false);}
    }
  };

  const handleExport = async () => {
    setExportError(null);
    try {
      if (!dashboard) throw new Error("Generate a dashboard before exporting it.");
      const artifact = await api.reports.export({
        title: dashboard?.title || "Executive Dashboard Report",
        format: "pdf",
        dashboard,
      });
      const response = await api.reports.download(artifact.download_url);
      const blobUrl = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = blobUrl;
      anchor.download = `${artifact.report_id}.pdf`;
      anchor.click();
      URL.revokeObjectURL(blobUrl);
      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 3000);
    } catch (err: unknown) {
      setExportError(err instanceof Error ? err.message : "Dashboard report export failed.");
    }
  };

  const formatLineChartSpec = (data: Record<string, unknown>) => ({
    xAxis: {
      type: "category",
      data: (data.x_axis as string[]) || [],
      axisLine: { lineStyle: { color: "rgba(15, 23, 42, 0.15)" } },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: "rgba(15, 23, 42, 0.05)" } },
    },
    series: [
      {
        data: (data.series as number[]) || [],
        type: "line",
        smooth: true,
        symbolSize: 8,
        itemStyle: { color: "#6366F1" },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(99, 102, 241, 0.35)" },
              { offset: 1, color: "rgba(99, 102, 241, 0.0)" },
            ],
          },
        },
      },
    ],
  });

  const formatPieChartSpec = (data: Record<string, unknown>) => ({
    tooltip: { trigger: "item", formatter: "{b}: ${c} ({d}%)" },
    series: [
      {
        type: "pie",
        radius: ["40%", "72%"],
        center: ["50%", "50%"],
        itemStyle: { borderRadius: 8, borderColor: "#fff", borderWidth: 2 },
        data: ((data.slices as PieSlice[]) || []).map((s) => ({ name: s.name, value: s.value })),
      },
    ],
  });

  return (
    <div className="min-h-screen bg-white text-ink pt-28 pb-16 px-4 sm:px-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs uppercase tracking-widest text-ink-muted font-medium">
              Live Analytical Canvas
            </span>
          </div>
          <h1 className="text-3xl font-serif tracking-tight font-medium text-ink">
            Executive Dashboards
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Live summaries computed from your selected files in the analytical database.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="md"
            onClick={handleExport}
            className="text-xs"
          >
            {exportSuccess ? (
              <>
                <Check className="w-4 h-4 mr-1.5 text-emerald-600" />
                Report Queued
              </>
            ) : (
              <>
                <FileDown className="w-4 h-4 mr-1.5" />
                Export PDF
              </>
            )}
          </Button>

          <Button
            size="md"
            onClick={() => fetchDashboard("Executive Sales & Operations Overview", selectedDashboard)}
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Compiling...
              </span>
            ) : (
              <>
                <Plus className="w-4 h-4 mr-2" />
                Generate Dashboard
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Preset Dashboard Tabs */}
      <div className="flex items-center gap-2 mb-6 border-b border-hairline pb-3 overflow-x-auto">
        <Layers className="w-4 h-4 text-ink-muted mr-1 flex-shrink-0" />
        {scopes.map((p) => (
          <button
            key={p.id}
            onClick={() => {
              setSelectedDashboard(p.id);
              void fetchDashboard(p.title, p.id);
            }}
            className={`px-3 py-1.5 text-xs rounded-full font-medium transition-colors whitespace-nowrap ${
              selectedDashboard === p.id
                ? "bg-ink text-white shadow-soft-xs"
                : "bg-surface hover:bg-slate-100 text-ink-muted hover:text-ink"
            }`}
          >
            {p.title}
          </button>
        ))}
      </div>

      {exportError && <div role="alert" className="mb-5 p-3 rounded-16 bg-rose-50 border border-rose-100 text-rose-700 text-sm">{exportError}</div>}
      {dashboard?.explanation && <p className="mb-5 text-xs text-ink-muted">{dashboard.explanation}</p>}
      {!loading && !dashboard && <Card className="p-8 text-center text-sm text-ink-muted">Upload a dataset to generate a live dashboard.</Card>}

      {/* Widgets Grid with Staggered Entrance */}
      <motion.div
        layout
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-6"
      >
        <AnimatePresence>
          {widgets.map((widget, idx) => {
            const isFullWidth = widget.type === "chart_line" || widget.type === "chart_pie";
            const colSpan = isFullWidth
              ? "lg:col-span-6"
              : widget.type === "kpi_card"
              ? "lg:col-span-4"
              : "lg:col-span-4";

            return (
              <motion.div
                key={widget.id}
                layout
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.4, delay: idx * 0.08 }}
                className={`${colSpan} flex flex-col`}
              >
                <Card className="h-full flex flex-col justify-between border-hairline hover:shadow-soft-md transition-shadow group relative">
                  {/* Reorder and Action Bar */}
                  <div className="absolute top-3 right-3 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10 bg-white/90 backdrop-blur-sm rounded-12 p-1 border border-hairline shadow-soft-xs">
                    <button
                      onClick={() => moveWidget(idx, "up")}
                      disabled={idx === 0 || savingOrder}
                      title="Move up"
                      className="p-1 rounded-8 hover:bg-surface disabled:opacity-30 text-ink-muted hover:text-ink"
                    >
                      <MoveUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => moveWidget(idx, "down")}
                      disabled={idx === widgets.length - 1 || savingOrder}
                      title="Move down"
                      className="p-1 rounded-8 hover:bg-surface disabled:opacity-30 text-ink-muted hover:text-ink"
                    >
                      <MoveDown className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => setFullscreenWidget(widget)}
                      title="Fullscreen"
                      className="p-1 rounded-8 hover:bg-surface text-ink-muted hover:text-ink"
                    >
                      <Maximize2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <CardHeader className="pb-2">
                    <div className="flex items-center gap-2">
                      {widget.type === "kpi_card" && (
                        <TrendingUp className="w-4 h-4 text-accent-indigo" />
                      )}
                      {widget.type === "alert_panel" && (
                        <AlertTriangle className="w-4 h-4 text-amber-500" />
                      )}
                      {widget.type.startsWith("chart") && (
                        <LayoutDashboard className="w-4 h-4 text-accent-indigo" />
                      )}
                      <CardTitle className="text-sm font-semibold text-ink">
                        {widget.title}
                      </CardTitle>
                    </div>
                  </CardHeader>

                  <CardContent className="pt-2 flex-1 flex flex-col justify-center">
                    {typeof widget.data.sql === "string" && <details className="text-xs text-ink-muted"><summary>SQL</summary><pre className="overflow-x-auto whitespace-pre-wrap">{widget.data.sql}</pre></details>}
                    {/* KPI Widget */}
                    {widget.type === "kpi_card" && (
                      <div className="py-2">
                        <div className="text-3xl font-bold tracking-tight text-ink font-mono mb-1">
                          {widget.data.numeric_val ? (
                            <NumberCountUp
                              value={Number(widget.data.numeric_val)}
                              prefix={String(widget.data.primary_value || "").startsWith("$") ? "$" : ""}
                              decimals={2}
                            />
                          ) : (
                            String(widget.data.primary_value || "")
                          )}
                        </div>
                        {Boolean(widget.data.comparison) && (
                          <div className="flex items-center gap-2 text-xs">
                            <Badge
                              variant={widget.data.status === "positive" ? "success" : "neutral"}
                              size="sm"
                            >
                              {String(widget.data.comparison)}
                            </Badge>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Line Chart Widget */}
                    {widget.type === "chart_line" && (
                      <div className="pt-2">
                        <ChartRenderer
                          title={widget.title}
                          spec={formatLineChartSpec(widget.data)}
                        />
                        {Boolean(widget.data.annotation) && (
                          <p className="text-xs text-ink-muted mt-2 italic flex items-center gap-1.5">
                            <Activity className="w-3.5 h-3.5 text-emerald-700" />
                            {String(widget.data.annotation)}
                          </p>
                        )}
                      </div>
                    )}

                    {/* Pie Chart Widget */}
                    {widget.type === "chart_pie" && (
                      <div className="pt-2">
                        <ChartRenderer
                          title={widget.title}
                          spec={formatPieChartSpec(widget.data)}
                        />
                      </div>
                    )}

                    {/* Anomaly Alerts Panel */}
                    {widget.type === "alert_panel" && (
                      <div className="space-y-2 py-2">
                        <div className="flex items-center justify-between text-xs text-ink-muted mb-1">
                          <span>Computed observations</span>
                          <Badge variant="warning" size="sm">
                            {Number(widget.data.alerts_count || ((widget.data.items as AnomalyItem[])?.length) || 0)} Flagged
                          </Badge>
                        </div>
                        <div className="space-y-2">
                          {((widget.data.items as AnomalyItem[]) || []).map((item, i) => (
                            <div
                              key={i}
                              className="p-2.5 rounded-12 bg-amber-50/50 border border-amber-200/60 text-xs flex items-center justify-between"
                            >
                              <div className="font-mono text-ink font-medium">
                                {item.id}
                              </div>
                              <div className="text-ink-muted text-right">
                                {item.detail}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </motion.div>

      {/* Fullscreen Widget Modal */}
      <Dialog
        isOpen={Boolean(fullscreenWidget)}
        onClose={() => setFullscreenWidget(null)}
        title={fullscreenWidget?.title || "Widget Detail"}
      >
        <div className="p-4 space-y-4">
          {fullscreenWidget?.type === "kpi_card" && (
            <div className="text-center py-8">
              <div className="text-5xl font-bold font-mono text-ink mb-2">
                {String(fullscreenWidget.data.primary_value || "")}
              </div>
              <p className="text-sm text-ink-muted">
                {String(fullscreenWidget.data.comparison || "")}
              </p>
            </div>
          )}

          {fullscreenWidget?.type === "chart_line" && (
            <div>
              <ChartRenderer
                title={fullscreenWidget.title}
                spec={formatLineChartSpec(fullscreenWidget.data)}
              />
              <p className="text-xs text-ink-muted mt-3">
                {String(fullscreenWidget.data.annotation || "")}
              </p>
            </div>
          )}

          {fullscreenWidget?.type === "chart_pie" && (
            <div>
              <ChartRenderer
                title={fullscreenWidget.title}
                spec={formatPieChartSpec(fullscreenWidget.data)}
              />
            </div>
          )}

          {fullscreenWidget?.type === "alert_panel" && (
            <div className="space-y-3">
              {((fullscreenWidget.data.items as AnomalyItem[]) || []).map((item, i) => (
                <div
                  key={i}
                  className="p-4 rounded-16 bg-surface border border-hairline flex items-center justify-between"
                >
                  <span className="font-mono font-semibold">{item.id}</span>
                  <span className="text-sm text-ink-muted">{item.detail}</span>
                  <Badge variant="warning">{item.severity}</Badge>
                </div>
              ))}
            </div>
          )}

          <div className="flex justify-end pt-4">
            <Button variant="secondary" onClick={() => setFullscreenWidget(null)}>
              Close
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};
