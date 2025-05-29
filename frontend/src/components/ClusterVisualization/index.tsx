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
    <div className="p-4 bg-gray-50 min-h-screen">
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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="md:col-span-2 shadow-lg" collapsible={false}>
          <Card.Header>
            <h2 className="text-lg font-bold">
              Cluster Scatter Plot ({clusterData.totalPoints} comments in {clusterData.clusters.length} clusters)
            </h2>
          </Card.Header>
          <Card.Body className="p-0 relative">
            <div style={{ minHeight: '500px' }}>
              <ClusterChart
                data={chartDisplayData}
                bounds={clusterData.bounds}
              />
            </div>
          </Card.Body>
        </Card>
      </div>
    </div>
  );
};

export default ClusterVisualization;