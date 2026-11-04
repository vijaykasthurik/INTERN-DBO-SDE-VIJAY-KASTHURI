import React, { useEffect, Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ToastProvider } from "./components/ui/Toast";
import { Navbar } from "./components/Navbar";
import { CommandPalette } from "./components/CommandPalette";
import { useAuthStore } from "./stores/authStore";

// Route-level code splitting
const LandingPage = lazy(() =>
  import("./pages/LandingPage").then((m) => ({ default: m.LandingPage }))
);
const AuthPage = lazy(() =>
  import("./pages/AuthPage").then((m) => ({ default: m.AuthPage }))
);
const WorkspacePage = lazy(() =>
  import("./pages/WorkspacePage").then((m) => ({ default: m.WorkspacePage }))
);
const DatasetsPage = lazy(() =>
  import("./pages/DatasetsPage").then((m) => ({ default: m.DatasetsPage }))
);
const DashboardsPage = lazy(() =>
  import("./pages/DashboardsPage").then((m) => ({ default: m.DashboardsPage }))
);
const ReportsPage = lazy(() =>
  import("./pages/ReportsPage").then((m) => ({ default: m.ReportsPage }))
);
const SettingsPage = lazy(() =>
  import("./pages/SettingsPage").then((m) => ({ default: m.SettingsPage }))
);
const NotFoundPage = lazy(() =>
  import("./pages/NotFoundPage").then((m) => ({ default: m.NotFoundPage }))
);

const RouteLoadingSkeleton: React.FC = () => (
  <div className="min-h-screen bg-white flex items-center justify-center">
    <div className="flex flex-col items-center gap-3">
      <div className="w-8 h-8 rounded-full border-2 border-accent-indigo border-t-transparent animate-spin" />
      <span className="text-xs uppercase tracking-widest text-ink-muted font-medium">
        Loading View...
      </span>
    </div>
  </div>
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      retry: 1,
    },
  },
});

const AnimatedRoutes: React.FC = () => {
  return (
    <Suspense fallback={<RouteLoadingSkeleton />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/workspace" element={<WorkspacePage />} />
        <Route path="/datasets" element={<DatasetsPage />} />
        <Route path="/dashboards" element={<DashboardsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  );
};

export const App: React.FC = () => {
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <BrowserRouter>
            <div className="min-h-screen bg-white font-sans text-ink flex flex-col relative selection:bg-accent-indigo/20">
              <Navbar />
              <CommandPalette />
              <main className="flex-1 w-full">
                <AnimatedRoutes />
              </main>
            </div>
          </BrowserRouter>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};

export default App;
