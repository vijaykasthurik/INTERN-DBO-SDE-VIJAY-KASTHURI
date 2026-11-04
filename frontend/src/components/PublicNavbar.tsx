import { NavLink } from "react-router-dom";
import { Wordmark } from "./Wordmark";
import { useAuthStore } from "../stores/authStore";
export const PublicNavbar = () => {
  const authenticated = useAuthStore((s) => s.isAuthenticated);
  return <header className="relative z-40 px-4 pt-4"><nav aria-label="Public navigation" className="mx-auto max-w-5xl flex flex-wrap items-center justify-center gap-x-5 gap-y-2 px-5 py-3 rounded-pill border border-hairline bg-white/90 backdrop-blur-md shadow-soft-sm">
    <NavLink to="/" aria-label="Lumen home"><Wordmark /></NavLink>
    {[["/", "Home"], ["/how-it-works", "How it works"], ["/about", "About"], ["/contact", "Contact"]].map(([to, label]) => <NavLink key={to} to={to} end={to === "/"} className={({isActive}) => `text-xs min-h-11 inline-flex items-center ${isActive ? "text-accent-indigo font-semibold" : "text-ink-muted"}`}>{label}</NavLink>)}
    {authenticated ? <NavLink to="/workspace" className="text-xs px-4 py-3 rounded-pill bg-ink text-white">Go to workspace</NavLink> : <><NavLink to="/auth" className="text-xs min-h-11 inline-flex items-center">Sign in</NavLink><NavLink to="/auth?mode=register" className="text-xs px-4 py-3 rounded-pill bg-accent-gradient text-white">Get started</NavLink></>}
  </nav></header>;
};
