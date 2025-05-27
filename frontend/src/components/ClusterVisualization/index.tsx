'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { ClusterData, ClusterPoint } from '@/lib/actions/clusters';
import Card from '@/components/ui/Card';
import ClusterControls from './ClusterControls';
import ClusterTooltip from './ClusterTooltip';
import { useRouter } from 'next/navigation';

// Dynamically import the chart to avoid SSR issues
const ClusterChart = dynamic(() => import('./ClusterChart'), {
  ssr: false,
  loading: () => (
    <div className="h-[600px] flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500" />
    </div>
  ),
});

interface ClusterVisualizationProps {
  data: ClusterData;
}

export default function ClusterVisualization({ data }: ClusterVisualizationProps) {
  const router = useRouter();
  const [selectedCluster, setSelectedCluster] = useState<number | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<ClusterPoint | null>(null);
  const [showStanceColors, setShowStanceColors] = useState(false);

  const handlePointClick = (point: ClusterPoint) => {
    router.push(`/comment/${point.id}`);
  };

  // Convert Map to array for chart
  const chartData = Array.from(data.clusters.entries()).map(([clusterId, points]) => ({
    id: `Cluster ${clusterId}`,
    data: points.map(point => ({
      x: point.pcaX,
      y: point.pcaY,
      ...point,
    })),
  }));

  const filteredData = selectedCluster !== null
    ? chartData.filter(series => series.id === `Cluster ${selectedCluster}`)
    : chartData;

  return (
    <div className="space-y-6">
      <Card collapsible={false}>
        <Card.Header className="bg-gradient-to-r from-purple-500 to-pink-500">
          <h2 className="text-lg font-bold text-white flex items-center">
            <span className="mr-2">🔮</span>
            Cluster Visualization
          </h2>
        </Card.Header>
        <Card.Body className="p-4">
          <ClusterControls
            clusters={Array.from(data.clusters.keys())}
            selectedCluster={selectedCluster}
            onClusterSelect={setSelectedCluster}
            showStanceColors={showStanceColors}
            onStanceColorsToggle={setShowStanceColors}
          />
          
          <div className="relative">
            <ClusterChart
              data={filteredData}
              bounds={data.bounds}
              showStanceColors={showStanceColors}
              onPointClick={handlePointClick}
              onPointHover={setHoveredPoint}
            />
            
            {hoveredPoint && (
              <ClusterTooltip point={hoveredPoint} />
            )}
          </div>
        </Card.Body>
      </Card>

      {/* Cluster Statistics */}
      <Card collapsible={true}>
        <Card.Header className="bg-gradient-to-r from-blue-500 to-blue-600">
          <h3 className="text-lg font-bold text-white">Cluster Statistics</h3>
        </Card.Header>
        <Card.Body className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Array.from(data.clusters.entries()).map(([clusterId, points]) => (
              <div key={clusterId} className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-semibold text-gray-700">Cluster {clusterId}</h4>
                <p className="text-2xl font-bold text-blue-600">{points.length}</p>
                <p className="text-sm text-gray-500">comments</p>
              </div>
            ))}
          </div>
        </Card.Body>
      </Card>
    </div>
  );
}