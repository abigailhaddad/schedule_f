'use client';

import ServerFilterSection from '../ServerFilterSection';
import ServerCommentTable from '../ServerCommentTable';
import ServerStatisticsCard from '../ServerStatisticsCard';
import StanceOverTimeClient from '../StanceOverTime/StanceOverTimeClient';

export default function ServerDataState() {
  return (
    <div className="container-fluid py-4">
      {/* First row: Statistics and Filters side by side */}
      <div className="row mb-4">
        <div className="col-md-6">
          <ServerStatisticsCard />
        </div>
        <div className="col-md-6">
          <ServerFilterSection />
        </div>
      </div>

      {/* Second row: Stance Over Time Chart */}
      <div className="row mb-4">
        <div className="col-12">
          <StanceOverTimeClient />
        </div>
      </div>
      
      {/* Third row: Data Table */}
      <div className="row">
        <div className="col-12">
          <div className="card">
            <div className="card-body table-responsive">
              <ServerCommentTable />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}