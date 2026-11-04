import React from "react";
import { LayoutDashboard, Plus, Sparkles } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";

export const DashboardsPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-white text-ink pt-28 pb-16 px-4 sm:px-6 max-w-7xl mx-auto">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-serif tracking-tight font-medium text-ink">
            Executive Dashboards
          </h1>
          <p className="text-sm text-ink-muted mt-1">
            Auto-compiled 5-widget business overviews with KPIs, trends, and market share.
          </p>
        </div>
        <Button size="md">
          <Plus className="w-4 h-4 mr-2" />
          Generate Dashboard
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-6 border-hairline">
          <div className="flex items-center gap-2 mb-2 text-accent-indigo">
            <LayoutDashboard className="w-5 h-5" />
            <h3 className="font-semibold text-ink">Executive Revenue Overview</h3>
          </div>
          <p className="text-xs text-ink-muted mb-4">
            Aggregated KPIs, monthly sales volume, top customer segments, and anomaly alerts.
          </p>
          <div className="p-4 bg-surface rounded-16 border border-hairline text-center text-xs text-ink-muted">
            <Sparkles className="w-4 h-4 text-accent-indigo mx-auto mb-1" />
            Click to open interactive dashboard widgets
          </div>
        </Card>
      </div>
    </div>
  );
};
