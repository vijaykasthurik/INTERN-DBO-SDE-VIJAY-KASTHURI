import React from "react";
import { FileText, Download, Clock } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";

export const ReportsPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-white text-ink pt-28 pb-16 px-4 sm:px-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-serif tracking-tight font-medium text-ink">
          Executive Reports & Dossiers
        </h1>
        <p className="text-sm text-ink-muted mt-1">
          Export full analytical sessions and dashboards to publication-grade PDF and Markdown.
        </p>
      </div>

      <div className="space-y-4">
        <Card className="p-5 border-hairline flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 rounded-16 bg-surface border border-hairline flex items-center justify-center text-accent-indigo">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-semibold text-ink">Q1 2024 Revenue & Anomaly Audit</h4>
                <Badge variant="accent" size="sm">PDF</Badge>
              </div>
              <p className="text-xs text-ink-muted flex items-center gap-1 mt-0.5">
                <Clock className="w-3 h-3" />
                Generated 10 minutes ago • 4 pages • Includes Matplotlib figures
              </p>
            </div>
          </div>
          <Button variant="secondary" size="sm">
            <Download className="w-3.5 h-3.5 mr-1.5" />
            Download PDF
          </Button>
        </Card>
      </div>
    </div>
  );
};
