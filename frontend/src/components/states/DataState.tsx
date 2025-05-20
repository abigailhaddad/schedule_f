'use client';

import { CommentWithAnalysis } from '@/lib/db/schema';
import FilterSection from '../FilterSection';
import CommentTable from '../CommentTable';
import StatisticsCard from '../StatisticsCard';

interface DataStateProps {
  comments: CommentWithAnalysis[];
  filters: Record<string, unknown>;
  onFilterChange: (filters: Record<string, unknown>) => void;
}

export default function DataState({ comments, filters, onFilterChange }: DataStateProps) {
  return (
    <div className="container-fluid">
      <div className="row mb-4">
        <div className="col-12">
          <StatisticsCard data={comments} />
        </div>
      </div>
      
      <div className="row">
        <div className="col-md-3 mb-4">
          <FilterSection onFilterChange={onFilterChange} />
        </div>
        <div className="col-md-9 mb-4">
          <CommentTable data={comments} filters={filters} />
        </div>
      </div>
    </div>
  );
} 