import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  UploadCloud,
  FileSpreadsheet,
  AlertCircle,
  Trash2,
  ChevronDown,
  ChevronUp,
  Table,
  Link as LinkIcon,
} from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "../components/ui/Card";
import { ProgressRing } from "../components/ui/ProgressRing";
import { Badge } from "../components/ui/Badge";
import { EmptyState } from "../components/ui/EmptyState";
import { useDatasetStore } from "../stores/datasetStore";

export const DatasetsPage: React.FC = () => {
  const {
    datasets,
    selectedDataset,
    relationships,
    isLoading,
    fetchDatasets,
    selectDataset,
    uploadFiles,
    deleteDataset,
  } = useDatasetStore();

  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isQualityExpanded, setIsQualityExpanded] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const handleFiles = async (files: FileList | File[]) => {
    const validFiles: File[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file.name.endsWith(".csv") || file.name.endsWith(".txt")) {
        validFiles.push(file);
      } else {
        setUploadError(`File "${file.name}" is not a CSV. Please upload CSV files only.`);
        return;
      }
    }

    if (validFiles.length === 0) return;

    setUploadError(null);
    setUploadProgress(15);
    const progressTimer = setInterval(() => {
      setUploadProgress((prev) => {
        if (!prev) return 15;
        if (prev >= 90) return prev;
        return prev + 25;
      });
    }, 200);

    try {
      await uploadFiles(validFiles);
      setUploadProgress(100);
      setTimeout(() => setUploadProgress(null), 500);
    } catch (err: unknown) {
      setUploadProgress(null);
      setUploadError(err instanceof Error ? err.message : "Failed to upload file");
    } finally {
      clearInterval(progressTimer);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const qualityScore = Math.round(
    selectedDataset?.quality_score ??
      selectedDataset?.quality_report?.overall_score ??
      94
  );

  const issues = selectedDataset?.quality_summary?.issues || [];
  const dupCount =
    selectedDataset?.quality_report?.duplicate_rows ??
    issues.filter((i) => i.category === "duplicates").length;
  const missingCount =
    selectedDataset?.quality_report?.missing_values_count ??
    issues.filter((i) => i.category === "missing").length;
  const constantCount =
    selectedDataset?.quality_report?.constant_columns?.length ??
    issues.filter((i) => i.category === "constant").length;
  const impossibleCount =
    selectedDataset?.quality_report?.impossible_values_count ??
    issues.filter((i) => i.category === "impossible_value").length;

  return (
    <div className="min-h-screen bg-white text-ink pt-28 pb-16 px-4 sm:px-6 max-w-7xl mx-auto">
      {/* PAGE HEADER */}
      <div className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-serif tracking-tight font-medium text-ink">
            Datasets & Data Quality
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Upload CSVs into your isolated DuckDB database. Profiling and health checks run automatically.
          </p>
        </div>
        <Button
          onClick={() => fileInputRef.current?.click()}
          className="shadow-soft-xs"
          size="md"
        >
          <UploadCloud className="w-4 h-4 mr-2" />
          Upload New CSV
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.txt"
          multiple
          className="hidden"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
      </div>

      {/* UPLOAD DROPZONE */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-28 p-8 text-center cursor-pointer transition-all duration-200 select-none ${
          isDragging
            ? "border-accent-indigo bg-indigo-50/40"
            : "border-hairline bg-surface/40 hover:bg-surface/80"
        }`}
      >
        <div className="max-w-md mx-auto flex flex-col items-center">
          {uploadProgress !== null ? (
            <div className="flex flex-col items-center py-2">
              <ProgressRing value={uploadProgress} size={64} strokeWidth={6} />
              <p className="text-xs font-medium text-ink mt-3">Ingesting & Profiling CSV...</p>
            </div>
          ) : (
            <>
              <div className="w-12 h-12 rounded-24 bg-white border border-hairline shadow-soft-xs flex items-center justify-center text-accent-indigo mb-3">
                <UploadCloud className="w-6 h-6" />
              </div>
              <h3 className="text-base font-semibold text-ink">
                Drag and drop your CSV files here
              </h3>
              <p className="text-xs text-ink-muted mt-1">
                Supports sales, customer, orders, or any structured tabular data.
              </p>
              <span className="text-[11px] font-medium text-accent-indigo mt-3">
                Or click to browse from your computer
              </span>
            </>
          )}
        </div>
      </div>

      {uploadError && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 p-4 rounded-16 bg-rose-50 border border-rose-100 text-rose-700 text-xs flex items-center gap-2"
        >
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{uploadError}</span>
        </motion.div>
      )}

      {/* MAIN DATASET WORKSPACE: LIST & INSPECTOR */}
      {datasets.length === 0 && !isLoading ? (
        <div className="mt-12">
          <EmptyState
            icon={<FileSpreadsheet className="w-6 h-6" />}
            title="No datasets uploaded yet"
            description="Upload one or more CSVs above to begin chatting with your data and detecting automated insights."
          />
        </div>
      ) : (
        <div className="mt-10 grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* DATASET SELECTOR LIST */}
          <div className="lg:col-span-4 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-ink-muted mb-2">
              Available Tables ({datasets.length})
            </h3>
            <div className="space-y-2">
              {datasets.map((d) => {
                const isSelected = selectedDataset?.id === d.id;
                return (
                  <motion.div
                    key={d.id}
                    layout
                    onClick={() => selectDataset(d.id)}
                    className={`p-4 rounded-20 border transition-all cursor-pointer flex items-center justify-between ${
                      isSelected
                        ? "bg-white border-accent-indigo shadow-soft-sm"
                        : "bg-surface/50 border-hairline hover:bg-white"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-16 bg-white border border-hairline flex items-center justify-center text-accent-indigo">
                        <Table className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-ink">{d.name}</p>
                        <p className="text-xs text-ink-muted font-mono">
                          {d.row_count.toLocaleString()} rows • {d.column_count} cols
                        </p>
                      </div>
                    </div>
                    {isSelected && (
                      <Badge variant="accent" size="sm">Active</Badge>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </div>

          {/* ACTIVE DATASET DETAILS & QUALITY INSPECTOR */}
          {selectedDataset && (
            <div className="lg:col-span-8 space-y-6">
              {/* TABLE HEADER & ACTIONS */}
              <div className="p-6 bg-white rounded-24 border border-hairline shadow-soft-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-serif font-medium text-ink">
                      {selectedDataset.name}
                    </h2>
                    <Badge variant="neutral" size="sm">DuckDB Staged</Badge>
                  </div>
                  <p className="text-xs text-ink-muted mt-1">
                    Ingested{" "}
                    {new Date(
                      selectedDataset.created_at || Date.now()
                    ).toLocaleDateString()}{" "}
                    • {(((selectedDataset.file_size || 0)) / 1024).toFixed(1)} KB
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => deleteDataset(selectedDataset.id)}
                    className="text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                    Delete Table
                  </Button>
                </div>
              </div>

              {/* DATA HEALTH AUDITOR CARD */}
              <Card className="p-6 border-hairline bg-surface/40">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
                  <div className="flex items-center gap-5">
                    <ProgressRing
                      value={qualityScore}
                      size={72}
                      strokeWidth={7}
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-base font-semibold text-ink">Data Health Score</h4>
                        <Badge
                          variant={qualityScore >= 80 ? "success" : qualityScore >= 60 ? "warning" : "error"}
                          size="sm"
                        >
                          {qualityScore >= 80 ? "High Integrity" : qualityScore >= 60 ? "Moderate" : "Action Needed"}
                        </Badge>
                      </div>
                      <p className="text-xs text-ink-muted mt-1 max-w-sm">
                        Calculated from duplicate records, missing cells, type stability, and statistical outliers.
                      </p>
                    </div>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsQualityExpanded(!isQualityExpanded)}
                  >
                    <span>{isQualityExpanded ? "Hide Audit Details" : "View Quality Breakdown"}</span>
                    {isQualityExpanded ? (
                      <ChevronUp className="w-4 h-4 ml-1" />
                    ) : (
                      <ChevronDown className="w-4 h-4 ml-1" />
                    )}
                  </Button>
                </div>

                {/* EXPANDABLE QUALITY DETAILS */}
                <AnimatePresence>
                  {isQualityExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-6 pt-6 border-t border-hairline overflow-hidden"
                    >
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div className="p-3 bg-white rounded-16 border border-hairline">
                          <p className="text-[11px] text-ink-muted">Duplicate Rows</p>
                          <p className="text-lg font-mono font-semibold text-ink mt-1">
                            {dupCount}
                          </p>
                        </div>
                        <div className="p-3 bg-white rounded-16 border border-hairline">
                          <p className="text-[11px] text-ink-muted">Missing Values</p>
                          <p className="text-lg font-mono font-semibold text-ink mt-1">
                            {missingCount}
                          </p>
                        </div>
                        <div className="p-3 bg-white rounded-16 border border-hairline">
                          <p className="text-[11px] text-ink-muted">Constant Columns</p>
                          <p className="text-lg font-mono font-semibold text-ink mt-1">
                            {constantCount}
                          </p>
                        </div>
                        <div className="p-3 bg-white rounded-16 border border-hairline">
                          <p className="text-[11px] text-ink-muted">Outliers / Impossible</p>
                          <p className="text-lg font-mono font-semibold text-ink mt-1">
                            {impossibleCount}
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </Card>

              {/* RELATIONSHIP GRAPH CARD */}
              <Card className="p-6 border-hairline">
                <CardHeader className="p-0 pb-4">
                  <div className="flex items-center gap-2">
                    <LinkIcon className="w-4 h-4 text-accent-indigo" />
                    <CardTitle className="text-base">Foreign Key Relationships</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  {relationships.length === 0 ? (
                    <p className="text-xs text-ink-muted py-3">
                      No multi-table join relationships detected. Upload related tables (e.g. customers, products) to auto-detect join keys.
                    </p>
                  ) : (
                    <div className="space-y-3">
                      {relationships.map((rel, i) => (
                        <div
                          key={i}
                          className="p-3 rounded-16 bg-surface border border-hairline flex items-center justify-between text-xs"
                        >
                          <div className="flex items-center gap-2 font-mono">
                            <span className="font-semibold text-ink">{rel.source_table}.{rel.source_column}</span>
                            <span className="text-accent-indigo font-bold">⇄</span>
                            <span className="font-semibold text-ink">{rel.target_table}.{rel.target_column}</span>
                          </div>
                          <Badge variant="accent" size="sm">
                            {Math.round(rel.overlap_ratio * 100)}% Match
                          </Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* COLUMN PROFILING LIST */}
              <Card className="p-6 border-hairline">
                <CardHeader className="p-0 pb-4">
                  <CardTitle className="text-base">Columns & Statistical Schema</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="divide-y divide-hairline">
                    {(selectedDataset.columns || []).map((col) => (
                      <div key={col.name} className="py-3 flex items-center justify-between text-xs">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-semibold text-ink">{col.name}</span>
                            <Badge variant="neutral" size="sm">{col.data_type}</Badge>
                          </div>
                          {col.description && (
                            <p className="text-[11px] text-ink-muted mt-0.5">{col.description}</p>
                          )}
                        </div>
                        <div className="text-right font-mono text-[11px] text-ink-muted">
                          <span>{col.distinct_count ?? 0} unique</span>
                          {(col.null_count || 0) > 0 && (
                            <span className="text-amber-600 ml-2">({col.null_count} nulls)</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
