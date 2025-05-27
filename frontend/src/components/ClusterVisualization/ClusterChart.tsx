'use client';

import { ResponsiveScatterPlot } from '@nivo/scatterplot';
import { ClusterPoint } from '@/lib/actions/clusters';

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
    '#e11d48', '#db2777', '#c026d3', '#9333ea', '#7c3aed',
    '#6366f1', '#3b82f6', '#0ea5e9', '#06b6d4', '#14b8a6',
    '#10b981', '#22c55e', '#84cc16', '#eab308', '#f59e0b',
    '#f97316', '#ef4444', '#dc2626', '#b91c1c', '#991b1b',
  ];

  // Color scheme for stances
  const stanceColors = {
    'For': '#10b981',
    'Against': '#ef4444',
    'Neutral/Unclear': '#64748b',
  };

  const getNodeColor = (node: any) => {
    if (showStanceColors && node.data.stance) {
      return stanceColors[node.data.stance as keyof typeof stanceColors] || '#64748b';
    }
    const clusterIndex = parseInt(node.serieId.replace('Cluster ', '')) % clusterColors.length;
    return clusterColors[clusterIndex];
  };

  return (
    <div style={{ height: 600 }} className="bg-white rounded-lg">
      <ResponsiveScatterPlot
        data={data}
        margin={{ top: 20, right: 20, bottom: 60, left: 60 }}
        xScale={{
          type: 'linear',
          min: bounds.minX * 1.1,
          max: bounds.maxX * 1.1,
        }}
        yScale={{
          type: 'linear',
          min: bounds.minY * 1.1,
          max: bounds.maxY * 1.1,
        }}
        blendMode="multiply"
        axisTop={null}
        axisRight={null}
        axisBottom={{
          tickSize: 5,
          tickPadding: 5,
          tickRotation: 0,
          legend: 'PCA Component 1',
          legendPosition: 'middle',
          legendOffset: 46,
        }}
        axisLeft={{
          tickSize: 5,
          tickPadding: 5,
          tickRotation: 0,
          legend: 'PCA Component 2',
          legendPosition: 'middle',
          legendOffset: -60,
        }}
        nodeSize={8}
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
        tooltip={() => null} // We'll use our custom tooltip
        legends={[
          {
            anchor: 'top-right',
            direction: 'column',
            justify: false,
            translateX: -20,
            translateY: 20,
            itemsSpacing: 5,
            itemDirection: 'left-to-right',
            itemWidth: 80,
            itemHeight: 20,
            itemOpacity: 0.75,
            symbolSize: 12,
            symbolShape: 'circle',
            effects: [
              {
                on: 'hover',
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