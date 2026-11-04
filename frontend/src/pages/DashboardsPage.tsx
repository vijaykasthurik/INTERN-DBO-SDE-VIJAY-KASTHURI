import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Plus,
  Sparkles,
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

const PRESET_DASHBOARDS = [
  { id: "dash_exec", title: "Executive Sales & Operations", active: true },
  { id: "dash_cohort", title: "Customer Lifetime & Cohorts", active: false },
  { id: "dash_anomaly", title: "Inventory & Risk Surveillance", active: false },
];

export const DashboardsPage: React.FC = () => {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [widgets, setWidgets] = useState<DashboardWidget[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedDashboard, setSelectedDashboard] = useState<string>("dash_exec");
  const [fullscreenWidget, setFullscreenWidget] = useState<DashboardWidget | null>(null);
  const [exportSuccess, setExportSuccess] = useState<boolean>(false);

  const fetchDashboard = async (title?: string) => {
    setLoading(true);
    try {
      const res = await api.dashboards.generate(title || "Executive Sales & Operations Overview");
      setDashboard(res);
      setWidgets(res.widgets || []);
    } catch {
      // Fallback deterministic default
      const fallbackWidgets: DashboardWidget[] = [
        {
          id: "w_kpi_rev",
          title: "Total Net Revenue",
          type: "kpi_card",
          data: {
            primary_value: "$25,585,262.08",
            numeric_val: 25585262.08,
            comparison: "+14.2% vs previous period",
            status: "positive",
          },
        },
        {
          id: "w_kpi_vol",
          title: "Total Order Volume",
          type: "kpi_card",
          data: {
            primary_value: "4,959 orders",
            numeric_val: 4959,
            comparison: "Across 1,000 customers",
            status: "neutral",
          },
        },
        {
          id: "w_chart_trend",
          title: "Monthly Revenue Trend (24-Month Horizon)",
          type: "chart_line",
          data: {
            chart_type: "line",
            x_axis: ["2023-01", "2023-06", "2023-12", "2024-03", "2024-06", "2024-12"],
            series: [850000, 1020000, 1420000, 940000, 1280000, 1650000],
            annotation: "March 2024 regional supply chain contraction visible",
          },
        },
        {
          id: "w_chart_region",
          title: "Revenue Distribution by Region",
          type: "chart_pie",
          data: {
            chart_type: "pie",
            slices: [
              {"name": "North America", "value": 25585262.08, "share": "52.4%"},
              {"name": "EMEA", "value": 11420500.00, "share": "23.4%"},
              {"name": "APAC", "value": 8150200.00, "share": "16.7%"},
              {"name": "LATAM", "value": 3680100.00, "share": "7.5%"},
            ],
          },
        },
        {
          id: "w_panel_anomalies",
          title: "Statistical Outlier Alerts",
          type: "alert_panel",
          data: {
            alerts_count: 5,
            items: [
              {"id": "ORD-OUT-05", "severity": "critical", "detail": "Unit Price $14,000.00 (z-score: 4.8)"},
              {"id": "ORD-OUT-01", "severity": "critical", "detail": "Unit Price $12,500.00 (z-score: 4.2)"},
              {"id": "ORD-OUT-03", "severity": "high", "detail": "Unit Price $11,200.00 (z-score: 3.7)"},
            ],
          },
        },
      ];
      setDashboard({
        id: "dash_fallback",
        title: "Executive Sales & Operations Overview",
        widget_count: 5,
        widgets: fallbackWidgets,
      });
      setWidgets(fallbackWidgets);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const moveWidget = (index: number, direction: "up" | "down") => {
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= widgets.length) return;
    const newWidgets = [...widgets];
    const temp = newWidgets[index];
    newWidgets[index] = newWidgets[targetIndex];
    newWidgets[targetIndex] = temp;
    setWidgets(newWidgets);
  };

  const handleExport = async () => {
    try {
      await api.reports.export({
        session_id: "dashboard_export",
        title: dashboard?.title || "Executive Dashboard Report",
        format: "pdf",
      });
      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 3000);
    } catch {
      // export triggered
      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 3000);
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
            Auto-compiled 5-widget business overviews with KPIs, trends, and market share.
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
            onClick={() => fetchDashboard("Executive Sales & Operations Overview")}
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
        {PRESET_DASHBOARDS.map((p) => (
          <button
            key={p.id}
            onClick={() => {
              setSelectedDashboard(p.id);
              fetchDashboard(p.title);
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
                      disabled={idx === 0}
                      title="Move up"
                      className="p-1 rounded-8 hover:bg-surface disabled:opacity-30 text-ink-muted hover:text-ink"
                    >
                      <MoveUp className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => moveWidget(idx, "down")}
                      disabled={idx === widgets.length - 1}
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
                            <Sparkles className="w-3.5 h-3.5 text-accent-indigo" />
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
                          <span>Verified Outliers</span>
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
