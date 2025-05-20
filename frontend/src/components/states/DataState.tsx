'use client';

import FilterSection from '../FilterSection';
import CommentTable from '../CommentTable';
import StatisticsCard from '../StatisticsCard';
import { useDataContext } from '@/contexts/DataContext';

// DataState no longer needs props as it gets data from context
export default function DataState() {
  // Get data and state from context
  const { data } = useDataContext();

  return (
    <div className="container-fluid py-4">
      {/* First row: Statistics and Filters side by side */}
      <div className="row mb-4">
        <div className="col-md-6">
          <StatisticsCard data={data} />
        </div>
        <div className="col-md-6">
          <FilterSection />
        </div>
      </div>
      
      {/* Second row: Data Table */}
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body table-responsive">
              <CommentTable />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 