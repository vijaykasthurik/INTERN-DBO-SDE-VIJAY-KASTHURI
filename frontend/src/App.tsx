import React from "react";
import { Sparkles, ArrowRight, Database, ShieldCheck, Zap } from "lucide-react";

/**
 * Navbar variant design token:
 * "capsule" -> Floating capsule centered at top with rounded ends
 * "bottom-rounded" -> Navbar rounded only at bottom corners
 */
export const NAV_VARIANT: "capsule" | "bottom-rounded" = "capsule";

export const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-background text-ink flex flex-col items-center justify-between relative overflow-hidden font-sans selection:bg-accent-violet/10">
      {/* Background Subtle Ambience */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-radial-glow pointer-events-none opacity-60" />

      {/* Floating Capsule Navbar */}
      <header
        className={`fixed top-5 z-50 flex items-center justify-between px-6 py-2.5 bg-white/80 backdrop-blur-md border border-hairline shadow-soft-sm transition-all duration-300 ${
          NAV_VARIANT === "capsule" ? "rounded-pill" : "rounded-b-28 rounded-t-none"
        } w-[92%] max-w-4xl`}
      >
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-accent-gradient flex items-center justify-center shadow-soft-xs">
            <div className="w-2.5 h-2.5 rounded-full bg-white shadow-xs" />
          </div>
          <span className="font-semibold tracking-tight text-ink text-base">Lumen</span>
          <span className="text-[11px] font-medium tracking-wide uppercase px-2 py-0.5 rounded-pill bg-surface text-ink-muted border border-hairline">
            Autonomous
          </span>
        </div>

        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-ink-muted">
          <a href="#features" className="hover:text-ink transition-colors">Capabilities</a>
          <a href="#architecture" className="hover:text-ink transition-colors">Evidence Ledger</a>
          <a href="#safety" className="hover:text-ink transition-colors">Trust Engine</a>
        </nav>

        <div className="flex items-center gap-3">
          <button
            type="button"
            className="px-4 py-1.5 text-xs font-semibold rounded-pill bg-accent-gradient text-white hover:opacity-95 transition-all shadow-soft-xs hover:shadow-nav-glow active:scale-[0.98]"
          >
            Launch Studio
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <main className="w-full max-w-5xl px-6 pt-36 pb-20 flex flex-col items-center text-center">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-pill bg-surface border border-hairline text-xs font-medium text-ink-muted mb-8 shadow-soft-xs">
          <Sparkles className="w-3.5 h-3.5 text-accent-indigo" />
          <span>The Verified AI Data Analyst for Enterprise Data</span>
        </div>

        <h1 className="text-5xl sm:text-7xl font-normal tracking-tight leading-[1.08] text-ink max-w-3xl mb-6">
          Chat with datasets. <br />
          <span className="font-serif italic text-accent-violet">Ground truth</span> only.
        </h1>

        <p className="text-base sm:text-lg text-ink-muted max-w-xl mb-10 leading-relaxed font-normal">
          Upload multi-table CSVs and query across them seamlessly. Every insight is verified,
          backed by DuckDB evidence, and cryptographically grounded.
        </p>

        <div className="flex flex-col sm:flex-row items-center gap-4 mb-16">
          <button
            type="button"
            className="h-11 px-6 rounded-pill bg-accent-gradient text-white font-medium text-sm flex items-center gap-2 shadow-soft-sm hover:shadow-nav-glow transition-all active:scale-[0.98]"
          >
            <span>Upload Your CSV</span>
            <ArrowRight className="w-4 h-4" />
          </button>
          <button
            type="button"
            className="h-11 px-6 rounded-pill bg-white border border-hairline text-ink font-medium text-sm hover:bg-surface shadow-soft-xs transition-colors"
          >
            Explore Golden Benchmark
          </button>
        </div>

        {/* Live Mini-Demo Card Preview */}
        <div className="w-full max-w-3xl rounded-28 border border-hairline bg-surface/70 backdrop-blur-md p-6 shadow-soft-md text-left">
          <div className="flex items-center justify-between pb-4 mb-4 border-b border-hairline">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-400/80" />
              <div className="w-3 h-3 rounded-full bg-amber-400/80" />
              <div className="w-3 h-3 rounded-full bg-emerald-400/80" />
              <span className="ml-2 text-xs font-mono text-ink-muted">sales_q3_actuals.duckdb</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 bg-emerald-50 px-2.5 py-0.5 rounded-pill border border-emerald-100">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Verifier: High Confidence</span>
            </div>
          </div>

          <div className="space-y-4 font-mono text-xs">
            <div className="bg-white p-3.5 rounded-16 border border-hairline text-ink-muted">
              <span className="text-accent-indigo font-semibold">User:</span> Which region generated the highest revenue, and why did EMEA sales drop in March?
            </div>
            <div className="bg-white p-4 rounded-16 border border-hairline space-y-2">
              <div className="flex items-center justify-between text-ink">
                <span className="font-semibold text-accent-violet">Lumen Evidence Ledger:</span>
                <span className="text-ink-muted tabular-nums">48ms &bull; 5,000 rows evaluated</span>
              </div>
              <p className="text-ink-muted font-sans text-sm">
                North America led total revenue at <strong className="text-ink tabular-nums">$1,482,900.00</strong>. EMEA March revenue fell by <strong className="text-ink tabular-nums">34.2%</strong> due to an anomalous supply outage affecting SKU-009.
              </p>
            </div>
          </div>
        </div>

        {/* Feature Grid */}
        <div id="features" className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-4xl mt-20 text-left">
          <div className="p-6 rounded-24 bg-surface border border-hairline shadow-soft-xs">
            <div className="w-9 h-9 rounded-16 bg-white border border-hairline flex items-center justify-center text-accent-indigo mb-4 shadow-soft-xs">
              <Database className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-ink text-sm mb-1.5">DuckDB Analytical Engine</h3>
            <p className="text-xs text-ink-muted leading-relaxed">
              Native analytical execution over multi-table relational CSV schemas with automatic relationship graph resolution.
            </p>
          </div>

          <div className="p-6 rounded-24 bg-surface border border-hairline shadow-soft-xs">
            <div className="w-9 h-9 rounded-16 bg-white border border-hairline flex items-center justify-center text-accent-violet mb-4 shadow-soft-xs">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-ink text-sm mb-1.5">Dual-Pass Verifier</h3>
            <p className="text-xs text-ink-muted leading-relaxed">
              Every query output is independently reconciled via cross-check (SQL vs Pandas sandbox) before narration.
            </p>
          </div>

          <div className="p-6 rounded-24 bg-surface border border-hairline shadow-soft-xs">
            <div className="w-9 h-9 rounded-16 bg-white border border-hairline flex items-center justify-center text-accent-cyan mb-4 shadow-soft-xs">
              <Zap className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-ink text-sm mb-1.5">SSE Reasoning Stream</h3>
            <p className="text-xs text-ink-muted leading-relaxed">
              Observe DAG steps, query repair loops, and ledger updates in real-time with sub-millisecond SSE telemetry.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full border-t border-hairline py-6 text-center text-xs text-ink-muted">
        <div className="max-w-5xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <span>&copy; {new Date().getFullYear()} Lumen Systems Inc. Engineered for absolute data trust.</span>
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Offline Mock Provider Ready</span>
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
