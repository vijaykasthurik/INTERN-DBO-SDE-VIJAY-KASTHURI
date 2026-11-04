import React from "react";
import { cn } from "../../lib/utils";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "text" | "circular" | "rectangular";
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = "text",
  width,
  height,
  style,
  ...props
}) => {
  const variantStyles = {
    text: "h-4 w-full rounded-md",
    circular: "rounded-full",
    rectangular: "rounded-16",
  };

  return (
    <div
      className={cn(
        "relative overflow-hidden bg-slate-100",
        "before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_2s_infinite_linear] before:bg-gradient-to-r before:from-transparent before:via-white/60 before:to-transparent",
        variantStyles[variant],
        className
      )}
      style={{
        width,
        height,
        ...style,
      }}
      {...props}
    />
  );
};
