import React, { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2, Circle, X, ArrowRight, HelpCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface GuidedOnboardingCardProps {
  hasDatasets: boolean;
  hasAskedQuestion: boolean;
  hasViewedEvidence: boolean;
  hasReports: boolean;
  hasDashboards: boolean;
  onOpenHelp?: () => void;
}

export const GuidedOnboardingCard: React.FC<GuidedOnboardingCardProps> = ({
  hasDatasets,
  hasAskedQuestion,
  hasViewedEvidence,
  hasReports,
  hasDashboards,
  onOpenHelp,
}) => {
  const [dismissed, setDismissed] = useState<boolean>(() => {
    return localStorage.getItem("lumen_onboarding_dismissed") === "true";
  });

  const steps = [
    {
      id: "upload",
      label: "Upload tabular data",
      desc: "Ingest CSV or XLSX files into your isolated DuckDB warehouse",
      done: hasDatasets,
      href: "/datasets",
    },
    {
      id: "dashboard",
      label: "Review generated dashboard",
      desc: "Examine auto-generated KPI widgets and distribution charts",
      done: hasDashboards,
      href: "/dashboards",
    },
    {
      id: "ask",
      label: "Ask an analytical question",
      desc: "Inquire in plain language; watch DAG planning in real time",
      done: hasAskedQuestion,
      href: "/workspace",
    },
    {
      id: "evidence",
      label: "Inspect source queries",
      desc: "Audit the exact SQL, execution runtime, and cross-check ledger",
      done: hasViewedEvidence,
      href: "/workspace",
    },
    {
      id: "report",
      label: "Export verifiable report",
      desc: "Generate standalone publication-grade PDF or Markdown dossiers",
      done: hasReports,
      href: "/reports",
    },
  ];

  const completedCount = steps.filter((s) => s.done).length;
  const progressPct = Math.round((completedCount / steps.length) * 100);

  const handleDismiss = () => {
    setDismissed(true);
    localStorage.setItem("lumen_onboarding_dismissed", "true");
  };

  const handleReopen = () => {
    setDismissed(false);
    localStorage.removeItem("lumen_onboarding_dismissed");
  };

  if (dismissed) {
    return (
      <button
        onClick={handleReopen}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-ink bg-white border border-hairline rounded-pill shadow-soft-xs hover:bg-surface transition-colors select-none"
        title="Reopen onboarding guide"
      >
        <HelpCircle className="w-3.5 h-3.5 text-emerald-700" />
        <span>Getting started ({completedCount}/{steps.length})</span>
      </button>
    );
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.98 }}
        className="w-full bg-white border border-hairline rounded-24 p-5 shadow-soft-sm mb-6 relative overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-start justify-between pb-3 border-b border-hairline">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-800">
                Getting Started Guide
              </span>
              <span className="text-[11px] font-medium text-ink-muted px-2 py-0.5 rounded-pill bg-surface border border-hairline">
                {completedCount} of {steps.length} completed
              </span>
            </div>
            <h4 className="text-sm font-semibold text-ink mt-0.5">
              Five steps to verifiable data analysis
            </h4>
          </div>

          <div className="flex items-center gap-1">
            {onOpenHelp && (
              <button
                type="button"
                onClick={onOpenHelp}
                className="text-xs text-ink-muted hover:text-ink px-2 py-1 rounded-16 hover:bg-surface transition-colors flex items-center gap-1"
              >
                <HelpCircle className="w-3.5 h-3.5 text-emerald-700" />
                <span>How Lumen works</span>
              </button>
            )}
            <button
              type="button"
              onClick={handleDismiss}
              className="text-ink-muted hover:text-ink p-1 rounded-pill hover:bg-surface transition-colors"
              aria-label="Dismiss guide"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-surface h-1.5 rounded-pill mt-3 overflow-hidden border border-hairline">
          <motion.div
            className="bg-emerald-600 h-full rounded-pill"
            initial={{ width: 0 }}
            animate={{ width: `${progressPct}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>

        {/* Steps Grid */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 mt-4">
          {steps.map((step, idx) => (
            <Link
              key={step.id}
              to={step.href}
              className={`p-3 rounded-20 border transition-all text-left flex flex-col justify-between group ${
                step.done
                  ? "bg-emerald-50/40 border-emerald-200/80 hover:border-emerald-300"
                  : "bg-surface/50 border-hairline hover:bg-white hover:border-hairline-dark hover:shadow-soft-xs"
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-mono text-ink-muted">
                    0{idx + 1}
                  </span>
                  {step.done ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-700" />
                  ) : (
                    <Circle className="w-4 h-4 text-ink-muted/50 group-hover:text-ink-muted" />
                  )}
                </div>
                <p className={`text-xs font-semibold ${step.done ? "text-emerald-950" : "text-ink"}`}>
                  {step.label}
                </p>
                <p className="text-[11px] text-ink-muted mt-1 leading-snug">
                  {step.desc}
                </p>
              </div>

              <div className="mt-2 pt-2 border-t border-hairline/60 flex items-center justify-between text-[11px] font-medium text-ink-muted group-hover:text-ink">
                <span>{step.done ? "Complete" : "Start"}</span>
                <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
              </div>
            </Link>
          ))}
        </div>
      </motion.div>
    </AnimatePresence>
  );
};
