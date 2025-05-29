"use client";

import { useRef, useState, useCallback, useEffect, useMemo } from 'react';
import {
  ResponsiveScatterPlotCanvas
} from "@nivo/scatterplot";
import { ClusterPoint } from "@/lib/actions/clusters";
import { useRouter, useSearchParams } from 'next/navigation';
// import d3 from 'd3'; // d3 import seems unused
import ClusterTooltipOverlay from './ClusterTooltipOverlay';

interface ClusterChartProps {
  data: Array<{
    id: string; // This is the clusterId string
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

  // Create a stable color mapping for cluster IDs
  const clusterIdToColorIndex = useMemo(() => {
    const mapping = new Map<string, number>();
    const parentMapping = new Map<string, number>();
    let nextParentIndex = 0;
    
    // First, identify parent clusters and assign base colors
    (data || []).forEach(series => {
      if (series && series.id && typeof series.id === 'string' && series.id.length > 0) {
        // Extract parent cluster (everything except last character)
        const parentCluster = series.id.slice(0, -1);
        if (!parentMapping.has(parentCluster)) {
          parentMapping.set(parentCluster, nextParentIndex++);
        }
      }
    });
    
    // Then, assign colors to sub-clusters based on their parent
    (data || []).forEach(series => {
      if (series && series.id && typeof series.id === 'string' && series.id.length > 0 && !mapping.has(series.id)) {
        const parentCluster = series.id.slice(0, -1);
        const parentIndex = parentMapping.get(parentCluster) || 0;
        const subClusterLetter = series.id.slice(-1);
        // Create variation based on the last character (a=0, b=1, c=2, etc.)
        const variation = subClusterLetter.charCodeAt(0) - 'a'.charCodeAt(0);
        // Combine parent index with variation for unique but related colors
        mapping.set(series.id, parentIndex * 10 + variation);
      }
    });
    return mapping;
  }, [data]);

  // Check for pinned comment ID in URL on mount
  useEffect(() => {
    const pinnedId = searchParams.get('pinned');
    if (pinnedId && data) {
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

  // Base colors for parent clusters
  const baseColors = [
    "#e11d48", "#9333ea", "#3b82f6", "#10b981", "#f59e0b",
    "#ec4899", "#6366f1", "#06b6d4", "#84cc16", "#f97316",
    "#a855f7", "#14b8a6", "#eab308", "#ef4444", "#8b5cf6"
  ];

  // const stanceColors = { // This was commented out by user, ensuring it's fully gone or remains commented
  //   For: "#10b981",
  //   Against: "#ef4444",
  //   "Neutral/Unclear": "#64748b",
  // };

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
      className="bg-white rounded-lg relative"
      style={{ height: '600px' }}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => !clickedPoint && handlePointHover(null)}
      onClick={handleChartClick}
    >
      <ResponsiveScatterPlotCanvas
        data={data || []}
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
        colors={(node) => {
          // Access the series id from the node
          const serieId = node.serieId;
          
          if (!serieId || typeof serieId !== 'string') {
            return baseColors[0]; // Fallback color
          }
          
          const colorIndex = clusterIdToColorIndex.get(serieId);
          if (colorIndex !== undefined) {
            const parentIndex = Math.floor(colorIndex / 10);
            const variation = colorIndex % 10;
            const baseColor = baseColors[parentIndex % baseColors.length];
            
            // Create shade variations
            const shadeMultiplier = 1 - (variation * 0.15);
            
            // Parse hex color and apply shade
            const r = parseInt(baseColor.slice(1, 3), 16);
            const g = parseInt(baseColor.slice(3, 5), 16);
            const b = parseInt(baseColor.slice(5, 7), 16);
            
            const newR = Math.round(r * shadeMultiplier);
            const newG = Math.round(g * shadeMultiplier);
            const newB = Math.round(b * shadeMultiplier);
            
            return `#${newR.toString(16).padStart(2, '0')}${newG.toString(16).padStart(2, '0')}${newB.toString(16).padStart(2, '0')}`;
          }
          return baseColors[0]; // Fallback color
        }}
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
        Hover to preview • Click to freeze tooltip • {(data || []).length} clusters shown
      </div>
    </div>
  );
}