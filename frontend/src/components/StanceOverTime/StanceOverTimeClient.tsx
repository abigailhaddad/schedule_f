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
  const [isChartVisible, setIsChartVisible] = useState(true);

  const chartData = useMemo(() => {
    if (!stanceTimeSeriesData) return [];
    return stanceTimeSeriesData[selectedDateType] || [];
  }, [stanceTimeSeriesData, selectedDateType]);

  if (contextLoading && !stanceTimeSeriesData) {
    return <LoadingSkeleton />;
  }

  if (stanceTimeSeriesData?.error) {
    return (
      <Card>
        <Card.Header className="bg-gradient-to-r from-indigo-500 to-purple-600 flex justify-between items-center">
          <div className="flex items-center">
            <button 
              onClick={() => setIsChartVisible(!isChartVisible)}
              className="mr-2 p-1 text-white hover:bg-white hover:bg-opacity-20 rounded-full transition-colors"
              aria-label={isChartVisible ? "Collapse chart" : "Expand chart"}
              title={isChartVisible ? "Collapse chart" : "Expand chart"}
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={`w-5 h-5 transform transition-transform ${isChartVisible ? '' : '-rotate-90'}`}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
              </svg>
            </button>
            <h5 className="text-lg font-bold text-white flex items-center">
              <span className="mr-2">📈</span>
              Comments Over Time
            </h5>
          </div>
          <select
            value={selectedDateType}
            onChange={(e) => setSelectedDateType(e.target.value as 'posted_date' | 'received_date')}
            className="bg-white bg-opacity-20 text-white text-sm px-3 py-1 rounded-md focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-50"
          >
            <option value="posted_date" className="text-gray-700">By Posted Date</option>
            <option value="received_date" className="text-gray-700">By Received Date</option>
          </select>
        </Card.Header>
        {isChartVisible && (
          <Card.Body className="text-center py-8">
            <p className="text-red-500">Error loading chart data: {stanceTimeSeriesData.error}</p>
          </Card.Body>
        )}
      </Card>
    );
  }
  
  if (!stanceTimeSeriesData) {
    return <LoadingSkeleton />;
  }

  return (
    <Card>
      <Card.Header className="bg-gradient-to-r from-indigo-500 to-purple-600 flex justify-between items-center">
        <div className="flex items-center">
          <button 
            onClick={() => setIsChartVisible(!isChartVisible)}
            className="mr-2 p-1 text-white hover:bg-white hover:bg-opacity-20 rounded-full transition-colors"
            aria-label={isChartVisible ? "Collapse chart" : "Expand chart"}
            title={isChartVisible ? "Collapse chart" : "Expand chart"}
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className={`w-5 h-5 transform transition-transform ${isChartVisible ? '' : '-rotate-90'}`}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
            </svg>
          </button>
          <h5 className="text-lg font-bold text-white flex items-center">
            <span className="mr-2">📈</span>
            Comments Over Time
          </h5>
        </div>
        <select
          value={selectedDateType}
          onChange={(e) => setSelectedDateType(e.target.value as 'posted_date' | 'received_date')}
          className="bg-white bg-opacity-20 text-white text-sm px-3 py-1 rounded-md focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-50"
        >
          <option value="posted_date" className="text-gray-700">By Posted Date</option>
          <option value="received_date" className="text-gray-700">By Received Date</option>
        </select>
      </Card.Header>
      {isChartVisible && (
        <Card.Body className="p-4">
          <TimeSeriesChart data={chartData} />
        </Card.Body>
      )}
    </Card>
  );
}