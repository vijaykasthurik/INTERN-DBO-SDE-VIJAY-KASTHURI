import React from "react";
import { motion } from "framer-motion";
import { cn } from "../../lib/utils";

export interface ProgressRingProps {
  score?: number; // 0 to 100
  value?: number;
  size?: number;
  strokeWidth?: number;
  className?: string;
  label?: string;
}

export const ProgressRing: React.FC<ProgressRingProps> = ({
  score,
  value,
  size = 120,
  strokeWidth = 10,
  className,
  label = "Health Score",
}) => {
  const currentVal = score ?? value ?? 0;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(100, Math.max(0, currentVal));
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  // Color thresholding
  const getColor = () => {
    if (progress >= 80) return "#10B981"; // Emerald
    if (progress >= 60) return "#F59E0B"; // Amber
    return "#EF4444"; // Rose
  };

  return (
    <div className={cn("relative inline-flex flex-col items-center justify-center", className)}>
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(15, 23, 42, 0.06)"
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        {/* Animated Progress Ring */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={getColor()}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          strokeLinecap="round"
          fill="transparent"
        />
      </svg>
      {/* Centered Metric Number */}
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-2xl font-bold tracking-tight text-ink tabular-nums">
          {Math.round(progress)}
        </span>
        {label && <span className="text-[10px] font-medium text-ink-muted -mt-0.5">{label}</span>}
      </div>
    </div>
  );
};
