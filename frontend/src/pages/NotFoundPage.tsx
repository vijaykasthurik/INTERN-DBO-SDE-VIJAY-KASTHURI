import React from "react";
import { Link } from "react-router-dom";
import { FileQuestion, ArrowLeft } from "lucide-react";
import { Button } from "../components/ui/Button";

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-white flex flex-col items-center justify-center p-6 text-center select-none">
      <div className="w-12 h-12 rounded-24 bg-surface border border-hairline flex items-center justify-center text-ink mb-4 shadow-soft-xs">
        <FileQuestion className="w-6 h-6 text-ink-muted" />
      </div>
      <span className="text-4xl font-serif text-ink tracking-tight font-medium">404</span>
      <h1 className="text-xl font-semibold text-ink mt-2">Page Not Found</h1>
      <p className="text-sm text-ink-muted mt-1 max-w-sm leading-relaxed">
        The requested view does not exist or has moved. Return to the analyst workspace to query your data.
      </p>
      <Link to="/workspace" className="mt-6">
        <Button size="md">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Return to Workspace
        </Button>
      </Link>
    </div>
  );
};
