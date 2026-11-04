import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  MessageSquare,
  Database,
  LayoutDashboard,
  FileText,
  Settings,
  Compass,
  Command,
} from "lucide-react";

export const CommandPalette: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key?.toLowerCase() === "k" || e.code === "KeyK")) {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    };
    const handleCustomOpen = () => setIsOpen(true);

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("lumen:open-command-palette", handleCustomOpen);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("lumen:open-command-palette", handleCustomOpen);
    };
  }, [isOpen]);

  const navItems = [
    { title: "Workspace", path: "/workspace", icon: MessageSquare, category: "Navigation" },
    { title: "Datasets", path: "/datasets", icon: Database, category: "Navigation" },
    { title: "Dashboards", path: "/dashboards", icon: LayoutDashboard, category: "Navigation" },
    { title: "Reports", path: "/reports", icon: FileText, category: "Navigation" },
    { title: "Settings & Diagnostics", path: "/settings", icon: Settings, category: "Navigation" },
  ];

  const quickPrompts = [
    "Which region generated the highest revenue?",
    "Show monthly sales trends.",
    "Which products are underperforming?",
    "What are the top five customers?",
    "Detect anomalies in the dataset.",
    "Generate SQL for this analysis.",
  ];

  const filteredNav = navItems.filter((i) =>
    i.title.toLowerCase().includes(query.toLowerCase())
  );

  const filteredPrompts = quickPrompts.filter((p) =>
    p.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelect = (path: string) => {
    setIsOpen(false);
    navigate(path);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-ink/20 backdrop-blur-sm"
            onClick={() => setIsOpen(false)}
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -10 }}
            transition={{ type: "spring", duration: 0.25, bounce: 0.1 }}
            className="w-full max-w-lg bg-white rounded-24 border border-hairline shadow-soft-lg overflow-hidden z-10 p-2"
          >
            {/* SEARCH INPUT */}
            <div className="flex items-center px-3 border-b border-hairline pb-2 pt-1 gap-2.5">
              <Search className="w-4 h-4 text-ink-muted" />
              <input
                autoFocus
                type="text"
                placeholder="Search commands, navigate, or ask a question..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full text-sm outline-none text-ink placeholder:text-ink-muted bg-transparent"
              />
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface border border-hairline text-ink-muted">
                ESC
              </span>
            </div>

            {/* RESULTS LIST */}
            <div className="py-2 max-h-80 overflow-y-auto space-y-3">
              {filteredNav.length > 0 && (
                <div>
                  <p className="px-3 py-1 text-[10px] font-semibold text-ink-muted uppercase tracking-wider">
                    Pages
                  </p>
                  {filteredNav.map((item) => {
                    const Icon = item.icon;
                    return (
                      <button
                        key={item.path}
                        onClick={() => handleSelect(item.path)}
                        className="w-full px-3 py-2 text-left text-xs text-ink hover:bg-surface rounded-16 flex items-center justify-between transition-colors group"
                      >
                        <div className="flex items-center gap-2.5">
                          <Icon className="w-4 h-4 text-ink-muted group-hover:text-accent-indigo" />
                          <span>{item.title}</span>
                        </div>
                        <span className="text-[10px] text-ink-muted font-mono">Go to page</span>
                      </button>
                    );
                  })}
                </div>
              )}

              {filteredPrompts.length > 0 && (
                <div>
                  <p className="px-3 py-1 text-[10px] font-semibold text-ink-muted uppercase tracking-wider">
                    Quick Analytical Inquiries
                  </p>
                  {filteredPrompts.map((prompt) => (
                    <button
                      key={prompt}
                      onClick={() => handleSelect(`/workspace`)}
                      className="w-full px-3 py-2 text-left text-xs text-ink hover:bg-surface rounded-16 flex items-center gap-2.5 transition-colors group"
                    >
                      <Compass className="w-3.5 h-3.5 text-emerald-700" />
                      <span className="truncate">{prompt}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* FOOTER */}
            <div className="px-3 py-2 border-t border-hairline flex items-center justify-between text-[11px] text-ink-muted">
              <span>Lumen Command Palette</span>
              <span className="flex items-center gap-1 font-mono">
                <Command className="w-3 h-3" /> + K to toggle
              </span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
