import React from "react";
import { NavLink, Link } from "react-router-dom";
import { Wordmark } from "./Wordmark";
import { useAuthStore } from "../stores/authStore";
import { cn } from "../lib/utils";

export const PublicNavbar: React.FC = () => {
  const authenticated = useAuthStore((s) => s.isAuthenticated);

  const links = [
    { to: "/", label: "Home" },
    { to: "/how-it-works", label: "How it works" },
    { to: "/about", label: "About" },
    { to: "/contact", label: "Contact" },
  ];

  return (
    <header className="fixed top-4 inset-x-0 z-40 flex justify-center px-4 pointer-events-none">
      <nav
        aria-label="Public navigation"
        className="pointer-events-auto w-full max-w-4xl flex items-center justify-between px-5 py-2.5 rounded-pill border border-hairline bg-white/85 backdrop-blur-md shadow-soft-sm transition-all"
      >
        {/* Left: Brand Wordmark */}
        <Link to="/" aria-label="Lumen home" className="flex items-center pr-3 border-r border-hairline">
          <Wordmark />
        </Link>

        {/* Center: Cleanly aligned navigation links */}
        <div className="flex items-center gap-1 sm:gap-2">
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

        {/* Right: Actions */}
        <div className="flex items-center gap-2 pl-3 border-l border-hairline">
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
      </nav>
    </header>
  );
};
