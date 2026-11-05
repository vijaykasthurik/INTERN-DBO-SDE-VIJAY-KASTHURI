import React, { useState, useEffect, useMemo } from "react";
import ReactECharts from "echarts-for-react";
import {
  Activity,
  Users,
  Database,
  Sliders,
  ShieldAlert,
  LogOut,
  Search,
  Eye,
  UserCheck,
  UserX,
  Trash2,
  Play,
  Download,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Lock,
  Mail,
  Shield,
  Clock,
  HardDrive,
  Cpu,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

interface AdminUser {
  id: number;
  email: string;
  role: string;
}

export const AdminPage: React.FC = () => {
  // Ensure robots meta tag
  useEffect(() => {
    let meta = document.querySelector('meta[name="robots"]') as HTMLMetaElement | null;
    const originalContent = meta?.getAttribute("content") || null;
    if (!meta) {
      meta = document.createElement("meta");
      meta.name = "robots";
      document.head.appendChild(meta);
    }
    meta.content = "noindex, nofollow";

    return () => {
      if (meta) {
        if (originalContent) meta.content = originalContent;
        else meta.remove();
      }
    };
  }, []);

  // Auth state
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem("lumen_admin_token"));
  const [adminUser, setAdminUser] = useState<AdminUser | null>(() => {
    const raw = sessionStorage.getItem("lumen_admin_user");
    return raw ? JSON.parse(raw) : null;
  });

  // Login form state
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginTotp, setLoginTotp] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Active tab: 'dashboard' | 'users' | 'database' | 'operations' | 'audit'
  const [activeTab, setActiveTab] = useState<"dashboard" | "users" | "database" | "operations" | "audit">("dashboard");

  // Common notification banner
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const showBanner = (type: "success" | "error", message: string) => {
    setBanner({ type, message });
    setTimeout(() => setBanner(null), 5000);
  };

  const handleSignOut = () => {
    sessionStorage.removeItem("lumen_admin_token");
    sessionStorage.removeItem("lumen_admin_user");
    setToken(null);
    setAdminUser(null);
    window.location.href = "/";
  };

  // Helper for authenticated admin fetch
  const adminFetch = async (endpoint: string, options: RequestInit = {}) => {
    if (!token) throw new Error("Unauthenticated");
    const headers = new Headers(options.headers || {});
    headers.set("Authorization", `Bearer ${token}`);
    if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }

    const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
    if (res.status === 401 || res.status === 403) {
      handleSignOut();
      throw new Error("Session expired or unauthorized.");
    }
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || data.detail || `Request failed with status ${res.status}`);
    }
    return data;
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError(null);
    try {
      const res = await fetch(`${API_BASE}/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: loginEmail.trim(),
          password: loginPassword,
          totp_code: loginTotp.trim() || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.message || "Invalid administrative credentials");
      }

      sessionStorage.setItem("lumen_admin_token", data.access_token);
      sessionStorage.setItem("lumen_admin_user", JSON.stringify(data.admin));
      setToken(data.access_token);
      setAdminUser(data.admin);
    } catch (err: unknown) {
      setLoginError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoginLoading(false);
    }
  };

  // -------------------------------------------------------------
  // TAB 1: Dashboard State & Fetch
  // -------------------------------------------------------------
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);

  const fetchDashboard = async () => {
    if (!token) return;
    setDashboardLoading(true);
    try {
      const data = await adminFetch("/admin/dashboard");
      setDashboardData(data);
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Failed to load dashboard telemetry");
    } finally {
      setDashboardLoading(false);
    }
  };

  useEffect(() => {
    if (token && activeTab === "dashboard") {
      fetchDashboard();
    }
  }, [token, activeTab]);

  // -------------------------------------------------------------
  // TAB 2: Users State & Fetch
  // -------------------------------------------------------------
  const [usersList, setUsersList] = useState<any[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersPage, setUsersPage] = useState(1);
  const [usersSearch, setUsersSearch] = useState("");
  const [usersRoleFilter, setUsersRoleFilter] = useState("");
  const [usersLoading, setUsersLoading] = useState(false);
  const [selectedUserDetails, setSelectedUserDetails] = useState<any | null>(null);

  const fetchUsers = async () => {
    if (!token) return;
    setUsersLoading(true);
    try {
      const query = new URLSearchParams({
        page: usersPage.toString(),
        per_page: "15",
        search: usersSearch,
        role: usersRoleFilter,
      });
      const data = await adminFetch(`/admin/users?${query.toString()}`);
      setUsersList(data.items || []);
      setUsersTotal(data.total || 0);
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Failed to load user directory");
    } finally {
      setUsersLoading(false);
    }
  };

  useEffect(() => {
    if (token && activeTab === "users") {
      fetchUsers();
    }
  }, [token, activeTab, usersPage, usersRoleFilter]);

  const handleToggleUserStatus = async (user: any) => {
    try {
      await adminFetch(`/admin/users/${user.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !user.is_active }),
      });
      showBanner("success", `User ${user.email} ${user.is_active ? "disabled" : "enabled"} successfully.`);
      fetchUsers();
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Status update failed");
    }
  };

  const handleForceLogout = async (user: any) => {
    try {
      await adminFetch(`/admin/users/${user.id}/logout`, { method: "POST" });
      showBanner("success", `Active sessions revoked for ${user.email}.`);
      fetchUsers();
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Force logout failed");
    }
  };

  const handleDeleteUser = async (user: any) => {
    if (!window.confirm(`Are you sure you want to permanently delete user ${user.email} and all data?`)) {
      return;
    }
    try {
      await adminFetch(`/admin/users/${user.id}`, { method: "DELETE" });
      showBanner("success", `User ${user.email} deleted.`);
      fetchUsers();
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Delete failed");
    }
  };

  const handleViewUserDetails = async (user: any) => {
    try {
      const data = await adminFetch(`/admin/users/${user.id}/details`);
      setSelectedUserDetails(data);
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Failed to load details");
    }
  };

  // -------------------------------------------------------------
  // TAB 3: Database & SQL Console
  // -------------------------------------------------------------
  const [dbSubTab, setDbSubTab] = useState<"browser" | "sql" | "maintenance">("browser");
  const [tablesList, setTablesList] = useState<any[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>("");
  const [tableData, setTableData] = useState<any>(null);
  const [tablePage, setTablePage] = useState(1);
  const [sqlQuery, setSqlQuery] = useState("SELECT id, email, role, is_active FROM users LIMIT 10;");
  const [queryResult, setQueryResult] = useState<any | null>(null);
  const [queryRunning, setQueryRunning] = useState(false);

  const fetchTables = async () => {
    if (!token) return;
    try {
      const data = await adminFetch("/admin/database/tables");
      setTablesList(data.tables || []);
      if (!selectedTable && data.tables?.length > 0) {
        setSelectedTable(data.tables[0].name);
      }
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Failed to list tables");
    }
  };

  const fetchTableRows = async (table: string, page: number) => {
    if (!token || !table) return;
    try {
      const data = await adminFetch(`/admin/database/browse/${table}?page=${page}&per_page=20`);
      setTableData(data);
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Failed to browse table");
    }
  };

  useEffect(() => {
    if (token && activeTab === "database") {
      fetchTables();
    }
  }, [token, activeTab]);

  useEffect(() => {
    if (token && activeTab === "database" && dbSubTab === "browser" && selectedTable) {
      fetchTableRows(selectedTable, tablePage);
    }
  }, [token, activeTab, dbSubTab, selectedTable, tablePage]);


  const handleRunSql = async () => {
    if (!sqlQuery.trim()) return;
    setQueryRunning(true);
    setQueryResult(null);
    try {
      const data = await adminFetch("/admin/database/query", {
        method: "POST",
        body: JSON.stringify({ query: sqlQuery }),
      });
      setQueryResult(data);
      showBanner("success", `Query completed in ${data.duration_ms}ms (${data.row_count} rows).`);
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Query failed");
    } finally {
      setQueryRunning(false);
    }
  };

  const handleExportCsv = () => {
    if (!queryResult || !queryResult.rows || queryResult.rows.length === 0) return;
    const cols = queryResult.columns;
    const csvRows = [cols.join(",")];
    for (const r of queryResult.rows) {
      const values = cols.map((c: string) => {
        const val = r[c] !== null && r[c] !== undefined ? String(r[c]) : "";
        return `"${val.replace(/"/g, '""')}"`;
      });
      csvRows.push(values.join(","));
    }
    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `admin_query_export_${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleMaintenance = async (action: "vacuum" | "purge_traces" | "clear_cache") => {
    if (!window.confirm(`Execute maintenance action '${action}'?`)) return;
    try {
      await adminFetch("/admin/database/maintenance", {
        method: "POST",
        body: JSON.stringify({ action }),
      });
      showBanner("success", `Maintenance action '${action}' completed successfully.`);
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Maintenance execution failed");
    }
  };

  // -------------------------------------------------------------
  // TAB 4: Operations & Settings
  // -------------------------------------------------------------
  const [sysSettings, setSysSettings] = useState<any>(null);
  const [envStatus, setEnvStatus] = useState<{ name: string; is_set: boolean }[]>([]);
  const [contactMessages, setContactMessages] = useState<any[]>([]);

  const fetchOperations = async () => {
    if (!token) return;
    try {
      const data = await adminFetch("/admin/operations/settings");
      setSysSettings(data.settings);
      setEnvStatus(data.env_status || []);

      const msgData = await adminFetch("/admin/operations/contact-messages?page=1&per_page=20");
      setContactMessages(msgData.items || []);
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Failed to load operations telemetry");
    }
  };

  useEffect(() => {
    if (token && activeTab === "operations") {
      fetchOperations();
    }
  }, [token, activeTab]);

  const handleUpdateFlag = async (key: string, currentValue: boolean) => {
    try {
      await adminFetch("/admin/operations/settings", {
        method: "PATCH",
        body: JSON.stringify({
          key,
          value: { enabled: !currentValue },
        }),
      });
      showBanner("success", `Setting '${key}' updated to ${!currentValue}.`);
      fetchOperations();
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Update failed");
    }
  };

  const handleDeleteContact = async (id: number) => {
    try {
      await adminFetch(`/admin/operations/contact-messages/${id}`, { method: "DELETE" });
      showBanner("success", "Message removed.");
      fetchOperations();
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Delete failed");
    }
  };

  // -------------------------------------------------------------
  // TAB 5: Audit Log
  // -------------------------------------------------------------
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [auditActionFilter, setAuditActionFilter] = useState("");
  const [expandedLogId, setExpandedLogId] = useState<number | null>(null);

  const fetchAuditLogs = async () => {
    if (!token) return;
    try {
      const query = new URLSearchParams({
        action: auditActionFilter,
        page: "1",
        per_page: "50",
      });
      const data = await adminFetch(`/admin/audit-logs?${query.toString()}`);
      setAuditLogs(data.items || []);
    } catch (err: unknown) {
      showBanner("error", err instanceof Error ? err.message : "Failed to load audit logs");
    }
  };

  useEffect(() => {
    if (token && activeTab === "audit") {
      fetchAuditLogs();
    }
  }, [token, activeTab, auditActionFilter]);

  // ECharts specs
  const dailyQueriesChartOption = useMemo(() => {
    if (!dashboardData?.charts?.daily_queries) return {};
    const dates = dashboardData.charts.daily_queries.map((d: any) => d.date);
    const counts = dashboardData.charts.daily_queries.map((d: any) => d.count);
    return {
      tooltip: { trigger: "axis" },
      grid: { left: "3%", right: "4%", bottom: "3%", top: "10%", containLabel: true },
      xAxis: { type: "category", data: dates, boundaryGap: false },
      yAxis: { type: "value", splitLine: { lineStyle: { color: "#F1F5F9" } } },
      series: [
        {
          name: "Queries",
          type: "line",
          smooth: true,
          data: counts,
          areaStyle: { opacity: 0.1, color: "#6366F1" },
          itemStyle: { color: "#6366F1" },
        },
      ],
    };
  }, [dashboardData]);

  const providerTokensChartOption = useMemo(() => {
    if (!dashboardData?.charts?.tokens_by_provider) return {};
    const providers = dashboardData.charts.tokens_by_provider.map((p: any) => p.provider);
    const tokens = dashboardData.charts.tokens_by_provider.map((p: any) => p.tokens);
    return {
      tooltip: { trigger: "axis" },
      grid: { left: "3%", right: "4%", bottom: "3%", top: "10%", containLabel: true },
      xAxis: { type: "category", data: providers },
      yAxis: { type: "value", splitLine: { lineStyle: { color: "#F1F5F9" } } },
      series: [
        {
          name: "Tokens",
          type: "bar",
          data: tokens,
          itemStyle: {
            color: "#8B5CF6",
            borderRadius: [4, 4, 0, 0],
          },
        },
      ],
    };
  }, [dashboardData]);

  // -------------------------------------------------------------
  // RENDER: Unauthenticated Login Card
  // -------------------------------------------------------------
  if (!token) {
    return (
      <div className="min-h-screen bg-[#FAFAFB] flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-md bg-white border border-slate-200/80 rounded-2xl p-8 shadow-sm">
          <div className="flex flex-col items-center text-center mb-6">
            <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-800 mb-3 border border-slate-200">
              <Shield className="w-5 h-5 text-slate-700" />
            </div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-50 border border-amber-200/80 text-amber-700 text-[11px] font-semibold tracking-wider uppercase mb-2">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
              Confidential Console
            </div>
            <h1 className="text-xl font-semibold tracking-tight text-slate-900">Lumen Administration</h1>
            <p className="text-xs text-slate-500 mt-1">Authorized personnel authentication required</p>
          </div>

          {loginError && (
            <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200/80 text-rose-700 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{loginError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Administrative Email</label>
              <input
                type="email"
                required
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                placeholder="admin@lumen.internal"
                className="w-full text-sm px-3 py-2 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Password</label>
              <input
                type="password"
                required
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="••••••••••••••••"
                className="w-full text-sm px-3 py-2 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                2FA TOTP Code <span className="text-slate-400 font-normal">(if configured)</span>
              </label>
              <input
                type="text"
                value={loginTotp}
                onChange={(e) => setLoginTotp(e.target.value)}
                placeholder="6-digit code"
                maxLength={6}
                className="w-full text-sm px-3 py-2 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-colors tracking-widest font-mono"
              />
            </div>

            <button
              type="submit"
              disabled={loginLoading}
              className="w-full py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium transition-colors shadow-sm disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loginLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <span>Authenticate Session</span>
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------
  // RENDER: Authenticated Dashboard Shell
  // -------------------------------------------------------------
  return (
    <div className="min-h-screen bg-[#FAFAFB] text-slate-900 font-sans flex flex-col antialiased">
      {/* Top Administrative Header */}
      <header className="bg-white border-b border-slate-200/80 sticky top-0 z-30 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="font-serif text-lg font-bold tracking-tight text-slate-950">Lumen</span>
            <span className="text-xs text-slate-400 font-medium">/</span>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">Operations</span>
          </div>

          <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-50 border border-amber-200/70 text-amber-800 text-[10px] font-semibold tracking-wider uppercase">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
            ADMIN CONSOLE - CONFIDENTIAL
          </div>
        </div>

        {/* Tab Switcher */}
        <nav className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200/60">
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === "dashboard" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Dashboard</span>
          </button>
          <button
            onClick={() => setActiveTab("users")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === "users" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Users</span>
          </button>
          <button
            onClick={() => setActiveTab("database")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === "database" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Database</span>
          </button>
          <button
            onClick={() => setActiveTab("operations")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === "operations" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Operations</span>
          </button>
          <button
            onClick={() => setActiveTab("audit")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === "audit" ? "bg-white text-slate-950 shadow-sm" : "text-slate-600 hover:text-slate-900"
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Audit</span>
          </button>
        </nav>

        {/* User Profile & Logout */}
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-600 font-mono hidden md:inline">{adminUser?.email}</span>
          <button
            onClick={handleSignOut}
            title="Terminate session and redirect"
            className="flex items-center gap-1.5 text-xs font-medium text-slate-600 hover:text-rose-600 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:border-rose-200 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      {/* Global Toast Banner */}
      {banner && (
        <div
          className={`mx-6 mt-4 p-3 rounded-xl border text-xs flex items-center justify-between ${
            banner.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-rose-50 border-rose-200 text-rose-800"
          }`}
        >
          <div className="flex items-center gap-2">
            {banner.type === "success" ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
            <span>{banner.message}</span>
          </div>
          <button onClick={() => setBanner(null)} className="text-xs opacity-60 hover:opacity-100">
            Dismiss
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* ------------------------------------------------------------- */}
        {/* TAB 1: DASHBOARD */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "dashboard" && (
          <div className="space-y-6">
            {dashboardLoading && (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Loading latest system metrics...</span>
              </div>
            )}
            {/* Top Stat Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
                <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Active Users (24h)</div>
                <div className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
                  {dashboardData?.metrics?.active_users_24h ?? "-"}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Total: {dashboardData?.metrics?.total_users ?? 0}</div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
                <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Datasets Hosted</div>
                <div className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
                  {dashboardData?.metrics?.total_datasets ?? "-"}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Across all tenants</div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
                <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Total Queries</div>
                <div className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
                  {dashboardData?.metrics?.total_queries ?? "-"}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">Agent executions</div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
                <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Tokens Processed</div>
                <div className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
                  {dashboardData?.metrics?.total_tokens ? Number(dashboardData.metrics.total_tokens).toLocaleString() : "-"}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">All LLM lanes</div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
                <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Estimated Cost</div>
                <div className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
                  ${dashboardData?.metrics?.total_cost_usd?.toFixed(3) ?? "0.000"}
                </div>
                <div className="text-[11px] text-slate-400 mt-1">USD incurred</div>
              </div>
              <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-sm">
                <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Cache Hit Rate</div>
                <div className="text-2xl font-bold tracking-tight text-slate-900 mt-1">
                  {dashboardData?.metrics?.cache_hit_rate ?? 0}%
                </div>
                <div className="text-[11px] text-emerald-600 mt-1 font-medium">Verified answers</div>
              </div>
            </div>

            {/* Provider Health Grid */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-indigo-600" />
                <span>LLM Provider Health & Circuit Breakers</span>
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                {dashboardData?.providers?.providers &&
                  Object.entries(dashboardData.providers.providers).map(([providerKey, info]: [string, any]) => {
                    const isAvailable = info.available;
                    return (
                      <div key={providerKey} className="p-3 rounded-xl border border-slate-200/70 bg-[#FAFAFB]">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-semibold capitalize text-slate-800">{providerKey}</span>
                          <span
                            className={`w-2 h-2 rounded-full ${isAvailable ? "bg-emerald-500" : "bg-rose-500"}`}
                          />
                        </div>
                        <div className="text-[11px] text-slate-500">Latency: {info.latency_ms ?? 0}ms</div>
                        <div className="text-[10px] text-slate-400 mt-1">
                          Circuit: {info.circuit_state || "CLOSED (Normal)"}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>

            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-600 mb-4">
                  Query Volume (Last 30 Days)
                </h3>
                <div className="h-64">
                  <ReactECharts option={dailyQueriesChartOption} style={{ height: "100%", width: "100%" }} />
                </div>
              </div>
              <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-600 mb-4">
                  Token Consumption by Provider
                </h3>
                <div className="h-64">
                  <ReactECharts option={providerTokensChartOption} style={{ height: "100%", width: "100%" }} />
                </div>
              </div>
            </div>

            {/* Recent Logins Table */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-600" />
                <span>Recent Authentication Telemetry (Last 50 Events)</span>
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500">
                      <th className="pb-2 font-medium">Timestamp</th>
                      <th className="pb-2 font-medium">Identity</th>
                      <th className="pb-2 font-medium">Role</th>
                      <th className="pb-2 font-medium">IP Address</th>
                      <th className="pb-2 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {dashboardData?.recent_logins?.map((evt: any) => (
                      <tr key={evt.id} className="hover:bg-slate-50">
                        <td className="py-2.5 text-slate-500 font-mono text-[11px]">
                          {evt.created_at ? new Date(evt.created_at).toLocaleString() : "-"}
                        </td>
                        <td className="py-2.5 font-medium text-slate-900">{evt.email}</td>
                        <td className="py-2.5 text-slate-600 uppercase text-[10px] font-semibold">{evt.role}</td>
                        <td className="py-2.5 text-slate-500 font-mono text-[11px]">{evt.ip_address || "127.0.0.1"}</td>
                        <td className="py-2.5">
                          {evt.success ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Success
                            </span>
                          ) : (
                            <span
                              title={evt.failure_reason}
                              className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200"
                            >
                              Failed
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* TAB 2: USER MANAGEMENT */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "users" && (
          <div className="space-y-4">
            <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3 flex-1 min-w-[280px]">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={usersSearch}
                    onChange={(e) => setUsersSearch(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && fetchUsers()}
                    placeholder="Search users by email..."
                    className="w-full text-xs pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
                <select
                  value={usersRoleFilter}
                  onChange={(e) => setUsersRoleFilter(e.target.value)}
                  className="text-xs px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none"
                >
                  <option value="">All Roles</option>
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
                <button
                  onClick={fetchUsers}
                  className="px-3 py-2 bg-slate-900 text-white rounded-lg text-xs font-medium hover:bg-slate-800 transition-colors"
                >
                  Filter
                </button>
              </div>
              <div className="text-xs text-slate-500">Total Accounts: {usersTotal}</div>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-600 font-medium">
                    <tr>
                      <th className="py-3 px-4">ID</th>
                      <th className="py-3 px-4">Email</th>
                      <th className="py-3 px-4">Role</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Datasets</th>
                      <th className="py-3 px-4">Queries</th>
                      <th className="py-3 px-4">Storage</th>
                      <th className="py-3 px-4">Created</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {usersList.map((u) => (
                      <tr key={u.id} className="hover:bg-slate-50">
                        <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">{u.id}</td>
                        <td className="py-3 px-4 font-medium text-slate-900">{u.email}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                              u.role === "admin" ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {u.role}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${
                              u.is_active
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : "bg-slate-100 text-slate-600 border border-slate-200"
                            }`}
                          >
                            {u.is_active ? "Active" : "Disabled"}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-600">{u.datasets_count}</td>
                        <td className="py-3 px-4 text-slate-600">{u.queries_count}</td>
                        <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                          {(u.storage_bytes / (1024 * 1024)).toFixed(2)} MB
                        </td>
                        <td className="py-3 px-4 text-slate-500 text-[11px]">
                          {u.created_at ? new Date(u.created_at).toLocaleDateString() : "-"}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => handleViewUserDetails(u)}
                              title="Inspect user details"
                              className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleToggleUserStatus(u)}
                              title={u.is_active ? "Disable user" : "Enable user"}
                              className={`p-1.5 rounded hover:bg-slate-100 ${
                                u.is_active ? "text-amber-600" : "text-emerald-600"
                              }`}
                            >
                              {u.is_active ? <UserX className="w-3.5 h-3.5" /> : <UserCheck className="w-3.5 h-3.5" />}
                            </button>
                            <button
                              onClick={() => handleForceLogout(u)}
                              title="Force logout (invalidate JWT)"
                              className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                            >
                              <LogOut className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleDeleteUser(u)}
                              title="Delete user"
                              className="p-1.5 rounded hover:bg-rose-50 text-rose-600"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
              <div className="p-3 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500 bg-slate-50/50">
                <span>
                  {usersLoading ? "Refreshing user records..." : `Page ${usersPage} of ${Math.max(1, Math.ceil(usersTotal / 15))}`}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    disabled={usersPage <= 1 || usersLoading}
                    onClick={() => setUsersPage((p) => Math.max(1, p - 1))}
                    className="px-2.5 py-1 rounded border border-slate-200 hover:bg-white disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <button
                    disabled={usersPage >= Math.ceil(usersTotal / 15) || usersLoading}
                    onClick={() => setUsersPage((p) => p + 1)}
                    className="px-2.5 py-1 rounded border border-slate-200 hover:bg-white disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>

            {/* User Details Modal */}
            {selectedUserDetails && (
              <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-2xl max-w-2xl w-full p-6 border border-slate-200 shadow-xl space-y-4 max-h-[85vh] overflow-y-auto">
                  <div className="flex items-center justify-between border-b pb-3">
                    <h3 className="text-sm font-semibold text-slate-900">
                      User Profile: {selectedUserDetails.user.email}
                    </h3>
                    <button
                      onClick={() => setSelectedUserDetails(null)}
                      className="text-xs text-slate-400 hover:text-slate-700"
                    >
                      Close
                    </button>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Datasets</h4>
                    {selectedUserDetails.datasets?.length === 0 ? (
                      <p className="text-xs text-slate-400">No datasets uploaded.</p>
                    ) : (
                      <div className="divide-y divide-slate-100 border rounded-xl overflow-hidden">
                        {selectedUserDetails.datasets.map((d: any) => (
                          <div key={d.id} className="p-3 text-xs flex justify-between items-center bg-slate-50/50">
                            <span className="font-medium text-slate-800">{d.name}</span>
                            <span className="text-slate-500">
                              {d.row_count} rows • Quality: {d.quality_score}%
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                      Recent Chat Sessions
                    </h4>
                    {selectedUserDetails.recent_sessions?.length === 0 ? (
                      <p className="text-xs text-slate-400">No sessions recorded.</p>
                    ) : (
                      <div className="divide-y divide-slate-100 border rounded-xl overflow-hidden">
                        {selectedUserDetails.recent_sessions.map((s: any) => (
                          <div key={s.id} className="p-3 text-xs flex justify-between items-center">
                            <span className="text-slate-800">{s.title}</span>
                            <span className="text-slate-400 font-mono text-[11px]">
                              {new Date(s.created_at).toLocaleString()}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* TAB 3: DATABASE & SQL CONSOLE */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "database" && (
          <div className="space-y-4">
            {/* Sub-nav */}
            <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
              <button
                onClick={() => setDbSubTab("browser")}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  dbSubTab === "browser" ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                Table Browser
              </button>
              <button
                onClick={() => setDbSubTab("sql")}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  dbSubTab === "sql" ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                SQL Console (Read-Only)
              </button>
              <button
                onClick={() => setDbSubTab("maintenance")}
                className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  dbSubTab === "maintenance" ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                Maintenance & Optimization
              </button>
            </div>

            {/* Sub-Tab: Table Browser */}
            {dbSubTab === "browser" && (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <label className="text-xs font-medium text-slate-700">Select Metadata Table:</label>
                  <select
                    value={selectedTable}
                    onChange={(e) => {
                      setSelectedTable(e.target.value);
                      setTablePage(1);
                    }}
                    className="text-xs px-3 py-1.5 bg-white border border-slate-200 rounded-lg focus:outline-none"
                  >
                    {tablesList.map((t) => (
                      <option key={t.name} value={t.name}>
                        {t.name} ({t.row_count} rows)
                      </option>
                    ))}
                  </select>
                </div>

                {tableData && (
                  <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
                    <div className="overflow-x-auto max-h-[500px]">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 sticky top-0">
                          <tr>
                            {tableData.columns?.map((c: string) => (
                              <th key={c} className="py-2.5 px-3 font-medium whitespace-nowrap">
                                {c}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {tableData.rows?.map((row: any, idx: number) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              {tableData.columns?.map((c: string) => (
                                <td key={c} className="py-2 px-3 text-slate-700 font-mono text-[11px] whitespace-nowrap">
                                  {typeof row[c] === "object" ? JSON.stringify(row[c]) : String(row[c] ?? "")}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Sub-Tab: SQL Console */}
            {dbSubTab === "sql" && (
              <div className="space-y-4">
                <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5 text-indigo-600" />
                      Read-Only SELECT Console (Max 500 rows, 5s timeout)
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setSqlQuery("SELECT id, email, role, created_at FROM users LIMIT 10;")}
                        className="text-[10px] px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-600"
                      >
                        Sample Users
                      </button>
                      <button
                        onClick={() => setSqlQuery("SELECT trace_id, lane, provider, duration_ms, cost_usd FROM execution_traces ORDER BY created_at DESC LIMIT 10;")}
                        className="text-[10px] px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-600"
                      >
                        Sample Traces
                      </button>
                    </div>
                  </div>

                  <textarea
                    value={sqlQuery}
                    onChange={(e) => setSqlQuery(e.target.value)}
                    rows={4}
                    className="w-full font-mono text-xs p-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  />

                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-slate-400">
                      Mutation statements (DROP, DELETE, UPDATE, ALTER) are blocked by sqlglot AST verification.
                    </span>
                    <button
                      onClick={handleRunSql}
                      disabled={queryRunning}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
                    >
                      {queryRunning ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                      <span>Execute Query</span>
                    </button>
                  </div>
                </div>

                {queryResult && (
                  <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-600 font-medium">
                        Returned {queryResult.row_count} rows in {queryResult.duration_ms}ms
                      </span>
                      <button
                        onClick={handleExportCsv}
                        className="flex items-center gap-1.5 text-xs font-medium text-slate-700 hover:text-slate-900 border border-slate-200 px-3 py-1.5 rounded-lg hover:bg-slate-50 transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Export CSV</span>
                      </button>
                    </div>

                    <div className="overflow-x-auto max-h-[400px]">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 sticky top-0">
                          <tr>
                            {queryResult.columns?.map((c: string) => (
                              <th key={c} className="py-2 px-3 font-medium whitespace-nowrap">
                                {c}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {queryResult.rows?.map((row: any, idx: number) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              {queryResult.columns?.map((c: string) => (
                                <td key={c} className="py-2 px-3 font-mono text-[11px] whitespace-nowrap text-slate-700">
                                  {typeof row[c] === "object" ? JSON.stringify(row[c]) : String(row[c] ?? "")}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Sub-Tab: Maintenance */}
            {dbSubTab === "maintenance" && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700">Vacuum & Analyze</h4>
                  <p className="text-xs text-slate-500">
                    Reclaims free pages, reorganizes indexes, and updates database statistics for SQLite and PostgreSQL.
                  </p>
                  <button
                    onClick={() => handleMaintenance("vacuum")}
                    className="w-full py-2 bg-slate-900 text-white rounded-lg text-xs font-medium hover:bg-slate-800 transition-colors"
                  >
                    Run Vacuum & Analyze
                  </button>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700">Purge Old Traces</h4>
                  <p className="text-xs text-slate-500">
                    Clears observability and execution trace logs older than 30 days to optimize table size.
                  </p>
                  <button
                    onClick={() => handleMaintenance("purge_traces")}
                    className="w-full py-2 bg-slate-900 text-white rounded-lg text-xs font-medium hover:bg-slate-800 transition-colors"
                  >
                    Purge Historical Traces
                  </button>
                </div>

                <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-700">Clear Answer Cache</h4>
                  <p className="text-xs text-slate-500">
                    Invalidates and purges all verified-answer cache entries, ensuring questions re-execute.
                  </p>
                  <button
                    onClick={() => handleMaintenance("clear_cache")}
                    className="w-full py-2 bg-rose-600 text-white rounded-lg text-xs font-medium hover:bg-rose-700 transition-colors"
                  >
                    Flush Verified Cache
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* TAB 4: OPERATIONS & CONFIGURATION */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "operations" && (
          <div className="space-y-6">
            {/* Feature Flags */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <Sliders className="w-4 h-4 text-indigo-600" />
                <span>Operational Feature Flags & Guardrails</span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-semibold text-slate-900">Allow Public Registration</div>
                    <div className="text-[11px] text-slate-500">Permit new visitors to create accounts</div>
                  </div>
                  <button
                    onClick={() =>
                      handleUpdateFlag("allow_registration", sysSettings?.allow_registration?.enabled ?? true)
                    }
                    className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors ${
                      sysSettings?.allow_registration?.enabled ?? true ? "bg-indigo-600" : "bg-slate-300"
                    }`}
                  >
                    <div
                      className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                        sysSettings?.allow_registration?.enabled ?? true ? "translate-x-5" : ""
                      }`}
                    />
                  </button>
                </div>

                <div className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-semibold text-slate-900">Smart Provider Fallback</div>
                    <div className="text-[11px] text-slate-500">Enable shared pool fallback on key failure</div>
                  </div>
                  <button
                    onClick={() =>
                      handleUpdateFlag("allow_shared_fallback", sysSettings?.allow_shared_fallback?.enabled ?? true)
                    }
                    className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors ${
                      sysSettings?.allow_shared_fallback?.enabled ?? true ? "bg-indigo-600" : "bg-slate-300"
                    }`}
                  >
                    <div
                      className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                        sysSettings?.allow_shared_fallback?.enabled ?? true ? "translate-x-5" : ""
                      }`}
                    />
                  </button>
                </div>

                <div className="p-4 rounded-xl border border-slate-200/80 bg-slate-50/50 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-semibold text-slate-900">Global Maintenance Mode</div>
                    <div className="text-[11px] text-slate-500">Display polite maintenance banner to users</div>
                  </div>
                  <button
                    onClick={() =>
                      handleUpdateFlag("maintenance_mode", sysSettings?.maintenance_mode?.enabled ?? false)
                    }
                    className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors ${
                      sysSettings?.maintenance_mode?.enabled ? "bg-rose-600" : "bg-slate-300"
                    }`}
                  >
                    <div
                      className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                        sysSettings?.maintenance_mode?.enabled ? "translate-x-5" : ""
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>

            {/* Active Configuration (Names and Set/Unset Status Only - No Secret Exposure) */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-slate-600" />
                <span>Runtime Environment Configuration (Names & Status Only)</span>
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5 text-xs">
                {envStatus.map((item) => (
                  <div key={item.name} className="p-2.5 bg-slate-50/80 rounded-xl border border-slate-200/70 flex items-center justify-between gap-2">
                    <span className="font-mono text-[11px] text-slate-700 truncate" title={item.name}>
                      {item.name}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-semibold tracking-wide uppercase ${
                        item.is_set
                          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                          : "bg-slate-100 text-slate-500 border border-slate-200"
                      }`}
                    >
                      {item.is_set ? "SET" : "NOT SET"}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Contact Submissions Inbox */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <Mail className="w-4 h-4 text-indigo-600" />
                <span>Contact Messages Inbox</span>
              </h3>
              {contactMessages.length === 0 ? (
                <p className="text-xs text-slate-400">No contact messages received.</p>
              ) : (
                <div className="divide-y divide-slate-100 border rounded-xl overflow-hidden text-xs">
                  {contactMessages.map((msg) => (
                    <div key={msg.id} className="p-3 flex items-start justify-between gap-4 hover:bg-slate-50">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 font-medium text-slate-900">
                          <span>{msg.name}</span>
                          <span className="text-slate-400 font-normal">({msg.email})</span>
                          <span className="text-slate-400 font-mono text-[10px]">
                            {new Date(msg.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-slate-600">{msg.message}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <a
                          href={`mailto:${msg.email}?subject=RE: Lumen Inquiry`}
                          className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-medium"
                        >
                          Reply
                        </a>
                        <button
                          onClick={() => handleDeleteContact(msg.id)}
                          className="p-1 rounded text-rose-600 hover:bg-rose-50"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------- */}
        {/* TAB 5: AUDIT LOG */}
        {/* ------------------------------------------------------------- */}
        {activeTab === "audit" && (
          <div className="space-y-4">
            <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Search className="w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={auditActionFilter}
                  onChange={(e) => setAuditActionFilter(e.target.value)}
                  placeholder="Filter audit logs by action (e.g. login, query)..."
                  className="text-xs px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg w-72 focus:outline-none"
                />
              </div>
              <span className="text-xs text-slate-500">Showing recent 50 immutable audit records</span>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-medium">
                    <tr>
                      <th className="py-3 px-4">Timestamp</th>
                      <th className="py-3 px-4">Admin</th>
                      <th className="py-3 px-4">Action</th>
                      <th className="py-3 px-4">Target</th>
                      <th className="py-3 px-4">IP Address</th>
                      <th className="py-3 px-4 text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {auditLogs.map((log) => (
                      <React.Fragment key={log.id}>
                        <tr className="hover:bg-slate-50">
                          <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                            {log.created_at ? new Date(log.created_at).toLocaleString() : "-"}
                          </td>
                          <td className="py-3 px-4 font-medium text-slate-900">{log.admin_email}</td>
                          <td className="py-3 px-4 font-mono text-[11px] text-indigo-700">{log.action}</td>
                          <td className="py-3 px-4 text-slate-600">
                            {log.target_type ? `${log.target_type} #${log.target_id || ""}` : "-"}
                          </td>
                          <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                            {log.ip_address || "127.0.0.1"}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <button
                              onClick={() => setExpandedLogId(expandedLogId === log.id ? null : log.id)}
                              className="text-[11px] text-indigo-600 hover:underline"
                            >
                              {expandedLogId === log.id ? "Collapse" : "Expand JSON"}
                            </button>
                          </td>
                        </tr>
                        {expandedLogId === log.id && (
                          <tr>
                            <td colSpan={6} className="bg-slate-50 p-3">
                              <pre className="font-mono text-[10px] text-slate-700 p-2 bg-white rounded border overflow-x-auto">
                                {JSON.stringify(log.details, null, 2)}
                              </pre>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
