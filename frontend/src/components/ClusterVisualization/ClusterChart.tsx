"use client";

import { useRef, useState, useCallback, useEffect } from 'react';
import {
  ResponsiveScatterPlotCanvas
} from "@nivo/scatterplot";
import { ClusterPoint } from "@/lib/actions/clusters";
import { useRouter, useSearchParams } from 'next/navigation';
import d3 from 'd3';
import ClusterTooltipOverlay from './ClusterTooltipOverlay';

interface ClusterChartProps {
  data: Array<{
    id: string;
    data: Array<{
      x: number;
      y: number;
    } & ClusterPoint>;
  }>;
  bounds: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
  };
}

export default function ClusterChart({
  data,
  bounds,
}: ClusterChartProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const chartRef = useRef<HTMLDivElement>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [hoveredPoint, setHoveredPoint] = useState<ClusterPoint | null>(null);
  const [clickedPoint, setClickedPoint] = useState<ClusterPoint | null>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Check for pinned comment ID in URL on mount
  useEffect(() => {
    const pinnedId = searchParams.get('pinned');
    if (pinnedId) {
      // Find the point with this ID in the data
      for (const series of data) {
        const point = series.data.find(p => p.id === pinnedId);
        if (point) {
          setClickedPoint(point);
          // Set initial position to center of chart (will be adjusted by mouse move)
          setTooltipPosition({ x: 300, y: 300 });
          break;
        }
      }
    }
  }, [searchParams, data]);

  // Color schemes
  const clusterColors = [
    "#e11d48", "#db2777", "#c026d3", "#9333ea", "#7c3aed",
    "#6366f1", "#3b82f6", "#0ea5e9", "#06b6d4", "#14b8a6",
    "#10b981", "#22c55e", "#84cc16", "#eab308", "#f59e0b",
    "#f97316", "#ef4444", "#dc2626", "#b91c1c", "#991b1b",
  ];

  // const stanceColors = { // This was commented out by user, ensuring it's fully gone or remains commented
  //   For: "#10b981",
  //   Against: "#ef4444",
  //   "Neutral/Unclear": "#64748b",
  // };

  // Define a more specific type for the Nivo node object for colors
  type NivoColorNode = { serieId: string | number; data?: { stance?: string | null } };

  const getNodeColor = (param: NivoColorNode) => {
    // When showStanceColors is true, color by stance -- THIS LOGIC IS CURRENTLY NOT ACTIVE
    // if (showStanceColors) { // showStanceColors is not a prop anymore
    //   if (param.data) {
    //     const stance = param.data.stance || "Neutral/Unclear";
    //     return stanceColors[stance as keyof typeof stanceColors] || stanceColors["Neutral/Unclear"];
    //   }
    //   if (typeof param.serieId === 'string' && param.serieId in stanceColors) {
    //     return stanceColors[param.serieId as keyof typeof stanceColors];
    //   }
    // }
    
    // Default: color by cluster
    const clusterIndex = parseInt(String(param.serieId).replace("Cluster ", "")) % clusterColors.length;
    return clusterColors[clusterIndex];
  };

  const handleMouseMove = useCallback((event: React.MouseEvent) => {
    if (chartRef.current && hoveredPoint && !clickedPoint) {
      const rect = chartRef.current.getBoundingClientRect();
      setTooltipPosition({
        x: event.clientX - rect.left,
        y: event.clientY - rect.top
      });
    }
  }, [hoveredPoint, clickedPoint]);

  const handlePointHover = useCallback((point: ClusterPoint | null) => {
    // Don't update hover if we have a clicked point
    if (clickedPoint) return;
    
    // Clear any existing timeout
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }

    if (point) {
      setHoveredPoint(point);
    } else {
      // Add a delay before hiding tooltip to allow clicking
      hoverTimeoutRef.current = setTimeout(() => {
        setHoveredPoint(null);
      }, 100); // Reduced delay for better responsiveness
    }
  }, [clickedPoint]);

  const handlePointClick = useCallback((point: ClusterPoint) => {
    // If clicking the same point, toggle it off
    if (clickedPoint?.id === point.id) {
      setClickedPoint(null);
      setHoveredPoint(null);
    } else {
      setClickedPoint(point);
      setHoveredPoint(null);
    }
  }, [clickedPoint]);

  // Clear clicked point when clicking outside
  const handleChartClick = useCallback((event: React.MouseEvent) => {
    if (event.target === event.currentTarget) {
      setClickedPoint(null);
    }
  }, []);

  return (
    <div 
      ref={chartRef}
      style={{ height: 600, position: 'relative' }} 
      className="bg-white rounded-lg"
      onMouseMove={handleMouseMove}
      onMouseLeave={() => !clickedPoint && handlePointHover(null)}
      onClick={handleChartClick}
    >
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
        nodeSize={8}
        colors={getNodeColor}
        onClick={(node) => {
          if (node.data) {
            handlePointClick(node.data as ClusterPoint);
          }
        }}
        onMouseEnter={(node) => {
          if (node.data && !clickedPoint) {
            handlePointHover(node.data as ClusterPoint);
          }
        }}
        onMouseLeave={() => !clickedPoint && handlePointHover(null)}
        enableGridX={false}
        enableGridY={false}
        // Disable Nivo's built-in tooltip
        tooltip={() => null}
        // Show cluster legends
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
            data: data.map((series) => ({
              id: series.id,
              label: series.id,
              color: clusterColors[parseInt(series.id.replace('Cluster ', '')) % clusterColors.length]
            }))
          },
        ]}
      />
      
      {/* Show tooltip for either hovered or clicked point */}
      {(hoveredPoint || clickedPoint) && (
        <ClusterTooltipOverlay
          point={clickedPoint || hoveredPoint!}
          position={tooltipPosition}
          isFixed={!!clickedPoint}
          onClose={() => {
            setClickedPoint(null);
            setHoveredPoint(null);
          }}
          onNavigate={(id: string) => {
            const currentPath = window.location.pathname; // Base path e.g. /clusters
            const currentSearchParams = new URLSearchParams(window.location.search);
            
            // Remove existing 'pinned' param if any, then add new one
            currentSearchParams.delete('pinned');
            currentSearchParams.set('pinned', id);
            
            const returnUrl = encodeURIComponent(`${currentPath}?${currentSearchParams.toString()}`);
            router.push(`/comment/${id}?returnUrl=${returnUrl}`);
          }}
        />
      )}
      
      {/* Instructions */}
      <div className="absolute bottom-2 left-2 text-xs text-gray-500">
        Hover to preview • Click to freeze tooltip • {data.length} clusters shown
      </div>
    </div>
  );
}