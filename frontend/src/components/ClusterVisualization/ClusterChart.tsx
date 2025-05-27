"use client";

import { useRef, useState, useCallback, useEffect } from 'react';
import {
  ResponsiveScatterPlotCanvas
} from "@nivo/scatterplot";
import { ClusterPoint } from "@/lib/actions/clusters";
import { useRouter, useSearchParams } from 'next/navigation';

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

//   const stanceColors = {
//     For: "#10b981",
//     Against: "#ef4444",
//     "Neutral/Unclear": "#64748b",
//   };

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
          onNavigate={(id) => {
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

// New component for the tooltip overlay
function ClusterTooltipOverlay({ 
  point, 
  position, 
  isFixed,
  onClose,
  onNavigate
}: { 
  point: ClusterPoint; 
  position: { x: number; y: number };
  isFixed: boolean;
  onClose: () => void;
  onNavigate: (id: string) => void;
}) {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [adjustedPosition, setAdjustedPosition] = useState({ x: position.x, y: position.y });

  useEffect(() => {
    if (tooltipRef.current) {
      const tooltip = tooltipRef.current;
      const tooltipRect = tooltip.getBoundingClientRect();
      const parentRect = tooltip.offsetParent?.getBoundingClientRect();
      
      if (parentRect) {
        let newX = position.x + 10;
        let newY = position.y + 10;
        
        // Check if tooltip would go off the right edge
        if (newX + tooltipRect.width > parentRect.width - 20) {
          // Position to the left of the cursor instead
          newX = position.x - tooltipRect.width - 10;
        }
        
        // Check if tooltip would go off the bottom edge
        if (newY + tooltipRect.height > parentRect.height - 20) {
          // Position above the cursor instead
          newY = position.y - tooltipRect.height - 10;
        }
        
        // Ensure tooltip doesn't go off the left edge
        if (newX < 10) {
          newX = 10;
        }
        
        // Ensure tooltip doesn't go off the top edge
        if (newY < 10) {
          newY = 10;
        }
        
        setAdjustedPosition({ x: newX, y: newY });
      }
    }
  }, [position]);

  // Use adjusted position for tooltip
  const tooltipStyle: React.CSSProperties = {
    position: 'absolute',
    left: adjustedPosition.x,
    top: adjustedPosition.y,
    zIndex: 50,
    pointerEvents: 'auto', // Always allow interaction
  };

  return (
    <div 
      ref={tooltipRef}
      className={`bg-white p-4 rounded-lg shadow-lg border ${
        isFixed ? 'border-blue-400 ring-2 ring-blue-200' : 'border-gray-200'
      } max-w-sm transition-all`}
      style={tooltipStyle}
      onMouseEnter={(e) => e.stopPropagation()}
    >
      {isFixed && (
        <button
          onClick={onClose}
          className="absolute top-2 right-2 text-gray-400 hover:text-gray-600"
          aria-label="Close tooltip"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
      
      <h4 className="font-semibold text-gray-800 mb-2 line-clamp-2 pr-4">
        {point.title}
      </h4>
      
      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-gray-600">Cluster:</span>
          <span className="font-medium">{point.clusterId}</span>
        </div>
        
        {point.stance && (
          <div className="flex items-center gap-2">
            <span className="text-gray-600">Stance:</span>
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              point.stance === 'For' ? 'bg-green-100 text-green-800' :
              point.stance === 'Against' ? 'bg-red-100 text-red-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {point.stance}
            </span>
          </div>
        )}
        
        {point.keyQuote && (
          <div className="mt-2">
            <p className="text-gray-600 text-xs">Key Quote:</p>
            <p className="italic text-gray-700 line-clamp-2">&quot;{point.keyQuote}&quot;</p>
          </div>
        )}
        
        {point.themes && (
          <div className="mt-2">
            <p className="text-gray-600 text-xs">Themes:</p>
            <div className="flex flex-wrap gap-1 mt-1">
              {point.themes.split(',').slice(0, 3).map((theme, i) => (
                <span key={i} className="text-xs bg-gray-100 px-2 py-1 rounded">
                  {theme.trim()}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      
      {isFixed && (
        <button
          onClick={() => onNavigate(point.id)}
          className="w-full text-sm bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded mt-3 font-medium transition-colors"
        >
          View Full Comment →
        </button>
      )}
      
      {!isFixed && (
        <p className="text-xs text-gray-500 mt-3 italic">Click to pin this tooltip</p>
      )}
    </div>
  );
}