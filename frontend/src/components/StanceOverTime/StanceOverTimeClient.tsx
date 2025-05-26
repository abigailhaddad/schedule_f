// src/components/StanceOverTime/StanceOverTimeClient.tsx
'use client';

import { useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import Card from '@/components/ui/Card';
import LoadingSkeleton from './LoadingSkeleton';
import { useServerDataContext } from '@/contexts/ServerDataContext';

// Dynamically import the Nivo chart to avoid SSR issues
const TimeSeriesChart = dynamic(() => import('./NivoTimeSeriesChart'), {
  ssr: false,
  loading: () => <LoadingSkeleton />
});

export default function StanceOverTimeClient() {
  const { stanceTimeSeriesData, loading: contextLoading } = useServerDataContext();

  const [selectedDateType, setSelectedDateType] = useState<'posted_date' | 'received_date'>('posted_date');

  const chartData = useMemo(() => {
    if (!stanceTimeSeriesData) return [];
    return stanceTimeSeriesData[selectedDateType] || [];
  }, [stanceTimeSeriesData, selectedDateType]);

  if (contextLoading && !stanceTimeSeriesData) {
    return <LoadingSkeleton />;
  }

  if (stanceTimeSeriesData?.error) {
    return (
      <Card className="border-red-200" collapsible={false}>
        <Card.Header className="bg-gradient-to-r from-red-500 to-red-600 flex justify-between items-center">
          <h5 className="text-lg font-bold text-white flex items-center">
            <span className="mr-2">⚠️</span>
            Chart Error
          </h5>
        </Card.Header>
        <Card.Body className="text-center py-8">
          <p className="text-red-500">Error loading chart data: {stanceTimeSeriesData.error}</p>
        </Card.Body>
      </Card>
    );
  }
  
  if (!stanceTimeSeriesData) {
    return <LoadingSkeleton />;
  }

  return (
    <Card collapsible={true} initiallyCollapsed={false}>
      <Card.Header className="bg-gradient-to-r from-indigo-500 to-purple-600">
        <div className="flex justify-between items-center w-full">
          <h5 className="text-lg font-bold text-white flex items-center">
            <span className="mr-2">📈</span>
            Comments Over Time
          </h5>
          <select
            value={selectedDateType}
            onChange={(e) => setSelectedDateType(e.target.value as 'posted_date' | 'received_date')}
            className="bg-white bg-opacity-20 text-white text-sm px-3 py-1 rounded-md focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-50"
            aria-label="Select the appropriate date that you would like to see for the chart, whether it's the date the comment was posted or the date the comment was received."
          >
            <option value="posted_date" className="text-gray-700">By Posted Date</option>
            <option value="received_date" className="text-gray-700">By Received Date</option>
          </select>
        </div>
      </Card.Header>
      <Card.Body className="p-4">
        <TimeSeriesChart data={chartData} />
      </Card.Body>
    </Card>
  );
}