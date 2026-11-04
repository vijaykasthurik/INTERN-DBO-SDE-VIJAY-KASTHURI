import React, { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  Database,
  LayoutDashboard,
  FileText,
  Settings,
  LogOut,
  User as UserIcon,
  ChevronDown,
} from "lucide-react";
import { api } from "../lib/api";
import { Wordmark } from "./Wordmark";
import { cn } from "../lib/utils";
import { useAuthStore } from "../stores/authStore";
import { useAIConnectionStore } from "../stores/aiConnectionStore";

/**
 * Design constant: "capsule" (fully rounded half-circle ends) or "bottom-rounded" (rounded bottom corners).
 */
export const NAV_VARIANT: "capsule" | "bottom-rounded" = "capsule";

export const Navbar: React.FC = () => {
  const location = useLocation();
  const { user, logout, isAuthenticated } = useAuthStore();
  const { connection, fetchConnection, openConnectModal } = useAIConnectionStore();
  const [providerMode,setProviderMode]=useState<string|null>(null);
  useEffect(()=>{if(isAuthenticated)api.admin.providers().then(status=>setProviderMode(status.primary_provider)).catch(()=>setProviderMode(null));},[isAuthenticated]);
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      fetchConnection();
    }
  }, [isAuthenticated, fetchConnection]);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const navItems = [
    { name: "Workspace", href: "/workspace", icon: MessageSquare },
    { name: "Datasets", href: "/datasets", icon: Database },
    { name: "Dashboards", href: "/dashboards", icon: LayoutDashboard },
    { name: "Reports", href: "/reports", icon: FileText },
    { name: "Settings", href: "/settings", icon: Settings },
  ];

  const currentPath = location.pathname;

  // Desktop floating navbar styles depending on NAV_VARIANT
  const shapeStyles =
    NAV_VARIANT === "capsule"
      ? "rounded-pill"
      : "rounded-b-24 rounded-t-none border-t-0";

  return (
    <>
      {/* MOBILE TOP HEADER */}
      <header className="fixed top-0 inset-x-0 z-40 md:hidden bg-white/80 backdrop-blur-md border-b border-hairline py-2.5 px-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <Wordmark />
        </Link>
        {!isAuthenticated && (
          <Link
            to="/auth"
            className="px-3 py-1 text-xs font-medium text-white bg-accent-gradient rounded-pill shadow-soft-xs"
          >
            Sign In
          </Link>
        )}
      </header>

      {/* DESKTOP FLOATING NAVBAR */}
      <header className="fixed top-4 inset-x-0 z-40 hidden md:flex justify-center pointer-events-none px-4">
        <motion.div
          animate={{
            y: 0,
            scale: scrolled ? 0.98 : 1,
            boxShadow: scrolled
              ? "0 8px 32px rgba(15, 23, 42, 0.10)"
              : "0 4px 20px rgba(15, 23, 42, 0.05)",
          }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className={cn(
            "pointer-events-auto relative flex items-center justify-between border border-hairline bg-white/80 backdrop-blur-md transition-all duration-300",
            shapeStyles,
            scrolled ? "py-1.5 px-3" : "py-2 px-4"
          )}
        >
          {/* Rotating gradient border glow accent */}
          <div className="absolute -inset-[1px] rounded-pill bg-accent-gradient opacity-15 blur-[2px] -z-10 animate-border-glow pointer-events-none" />

          {/* BRAND LOGO */}
          <Link
            to="/"
            className="flex items-center gap-2 pr-4 mr-2 border-r border-hairline group"
          >
            <Wordmark />
          </Link>

          {/* NAV LINKS WITH GLIDING ACTIVE INDICATOR */}
          <nav className="flex items-center space-x-1" role="navigation" aria-label="Main Navigation">
            {navItems.map((item) => {
              const isActive =
                item.href === "/"
                  ? currentPath === "/"
                  : currentPath.startsWith(item.href);
              const Icon = item.icon;

              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    "relative px-3.5 py-1.5 text-sm font-medium rounded-pill transition-colors flex items-center gap-2 select-none",
                    isActive ? "text-ink" : "text-ink-muted hover:text-ink hover:bg-surface/60"
                  )}
                >
                  {isActive && (
                    <motion.div
                      layoutId="nav-pill"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.4 }}
                      className="absolute inset-0 bg-surface border border-hairline rounded-pill shadow-soft-xs"
                    />
                  )}
                  <Icon className={cn("w-4 h-4 relative z-10", isActive ? "text-accent-indigo" : "text-ink-muted")} />
                  <span className="relative z-10">{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* AI CONNECTION STATUS CHIP */}
          {isAuthenticated && (
            <button
              type="button"
              onClick={() => openConnectModal()}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-pill bg-surface/70 hover:bg-surface border border-hairline hover:border-hairline-dark transition-all select-none ml-2"
              title={
                connection?.connected
                  ? `Connected: ${connection.provider_id?.toUpperCase()} (${connection.status})`
                  : "Using Shared Demo Pool (Click to connect your own key)"
              }
            >
              <span
                className={cn(
                  "w-2 h-2 rounded-full",
                  connection?.connected
                    ? connection.status === "active"
                      ? "bg-emerald-500 animate-pulse"
                      : connection.status === "quota_exhausted" || connection.status === "rate_limited"
                      ? "bg-amber-500"
                      : "bg-rose-500"
                    : "bg-indigo-500"
                )}
              />
              <span className="text-[11px] text-ink font-medium">
                {connection?.connected
                  ? connection.provider_id?.toUpperCase()
                  : (providerMode === "mock" ? "Offline demo mode" : providerMode ? "Shared AI" : "AI unavailable")}
              </span>
            </button>
          )}

          {/* USER AVATAR MENU / LOGIN */}
          <div className="pl-3 ml-2 border-l border-hairline relative">
            {isAuthenticated ? (
              <div className="relative">
                <button
                  onClick={() => setMenuOpen(!menuOpen)}
                  className="flex items-center gap-2 py-1 px-2 rounded-pill hover:bg-surface border border-transparent hover:border-hairline transition-colors select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-indigo"
                  aria-expanded={menuOpen}
                  aria-label="User profile menu"
                >
                  <div className="w-7 h-7 rounded-pill bg-gradient-to-br from-indigo-100 to-violet-100 border border-hairline flex items-center justify-center text-accent-indigo font-semibold text-xs">
                    {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
                  </div>
                  <span className="text-xs font-medium text-ink max-w-[100px] truncate">
                    {user?.full_name || user?.email || "Account"}
                  </span>
                  <ChevronDown className="w-3.5 h-3.5 text-ink-muted" />
                </button>

                <AnimatePresence>
                  {menuOpen && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95, y: 8 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95, y: 8 }}
                      transition={{ duration: 0.15 }}
                      className="absolute right-0 mt-2 w-56 bg-white border border-hairline rounded-20 shadow-soft-lg p-2 z-50"
                      onClick={() => setMenuOpen(false)}
                    >
                      <div className="px-3 py-2 border-b border-hairline mb-1">
                        <p className="text-xs font-semibold text-ink truncate">
                          {user?.full_name || "Lumen User"}
                        </p>
                        <p className="text-xs text-ink-muted truncate">
                          {user?.email}
                        </p>
                      </div>
                      <Link
                        to="/profile"
                        className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-ink rounded-16 hover:bg-surface transition-colors"
                      >
                        <UserIcon className="w-3.5 h-3.5 text-accent-indigo" />
                        AI Profile & Keys
                      </Link>
                      <Link
                        to="/settings"
                        className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-ink rounded-16 hover:bg-surface transition-colors"
                      >
                        <Settings className="w-3.5 h-3.5 text-ink-muted" />
                        System Settings
                      </Link>
                      <button
                        onClick={logout}
                        className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-rose-600 rounded-16 hover:bg-rose-50 transition-colors"
                      >
                        <LogOut className="w-3.5 h-3.5 text-rose-500" />
                        Sign Out
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <Link
                to="/auth"
                className="px-3.5 py-1.5 text-xs font-medium text-white bg-accent-gradient rounded-pill shadow-soft-xs hover:shadow-nav-glow transition-all active:scale-95 inline-block"
              >
                Sign In
              </Link>
            )}
          </div>
        </motion.div>
      </header>

      {/* MOBILE BOTTOM CAPSULE NAVBAR */}
      <nav
        className="fixed bottom-4 inset-x-4 z-40 md:hidden bg-white/90 backdrop-blur-md border border-hairline rounded-pill shadow-soft-lg py-2 px-3 flex items-center justify-around"
        role="navigation"
        aria-label="Mobile Navigation"
      >
        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? currentPath === "/"
              : currentPath.startsWith(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                "relative p-2 rounded-pill flex flex-col items-center justify-center transition-colors",
                isActive ? "text-accent-indigo" : "text-ink-muted hover:text-ink"
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="mobile-nav-pill"
                  transition={{ type: "spring", bounce: 0.2, duration: 0.3 }}
                  className="absolute inset-0 bg-surface border border-hairline rounded-pill -z-10"
                />
              )}
              <Icon className="w-5 h-5" />
              <span className="text-[10px] font-medium mt-0.5">{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
};
