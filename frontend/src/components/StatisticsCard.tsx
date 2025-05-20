// components/StatisticsCard.tsx
'use client';

import { CommentWithAnalysis } from '@/lib/db/schema';
import { datasetConfig } from '@/lib/config';

interface StatisticsCardProps {
  data: CommentWithAnalysis[];
}

// Define a type for the statistics
interface Stat {
  key: string;
  label: string;
  type: string;
  match?: string;
  value?: number;
}

export default function StatisticsCard({ data }: StatisticsCardProps) {
  // Calculate statistics based on our data and config
  const calculateStats = () => {
    const stats = datasetConfig.stats.map(stat => {
      let value = 0;
      
      switch (stat.type) {
        case 'count':
          if (stat.key === 'total') {
            value = data.length;
          } else if (stat.match) {
            value = data.filter(item => {
              if (stat.key === 'stance' && item.analysis) {
                return item.analysis.stance === stat.match;
              }
              return false;
            }).length;
          }
          break;
        // Add other stat types as needed
      }
      
      return {
        ...stat,
        value
      };
    });
    
    return stats;
  };
  
  const stats = calculateStats();
  
  // Function to get color based on stat key
  const getStatColors = (stat: Stat) => {
    if (stat.match === 'For') return { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200' };
    if (stat.match === 'Against') return { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' };
    if (stat.match === 'Neutral/Unclear') return { bg: 'bg-gray-50', text: 'text-gray-700', border: 'border-gray-200' };
    
    // Default for total
    return { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' };
  };
  
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
          {stats.map((stat, index) => {
            const colors = getStatColors(stat);
            return (
              <div 
                key={index} 
                className={`p-4 rounded-lg border shadow-sm ${colors.bg} ${colors.border}`}
              >
                <p className={`text-sm uppercase font-semibold mb-1 ${colors.text}`}>{stat.label}</p>
                <h3 className={`text-3xl font-bold mb-1 ${colors.text}`}>
                  {stat.value?.toLocaleString() || '0'}
                </h3>
                {stat.match && (
                  <div className="mt-2 flex items-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text} border ${colors.border}`}>
                      {stat.match}
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