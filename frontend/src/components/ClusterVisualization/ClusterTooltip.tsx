'use client';

import { ClusterPoint } from '@/lib/actions/clusters';
import Badge from '@/components/ui/Badge';

interface ClusterTooltipProps {
  point: ClusterPoint;
}

export default function ClusterTooltip({ point }: ClusterTooltipProps) {
  const getBadgeType = (stance: string): 'success' | 'danger' | 'warning' => {
    if (stance === 'For') return 'success';
    if (stance === 'Against') return 'danger';
    return 'warning';
  };

  return (
    <div className="absolute z-50 pointer-events-none bg-white p-4 rounded-lg shadow-lg border border-gray-200 max-w-sm"
         style={{
           left: '50%',
           top: '50%',
           transform: 'translate(-50%, -50%)',
         }}>
      <h4 className="font-semibold text-gray-800 mb-2 line-clamp-2">
        {point.title}
      </h4>
      
      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-gray-600">Cluster:</span>
          <span className="font-medium">{point.clusterId}</span>
        </div>
        
        {point.stance && (
          <div className="flex items-center gap-2">
            <span className="text-gray-600">Stance:</span>
            <Badge type={getBadgeType(point.stance)} label={point.stance} />
          </div>
        )}
        
        {point.keyQuote && (
          <div className="mt-2">
            <p className="text-gray-600 text-xs">Key Quote:</p>
            <p className="italic text-gray-700 line-clamp-2">"{point.keyQuote}"</p>
          </div>
        )}
        
        {point.themes && (
          <div className="mt-2">
            <p className="text-gray-600 text-xs">Themes:</p>
            <div className="flex flex-wrap gap-1 mt-1">
              {point.themes.split(',').slice(0, 3).map((theme, i) => (
                <span key={i} className="text-xs bg-gray-100 px-2 py-1 rounded">
                  {theme.trim()}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      
      <p className="text-xs text-blue-600 mt-3">Click to view full comment</p>
    </div>
  );
}