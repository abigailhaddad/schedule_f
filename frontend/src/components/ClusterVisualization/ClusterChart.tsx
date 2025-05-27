"use client";

import {
  ResponsiveScatterPlotCanvas,
  ScatterPlotNodeData,
} from "@nivo/scatterplot";
import { BasicTooltip } from "@nivo/tooltip";
import { ClusterPoint } from "@/lib/actions/clusters";

type ClusterDatum = ClusterPoint & { x: number; y: number };
// Define a type for the node object passed by Nivo, acknowledging runtime shape
interface NivoNodeWithData {
  serieId: string | number; // Nivo generally uses string | number for IDs
  data: { x: number; y: number; stance?: string | null } & Omit<
    ClusterPoint,
    "x" | "y" | "stance"
  >;
}

interface ClusterChartProps {
  data: Array<{
    id: string;
    data: Array<
      {
        x: number;
        y: number;
      } & ClusterPoint
    >;
  }>;
  bounds: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
  };
  showStanceColors: boolean;
  onPointClick: (point: ClusterPoint) => void;
  onPointHover: (point: ClusterPoint | null) => void;
}

export default function ClusterChart({
  data,
  bounds,
  showStanceColors,
  onPointClick,
  onPointHover,
}: ClusterChartProps) {
  // Color scheme for clusters
  const clusterColors = [
    "#e11d48",
    "#db2777",
    "#c026d3",
    "#9333ea",
    "#7c3aed",
    "#6366f1",
    "#3b82f6",
    "#0ea5e9",
    "#06b6d4",
    "#14b8a6",
    "#10b981",
    "#22c55e",
    "#84cc16",
    "#eab308",
    "#f59e0b",
    "#f97316",
    "#ef4444",
    "#dc2626",
    "#b91c1c",
    "#991b1b",
  ];

  // Color scheme for stances
  const stanceColors = {
    For: "#10b981",
    Against: "#ef4444",
    "Neutral/Unclear": "#64748b",
  };

  const getNodeColor = (param: any) => {
    // Assert that the param, despite its narrow Nivo typing for this callback,
    // actually contains the full data we need at runtime for points.
    const node = param as NivoNodeWithData;

    // Check if node.data exists, as Nivo might call this for non-point elements (e.g., legend)
    if (showStanceColors && node.data && node.data.stance) {
      return (
        stanceColors[node.data.stance as keyof typeof stanceColors] || "#64748b"
      );
    }
    // Ensure serieId is treated as a string for .replace()
    const clusterIndex =
      parseInt(String(node.serieId).replace("Cluster ", "")) %
      clusterColors.length;
    return clusterColors[clusterIndex];
  };

  return (
    <div style={{ height: 600 }} className="bg-white rounded-lg">
      <ResponsiveScatterPlotCanvas
        data={data}
        margin={{ top: 20, right: 20, bottom: 60, left: 60 }}
        xScale={{
          type: "linear",
          min: bounds.minX * 1.1,
          max: bounds.maxX * 1.1,
        }}
        yScale={{
          type: "linear",
          min: bounds.minY * 1.1,
          max: bounds.maxY * 1.1,
        }}
        // blendMode="multiply"
        axisTop={null}
        axisRight={null}
        axisBottom={{
          tickSize: 5,
          tickPadding: 5,
          tickRotation: 0,
          legend: "PCA Component 1",
          legendPosition: "middle",
          legendOffset: 46,
        }}
        axisLeft={{
          tickSize: 5,
          tickPadding: 5,
          tickRotation: 0,
          legend: "PCA Component 2",
          legendPosition: "middle",
          legendOffset: -60,
        }}
        nodeSize={6}
        colors={getNodeColor}
        onClick={(node) => {
          if (node.data) {
            onPointClick(node.data as ClusterPoint);
          }
        }}
        onMouseEnter={(node) => {
          if (node.data) {
            onPointHover(node.data as ClusterPoint);
          }
        }}
        onMouseLeave={() => onPointHover(null)}
        tooltip={({
          node, // <- { x, y, data, serieId, color/style, … }
        }: {
          node: ScatterPlotNodeData<ClusterDatum>;
        }) => (
          <BasicTooltip
            enableChip
            /* chip color */ color={
              "style" in node ? (node as any).style.color : node.color
            }
            /* everything else lives in `id` */
            id={
              <div className="space-y-1 max-w-[240px]">
                <p className="font-semibold">{node.data.title}</p>
                <p className="text-xs text-gray-500">
                  Cluster {node.data.clusterId} •&nbsp;
                  {node.data.stance ?? "No stance"}
                </p>

                {node.data.keyQuote && (
                  <p className="italic text-xs">
                    “{node.data.keyQuote.slice(0, 80)}
                    {node.data.keyQuote.length > 80 && "…"}”
                  </p>
                )}
              </div>
            }
          />
        )}
        legends={[
          {
            anchor: "top-right",
            direction: "column",
            justify: false,
            translateX: -20,
            translateY: 20,
            itemsSpacing: 5,
            itemDirection: "left-to-right",
            itemWidth: 80,
            itemHeight: 20,
            itemOpacity: 0.75,
            symbolSize: 12,
            symbolShape: "circle",
            effects: [
              {
                on: "hover",
                style: {
                  itemOpacity: 1,
                },
              },
            ],
          },
        ]}
      />
    </div>
  );
}
