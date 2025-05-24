'use client';

import { StanceData, ChartType } from './types';
import SimpleSVGChart from './SimpleSVGChart';

interface ChartSelectorProps {
  data: StanceData[];
  chartType: ChartType;
  className?: string;
}

export default function ChartSelector({ data, chartType, className }: ChartSelectorProps) {
  switch (chartType) {
    case 'svg':
      return <SimpleSVGChart data={data} className={className} />;
    
    // Add more chart types here as needed
    // case 'visx':
    //   return <VisxChart data={data} className={className} />;
    
    default:
      return <SimpleSVGChart data={data} className={className} />;
  }
} 