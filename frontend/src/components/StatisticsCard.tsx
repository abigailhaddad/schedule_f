// components/StatisticsCard.tsx
'use client';

import { Comment, Analysis } from '@/lib/db/schema';
import { datasetConfig } from '@/lib/config';

type CommentWithAnalysis = Comment & {
  analysis: Analysis | null;
};

interface StatisticsCardProps {
  data: CommentWithAnalysis[];
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
  
  return (
    <div className="card">
      <div className="card-header">
        <h5 className="m-0"><i className="bi bi-graph-up me-2"></i>Statistics</h5>
      </div>
      <div className="card-body" id="statistics">
        <div className="row text-center">
          {stats.map((stat, index) => (
            <div className="col" key={index}>
              <h3>{stat.value.toLocaleString()}</h3>
              <p>{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}