// src/components/ClusterVisualization/index.tsx
"use client";

import React, { useState, useMemo, useCallback } from 'react';
import { ClusterData, ClusterPoint } from "@/lib/actions/clusters";
import ClusterChart from './ClusterChart';
import ClusterControls from "./ClusterControls";
import Card from "@/components/ui/Card";
import LoadingSpinner from '@/components/ui/LoadingSpinner';

interface ClusterVisualizationProps {
  initialData: ClusterData | null;
  isLoading: boolean;
  error: string | null;
}

const ClusterVisualization: React.FC<ClusterVisualizationProps> = ({ initialData, isLoading, error }) => {
  const [clusterData, setClusterData] = useState<ClusterData | null>(initialData);
  const [selectedClusterId, setSelectedClusterId] = useState<string | null>(null);

  const handleClusterSelected = useCallback((clusterId: string | null) => {
    setSelectedClusterId(clusterId);
  }, []);

  React.useEffect(() => {
    setClusterData(initialData);
  }, [initialData]);

  // Data for the chart, formatted as Nivo expects series.
  const chartSeriesData = useMemo(() => {
    if (!clusterData) return [];
    return clusterData.clusters.map(([id, points]) => ({
      id: id,
      data: points.map(p => ({ ...p, x: p.pcaX, y: p.pcaY })),
    }));
  }, [clusterData]);

  // Points to render: all if no selection, or only selected cluster's points.
  const pointsToRender = useMemo(() => {
    if (!clusterData) return [];
    if (!selectedClusterId) return chartSeriesData.flatMap(series => series.data);
    const selectedSeries = chartSeriesData.find(series => series.id === selectedClusterId);
    return selectedSeries ? selectedSeries.data : [];
  }, [chartSeriesData, selectedClusterId, clusterData]);
  
  // Data for ClusterChart component: if a cluster is selected, only pass that series
  const chartDisplayData = useMemo(() => {
    if (!selectedClusterId || !chartSeriesData) return chartSeriesData;
    return chartSeriesData.filter(series => series.id === selectedClusterId);
  }, [chartSeriesData, selectedClusterId]);

  // Get cluster-specific information
  const selectedClusterInfo = useMemo(() => {
    if (!selectedClusterId || !clusterData) return null;
    const clusterPoints = clusterData.clusters.find(([id]) => id === selectedClusterId)?.[1];
    if (!clusterPoints) return null;

    // Calculate statistics for the selected cluster
    const stanceCounts = clusterPoints.reduce((acc, point) => {
      acc[point.stance || 'Neutral/Unclear'] = (acc[point.stance || 'Neutral/Unclear'] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return {
      totalComments: clusterPoints.length,
      stanceCounts,
      sampleComments: clusterPoints.slice(0, 5) // First 5 comments as samples
    };
  }, [selectedClusterId, clusterData]);

  if (isLoading) {
    return <div className="flex justify-center items-center h-64"><LoadingSpinner /></div>;
  }

  if (error) {
    return <div className="text-red-500 text-center p-4">Error loading cluster data: {error}</div>;
  }

  if (!clusterData || clusterData.clusters.length === 0) {
    return <div className="text-center p-4">No cluster data available.</div>;
  }

  return (
    <div className="h-full flex flex-col p-4">
      {/* Controls Section */}
      <Card className="mb-4 shadow-lg" collapsible={false}>
        <Card.Header>
          <h2 className="text-lg font-bold">Cluster Controls</h2>
        </Card.Header>
        <Card.Body>
          <ClusterControls
            clusters={clusterData.clusters.map(([clusterId]) => clusterId)}
            selectedCluster={selectedClusterId}
            onClusterSelect={handleClusterSelected}
          />
        </Card.Body>
      </Card>

      {/* Main content area with chart and info */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Chart Section - spans 2 columns on large screens */}
        <Card className="lg:col-span-2 shadow-lg h-full" collapsible={false}>
          <Card.Header>
            <h2 className="text-lg font-bold">
              Cluster Scatter Plot ({clusterData.totalPoints} comments in {clusterData.clusters.length} clusters)
            </h2>
          </Card.Header>
          <Card.Body className="p-0 relative flex-1">
            <div className="h-full">
              <ClusterChart
                data={chartDisplayData}
                bounds={clusterData.bounds}
              />
            </div>
          </Card.Body>
        </Card>

        {/* Cluster Information Section */}
        <Card className="shadow-lg h-full overflow-hidden" collapsible={false}>
          <Card.Header>
            <h2 className="text-lg font-bold">
              {selectedClusterId ? `Cluster ${selectedClusterId} Details` : 'Cluster Information'}
            </h2>
          </Card.Header>
          <Card.Body className="overflow-y-auto">
            {selectedClusterInfo ? (
              <div className="space-y-4">
                <div>
                  <h3 className="font-semibold text-sm text-gray-700">Total Comments</h3>
                  <p className="text-2xl font-bold">{selectedClusterInfo.totalComments}</p>
                </div>
                
                <div>
                  <h3 className="font-semibold text-sm text-gray-700 mb-2">Stance Distribution</h3>
                  <div className="space-y-1">
                    {Object.entries(selectedClusterInfo.stanceCounts).map(([stance, count]) => (
                      <div key={stance} className="flex justify-between items-center">
                        <span className={`text-sm ${
                          stance === 'For' ? 'text-green-600' : 
                          stance === 'Against' ? 'text-red-600' : 
                          'text-gray-600'
                        }`}>{stance}:</span>
                        <span className="font-medium">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-sm text-gray-700 mb-2">Sample Comments</h3>
                  <div className="space-y-2">
                    {selectedClusterInfo.sampleComments.map((comment, idx) => (
                      <div key={comment.id} className="bg-gray-50 p-2 rounded text-xs">
                        <p className="text-gray-600 line-clamp-2">{comment.title}</p>
                        {comment.keyQuote && (
                          <p className="text-gray-500 italic mt-1 line-clamp-2">"{comment.keyQuote}"</p>
                        )}
                        <p className="text-gray-400 mt-1">
                          Stance: <span className={
                            comment.stance === 'For' ? 'text-green-600' : 
                            comment.stance === 'Against' ? 'text-red-600' : 
                            'text-gray-600'
                          }>{comment.stance || 'Neutral/Unclear'}</span>
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-gray-500 text-center py-8">
                <p>Select a cluster to view detailed information</p>
                <p className="text-sm mt-2">Click on a cluster in the controls above or on the chart</p>
              </div>
            )}
          </Card.Body>
        </Card>
      </div>
    </div>
  );
};

export default ClusterVisualization;