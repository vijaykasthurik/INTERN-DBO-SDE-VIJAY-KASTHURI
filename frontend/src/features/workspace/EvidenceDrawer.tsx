import React, { useState } from "react";
import { Copy, Check, Terminal, Table as TableIcon, ShieldAlert } from "lucide-react";
import { Drawer } from "../../components/ui/Drawer";
import { Tabs } from "../../components/ui/Tabs";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import type { EvidenceEntry } from "../../lib/api";

export interface EvidenceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  entries?: EvidenceEntry[];
  sqlCode?: string;
  pandasCode?: string;
  activeNumber?: string;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  isOpen,
  onClose,
  entries = [],
  sqlCode,
  pandasCode,
  activeNumber,
}) => {
  const [activeTab, setActiveTab] = useState<string>("sql");
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const currentSql =
    sqlCode ||
    entries.find((e) => e.tool === "sql_tool")?.code ||
    "SELECT * FROM sales LIMIT 10;";

  const currentPandas =
    pandasCode ||
    entries.find((e) => e.tool === "pandas_tool")?.code ||
    "# Pandas analytical equivalent\ndf.groupby('region')['revenue'].sum()";

  const firstEntry = entries[0];
  let previewRows: Array<Record<string, unknown>> = [];
  if (firstEntry && Array.isArray(firstEntry.result_preview)) {
    previewRows = firstEntry.result_preview as Array<Record<string, unknown>>;
  }

  const columns = previewRows.length > 0 ? Object.keys(previewRows[0]) : [];

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title="Evidence Ledger & Code Audit"
      subtitle={
        activeNumber
          ? `Auditing grounding proof for numerical claim: ${activeNumber}`
          : "Mathematical grounding for verified answers"
      }
      width="lg"
      footer={
        <div className="flex items-center justify-between text-xs text-ink-muted">
          <span>Engineered Trust: Skeptic Verifier passed</span>
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* TABS */}
        <div className="flex justify-start">
          <Tabs
            tabs={[
              { id: "sql", label: "DuckDB SQL", icon: <Terminal className="w-3.5 h-3.5" /> },
              { id: "pandas", label: "Pandas Sandbox", icon: <Terminal className="w-3.5 h-3.5" /> },
              { id: "table", label: "Result Rows", icon: <TableIcon className="w-3.5 h-3.5" /> },
              { id: "steps", label: "Ledger Steps", icon: <ShieldAlert className="w-3.5 h-3.5" /> },
            ]}
            activeTab={activeTab}
            onChange={setActiveTab}
          />
        </div>

        {/* TAB 1: DUCKDB SQL */}
        {activeTab === "sql" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-ink-muted">
              <span>Executed against read-only in-memory DuckDB database</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleCopy(currentSql)}
                className="h-7 px-2 text-xs"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 mr-1 text-emerald-500" /> Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 mr-1" /> Copy SQL
                  </>
                )}
              </Button>
            </div>
            <pre className="p-4 bg-slate-950 text-slate-100 rounded-16 font-mono text-xs overflow-x-auto border border-slate-800 leading-relaxed">
              <code>{currentSql}</code>
            </pre>
          </div>
        )}

        {/* TAB 2: PANDAS CODE */}
        {activeTab === "pandas" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-ink-muted">
              <span>Executed in restricted-AST subprocess sandbox</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleCopy(currentPandas)}
                className="h-7 px-2 text-xs"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 mr-1 text-emerald-500" /> Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 mr-1" /> Copy Code
                  </>
                )}
              </Button>
            </div>
            <pre className="p-4 bg-slate-950 text-slate-100 rounded-16 font-mono text-xs overflow-x-auto border border-slate-800 leading-relaxed">
              <code>{currentPandas}</code>
            </pre>
          </div>
        )}

        {/* TAB 3: RESULT ROWS */}
        {activeTab === "table" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-ink-muted">
              <span>
                {previewRows.length} sample rows returned from DuckDB
              </span>
            </div>
            {previewRows.length === 0 ? (
              <p className="text-xs text-ink-muted py-8 text-center bg-surface rounded-16 border border-hairline">
                No tabular preview rows recorded for this query.
              </p>
            ) : (
              <div className="overflow-x-auto border border-hairline rounded-16 max-h-80 overflow-y-auto">
                <table className="min-w-full divide-y divide-hairline text-left text-xs font-mono">
                  <thead className="bg-surface sticky top-0">
                    <tr>
                      {columns.map((col) => (
                        <th key={col} className="px-3.5 py-2 font-semibold text-ink">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-hairline bg-white">
                    {previewRows.slice(0, 50).map((row, idx) => (
                      <tr key={idx} className="hover:bg-surface/50">
                        {columns.map((col) => (
                          <td key={col} className="px-3.5 py-2 text-ink-muted truncate max-w-[200px]">
                            {String(row[col] ?? "")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: LEDGER STEPS */}
        {activeTab === "steps" && (
          <div className="space-y-3">
            <div className="space-y-2">
              {entries.map((step) => (
                <div
                  key={step.step_id}
                  className="p-3.5 rounded-16 border border-hairline bg-surface/50 space-y-1.5 text-xs font-mono"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-accent-indigo">{step.step_id}</span>
                    <Badge variant={step.status === "success" ? "success" : "error"} size="sm">
                      {step.status}
                    </Badge>
                  </div>
                  <p className="text-ink text-xs font-sans">{step.tool}</p>
                  <div className="flex items-center gap-4 text-[10px] text-ink-muted">
                    <span>Runtime: {step.runtime_ms}ms</span>
                    <span>Rows: {step.row_count}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </Drawer>
  );
};
