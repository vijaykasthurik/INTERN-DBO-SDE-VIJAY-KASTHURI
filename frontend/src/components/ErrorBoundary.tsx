import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "./ui/Button";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught application error:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-white flex items-center justify-center p-6 text-center">
          <div className="max-w-md w-full bg-surface border border-hairline rounded-24 p-8 shadow-soft-lg">
            <div className="w-12 h-12 rounded-20 bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-500 mx-auto mb-4">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h1 className="text-xl font-semibold text-ink tracking-tight mb-2">
              Something went wrong
            </h1>
            <p className="text-sm text-ink-muted mb-6 leading-relaxed">
              Lumen encountered an unexpected error while rendering this view. Our team has been notified.
            </p>
            {this.state.error && (
              <div className="p-3 bg-white border border-hairline rounded-16 text-left mb-6 overflow-x-auto text-xs font-mono text-ink-muted">
                {this.state.error.message}
              </div>
            )}
            <Button onClick={this.handleReset} className="w-full">
              <RotateCcw className="w-4 h-4 mr-2" />
              Reload Application
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
