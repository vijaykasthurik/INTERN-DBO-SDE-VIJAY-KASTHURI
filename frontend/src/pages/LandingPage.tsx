import { Wordmark } from "../components/Wordmark";
import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import {
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Zap,
  BarChart3,
  Search,
  CheckCircle2,
  FileSpreadsheet,
  Cpu,
} from "lucide-react";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { Card } from "../components/ui/Card";

export const LandingPage: React.FC = () => {
  // Mini-demo animation cycle: 0 = Question typing, 1 = Plan DAG, 2 = Execution, 3 = Chart + Insight
  const reducedMotion = useReducedMotion();
  const [demoStep, setDemoStep] = useState(0);

  useEffect(() => {
    if (reducedMotion) return;
    const timer = setInterval(() => {
      setDemoStep((prev) => (prev + 1) % 4);
    }, 3800);
    return () => clearInterval(timer);
  }, [reducedMotion]);

  const features = [
    {
      icon: ShieldCheck,
      title: "Evidence Ledger Verification",
      description:
        "DuckDB and Python compute analytical results. A separate verifier checks numerical claims against the recorded evidence.",
    },
    {
      icon: Zap,
      title: "Sub-Second In-Memory DuckDB",
      description:
        "Zero slow round-trips to cloud warehouses. Query millions of rows directly in an isolated, read-only vectorized engine.",
    },
    {
      icon: BarChart3,
      title: "Auto-Compiled ECharts",
      description:
        "Lumen inspects the statistical shape of your results to automatically select the optimal chart type with interactive tooltips.",
    },
    {
      icon: Search,
      title: "Root-Cause Hypothesis Engine",
      description:
        "Ask why a metric changed and inspect candidate explanations against the computed evidence.",
    },
    {
      icon: Cpu,
      title: "Multi-Model Fallback Router",
      description:
        "Enterprise resilience with automated token-bucket rate limiting, circuit breakers, and seamless failovers.",
    },
    {
      icon: FileSpreadsheet,
      title: "Executive PDF & Markdown Exports",
      description:
        "Generate publication-ready executive dossiers with high-resolution Matplotlib figures and complete SQL audit trails.",
    },
  ];

  const steps = [
    {
      step: "01",
      title: "Drop your CSVs",
      desc: "Auto-detects delimiters, schema types, foreign key relationships, and data quality flaws with 0-100 health scoring.",
    },
    {
      step: "02",
      title: "Ask in plain English",
      desc: "Our intent router translates complex business inquiries into directed acyclic dependency graphs.",
    },
    {
      step: "03",
      title: "Engineered Trust",
      desc: "The skeptic Verifier cross-checks DuckDB SQL against Pandas, redacting any metric ungrounded by the ledger.",
    },
    {
      step: "04",
      title: "Act on Insights",
      desc: "Stream grounded narratives, interactive visualizations, and export board-ready executive reports in one click.",
    },
  ];

  return (
    <div className="min-h-screen bg-white text-ink pt-28 pb-16 overflow-hidden">
      {/* HERO SECTION */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 text-center relative">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-pill bg-surface border border-hairline shadow-soft-xs text-xs font-medium mb-6 select-none"
        >
          <Sparkles className="w-3.5 h-3.5 text-accent-indigo" />
          <span>Next-Generation Autonomous Analytics</span>
          <Badge variant="accent" size="sm">v1.0</Badge>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-4xl sm:text-6xl md:text-7xl font-serif tracking-tight leading-[1.08] text-ink max-w-4xl mx-auto"
        >
          Instant clarity from <br />
          <span className="italic font-normal bg-accent-gradient bg-clip-text text-transparent">
            raw tabular data.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-6 text-lg sm:text-xl text-ink-muted max-w-2xl mx-auto font-sans font-normal leading-relaxed"
        >
          Lumen pairs vectorized DuckDB speed with an engineered-trust Skeptic Verifier.
          Zero hallucinations. 100% verified numbers.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Link to="/workspace">
            <Button size="lg" className="shadow-nav-glow font-medium group">
              Launch Workspace
              <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
            </Button>
          </Link>
          <Link to="/datasets">
            <Button variant="secondary" size="lg">
              Explore Sample Data
            </Button>
          </Link>
        </motion.div>

        {/* LIVE MINI-DEMO CONTAINER */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 30 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4 }}
          className="mt-16 max-w-4xl mx-auto rounded-28 border border-hairline bg-surface/60 backdrop-blur-sm p-4 sm:p-6 shadow-soft-lg relative"
        >
          {/* Header bar of mini-demo */}
          <div className="flex items-center justify-between pb-4 border-b border-hairline text-left">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-rose-400" />
              <div className="w-3 h-3 rounded-full bg-amber-400" />
              <div className="w-3 h-3 rounded-full bg-emerald-400" />
              <span className="text-xs text-ink-muted font-mono ml-2">Product workflow preview</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={demoStep === 3 ? "success" : "neutral"} size="sm">
                {demoStep === 0 && "1. Query Input"}
                {demoStep === 1 && "2. DAG Planning"}
                {demoStep === 2 && "3. DuckDB Execution"}
                {demoStep === 3 && "4. Verified Narrative"}
              </Badge>
            </div>
          </div>

          {/* Interactive animated content */}
          <div className="py-6 min-h-[300px] flex flex-col justify-center">
            <AnimatePresence mode="wait">
              {demoStep === 0 && (
                <motion.div
                  key="step0"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="space-y-4 text-left max-w-lg mx-auto"
                >
                  <p className="text-xs font-semibold text-ink-muted uppercase tracking-wider">Natural Language Request</p>
                  <div className="p-4 bg-white rounded-20 border border-hairline shadow-soft-xs text-sm font-medium text-ink flex items-center gap-3">
                    <Search className="w-4 h-4 text-accent-indigo animate-pulse" />
                    <span>"Why did revenue dip in March 2024, and which region caused it?"</span>
                  </div>
                  <p className="text-xs text-ink-muted">Resolving entity memory and catalog embeddings...</p>
                </motion.div>
              )}

              {demoStep === 1 && (
                <motion.div
                  key="step1"
                  initial={{ opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  className="text-left space-y-4"
                >
                  <p className="text-xs font-semibold text-ink-muted uppercase tracking-wider">DAG Wave Planner</p>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="p-3 bg-white rounded-16 border-2 border-accent-indigo shadow-soft-xs">
                      <p className="text-[10px] font-mono text-accent-indigo font-bold">WAVE 1 • STEP 1</p>
                      <p className="text-xs font-semibold text-ink mt-1">Aggregate monthly revenue</p>
                      <p className="text-[10px] text-emerald-600 mt-2 font-mono">Status: READY</p>
                    </div>
                    <div className="p-3 bg-white rounded-16 border-2 border-accent-violet shadow-soft-xs">
                      <p className="text-[10px] font-mono text-accent-violet font-bold">WAVE 1 • STEP 2</p>
                      <p className="text-xs font-semibold text-ink mt-1">Detect anomaly flags</p>
                      <p className="text-[10px] text-emerald-600 mt-2 font-mono">Status: READY</p>
                    </div>
                    <div className="p-3 bg-white rounded-16 border border-hairline shadow-soft-xs opacity-75">
                      <p className="text-[10px] font-mono text-ink-muted font-bold">WAVE 2 • STEP 3</p>
                      <p className="text-xs font-semibold text-ink mt-1">Hypothesis ranking</p>
                      <p className="text-[10px] text-ink-muted mt-2 font-mono">Awaiting inputs...</p>
                    </div>
                  </div>
                </motion.div>
              )}

              {demoStep === 2 && (
                <motion.div
                  key="step2"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="text-left space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-ink-muted uppercase tracking-wider">DuckDB Execution & Verifier</p>
                    <span className="text-[11px] font-mono text-emerald-600 font-medium">Runtime and join checks appear after execution</span>
                  </div>
                  <div className="p-3 bg-slate-900 text-slate-100 rounded-16 font-mono text-xs overflow-x-auto">
                    <code>
                      {"SELECT strftime('%Y-%m', order_date) AS month, SUM(amount) AS revenue\nFROM sales JOIN customers USING (customer_id)\nGROUP BY 1 ORDER BY 1;"}
                    </code>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-ink font-medium">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    <span>Review the recorded verification checks and confidence</span>
                  </div>
                </motion.div>
              )}

              {demoStep === 3 && (
                <motion.div
                  key="step3"
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  className="text-left space-y-4"
                >
                  <div className="p-4 bg-white rounded-20 border border-hairline shadow-soft-sm">
                    <div className="flex items-start justify-between">
                      <div>
                        <span className="text-xs font-bold text-accent-indigo uppercase tracking-wider">Executive Finding</span>
                        <h4 className="text-base font-semibold text-ink mt-1">
                          Inspect the answer and its evidence
                        </h4>
                      </div>
                      <Badge variant="success">Recorded confidence</Badge>
                    </div>
                    <p className="text-xs text-ink-muted mt-2 leading-relaxed">
                      After running your query, review its computed results, executed SQL and verification notes. Export your analysis when you are ready.
                    </p>
                    <div className="mt-4 pt-3 border-t border-hairline flex flex-wrap gap-3 text-xs text-ink-muted">
                      <span>Computed result</span><span>Executed query</span><span>Evidence ledger</span>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      </section>

      {/* HOW IT WORKS SECTION */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 mt-28">
        <div className="text-center mb-16">
          <p className="text-xs font-semibold text-accent-indigo uppercase tracking-wider mb-2">
            Engineered Trust
          </p>
          <h2 className="text-3xl sm:text-4xl font-serif text-ink tracking-tight font-medium">
            How Lumen makes analysis inspectable
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {steps.map((item) => (
            <div
              key={item.step}
              className="p-6 rounded-24 bg-surface/50 border border-hairline relative flex flex-col justify-between"
            >
              <div>
                <span className="text-2xl font-serif text-accent-indigo font-normal block mb-4">
                  {item.step}
                </span>
                <h3 className="text-base font-semibold text-ink tracking-tight mb-2">
                  {item.title}
                </h3>
                <p className="text-xs text-ink-muted leading-relaxed">
                  {item.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* FEATURES GRID */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 mt-28">
        <div className="text-center mb-16">
          <p className="text-xs font-semibold text-accent-indigo uppercase tracking-wider mb-2">
            Capabilities
          </p>
          <h2 className="text-3xl sm:text-4xl font-serif text-ink tracking-tight font-medium">
            Engineered for high-stakes business analytics
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feat) => {
            const Icon = feat.icon;
            return (
              <Card key={feat.title} className="p-6 hover:shadow-soft-md transition-shadow">
                <div className="w-10 h-10 rounded-20 bg-accent-indigo/10 flex items-center justify-center text-accent-indigo mb-4">
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="text-base font-semibold text-ink tracking-tight mb-2">
                  {feat.title}
                </h3>
                <p className="text-xs text-ink-muted leading-relaxed">
                  {feat.description}
                </p>
              </Card>
            );
          })}
        </div>
      </section>

      {/* FOOTER */}
      <footer className="max-w-6xl mx-auto px-4 sm:px-6 mt-32 pt-8 border-t border-hairline flex flex-col sm:flex-row items-center justify-between text-xs text-ink-muted gap-4">
        <div className="flex items-center gap-2">
          <Wordmark />
          <span>© 2026 Lumen AI. All rights reserved.</span>
        </div>
        <div className="flex items-center space-x-6">
          <Link to="/workspace" className="hover:text-ink transition-colors">Workspace</Link>
          <Link to="/datasets" className="hover:text-ink transition-colors">Datasets</Link>
          <Link to="/settings" className="hover:text-ink transition-colors">Diagnostics</Link>
        </div>
      </footer>
    </div>
  );
};
