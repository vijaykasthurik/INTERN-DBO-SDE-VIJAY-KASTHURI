import React from "react";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";

export interface TagProps {
  label: React.ReactNode;
  icon?: React.ReactNode;
  onRemove?: () => void;
  selected?: boolean;
  onClick?: () => void;
  className?: string;
  size?: "sm" | "md";
}

export const Tag: React.FC<TagProps> = ({
  label,
  icon,
  onRemove,
  selected = false,
  onClick,
  className,
  size = "md",
}) => {
  const isInteractive = !!onClick;

  const sizeStyles = {
    sm: "h-6 px-2.5 text-xs gap-1",
    md: "h-8 px-3 text-xs gap-1.5",
  };

  return (
    <span
      role={isInteractive ? "button" : undefined}
      tabIndex={isInteractive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={(e) => {
        if (isInteractive && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          onClick();
        }
      }}
      className={cn(
        "inline-flex items-center justify-center font-medium rounded-pill transition-all select-none border",
        isInteractive && "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-indigo",
        selected
          ? "bg-ink text-white border-ink shadow-soft-xs"
          : "bg-surface text-ink-muted border-hairline hover:text-ink hover:border-slate-300",
        sizeStyles[size],
        className
      )}
    >
      {icon && <span className="w-3.5 h-3.5">{icon}</span>}
      <span>{label}</span>
      {onRemove && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="ml-1 -mr-1 p-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/20 transition-colors"
          aria-label="Remove tag"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </span>
  );
};
