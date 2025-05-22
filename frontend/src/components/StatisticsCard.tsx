// components/StatisticsCard.tsx
'use client';

import { Comment } from '@/lib/db/schema';
import { datasetConfig } from '@/lib/config';

interface StatisticsCardProps {
  data: Comment[];
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
              if (stat.key === 'stance') {
                return item.stance === stat.match;
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
  
  // Function to get color based on stat key with improved contrast
  const getStatColors = (stat: Stat) => {
    if (stat.match === 'For') return { bg: 'bg-green-100', text: 'text-green-900', border: 'border-green-300' };
    if (stat.match === 'Against') return { bg: 'bg-red-100', text: 'text-red-900', border: 'border-red-300' };
    if (stat.match === 'Neutral/Unclear') return { bg: 'bg-gray-100', text: 'text-gray-900', border: 'border-gray-300' };
    
    // Default for total
    return { bg: 'bg-blue-100', text: 'text-blue-900', border: 'border-blue-300' };
  };
  
  return (
    <section 
      className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden"
      aria-labelledby="statistics-heading"
    >
      <div className="border-b border-gray-200 px-6 py-4 bg-gradient-to-r from-blue-500 to-blue-600">
        <h2 id="statistics-heading" className="text-lg font-bold text-white flex items-center">
          <span className="mr-2" aria-hidden="true">📊</span>
          Statistics Overview
        </h2>
      </div>
      <div className="p-6">
        <div 
          className="grid grid-cols-1 md:grid-cols-4 gap-4"
          role="list"
          aria-label="Comment statistics"
        >
          {stats.map((stat, index) => {
            const colors = getStatColors(stat);
            return (
              <div 
                key={index} 
                className={`p-4 rounded-lg border shadow-sm ${colors.bg} ${colors.border}`}
                role="listitem"
              >
                <p 
                  className={`text-sm uppercase font-semibold mb-1 ${colors.text}`} 
                  id={`stat-label-${stat.key}`}
                >
                  {stat.label}
                </p>
                <h3 
                  className={`text-3xl font-bold mb-1 ${colors.text}`}
                  aria-labelledby={`stat-label-${stat.key}`}
                >
                  {stat.value?.toLocaleString() || '0'}
                  <span className="sr-only"> comments</span>
                </h3>
                {stat.match && (
                  <div className="mt-2 flex items-center">
                    <span 
                      className={`px-2 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text} border ${colors.border}`}
                      role="note"
                      aria-label={`Comments with stance: ${stat.match}`}
                    >
                      {stat.match}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}