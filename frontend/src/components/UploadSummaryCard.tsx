import React from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, AlertTriangle, ArrowRight, Table, Layers } from "lucide-react";
import { motion } from "framer-motion";

export interface DatasetSummaryItem {
  id: string | number;
  name: string;
  table_name?: string;
  row_count: number;
  column_count: number;
  quality_score?: number;
}

interface UploadSummaryCardProps {
  datasets: DatasetSummaryItem[];
  onDismiss?: () => void;
}

export const UploadSummaryCard: React.FC<UploadSummaryCardProps> = ({ datasets, onDismiss }) => {
  if (!datasets || datasets.length === 0) return null;

  const totalRows = datasets.reduce((acc, d) => acc + (d.row_count || 0), 0);
  const totalCols = datasets.reduce((acc, d) => acc + (d.column_count || 0), 0);
  const scored = datasets.filter((d) => typeof d.quality_score === "number");
  const avgQuality = scored.length
    ? Math.round(scored.reduce((acc, d) => acc + (d.quality_score || 0), 0) / scored.length)
    : 100;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full bg-white border border-hairline rounded-24 p-5 shadow-soft-sm mb-6"
    >
      <div className="flex items-start justify-between pb-3 border-b border-hairline">
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-emerald-800">
            Ingestion Pipeline Complete
          </span>
          <h3 className="text-base font-semibold text-ink mt-0.5">
            What Lumen just prepared
          </h3>
          <p className="text-xs text-ink-muted mt-0.5">
            Your data has been validated, loaded into isolated DuckDB analytical tables, and profiled with 0-100 quality scoring.
          </p>
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="text-xs text-ink-muted hover:text-ink px-2 py-1 rounded-16 hover:bg-surface transition-colors"
          >
            Dismiss
          </button>
        )}
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-4">
        <div className="p-3 bg-surface/60 border border-hairline rounded-16">
          <span className="text-[11px] text-ink-muted uppercase tracking-wider">Tables Created</span>
          <p className="text-lg font-semibold text-ink mt-0.5 tabular-nums">{datasets.length}</p>
        </div>
        <div className="p-3 bg-surface/60 border border-hairline rounded-16">
          <span className="text-[11px] text-ink-muted uppercase tracking-wider">Total Rows</span>
          <p className="text-lg font-semibold text-ink mt-0.5 tabular-nums">{totalRows.toLocaleString()}</p>
        </div>
        <div className="p-3 bg-surface/60 border border-hairline rounded-16">
          <span className="text-[11px] text-ink-muted uppercase tracking-wider">Profiled Columns</span>
          <p className="text-lg font-semibold text-ink mt-0.5 tabular-nums">{totalCols}</p>
        </div>
        <div className="p-3 bg-surface/60 border border-hairline rounded-16">
          <span className="text-[11px] text-ink-muted uppercase tracking-wider">Avg Quality Score</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="text-lg font-semibold text-ink tabular-nums">{avgQuality}/100</span>
            {avgQuality >= 80 ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-700" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-amber-600" />
            )}
          </div>
        </div>
      </div>

      {/* Table list */}
      <div className="space-y-2 mt-3">
        <span className="text-xs font-medium text-ink-muted">Registered Warehouse Tables:</span>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
          {datasets.map((d) => (
            <div
              key={d.id}
              className="p-2.5 rounded-16 border border-hairline bg-surface/40 flex items-center justify-between text-xs"
            >
              <div className="flex items-center gap-2 truncate">
                <Table className="w-3.5 h-3.5 text-emerald-700 shrink-0" />
                <span className="font-mono font-medium text-ink truncate">{d.table_name || d.name}</span>
              </div>
              <span className="text-[11px] text-ink-muted tabular-nums shrink-0 ml-2">
                {d.row_count.toLocaleString()} rows
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Next Actions Bar */}
      <div className="mt-4 pt-3 border-t border-hairline flex flex-wrap items-center justify-between gap-3 text-xs">
        <span className="text-ink-muted">
          Ready for analysis: DuckDB SQL queries, anomaly detection, and ECharts visualization.
        </span>
        <div className="flex items-center gap-2">
          <Link
            to="/dashboards"
            className="px-3.5 py-1.5 rounded-pill bg-white border border-hairline hover:bg-surface text-ink font-medium transition-colors shadow-soft-xs inline-flex items-center gap-1.5"
          >
            <Layers className="w-3.5 h-3.5 text-emerald-700" />
            <span>View Dashboard</span>
          </Link>
          <Link
            to="/workspace"
            className="px-4 py-1.5 rounded-pill bg-ink text-white hover:bg-ink/90 font-medium transition-all shadow-soft-xs inline-flex items-center gap-1.5"
          >
            <span>Ask Analyst</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    </motion.div>
  );
};
