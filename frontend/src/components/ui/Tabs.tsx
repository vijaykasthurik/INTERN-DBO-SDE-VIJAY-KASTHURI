import React from "react";
import { motion } from "framer-motion";
import { cn } from "../../lib/utils";

export interface TabItem {
  id: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  variant?: "pill" | "line";
  size?: "sm" | "md";
  className?: string;
  layoutId?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  variant = "pill",
  size = "md",
  className,
  layoutId = "active-tab",
}) => {
  const isPill = variant === "pill";

  const sizeStyles = {
    sm: "px-3 py-1.5 text-xs gap-1.5",
    md: "px-4 py-2 text-sm gap-2",
  };

  return (
    <div
      role="tablist"
      className={cn(
        "inline-flex items-center select-none",
        isPill ? "p-1 bg-surface border border-hairline rounded-pill" : "border-b border-hairline w-full space-x-6",
        className
      )}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={cn(
              "relative font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-indigo rounded-pill flex items-center justify-center",
              sizeStyles[size],
              isActive ? "text-ink" : "text-ink-muted hover:text-ink"
            )}
          >
            {isActive && isPill && (
              <motion.div
                layoutId={layoutId}
                transition={{ type: "spring", bounce: 0.15, duration: 0.35 }}
                className="absolute inset-0 bg-white rounded-pill shadow-soft-xs border border-hairline"
              />
            )}
            {isActive && !isPill && (
              <motion.div
                layoutId={layoutId}
                transition={{ type: "spring", bounce: 0.15, duration: 0.35 }}
                className="absolute -bottom-px left-0 right-0 h-0.5 bg-ink"
              />
            )}
            <span className="relative z-10 flex items-center gap-1.5">
              {tab.icon && <span className="w-4 h-4">{tab.icon}</span>}
              {tab.label}
              {tab.badge && <span className="ml-1">{tab.badge}</span>}
            </span>
          </button>
        );
      })}
    </div>
  );
};
