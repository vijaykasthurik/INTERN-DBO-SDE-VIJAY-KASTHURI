import React, { useRef } from "react";
import ReactECharts from "echarts-for-react";
import type { ECharts } from "echarts";
import { Download, BarChart2 } from "lucide-react";
import { Button } from "../../components/ui/Button";

export interface ChartRendererProps {
  spec?: Record<string, unknown>;
  title?: string;
  className?: string;
}

export const ChartRenderer: React.FC<ChartRendererProps> = ({
  spec,
  title,
  className,
}) => {
  const chartRef = useRef<ReactECharts>(null);

  if (!spec || Object.keys(spec).length === 0) {
    return null;
  }

  const handleDownload = () => {
    if (chartRef.current) {
      const echartsInstance = chartRef.current.getEchartsInstance() as ECharts;
      const dataUrl = echartsInstance.getDataURL({
        type: "png",
        pixelRatio: 2,
        backgroundColor: "#ffffff",
      });
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = `${(title || "chart").toLowerCase().replace(/\s+/g, "_")}.png`;
      a.click();
    }
  };

  // Base theme options for crisp editorial styling
  const defaultOption = {
    color: ["#6366F1", "#8B5CF6", "#22D3EE", "#10B981", "#F59E0B", "#EF4444"],
    backgroundColor: "transparent",
    textStyle: {
      fontFamily: "'Inter Variable', sans-serif",
      color: "#0B0B0F",
    },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: "rgba(15, 23, 42, 0.08)",
      borderWidth: 1,
      textStyle: {
        color: "#0B0B0F",
        fontSize: 12,
      },
      extraCssText: "box-shadow: 0 4px 20px rgba(15, 23, 42, 0.08); border-radius: 12px; font-variant-numeric: tabular-nums;",
    },
    grid: {
      top: 40,
      right: 20,
      bottom: 40,
      left: 50,
      containLabel: true,
    },
    animationDuration: 800,
    animationEasing: "cubicOut",
    ...spec,
  };

  return (
    <div className={`p-4 bg-white rounded-20 border border-hairline shadow-soft-xs ${className || ""}`}>
      <div className="flex items-center justify-between pb-3 border-b border-hairline mb-2">
        <div className="flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-accent-indigo" />
          <h4 className="text-xs font-semibold text-ink uppercase tracking-wider">
            {title || "Interactive Visualization"}
          </h4>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDownload}
          className="text-xs text-ink-muted hover:text-ink h-7 px-2"
        >
          <Download className="w-3.5 h-3.5 mr-1" />
          Export PNG
        </Button>
      </div>

      <div className="w-full h-72">
        <ReactECharts
          ref={chartRef}
          option={defaultOption}
          style={{ height: "100%", width: "100%" }}
          opts={{ renderer: "svg" }}
        />
      </div>
    </div>
  );
};
