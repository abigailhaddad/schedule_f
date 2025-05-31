'use client';

import { useState, useEffect } from 'react';
import Card from '@/components/ui/Card';
import { useServerDataContext } from '@/contexts/ServerDataContext';

export default function DedupedStatisticsCard() {
  const { dedupedStats, loading } = useServerDataContext();
  
  // Create a state to hold the displayed values
  const [displayedStats, setDisplayedStats] = useState(dedupedStats);
  // State to track if it's the very first load sequence
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  
  // Update displayed stats when new stats arrive and loading is complete
  useEffect(() => {
    if (!loading) {
      setDisplayedStats(dedupedStats);
      // Once data is loaded (or attempted to load and loading is false),
      // it's no longer the "initial load" for placeholder purposes.
      if (isInitialLoad) {
        setIsInitialLoad(false);
      }
    }
  }, [dedupedStats, loading, isInitialLoad]);

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
    { key: 'total', label: 'Unique Comments', value: displayedStats.total },
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

  // Loading state display
  if (isInitialLoad && loading) {
    return (
      <Card className="overflow-hidden" collapsible={true} initiallyCollapsed={false}>
        <Card.Header className="border-b border-gray-200 px-6 py-4 bg-gradient-to-r from-purple-500 to-purple-600">
          <h5 className="text-lg font-bold text-white flex items-center">
            <span className="mr-2">📊</span>
            Unique Statistics (Duplicates Removed)
          </h5>
        </Card.Header>
        <Card.Body className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            {[...Array(4)].map((_, index) => (
              <StatPlaceholder key={index} />
            ))}
          </div>
        </Card.Body>
      </Card>
    );
  }
  
  // Main display of statistics
  return (
    <Card className="overflow-hidden" collapsible={true} initiallyCollapsed={false}>
      <Card.Header className="border-b border-gray-200 px-6 py-4 bg-gradient-to-r from-purple-500 to-purple-600">
        <h5 className="text-lg font-bold text-white flex items-center">
          <span className="mr-2">📊</span>
          Unique Statistics (Duplicates Removed)
        </h5>
      </Card.Header>
      <Card.Body className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
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
      </Card.Body>
    </Card>
  );
}