'use client';

import { useMemo } from 'react';

interface ClusterControlsProps {
  clusters: string[];
  selectedCluster: string | null;
  onClusterSelect: (cluster: string | null) => void;
}

export default function ClusterControls({
  clusters,
  selectedCluster,
  onClusterSelect,
}: ClusterControlsProps) {
  // Base colors for parent clusters (same as in ClusterChart)
  const baseColors = [
    "#e11d48", "#9333ea", "#3b82f6", "#10b981", "#f59e0b",
    "#ec4899", "#6366f1", "#06b6d4", "#84cc16", "#f97316",
    "#a855f7", "#14b8a6", "#eab308", "#ef4444", "#8b5cf6"
  ];

  // Generate cluster colors (same logic as in ClusterChart)
  const clusterColors = useMemo(() => {
    const colors = new Map<string, string>();
    const parentMapping = new Map<string, number>();
    let nextParentIndex = 0;
    
    // First, identify parent clusters
    clusters.forEach(clusterId => {
      const parentCluster = clusterId.slice(0, -1);
      if (!parentMapping.has(parentCluster)) {
        parentMapping.set(parentCluster, nextParentIndex++);
      }
    });
    
    // Then, assign colors
    clusters.forEach(clusterId => {
      const parentCluster = clusterId.slice(0, -1);
      const parentIndex = parentMapping.get(parentCluster) || 0;
      const subClusterLetter = clusterId.slice(-1);
      const variation = subClusterLetter.charCodeAt(0) - 'a'.charCodeAt(0);
      
      const baseColor = baseColors[parentIndex % baseColors.length];
      const shadeMultiplier = 1 - (variation * 0.15);
      
      const r = parseInt(baseColor.slice(1, 3), 16);
      const g = parseInt(baseColor.slice(3, 5), 16);
      const b = parseInt(baseColor.slice(5, 7), 16);
      
      const newR = Math.round(r * shadeMultiplier);
      const newG = Math.round(g * shadeMultiplier);
      const newB = Math.round(b * shadeMultiplier);
      
      colors.set(clusterId, `#${newR.toString(16).padStart(2, '0')}${newG.toString(16).padStart(2, '0')}${newB.toString(16).padStart(2, '0')}`);
    });
    
    return colors;
  }, [clusters]);

  // Group clusters by parent for better organization
  const groupedClusters = useMemo(() => {
    const groups = new Map<string, string[]>();
    clusters.forEach(clusterId => {
      const parent = clusterId.slice(0, -1);
      if (!groups.has(parent)) {
        groups.set(parent, []);
      }
      groups.get(parent)!.push(clusterId);
    });
    // Sort groups and their clusters
    return Array.from(groups.entries())
      .sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }))
      .map(([parent, subs]) => [parent, subs.sort()] as const);
  }, [clusters]);

  return (
    <div className="space-y-4">
      {/* Filter Controls */}
      <div className="flex flex-wrap gap-4 items-center">
        <div className="flex items-center gap-2">
          <label htmlFor="cluster-select" className="text-sm font-medium text-gray-700">
            Filter by Cluster:
          </label>
          <select
            id="cluster-select"
            value={selectedCluster ?? ''}
            onChange={(e) => onClusterSelect(e.target.value ? e.target.value : null)}
            className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Clusters</option>
            {clusters.sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' })).map(clusterId => (
              <option key={`cluster-option-${clusterId}`} value={clusterId}>
                Cluster {clusterId}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Color Legend */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Cluster Legend</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
          {groupedClusters.map((group) => {
            const [parent, subClusters] = group;
            return (
              <div key={parent} className="space-y-1">
                <div className="text-xs font-medium text-gray-600">Group {parent}</div>
                {subClusters.map((clusterId: string) => (
                  <div key={clusterId} className="flex items-center gap-1">
                    <div 
                      className="w-3 h-3 rounded-full flex-shrink-0" 
                      style={{ backgroundColor: clusterColors.get(clusterId) }}
                    />
                    <span className="text-xs text-gray-700">{clusterId}</span>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}