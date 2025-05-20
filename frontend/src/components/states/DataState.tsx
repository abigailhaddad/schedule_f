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
    <div className="container-fluid py-4">
      {/* First row: Statistics and Filters side by side */}
      <div className="row mb-4">
        <div className="col-md-6">
          <StatisticsCard data={comments} />
        </div>
        <div className="col-md-6">
          <FilterSection onFilterChange={onFilterChange} />
        </div>
      </div>
      
      {/* Second row: Data Table */}
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body table-responsive">
              <CommentTable data={comments} filters={filters} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 