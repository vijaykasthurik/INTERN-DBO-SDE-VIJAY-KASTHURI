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
  const [providerMode, setProviderMode] = useState<string | null>(null);
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      api.admin.providers()
        .then((status) => setProviderMode(status.primary_provider))
        .catch(() => setProviderMode(null));
      fetchConnection();
    }
  }, [isAuthenticated, fetchConnection]);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 15);
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

  const shapeStyles =
    NAV_VARIANT === "capsule"
      ? "rounded-pill"
      : "rounded-b-24 rounded-t-none border-t-0";

  return (
    <>
      {/* MOBILE TOP HEADER */}
      <header className="fixed top-0 inset-x-0 z-40 md:hidden bg-white/90 backdrop-blur-md border-b border-hairline py-2 px-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <Wordmark />
        </Link>
        {!isAuthenticated && (
          <Link
            to="/auth"
            className="px-3.5 py-1 text-xs font-medium text-white bg-ink rounded-pill shadow-soft-xs hover:bg-ink/90 active:scale-95"
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
              ? "0 8px 30px rgba(15, 23, 42, 0.08)"
              : "0 4px 20px rgba(15, 23, 42, 0.04)",
          }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className={cn(
            "pointer-events-auto relative flex items-center justify-between gap-2 border border-hairline bg-white/90 backdrop-blur-md transition-all duration-300",
            shapeStyles,
            scrolled ? "py-1.5 px-3.5" : "py-2 px-4.5"
          )}
        >
          {/* BRAND LOGO */}
          <Link
            to="/"
            className="flex items-center gap-2 pr-3.5 mr-1 border-r border-hairline group"
          >
            <Wordmark />
          </Link>

          {/* NAV LINKS WITH NEAT ALIGNMENT & GLIDING INDICATOR */}
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
                    "relative px-3 py-1.5 text-xs font-medium tracking-tight rounded-pill transition-colors flex items-center gap-1.5 select-none justify-center",
                    isActive ? "text-ink font-semibold" : "text-ink-muted hover:text-ink hover:bg-surface/70"
                  )}
                >
                  {isActive && (
                    <motion.div
                      layoutId="nav-pill"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.35 }}
                      className="absolute inset-0 bg-surface border border-hairline rounded-pill shadow-soft-xs"
                    />
                  )}
                  <Icon className={cn("w-3.5 h-3.5 relative z-10", isActive ? "text-ink" : "text-ink-muted")} />
                  <span className="relative z-10 leading-none">{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* MODEL STATUS CHIP */}
          {isAuthenticated && (
            <button
              type="button"
              onClick={() => openConnectModal()}
              className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-pill bg-surface/80 hover:bg-surface border border-hairline hover:border-hairline-dark transition-all select-none ml-1"
              title={
                connection?.connected
                  ? `Connected: ${connection.provider_id?.toUpperCase()} (${connection.status})`
                  : "Using Shared Model Pool (Click to connect your own key)"
              }
            >
              <span
                className={cn(
                  "w-1.5 h-1.5 rounded-full",
                  connection?.connected
                    ? connection.status === "active"
                      ? "bg-emerald-600 animate-pulse"
                      : connection.status === "quota_exhausted" || connection.status === "rate_limited"
                      ? "bg-amber-500"
                      : "bg-rose-500"
                    : "bg-emerald-600"
                )}
              />
              <span className="text-[11px] text-ink font-medium leading-none">
                {connection?.connected
                  ? connection.provider_id?.toUpperCase()
                  : providerMode === "mock"
                  ? "Offline demo"
                  : providerMode
                  ? "Shared models"
                  : "Model unavailable"}
              </span>
            </button>
          )}

          {/* USER AVATAR MENU / LOGIN */}
          <div className="pl-2.5 ml-1 border-l border-hairline relative">
            {isAuthenticated ? (
              <div className="relative">
                <button
                  onClick={() => setMenuOpen(!menuOpen)}
                  className="flex items-center gap-1.5 py-1 px-2 rounded-pill hover:bg-surface border border-transparent hover:border-hairline transition-colors select-none focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ink"
                  aria-expanded={menuOpen}
                  aria-label="User profile menu"
                >
                  <div className="w-6 h-6 rounded-pill bg-ink text-white font-mono font-medium text-[11px] flex items-center justify-center">
                    {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "U"}
                  </div>
                  <span className="text-xs font-medium text-ink max-w-[90px] truncate leading-none">
                    {user?.full_name || user?.email || "Account"}
                  </span>
                  <ChevronDown className="w-3.5 h-3.5 text-ink-muted" />
                </button>

                <AnimatePresence>
                  {menuOpen && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.96, y: 6 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.96, y: 6 }}
                      transition={{ duration: 0.15 }}
                      className="absolute right-0 mt-2 w-52 bg-white border border-hairline rounded-20 shadow-soft-lg p-1.5 z-50"
                      onClick={() => setMenuOpen(false)}
                    >
                      <div className="px-3 py-2 border-b border-hairline mb-1">
                        <p className="text-xs font-semibold text-ink truncate">
                          {user?.full_name || "Lumen User"}
                        </p>
                        <p className="text-[11px] text-ink-muted truncate">
                          {user?.email}
                        </p>
                      </div>
                      <Link
                        to="/profile"
                        className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-ink rounded-16 hover:bg-surface transition-colors"
                      >
                        <UserIcon className="w-3.5 h-3.5 text-ink-muted" />
                        Model Settings & Keys
                      </Link>
                      <Link
                        to="/settings"
                        className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-ink rounded-16 hover:bg-surface transition-colors"
                      >
                        <Settings className="w-3.5 h-3.5 text-ink-muted" />
                        System Settings
                      </Link>
                      <button
                        onClick={logout}
                        className="w-full flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-rose-600 rounded-16 hover:bg-rose-50 transition-colors"
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
                className="px-4 py-1.5 text-xs font-medium text-white bg-ink rounded-pill shadow-soft-xs hover:bg-ink/90 active:scale-95 transition-all inline-block"
              >
                Sign In
              </Link>
            )}
          </div>
        </motion.div>
      </header>

      {/* MOBILE BOTTOM CAPSULE NAVBAR */}
      <nav
        className="fixed bottom-3 inset-x-4 z-40 md:hidden bg-white/95 backdrop-blur-md border border-hairline rounded-pill shadow-soft-lg py-2 px-3 flex items-center justify-around"
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
                "relative p-1.5 rounded-pill flex flex-col items-center justify-center transition-colors",
                isActive ? "text-ink font-semibold" : "text-ink-muted hover:text-ink"
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="mobile-nav-pill"
                  transition={{ type: "spring", bounce: 0.2, duration: 0.3 }}
                  className="absolute inset-0 bg-surface border border-hairline rounded-pill -z-10"
                />
              )}
              <Icon className="w-4.5 h-4.5" />
              <span className="text-[10px] font-medium mt-0.5">{item.name}</span>
            </Link>
          );
        })}
      </nav>
    </>
  );
};
