import React from 'react';
import { useRouter } from 'next/navigation';

interface ClusterSummaryCardProps {
  clusterId: string;
  label: string;
  total: number;
  forCount: number;
  againstCount: number;
  neutralCount: number;
  forPercentage: number;
  againstPercentage: number;
  dominantStance: string;
}

export default function ClusterSummaryCard({
  clusterId,
  label,
  total,
  forCount,
  againstCount,
  neutralCount,
  forPercentage,
  againstPercentage,
  dominantStance
}: ClusterSummaryCardProps) {
  const router = useRouter();

  const handleClick = () => {
    router.push(`/clusters/${clusterId}`);
  };

  return (
    <div
      onClick={handleClick}
      className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
    >
      <div className="flex justify-between items-start mb-2">
        <div>
          <h4 className="font-semibold text-sm text-gray-900">Cluster {clusterId}</h4>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
        <span className="text-xs bg-gray-100 px-2 py-1 rounded">
          {total} comments
        </span>
      </div>
      
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-green-600">For:</span>
          <div className="flex items-center gap-2">
            <div className="w-20 bg-gray-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-green-500 h-full"
                style={{ width: `${forPercentage}%` }}
              />
            </div>
            <span className="text-gray-700 w-12 text-right">
              {forPercentage.toFixed(0)}%
            </span>
          </div>
        </div>
        
        <div className="flex items-center justify-between text-xs">
          <span className="text-red-600">Against:</span>
          <div className="flex items-center gap-2">
            <div className="w-20 bg-gray-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-red-500 h-full"
                style={{ width: `${againstPercentage}%` }}
              />
            </div>
            <span className="text-gray-700 w-12 text-right">
              {againstPercentage.toFixed(0)}%
            </span>
          </div>
        </div>
        
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-600">Neutral:</span>
          <div className="flex items-center gap-2">
            <div className="w-20 bg-gray-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-gray-500 h-full"
                style={{ width: `${100 - forPercentage - againstPercentage}%` }}
              />
            </div>
            <span className="text-gray-700 w-12 text-right">
              {(100 - forPercentage - againstPercentage).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>
      
      <div className="mt-3 pt-3 border-t border-gray-100">
        <p className="text-xs text-gray-600">
          Dominant stance: <span className={
            dominantStance === 'For' ? 'text-green-600 font-medium' : 
            dominantStance === 'Against' ? 'text-red-600 font-medium' : 
            'text-gray-600 font-medium'
          }>{dominantStance}</span>
        </p>
      </div>
    </div>
  );
}