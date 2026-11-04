import React from "react";
import { Link } from "react-router-dom";
import { Sparkles, MessageSquare, Database, ArrowRight } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { useDatasetStore } from "../stores/datasetStore";

export const WorkspacePage: React.FC = () => {
  const { datasets } = useDatasetStore();

  return (
    <div className="min-h-screen bg-white text-ink pt-28 pb-16 px-4 sm:px-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-serif tracking-tight font-medium text-ink">
          Analyst Workspace
        </h1>
        <p className="text-sm text-ink-muted mt-1">
          Chat with your data using grounded DuckDB queries and skeptic verification.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 col-span-2 border-hairline">
          <div className="flex items-center gap-2 mb-4 text-accent-indigo">
            <Sparkles className="w-5 h-5" />
            <h3 className="font-semibold text-ink">Ask a Question</h3>
          </div>
          <p className="text-sm text-ink-muted mb-6">
            Lumen plans your analysis into DAG waves, queries DuckDB, verifies every number against the Evidence Ledger, and charts the result.
          </p>
          <div className="flex items-center gap-3">
            <input
              type="text"
              placeholder="e.g. Which region had the highest revenue last year?"
              className="flex-1 px-4 py-2.5 rounded-pill border border-hairline bg-surface text-sm focus:outline-none focus:ring-2 focus:ring-accent-indigo"
            />
            <Button size="md">
              <MessageSquare className="w-4 h-4 mr-2" />
              Ask
            </Button>
          </div>
        </Card>

        <Card className="p-6 border-hairline flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-3 text-ink">
              <Database className="w-5 h-5 text-accent-indigo" />
              <h3 className="font-semibold">Active Datasets</h3>
            </div>
            <p className="text-xs text-ink-muted">
              {datasets.length > 0
                ? `${datasets.length} tables currently staged in DuckDB.`
                : "No datasets loaded yet. Upload your CSV files to begin."}
            </p>
          </div>
          <Link to="/datasets" className="mt-4">
            <Button variant="secondary" size="sm" className="w-full">
              Manage Tables <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          </Link>
        </Card>
      </div>
    </div>
  );
};
