import React, { useState, useEffect } from "react";
import { Copy, Check, Terminal, Table as TableIcon, ShieldAlert, Play } from "lucide-react";
import { Drawer } from "../../components/ui/Drawer";
import { Tabs } from "../../components/ui/Tabs";
import { Button } from "../../components/ui/Button";
import { Badge } from "../../components/ui/Badge";
import type { EvidenceEntry } from "../../lib/api";
import { api } from "../../lib/api";

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
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<Awaited<ReturnType<typeof api.chat.executeSQL>> | null>(null);

  const handleCopy = async (text:string) => {
    setRunError(null);
    try {await navigator.clipboard.writeText(text);setCopied(true);setTimeout(()=>setCopied(false),2000);}
    catch {setRunError("Clipboard access was denied. Select and copy the code directly.");}
  };
  const downloadCode = (code:string, extension:string) => {
    const url=URL.createObjectURL(new Blob([code],{type:"text/plain;charset=utf-8"}));
    const anchor=document.createElement("a");anchor.href=url;anchor.download=`lumen-analysis.${extension}`;anchor.click();URL.revokeObjectURL(url);
  };
  const [editedSql,setEditedSql]=useState<string|null>(null);
  const [editedPandas,setEditedPandas]=useState<string|null>(null);

  const sqlEntry = entries.find((e) => e.tool === "sql_tool");
  const sourceSql = sqlCode || sqlEntry?.code || "";
  const currentSql = editedSql ?? sourceSql;

  const sourcePandas = pandasCode || entries.find((e) => e.tool === "pandas_tool")?.code || "";
  const currentPandas = editedPandas ?? sourcePandas;
  useEffect(()=>{setEditedSql(null);setEditedPandas(null);setRunResult(null);setRunError(null);},[sourceSql,sourcePandas,isOpen]);

  let previewRows: Array<Record<string, unknown>> = [];
  if (sqlEntry && Array.isArray(sqlEntry.result_preview)) {
    previewRows = sqlEntry.result_preview as Array<Record<string, unknown>>;
  }

  if(runResult)previewRows=runResult.rows;
  const columns = previewRows.length > 0 ? Object.keys(previewRows[0]) : [];

  const runSql = async () => {
    if (!currentSql) return;
    setRunning(true);
    setRunError(null);
    try {
      setRunResult(await api.chat.executeSQL(currentSql));
    } catch (err: unknown) {
      setRunResult(null);
      setRunError(err instanceof Error ? err.message : "SQL execution failed.");
    } finally {
      setRunning(false);
    }
  };

  const runPandas = async () => {
    setRunning(true);setRunError(null);
    try {setRunResult(await api.chat.executePandas(currentPandas));}
    catch(error){setRunResult(null);setRunError(error instanceof Error?error.message:"Pandas execution failed.");}
    finally{setRunning(false);}
  };
  const runTable = runResult && <div className="max-h-48 overflow-auto border border-hairline rounded-12"><table className="min-w-full text-xs font-mono"><thead><tr>{runResult.columns.map(column=><th key={column} className="px-2 py-1">{column}</th>)}</tr></thead><tbody>{runResult.rows.map((row,index)=><tr key={index}>{runResult.columns.map(column=><td key={column} className="px-2 py-1">{String(row[column]??"")}</td>)}</tr>)}</tbody></table></div>;
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
          <span>Inspect executed code and recorded evidence</span>
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
              <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" onClick={()=>downloadCode(currentSql,"sql")} disabled={!currentSql}>Download .sql</Button>
              <Button variant="secondary" size="sm" onClick={() => void runSql()} disabled={!currentSql || running} className="h-7 px-2 text-xs">
                <Play className="w-3.5 h-3.5 mr-1" />{running ? "Running..." : "Run SQL"}
              </Button>
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
            </div>
            {currentSql ? <textarea aria-label="SQL code" value={currentSql} onChange={event=>setEditedSql(event.target.value)} rows={8} className="w-full p-4 bg-slate-950 text-slate-100 rounded-16 font-mono text-xs overflow-x-auto border border-slate-800 leading-relaxed" /> : <p className="p-4 text-xs text-ink-muted bg-surface rounded-16">No SQL query was executed for this answer.</p>}
            {runError && <p role="alert" className="text-xs text-rose-700">{runError}</p>}
            {runResult && <p className="text-xs text-emerald-700">Validated query completed in {runResult.runtime_ms}ms and returned {runResult.row_count} rows.</p>}
            {runResult && <div className="max-h-48 overflow-auto border border-hairline rounded-12"><table className="min-w-full text-xs font-mono"><thead><tr>{runResult.columns.map((column) => <th key={column} className="px-2 py-1 text-left bg-surface">{column}</th>)}</tr></thead><tbody>{runResult.rows.slice(0, 20).map((row, index) => <tr key={index} className="border-t border-hairline">{runResult.columns.map((column) => <td key={column} className="px-2 py-1">{String(row[column] ?? "")}</td>)}</tr>)}</tbody></table></div>}
          </div>
        )}

        {/* TAB 2: PANDAS CODE */}
        {activeTab === "pandas" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-ink-muted">
              <span>Executed in restricted-AST subprocess sandbox</span>
              <Button variant="secondary" size="sm" disabled={running||!currentPandas} onClick={()=>void runPandas()}>{running?"Running...":"Run Pandas"}</Button>
              <Button variant="ghost" size="sm" disabled={!currentPandas} onClick={()=>downloadCode(currentPandas,"py")}>Download .py</Button>
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
            {currentPandas ? <textarea aria-label="Pandas code" value={currentPandas} onChange={event=>setEditedPandas(event.target.value)} rows={8} className="w-full p-4 bg-slate-950 text-slate-100 rounded-16 font-mono text-xs overflow-x-auto border border-slate-800 leading-relaxed" /> : <p className="p-4 text-xs text-ink-muted bg-surface rounded-16">No Pandas code was executed for this answer.</p>}
            {runError&&<p role="alert" className="text-xs text-rose-700">{runError}</p>}
            {runResult&&<p className="text-xs text-emerald-700">Validated Pandas execution returned {runResult.row_count} rows.</p>}
            {runTable}
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
