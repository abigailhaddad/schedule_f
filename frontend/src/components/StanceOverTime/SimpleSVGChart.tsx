"use client";

import { useMemo, useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ChartProps, StanceData } from "./types";

interface TooltipData {
  x: number;
  y: number;
  date: string;
  stance: "For" | "Against" | "Neutral/Unclear";
  count: number;
  comments?: Array<{ id: string; title: string; stance: string }>;
}

export default function SimpleSVGChart({ data }: ChartProps) {
  const router = useRouter();
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [tooltipPinned, setTooltipPinned] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 800, height: 320 });
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const newWidth = containerRef.current.getBoundingClientRect().width;
        setDimensions({ width: newWidth, height: newWidth * 0.4 });
      }
    };
    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, []);

  const chartData = useMemo(() => {
    if (!data || data.length === 0) return null;
    const margin = { top: 20, right: 20, bottom: 40, left: 40 };
    const innerWidth = dimensions.width - margin.left - margin.right;
    const innerHeight = dimensions.height - margin.top - margin.bottom;
    const maxValue = Math.max(
      ...data.map((d) => Math.max(d.For, d.Against, d["Neutral/Unclear"]))
    );
    const yScale = (value: number) =>
      innerHeight - (value / (maxValue || 1)) * innerHeight;
    const xScale = (index: number) =>
      data.length === 1
        ? innerWidth / 2
        : (index / (data.length - 1)) * innerWidth;
    return {
      width: dimensions.width,
      height: dimensions.height,
      margin,
      innerWidth,
      innerHeight,
      data,
      xScale,
      yScale,
      maxValue,
    };
  }, [data, dimensions]);

  const handlePointClick = useCallback(
    (commentId: string) => {
      router.push(`/comment/${commentId}`);
    },
    [router]
  );

  const handlePointHover = useCallback(
    (
      e: React.MouseEvent<SVGCircleElement>,
      date: string,
      stance: "For" | "Against" | "Neutral/Unclear",
      count: number,
      dataPoint: StanceData & {
        comments?: {
          [key in "For" | "Against" | "Neutral/Unclear"]?: Array<{
            id: string;
            title: string;
            stance: string;
          }>;
        };
      }
    ) => {
      if (svgRef.current) {
        const rect = svgRef.current.getBoundingClientRect();
        setTooltip({
          x: e.clientX - rect.left,
          y: e.clientY - rect.top,
          date,
          stance,
          count,
          comments: dataPoint.comments ? dataPoint.comments[stance] : [],
        });
      }
    },
    []
  );

  const handleMouseLeave = useCallback(() => {
    if (!tooltipPinned) {
      setTooltip(null);
    }
  }, [tooltipPinned]);

  const handleBackgroundClick = () => {
    setTooltipPinned(false);
    setTooltip(null);
  };

  return (
    <div ref={containerRef} className="w-full" onClick={handleBackgroundClick}>
      {chartData ? (
        <svg
          ref={svgRef}
          width={chartData.width}
          height={chartData.height}
          className="w-full h-auto"
          style={{ maxWidth: "100%" }}
        >
          <g
            transform={`translate(${chartData.margin.left},${chartData.margin.top})`}
          >
            {/* Grid lines */}
            {[0, 0.25, 0.5, 0.75, 1].map((tick) => (
              <g key={tick}>
                <line
                  x1={0}
                  y1={chartData.yScale(tick * chartData.maxValue)}
                  x2={chartData.innerWidth}
                  y2={chartData.yScale(tick * chartData.maxValue)}
                  stroke="#e5e7eb"
                  strokeDasharray="2,2"
                />
                <text
                  x={-10}
                  y={chartData.yScale(tick * chartData.maxValue)}
                  textAnchor="end"
                  alignmentBaseline="middle"
                  fontSize="12"
                  fill="#6b7280"
                >
                  {Math.round(tick * chartData.maxValue)}
                </text>
              </g>
            ))}
            {/* X-axis line */}
            <line
              x1={0}
              y1={chartData.innerHeight}
              x2={chartData.innerWidth}
              y2={chartData.innerHeight}
              stroke="#e5e7eb"
            />
            {/* Y-axis line */}
            <line
              x1={0}
              y1={0}
              x2={0}
              y2={chartData.innerHeight}
              stroke="#e5e7eb"
            />
            {/* X-axis labels */}
            {chartData.data.map((d, i) => (
              <text
                key={i}
                x={chartData.xScale(i)}
                y={chartData.innerHeight + 20}
                textAnchor="middle"
                fontSize="10"
                fill="#6b7280"
                transform={`rotate(-45, ${chartData.xScale(i)}, ${
                  chartData.innerHeight + 20
                })`}
              >
                {new Date(d.date).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                })}
              </text>
            ))}
            {/* Data lines */}
            {(["For", "Against", "Neutral/Unclear"] as const).map((stance) => {
              const pathData = chartData.data
                .map(
                  (d, i) =>
                    `${i === 0 ? "M" : "L"} ${chartData.xScale(
                      i
                    )} ${chartData.yScale(d[stance])}`
                )
                .join(" ");
              return (
                <path
                  key={stance}
                  d={pathData}
                  fill="none"
                  stroke={
                    {
                      For: "#10b981",
                      Against: "#ef4444",
                      "Neutral/Unclear": "#64748b",
                    }[stance]
                  }
                  strokeWidth="2"
                />
              );
            })}
            {/* Interactive data points */}
            {chartData.data.map((d, i) => (
              <g key={i}>
                {(["For", "Against", "Neutral/Unclear"] as const).map(
                  (stance) =>
                    d[stance] > 0 && (
                      <circle
                        key={`${i}-${stance}`}
                        cx={chartData.xScale(i)}
                        cy={chartData.yScale(d[stance])}
                        r="5"
                        fill={
                          {
                            For: "#10b981",
                            Against: "#ef4444",
                            "Neutral/Unclear": "#64748b",
                          }[stance]
                        }
                        stroke="white"
                        strokeWidth="2"
                        style={{ cursor: "pointer" }}
                        onMouseEnter={(e) =>
                          handlePointHover(e, d.date, stance, d[stance], d)
                        }
                        onClick={(e) => {
                          e.stopPropagation();
                          setTooltipPinned(true);
                          handlePointHover(e, d.date, stance, d[stance], d);
                        }}
                        onMouseLeave={handleMouseLeave}
                      />
                    )
                )}
              </g>
            ))}
            {/* Y-axis label */}
            <text
              transform={`rotate(-90)`}
              x={-chartData.innerHeight / 2}
              y={-40}
              textAnchor="middle"
              fontSize="12"
              fill="#6b7280"
            >
              Number of Comments
            </text>
          </g>
          {/* Tooltip */}
          {tooltip && (
            <g transform={`translate(${tooltip.x}, ${tooltip.y})`}>
              <rect
                x={tooltip.x > chartData.width / 2 ? -220 : 10}
                y={-10}
                width="200"
                height={Math.min(
                  150,
                  30 + (tooltip.comments?.length || 0) * 20
                )}
                fill="white"
                stroke="#e5e7eb"
                strokeWidth="1"
                rx="4"
                filter="url(#shadow)"
              />
              <text
                x={tooltip.x > chartData.width / 2 ? -210 : 20}
                y={10}
                fontSize="12"
                fontWeight="bold"
                fill="#111827"
              >
                {new Date(tooltip.date).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </text>
              <text
                x={tooltip.x > chartData.width / 2 ? -210 : 20}
                y={28}
                fontSize="11"
                fill={
                  {
                    For: "#10b981",
                    Against: "#ef4444",
                    "Neutral/Unclear": "#64748b",
                  }[tooltip.stance]
                }
                fontWeight="600"
              >
                {tooltip.stance}: {tooltip.count} comment
                {tooltip.count !== 1 ? "s" : ""}
              </text>
              {tooltip.comments && tooltip.comments.length > 0 && (
                <text
                  x={tooltip.x > chartData.width / 2 ? -210 : 20}
                  y={46}
                  fontSize="10"
                  fill="#6b7280"
                >
                  Click to view details
                </text>
              )}
              {tooltip.comments?.slice(0, 5).map((comment, idx) => (
                <g
                  key={comment.id}
                  style={{ cursor: "pointer" }}
                  onClick={(e) => {
                    e.stopPropagation();
                    handlePointClick(comment.id);
                  }}
                >
                  <rect
                    x={tooltip.x > chartData.width / 2 ? -215 : 15}
                    y={50 + idx * 20}
                    width="190"
                    height="18"
                    fill="transparent"
                    stroke="transparent"
                  />
                  <text
                    x={tooltip.x > chartData.width / 2 ? -210 : 20}
                    y={64 + idx * 20}
                    fontSize="10"
                    fill="#4b5563"
                    style={{ cursor: "pointer" }}
                  >
                    &#8226;{" "}
                    {comment.title.length > 25
                      ? `${comment.title.substring(0, 25)}...`
                      : comment.title}
                  </text>
                </g>
              ))}
              {tooltip.comments && tooltip.comments.length > 5 && (
                <text
                  x={tooltip.x > chartData.width / 2 ? -210 : 20}
                  y={64 + 5 * 20}
                  fontSize="10"
                  fill="#9ca3af"
                  fontStyle="italic"
                >
                  ...and {tooltip.comments.length - 5} more
                </text>
              )}
            </g>
          )}
          {/* Shadow filter for tooltip */}
          <defs>
            <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.1" />
            </filter>
          </defs>
        </svg>
      ) : (
        <div className="text-center text-gray-500 p-8">No data available</div>
      )}
    </div>
  );
}
