"use client";

import { useRef, useState, useCallback, useEffect, useMemo } from 'react';
import {
  ResponsiveScatterPlotCanvas
} from "@nivo/scatterplot";
import { ClusterPoint } from "@/lib/actions/clusters";
import { useRouter, useSearchParams } from 'next/navigation';
// import d3 from 'd3'; // d3 import seems unused
import ClusterTooltipOverlay from './ClusterTooltipOverlay';

// Base colors for parent clusters - moved outside component to ensure it's always available
const baseColors = [
  "#e11d48", "#9333ea", "#3b82f6", "#10b981", "#f59e0b",
  "#ec4899", "#6366f1", "#06b6d4", "#84cc16", "#f97316",
  "#a855f7", "#14b8a6", "#eab308", "#ef4444", "#8b5cf6"
];

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
  const lastHoverTimeRef = useRef<number>(0);
  const pendingHoverRef = useRef<ClusterPoint | null>(null);

  // Create a stable color mapping for cluster IDs
  const clusterIdToColorIndex = useMemo(() => {
    const mapping = new Map<string, number>();
    const parentMapping = new Map<string, number>();
    let nextParentIndex = 0;
    
    // Only proceed if we have data
    if (!data || data.length === 0) return mapping;
    
    // First, identify parent clusters and assign base colors
    data.forEach(series => {
      if (series && series.id && typeof series.id === 'string' && series.id.length > 0) {
        // Extract the numeric part at the beginning (parent cluster)
        const match = series.id.match(/^(\d+)/);
        const parentCluster = match ? match[1] : series.id;
        if (!parentMapping.has(parentCluster)) {
          parentMapping.set(parentCluster, nextParentIndex++);
        }
      }
    });
    
    // Then, assign colors to sub-clusters based on their parent
    data.forEach(series => {
      if (series && series.id && typeof series.id === 'string' && series.id.length > 0 && !mapping.has(series.id)) {
        const match = series.id.match(/^(\d+)(.*)/);
        const parentCluster = match ? match[1] : series.id;
        const subPart = match ? match[2] : '';
        const parentIndex = parentMapping.get(parentCluster) || 0;
        
        if (subPart) {
          // Create variation based on the sub-part (could be 'a', 'b', 'aa', 'ab', etc.)
          let variation = 0;
          for (let i = 0; i < subPart.length; i++) {
            variation += (subPart.charCodeAt(i) - 'a'.charCodeAt(0)) * Math.pow(26, subPart.length - 1 - i);
          }
          // Limit variation to prevent running out of distinguishable colors
          variation = Math.min(variation, 15);
          // Combine parent index with variation for unique but related colors
          mapping.set(series.id, parentIndex * 20 + variation);
        } else {
          // For simple clusters without sub-clusters, just use the parent index
          mapping.set(series.id, parentIndex * 20);
        }
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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
    };
  }, []);

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
    
    // Throttle hover updates to prevent excessive re-renders
    const now = Date.now();
    const timeSinceLastHover = now - lastHoverTimeRef.current;
    
    // Clear any existing timeout
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }

    if (point) {
      // Store the pending hover point
      pendingHoverRef.current = point;
      
      // If we're hovering too quickly, delay the update
      if (timeSinceLastHover < 50) { // 50ms throttle
        hoverTimeoutRef.current = setTimeout(() => {
          if (pendingHoverRef.current) {
            setHoveredPoint(pendingHoverRef.current);
            lastHoverTimeRef.current = Date.now();
          }
        }, 50 - timeSinceLastHover);
      } else {
        // Update immediately if enough time has passed
        setHoveredPoint(point);
        lastHoverTimeRef.current = now;
      }
    } else {
      // Clear pending hover
      pendingHoverRef.current = null;
      
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

  const handleMouseLeave = useCallback(() => {
    if (!clickedPoint) {
      handlePointHover(null);
    }
  }, [clickedPoint, handlePointHover]);

  const handleMouseEnter = useCallback((node: any) => {
    if (node.data && !clickedPoint) {
      handlePointHover(node.data as ClusterPoint);
    }
  }, [clickedPoint, handlePointHover]);

  const handleClick = useCallback((node: any) => {
    if (node.data) {
      handlePointClick(node.data as ClusterPoint);
    }
  }, [handlePointClick]);

  // Memoize the chart data to prevent unnecessary re-renders
  const chartData = useMemo(() => data || [], [data]);

  return (
    <div 
      ref={chartRef}
      className="bg-white rounded-lg relative"
      style={{ height: '600px' }}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onClick={handleChartClick}
    >
      <ResponsiveScatterPlotCanvas
        data={chartData}
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
          if (colorIndex !== undefined && baseColors && baseColors.length > 0) {
            const parentIndex = Math.floor(colorIndex / 20);
            const variation = colorIndex % 20;
            const baseColor = baseColors[parentIndex % baseColors.length];
            
            // Additional safety check
            if (!baseColor || typeof baseColor !== 'string' || baseColor.length !== 7) {
              return baseColors[0] || '#3b82f6'; // Fallback with extra safety
            }
            
            // Create shade variations - smaller multiplier for more variations
            const shadeMultiplier = 1 - (variation * 0.08);
            
            // Parse hex color and apply shade
            const r = parseInt(baseColor.slice(1, 3), 16);
            const g = parseInt(baseColor.slice(3, 5), 16);
            const b = parseInt(baseColor.slice(5, 7), 16);
            
            const newR = Math.round(r * shadeMultiplier);
            const newG = Math.round(g * shadeMultiplier);
            const newB = Math.round(b * shadeMultiplier);
            
            return `#${newR.toString(16).padStart(2, '0')}${newG.toString(16).padStart(2, '0')}${newB.toString(16).padStart(2, '0')}`;
          }
          return baseColors[0] || '#3b82f6'; // Fallback color with extra safety
        }}
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
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