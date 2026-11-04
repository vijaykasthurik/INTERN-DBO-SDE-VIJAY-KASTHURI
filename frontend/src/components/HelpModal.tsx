import React from "react";
import { X, ShieldCheck, Database, GitBranch, FileSpreadsheet, Activity } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const workflowSteps = [
    {
      num: "01",
      title: "Data Ingestion & Safety",
      desc: "CSVs and multi-sheet Excel workbooks are validated for safe headers, row/col limits, and ingested into isolated per-tenant DuckDB databases. Raw contents are treated strictly as data, never instructions.",
      icon: FileSpreadsheet,
    },
    {
      num: "02",
      title: "Profiling & Quality Score",
      desc: "Every column is profiled for types, null distributions, cardinality, and range fences. An automated 0-100 data health audit flags duplicates and anomalies.",
      icon: Activity,
    },
    {
      num: "03",
      title: "Catalog & Semantic Layer",
      desc: "Compact table summaries and relationship graph links (join keys detected by value overlap and naming) are cached for deterministic query generation.",
      icon: Database,
    },
    {
      num: "04",
      title: "DAG Planning & Execution",
      desc: "The model never does math in its head. It plans a DAG of tool calls. SQL queries execute inside DuckDB; sandboxed Pandas runs with strict AST restrictions.",
      icon: GitBranch,
    },
    {
      num: "05",
      title: "Dual-Pass Cross-Check",
      desc: "Before any answer is streamed to you, the Verifier independently computes key numbers using a secondary method and verifies that every number exists in the execution ledger.",
      icon: ShieldCheck,
    },
  ];

  const glossaryItems = [
    {
      term: "Source Queries (Evidence Ledger)",
      meaning: "The immutable record of every SQL and Pandas script executed by Lumen to answer a question, including row counts, previews, and runtimes.",
    },
    {
      term: "Cross-Check (Dual-Pass Verifier)",
      meaning: "An automated skepticism layer that re-evaluates queries, checks for negative revenues or percentages > 100%, and verifies exact numerical grounding.",
    },
    {
      term: "Per-Tenant Warehouse",
      meaning: "Every user has their own private DuckDB file. User queries cannot cross boundaries or access any other tenant's data.",
    },
    {
      term: "BYOK & Smart Fallback",
      meaning: "Connect your own API key from Groq, Gemini, OpenAI, or Anthropic. If your quota is exhausted, Lumen smoothly falls back to the shared server pool so your work is never interrupted.",
    },
  ];

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-white border border-hairline rounded-28 max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-soft-lg p-6"
        >
          {/* Header */}
          <div className="flex items-start justify-between pb-4 border-b border-hairline">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-800">
                Architecture & Transparency
              </span>
              <h2 className="text-xl font-serif font-medium text-ink mt-0.5">
                How Lumen Works
              </h2>
              <p className="text-xs text-ink-muted mt-1">
                Zero-hallucination data analysis with mathematical grounding in DuckDB.
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-pill hover:bg-surface text-ink-muted hover:text-ink transition-colors"
              aria-label="Close help"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Workflow Sequence */}
          <div className="mt-5 space-y-3">
            <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">
              The 5-Stage PEVN Pipeline
            </h3>
            <div className="space-y-2.5">
              {workflowSteps.map((s) => {
                const Icon = s.icon;
                return (
                  <div
                    key={s.num}
                    className="p-3.5 rounded-20 border border-hairline bg-surface/50 flex items-start gap-3.5"
                  >
                    <div className="w-8 h-8 rounded-pill bg-white border border-hairline flex items-center justify-center shrink-0 shadow-soft-xs text-emerald-700">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-mono font-medium text-ink-muted">{s.num}</span>
                        <h4 className="text-xs font-semibold text-ink">{s.title}</h4>
                      </div>
                      <p className="text-xs text-ink-muted mt-1 leading-relaxed">
                        {s.desc}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Glossary */}
          <div className="mt-6 pt-5 border-t border-hairline space-y-3">
            <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">
              Glossary of Terms
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {glossaryItems.map((g) => (
                <div key={g.term} className="p-3 rounded-16 border border-hairline bg-surface/30">
                  <p className="text-xs font-semibold text-ink">{g.term}</p>
                  <p className="text-[11px] text-ink-muted mt-1 leading-relaxed">{g.meaning}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 pt-4 border-t border-hairline flex justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-pill bg-ink text-white hover:bg-ink/90 text-xs font-medium transition-all shadow-soft-xs"
            >
              Close Guide
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
