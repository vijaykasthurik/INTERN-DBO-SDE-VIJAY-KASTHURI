import React, { useState } from "react";
import { NavLink, Link } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Wordmark } from "./Wordmark";
import { useAuthStore } from "../stores/authStore";
import { cn } from "../lib/utils";

export const PublicNavbar: React.FC = () => {
  const authenticated = useAuthStore((s) => s.isAuthenticated);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const links = [
    { to: "/", label: "Home" },
    { to: "/how-it-works", label: "How it works" },
    { to: "/about", label: "About" },
    { to: "/contact", label: "Contact" },
  ];

  return (
    <header className="fixed top-3 sm:top-4 inset-x-0 z-40 flex justify-center px-3 sm:px-4 pointer-events-none">
      <nav
        aria-label="Public navigation"
        className="pointer-events-auto w-full max-w-4xl flex items-center justify-between px-3.5 sm:px-5 py-2 sm:py-2.5 rounded-pill border border-hairline bg-white/90 backdrop-blur-md shadow-soft-sm transition-all"
      >
        {/* Left: Brand Wordmark */}
        <Link
          to="/"
          aria-label="Lumen home"
          className="flex items-center pr-2 sm:pr-3 sm:border-r sm:border-hairline"
        >
          <Wordmark />
        </Link>

        {/* Center: Desktop Navigation Links */}
        <div className="hidden sm:flex items-center gap-1 sm:gap-2">
          {links.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "text-xs font-medium px-3 py-1.5 rounded-pill transition-colors select-none",
                  isActive
                    ? "text-ink font-semibold bg-surface border border-hairline shadow-soft-xs"
                    : "text-ink-muted hover:text-ink hover:bg-surface/60"
                )
              }
            >
              {label}
            </NavLink>
          ))}
        </div>

        {/* Right: Desktop Actions */}
        <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-hairline">
          {authenticated ? (
            <Link
              to="/workspace"
              className="text-xs font-medium px-4 py-1.5 rounded-pill bg-ink text-white hover:bg-ink/90 active:scale-[0.98] transition-all shadow-soft-xs"
            >
              Go to workspace
            </Link>
          ) : (
            <>
              <Link
                to="/auth"
                className="text-xs font-medium px-3 py-1.5 rounded-pill text-ink hover:bg-surface transition-colors"
              >
                Sign in
              </Link>
              <Link
                to="/auth?mode=register"
                className="text-xs font-medium px-4 py-1.5 rounded-pill bg-ink text-white hover:bg-ink/90 active:scale-[0.98] transition-all shadow-soft-xs"
              >
                Get started
              </Link>
            </>
          )}
        </div>

        {/* Mobile: Compact Action + Hamburger Toggle */}
        <div className="flex sm:hidden items-center gap-2">
          {authenticated ? (
            <Link
              to="/workspace"
              className="text-[11px] font-medium px-3 py-1 rounded-pill bg-ink text-white shadow-soft-xs"
            >
              Workspace
            </Link>
          ) : (
            <Link
              to="/auth"
              className="text-[11px] font-medium px-2.5 py-1 rounded-pill bg-ink text-white shadow-soft-xs"
            >
              Sign In
            </Link>
          )}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-1 rounded-pill text-ink hover:bg-surface transition-colors"
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </nav>

      {/* Mobile Animated Dropdown Drawer */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="pointer-events-auto absolute top-14 inset-x-3 bg-white/95 backdrop-blur-md border border-hairline rounded-24 shadow-soft-lg p-3 sm:hidden z-50 flex flex-col gap-1"
          >
            {links.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  cn(
                    "px-4 py-2 text-xs font-medium rounded-16 transition-colors flex items-center justify-between",
                    isActive
                      ? "text-ink font-semibold bg-surface border border-hairline"
                      : "text-ink-muted hover:text-ink hover:bg-surface/50"
                  )
                }
              >
                <span>{label}</span>
              </NavLink>
            ))}

            <div className="pt-2 mt-1 border-t border-hairline flex flex-col gap-2">
              {authenticated ? (
                <Link
                  to="/workspace"
                  onClick={() => setMobileMenuOpen(false)}
                  className="w-full text-center text-xs font-medium py-2 rounded-16 bg-ink text-white shadow-soft-xs"
                >
                  Go to workspace
                </Link>
              ) : (
                <>
                  <Link
                    to="/auth?mode=register"
                    onClick={() => setMobileMenuOpen(false)}
                    className="w-full text-center text-xs font-medium py-2 rounded-16 bg-ink text-white shadow-soft-xs"
                  >
                    Get started free
                  </Link>
                  <Link
                    to="/auth"
                    onClick={() => setMobileMenuOpen(false)}
                    className="w-full text-center text-xs font-medium py-2 rounded-16 text-ink hover:bg-surface border border-hairline"
                  >
                    Sign in to account
                  </Link>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
};
