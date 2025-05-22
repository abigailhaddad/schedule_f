// components/ServerStatisticsCard.tsx
'use client';

import { useServerDataContext } from '@/contexts/ServerDataContext';
import { useState, useEffect } from 'react';

export default function ServerStatisticsCard() {
  const { stats, loading } = useServerDataContext();
  
  // Create a state to hold the displayed values
  const [displayedStats, setDisplayedStats] = useState(stats);
  // State to track if it's the very first load sequence
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  
  // Update displayed stats when new stats arrive and loading is complete
  useEffect(() => {
    if (!loading) {
      setDisplayedStats(stats);
      // Once data is loaded (or attempted to load and loading is false),
      // it's no longer the "initial load" for placeholder purposes.
      if (isInitialLoad) {
        setIsInitialLoad(false);
      }
    }
  }, [stats, loading, isInitialLoad]);
  
  // Function to get color based on stat type
  const getStatColors = (key: string) => {
    if (key === 'for') return { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' };
    if (key === 'against') return { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' };
    if (key === 'neutral') return { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' };
    
    // Default for total
    return { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' };
  };
  
  // Create statistics data with labels and values
  const statisticsData = [
    { key: 'total', label: 'Total Comments', value: displayedStats.total },
    { key: 'for', label: 'For', value: displayedStats.for, match: 'For' },
    { key: 'against', label: 'Against', value: displayedStats.against, match: 'Against' },
    { key: 'neutral', label: 'Neutral/Unclear', value: displayedStats.neutral, match: 'Neutral/Unclear' }
  ];

  // Placeholder component for individual stat
  const StatPlaceholder = () => (
    <div className="p-4 rounded-lg border shadow-sm bg-gray-100 animate-pulse">
      <div className="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
      <div className="h-8 bg-gray-300 rounded w-1/2 mb-1"></div>
      <div className="h-4 bg-gray-300 rounded w-1/4 mt-2"></div>
    </div>
  );

  // If it's the initial load sequence and data is currently loading from context
  if (isInitialLoad && loading) {
    return (
      <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
        <div className="border-b border-gray-200 px-6 py-4 bg-gradient-to-r from-blue-500 to-blue-600">
          <h5 className="text-lg font-bold text-white flex items-center">
            <span className="mr-2">📊</span>
            Statistics Overview
          </h5>
        </div>
        <div className="p-6" id="statistics">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, index) => (
              <StatPlaceholder key={index} />
            ))}
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
      <div className="border-b border-gray-200 px-6 py-4 bg-gradient-to-r from-blue-500 to-blue-600">
        <h5 className="text-lg font-bold text-white flex items-center">
          <span className="mr-2">📊</span>
          Statistics Overview
        </h5>
      </div>
      <div className="p-6" id="statistics">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {statisticsData.map((stat) => {
            const colors = getStatColors(stat.key);
            return (
              <div 
                key={stat.key} 
                className={`p-4 rounded-lg border shadow-sm ${colors.bg} ${colors.border}`}
              >
                <p className={`text-sm uppercase font-semibold mb-1 ${colors.text} ${stat.key === 'neutral' ? 'break-words text-xs' : ''}`}>
                  {stat.key === 'neutral' ? (
                    <>NEUTRAL/<wbr />UNCLEAR</>
                  ) : (
                    stat.label
                  )}
                </p>
                <h3 className={`text-3xl font-bold mb-1 ${colors.text}`}>
                  {(typeof stat.value === 'number' ? stat.value.toLocaleString() : '0')}
                </h3>
                {stat.match && (
                  <div className="mt-2 flex items-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text} border ${colors.border} ${stat.key === 'neutral' ? 'break-words' : ''}`}>
                      {stat.key === 'neutral' ? (
                        <>Neutral/<wbr />Unclear</>
                      ) : (
                        stat.match
                      )}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}