import React from "react";
import { cn } from "../../lib/utils";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className,
}) => {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center rounded-24 border border-dashed border-hairline bg-surface/50 max-w-lg mx-auto select-none",
        className
      )}
    >
      {icon && (
        <div className="w-12 h-12 rounded-20 bg-white border border-hairline shadow-soft-xs flex items-center justify-center text-ink-muted mb-4">
          {icon}
        </div>
      )}
      <h3 className="text-base font-semibold text-ink tracking-tight">{title}</h3>
      {description && (
        <p className="text-sm text-ink-muted mt-1.5 max-w-sm leading-relaxed">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
};
