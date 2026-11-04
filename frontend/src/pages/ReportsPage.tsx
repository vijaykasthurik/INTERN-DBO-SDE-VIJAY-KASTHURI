import React, { useState } from "react";
import {
  FileText,
  Download,
  Clock,
  Sparkles,
  Plus,
  Eye,
  CheckCircle2,
  FileCode,
  Trash2,
} from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Dialog } from "../components/ui/Dialog";
import { api, type ReportExportResponse } from "../lib/api";
import ReactMarkdown from "react-markdown";
import type { ChatSession, ReportArtifactItem } from "../lib/api";

interface ReportItem {
  id: string;
  title: string;
  format: "pdf" | "md";
  created_at: string;
  pages?: number;
  filename: string;
  download_url: string;
}

export const ReportsPage: React.FC = () => {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSession, setSelectedSession] = useState("");
  const [isExportOpen, setIsExportOpen] = useState<boolean>(false);
  const [exportTitle, setExportTitle] = useState<string>("Q1 2024 Revenue & Operations Brief");
  const [exportFormat, setExportFormat] = useState<"pdf" | "md">("pdf");
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [previewReport, setPreviewReport] = useState<ReportItem | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewMarkdown, setPreviewMarkdown] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  React.useEffect(() => {
    Promise.all([api.reports.list(), api.chat.listSessions()])
      .then(([artifacts, currentSessions]: [ReportArtifactItem[], ChatSession[]]) => {
        setReports(artifacts.map((item) => ({ ...item, id: item.report_id })));
        setSessions(currentSessions);
        setSelectedSession(currentSessions[0]?.id || "");
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Unable to load reports."));
  }, []);

  const handleExport = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsExporting(true);
    setError(null);
    try {
      if (!selectedSession) throw new Error("Create an analysis session before exporting a report.");
      const res: ReportExportResponse = await api.reports.export({
        session_id: selectedSession,
        title: exportTitle,
        format: exportFormat,
      });

      const newReport: ReportItem = {
        id: res.report_id,
        title: res.title,
        format: res.format,
        created_at: "Just now",
        filename: `${res.report_id}.${res.format}`,
        download_url: res.download_url,
      };

      setReports((current) => [newReport, ...current]);
      setIsExportOpen(false);
      await downloadReport(newReport);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Report generation failed.");
    } finally {
      setIsExporting(false);
    }
  };

  const saveBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const downloadReport = async (report: ReportItem) => {
    setDownloading(report.id);
    setError(null);
    try {
      const response = await api.reports.download(report.download_url);
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const serverName = disposition.match(/filename="?([^";]+)"?/i)?.[1];
      saveBlob(blob, serverName || report.filename);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Report download failed.");
    } finally {
      setDownloading(null);
    }
  };

  const preview = async (report: ReportItem) => {
    setError(null);
    setPreviewReport(report);
    setPreviewUrl(null);
    setPreviewMarkdown(null);
    try {
      const response = await api.reports.download(report.download_url);
      const blob = await response.blob();
      if (report.format === "md") setPreviewMarkdown(await blob.text());
      else setPreviewUrl(URL.createObjectURL(blob));
    } catch (err: unknown) {
      setPreviewReport(null);
      setError(err instanceof Error ? err.message : "Report preview failed.");
    }
  };

  const handleDeleteReport = async (reportId: string) => {
    setError(null);
    try {
      await api.reports.delete(reportId);
      setReports((current) => current.filter((r) => r.id !== reportId));
      if (previewReport?.id === reportId) {
        setPreviewReport(null);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete report.");
    }
  };

  return (
    <div className="min-h-screen bg-white text-ink pt-28 pb-16 px-4 sm:px-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-accent-indigo" />
            <span className="text-xs uppercase tracking-widest text-ink-muted font-medium">
              Publications & Artifacts
            </span>
          </div>
          <h1 className="text-3xl font-serif tracking-tight font-medium text-ink">
            Executive Reports & Dossiers
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Export full analytical sessions and dashboards to publication-grade PDF and Markdown.
          </p>
        </div>

        <Button size="md" onClick={() => setIsExportOpen(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Export New Report
        </Button>
      </div>

      {error && <div role="alert" className="mb-5 p-3 rounded-16 bg-rose-50 border border-rose-100 text-rose-700 text-sm">{error}</div>}

      {/* Reports List */}
      <div className="space-y-4">
        {reports.length === 0 && (
          <Card className="p-8 text-center text-sm text-ink-muted">No reports have been generated for this account yet.</Card>
        )}
        {reports.map((report) => (
          <Card
            key={report.id}
            className="p-5 border-hairline hover:shadow-soft-sm transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
          >
            <div className="flex items-start sm:items-center gap-4">
              <div className="w-10 h-10 rounded-16 bg-surface border border-hairline flex items-center justify-center text-accent-indigo flex-shrink-0">
                {report.format === "pdf" ? (
                  <FileText className="w-5 h-5" />
                ) : (
                  <FileCode className="w-5 h-5 text-accent-cyan" />
                )}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-semibold text-ink">{report.title}</h4>
                  <Badge
                    variant={report.format === "pdf" ? "accent" : "neutral"}
                    size="sm"
                  >
                    {report.format.toUpperCase()}
                  </Badge>
                </div>
                <p className="text-xs text-ink-muted flex items-center gap-1.5 mt-0.5">
                  <Clock className="w-3 h-3" />
                  Generated {report.created_at}
                  {report.format === "pdf" ? " • PDF report" : " • Markdown report"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={() => void preview(report)} className="text-xs text-ink-muted hover:text-ink">
                <Eye className="w-3.5 h-3.5 mr-1.5" />Preview
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => void downloadReport(report)}
                disabled={downloading === report.id}
                className="text-xs"
              >
                <Download className="w-3.5 h-3.5 mr-1.5" />
                {downloading === report.id ? "Downloading..." : `Download ${report.format.toUpperCase()}`}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => void handleDeleteReport(report.id)}
                className="text-xs text-rose-500 hover:text-rose-700 hover:bg-rose-50"
                aria-label="Delete report"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {/* Export Report Dialog */}
      <Dialog
        isOpen={isExportOpen}
        onClose={() => setIsExportOpen(false)}
        title="Export Analytical Report"
      >
        <form onSubmit={handleExport} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-ink uppercase tracking-wider mb-1.5">Analysis Session</label>
            <select value={selectedSession} onChange={(e) => setSelectedSession(e.target.value)} required className="w-full px-3 py-2 text-sm bg-surface rounded-12 border border-hairline text-ink">
              {sessions.length === 0 && <option value="">No analysis sessions available</option>}
              {sessions.map((session) => <option key={session.id} value={session.id}>{session.title}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-ink uppercase tracking-wider mb-1.5">
              Report Title
            </label>
            <input
              type="text"
              value={exportTitle}
              onChange={(e) => setExportTitle(e.target.value)}
              required
              className="w-full px-3 py-2 text-sm bg-surface rounded-12 border border-hairline text-ink focus:outline-none focus:ring-2 focus:ring-accent-indigo/20"
              placeholder="e.g. Q1 Revenue & Anomaly Audit"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-ink uppercase tracking-wider mb-1.5">
              Export Format
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setExportFormat("pdf")}
                className={`p-3 rounded-12 border text-left transition-all ${
                  exportFormat === "pdf"
                    ? "border-accent-indigo bg-indigo-50/30 text-ink ring-2 ring-accent-indigo/20"
                    : "border-hairline bg-surface hover:bg-slate-50 text-ink-muted"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-xs text-ink">PDF Document</span>
                  {exportFormat === "pdf" && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-accent-indigo" />
                  )}
                </div>
                <p className="text-[11px] text-ink-muted">
                  ReportLab compiled document with Matplotlib charts and executive summary.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setExportFormat("md")}
                className={`p-3 rounded-12 border text-left transition-all ${
                  exportFormat === "md"
                    ? "border-accent-indigo bg-indigo-50/30 text-ink ring-2 ring-accent-indigo/20"
                    : "border-hairline bg-surface hover:bg-slate-50 text-ink-muted"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-xs text-ink">Markdown</span>
                  {exportFormat === "md" && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-accent-indigo" />
                  )}
                </div>
                <p className="text-[11px] text-ink-muted">
                  Clean portable markdown formatted with Evidence Ledger citations.
                </p>
              </button>
            </div>
          </div>

          <div className="p-3 bg-surface rounded-12 border border-hairline text-xs text-ink-muted flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-accent-indigo flex-shrink-0 mt-0.5" />
            <span>
              All reports are compiled using verified query results from the Evidence Ledger.
              Ungrounded numbers are strictly excluded.
            </span>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsExportOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isExporting}>
              {isExporting ? "Compiling..." : "Generate & Export"}
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Generated Report Preview Dialog */}
      <Dialog
        isOpen={Boolean(previewReport)}
        onClose={() => { setPreviewReport(null); setPreviewMarkdown(null); if (previewUrl) URL.revokeObjectURL(previewUrl); setPreviewUrl(null); }}
        title={previewReport?.title || "Report Preview"}
      >
        <div className="space-y-4">
          {previewReport?.format === "pdf" ? (
            previewUrl ? <iframe title={previewReport.title} src={previewUrl} className="w-full h-[70vh] rounded-12 border border-hairline" /> : <p className="text-sm text-ink-muted">Loading report preview…</p>
          ) : (
            <div className="p-4 bg-surface rounded-12 text-sm max-h-96 overflow-y-auto prose prose-sm max-w-none">
              {previewMarkdown !== null ? <ReactMarkdown>{previewMarkdown}</ReactMarkdown> : <p className="text-ink-muted">Loading report preview…</p>}
            </div>
          )}
          <div className="flex justify-end">
            <Button variant="secondary" onClick={() => setPreviewReport(null)}>
              Close
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};
