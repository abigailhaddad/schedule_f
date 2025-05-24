export interface StanceData {
  date: string;
  For: number;
  Against: number;
  'Neutral/Unclear': number;
}

export interface ChartProps {
  data: StanceData[];
  className?: string;
}

export type ChartType = 'svg' | 'visx'; 