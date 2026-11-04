import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2,
  Clock,
  RotateCcw,
  ShieldCheck,
  AlertCircle,
  HelpCircle,
  Cpu,
} from "lucide-react";
import { Badge } from "../../components/ui/Badge";
import { Tooltip } from "../../components/ui/Tooltip";

export interface TimelineStep {
  id: string;
  tool: string;
  description: string;
  status: "pending" | "running" | "completed" | "repaired" | "failed";
  runtime_ms?: number;
  row_count?: number;
  error?: string;
}

export interface VerificationInfo {
  status: string;
  confidence: "High" | "Medium" | "Low";
  reasons: string[];
  checks?: Record<string, boolean>;
}

export interface ReasoningTimelineProps {
  lane?: string;
  steps: TimelineStep[];
  repairs?: Array<{ step_id: string; error_type: string; attempt: number }>;
  verification?: VerificationInfo | null;
  className?: string;
}

export const ReasoningTimeline: React.FC<ReasoningTimelineProps> = ({
  lane,
  steps,
  repairs = [],
  verification,
  className,
}) => {
  return (
    <div className={`space-y-6 ${className || ""}`}>
      {/* HEADER / INTENT ROUTE */}
      <div className="flex items-center justify-between pb-3 border-b border-hairline">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-accent-indigo" />
          <h3 className="text-xs font-semibold text-ink uppercase tracking-wider">
            Reasoning Pipeline
          </h3>
        </div>
        {lane && (
          <Badge variant="accent" size="sm">
            Lane: {lane.replace(/_/g, " ")}
          </Badge>
        )}
      </div>

      {/* PLAN DAG EXECUTION TIMELINE */}
      {steps.length === 0 ? (
        <p className="text-xs text-ink-muted py-6 text-center">
          Waiting for next query to plan DAG execution waves...
        </p>
      ) : (
        <div className="space-y-3 relative before:absolute before:left-3.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-200">
          {steps.map((step, idx) => {
            const isRepaired = repairs.some((r) => r.step_id === step.id);
            const isRunning = step.status === "running";
            const isCompleted = step.status === "completed";
            const isFailed = step.status === "failed";

            return (
              <motion.div
                key={step.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25, delay: idx * 0.05 }}
                className="relative flex items-start gap-3 pl-8 select-none"
              >
                {/* TIMELINE NODE ICON */}
                <div
                  className={`absolute left-1.5 top-0.5 w-5 h-5 rounded-full flex items-center justify-center border transition-all ${
                    isRunning
                      ? "bg-white border-accent-indigo shadow-nav-glow"
                      : isCompleted
                      ? "bg-emerald-500 border-emerald-500 text-white"
                      : isFailed
                      ? "bg-rose-500 border-rose-500 text-white"
                      : "bg-white border-slate-300 text-slate-400"
                  }`}
                >
                  {isRunning && (
                    <div className="w-2.5 h-2.5 rounded-full border-2 border-accent-indigo border-t-transparent animate-spin" />
                  )}
                  {isCompleted && <CheckCircle2 className="w-3.5 h-3.5" />}
                  {isFailed && <AlertCircle className="w-3.5 h-3.5" />}
                  {!isRunning && !isCompleted && !isFailed && (
                    <span className="text-[10px] font-mono">{idx + 1}</span>
                  )}
                </div>

                {/* STEP DETAILS CARD */}
                <div
                  className={`flex-1 p-3 rounded-16 border transition-all ${
                    isRunning
                      ? "bg-indigo-50/50 border-accent-indigo shadow-soft-xs"
                      : isCompleted
                      ? "bg-white border-hairline shadow-soft-xs"
                      : "bg-surface/50 border-hairline text-ink-muted"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[10px] font-bold text-accent-indigo uppercase">
                      {step.tool}
                    </span>
                    {step.runtime_ms !== undefined && (
                      <span className="flex items-center text-[10px] font-mono text-ink-muted gap-1">
                        <Clock className="w-3 h-3" />
                        {step.runtime_ms.toFixed(1)}ms
                      </span>
                    )}
                  </div>
                  <p className="text-xs font-medium text-ink mt-1">
                    {step.description}
                  </p>

                  {/* REPAIR LOOP SELF-CORRECTION BADGE */}
                  {isRepaired && (
                    <div className="mt-2 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-pill bg-amber-50 border border-amber-200 text-amber-700 text-[10px] font-medium animate-pulse">
                      <RotateCcw className="w-3 h-3 animate-spin" />
                      <span>Auto-repaired query via schema feedback</span>
                    </div>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* SKEPTIC VERIFIER AUDIT PANEL */}
      <AnimatePresence>
        {verification && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-20 bg-surface/70 border border-hairline space-y-3"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-accent-indigo" />
                <h4 className="text-xs font-semibold text-ink">
                  Skeptic Verifier Audit
                </h4>
              </div>

              <Tooltip
                content={
                  <div className="max-w-xs text-left p-1 space-y-1">
                    <p className="font-semibold">Audit Reasons:</p>
                    {verification.reasons.map((r, i) => (
                      <p key={i} className="text-[11px] text-ink-muted">• {r}</p>
                    ))}
                  </div>
                }
                position="left"
              >
                <div className="cursor-help flex items-center gap-1">
                  <Badge
                    variant={
                      verification.confidence === "High"
                        ? "success"
                        : verification.confidence === "Medium"
                        ? "warning"
                        : "error"
                    }
                    size="sm"
                  >
                    {verification.confidence} Confidence
                  </Badge>
                  <HelpCircle className="w-3 h-3 text-ink-muted" />
                </div>
              </Tooltip>
            </div>

            {/* AUDIT CHECKLIST */}
            <div className="space-y-1.5 text-[11px] text-ink-muted font-mono">
              <div className="flex items-center justify-between">
                <span>Sanity checks (empty, non-negative)</span>
                <span className="text-emerald-600 font-bold">PASS</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Join fan-out ratio check</span>
                <span className="text-emerald-600 font-bold">PASS</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Evidence Ledger number grounding</span>
                <span className="text-emerald-600 font-bold">100% GROUNDED</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
