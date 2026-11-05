import React from "react";
import { Link } from "react-router-dom";
import { Database, Table, HelpCircle, ChevronLeft, ChevronRight, Plus, X } from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { useDatasetStore } from "../../stores/datasetStore";

export interface DatasetRailProps {
  isOpen: boolean;
  onToggle: () => void;
  onSelectPrompt: (prompt: string) => void;
}

export const DatasetRail: React.FC<DatasetRailProps> = ({
  isOpen,
  onToggle,
  onSelectPrompt,
}) => {
  const { datasets, selectedDataset, selectDataset } = useDatasetStore();

  const samplePrompts = [
    "Which region generated the highest revenue?",
    "Show monthly sales trends.",
    "Which products are underperforming?",
    "What are the top five customers?",
    "Generate SQL for this analysis.",
    "Detect anomalies in the dataset.",
  ];

  const handlePromptClick = (prompt: string) => {
    onSelectPrompt(prompt);
    // On mobile screens, automatically close rail upon selecting prompt
    if (typeof window !== "undefined" && window.innerWidth < 768) {
      onToggle();
    }
  };

  if (!isOpen) {
    return (
      <div className="hidden md:flex border-r border-hairline bg-surface/40 p-2 flex-col items-center justify-between">
        <button
          onClick={onToggle}
          className="p-1.5 rounded-pill hover:bg-white border border-hairline text-ink-muted hover:text-ink transition-colors"
          title="Expand Dataset Rail"
          aria-label="Expand Dataset Rail"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <>
      {/* Mobile Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-ink/30 backdrop-blur-xs md:hidden"
        onClick={onToggle}
        aria-hidden="true"
      />

      <aside className="fixed inset-y-0 left-0 z-50 w-72 md:static md:w-64 md:z-auto border-r border-hairline bg-white md:bg-surface/40 flex flex-col justify-between p-4 h-full overflow-y-auto select-none shadow-soft-xl md:shadow-none transition-transform">
        <div className="space-y-6">
          {/* HEADER */}
          <div className="flex items-center justify-between pb-3 border-b border-hairline">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-accent-indigo" />
              <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">
                Tables & Catalog
              </h3>
            </div>
            <button
              onClick={onToggle}
              className="p-1 rounded-full hover:bg-surface text-ink-muted hover:text-ink transition-colors"
              title="Close Dataset Rail"
              aria-label="Close Dataset Rail"
            >
              <X className="w-4 h-4 md:hidden" />
              <ChevronLeft className="w-4 h-4 hidden md:block" />
            </button>
          </div>

          {/* TABLES LIST */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] text-ink-muted font-medium">
              <span>Staged DuckDB Tables</span>
              <Link
                to="/datasets"
                className="text-accent-indigo hover:underline flex items-center gap-0.5"
              >
                <Plus className="w-3 h-3" /> Add
              </Link>
            </div>

            {datasets.length === 0 ? (
              <div className="p-3 bg-white rounded-16 border border-hairline text-center text-xs text-ink-muted">
                <p>No tables loaded.</p>
                <Link to="/datasets" className="text-accent-indigo text-xs font-medium block mt-1">
                  Upload CSV
                </Link>
              </div>
            ) : (
              datasets.map((d) => {
                const isSelected = selectedDataset?.id === d.id;
                return (
                  <div
                    key={d.id}
                    onClick={() => selectDataset(d.id)}
                    className={`p-2.5 rounded-16 border transition-all cursor-pointer ${
                      isSelected
                        ? "bg-white border-accent-indigo shadow-soft-xs"
                        : "bg-surface border-hairline hover:bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-ink flex items-center gap-1.5">
                        <Table className="w-3.5 h-3.5 text-accent-indigo" />
                        {d.name}
                      </span>
                      <Badge variant="neutral" size="sm">
                        {d.row_count.toLocaleString()}
                      </Badge>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* SUGGESTED PROMPT TEMPLATES */}
          <div className="space-y-2">
            <span className="text-[11px] text-ink-muted font-medium block">
              Curated Prompts
            </span>
            <div className="space-y-1.5">
              {samplePrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => handlePromptClick(prompt)}
                  className="w-full text-left p-2 rounded-16 bg-white border border-hairline hover:border-accent-indigo hover:shadow-soft-xs text-xs text-ink-muted hover:text-ink transition-all flex items-start gap-2 group"
                >
                  <HelpCircle className="w-3.5 h-3.5 text-emerald-700 flex-shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
                  <span className="line-clamp-2 leading-relaxed">{prompt}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* FOOTER STATS */}
        <div className="pt-4 border-t border-hairline text-[11px] text-ink-muted">
          <span>Engine: DuckDB Vectorized (Read-Only)</span>
        </div>
      </aside>
    </>
  );
};
