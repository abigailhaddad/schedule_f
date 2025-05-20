// components/CommentsDataProvider.tsx
'use client';

import { useState, useEffect } from 'react';
import { CommentWithAnalysis } from '@/lib/db/schema';
import FilterSection from './FilterSection';
import CommentTable from './CommentTable';
import StatisticsCard from './StatisticsCard';
import { getComments, initDatabase } from '@/lib/actions';

export default function CommentsDataProvider() {
  const [comments, setComments] = useState<CommentWithAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<string, unknown>>({});
  const [dbStatus, setDbStatus] = useState<{success?: boolean, message?: string, counts?: {comments: number, analyses: number}} | null>(null);
  const [checkingDb, setCheckingDb] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const result = await getComments();
        
        if (result.success) {
          setComments(result.data || []);
        } else {
          console.error("Error fetching comments:", result.error);
          setError(result.error || 'Unknown error');
        }
      } catch (clientError) {
        console.error("Client-side error:", clientError);
        setError('Failed to fetch comments - client-side exception');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Handle filter changes
  const handleFilterChange = (newFilters: Record<string, unknown>) => {
    setFilters(newFilters);
  };

  // Check database connectivity
  const handleCheckDatabase = async () => {
    try {
      setCheckingDb(true);
      const result = await initDatabase();
      setDbStatus(result);
    } catch (error) {
      console.error("Database check failed:", error);
      setDbStatus({ success: false, message: "Failed to check database connection" });
    } finally {
      setCheckingDb(false);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <div className="alert alert-info p-4 text-center mb-4">
          Loading comments... <div className="spinner-border spinner-border-sm ms-2" role="status"></div>
        </div>
        <div className="d-grid gap-2 col-6 mx-auto">
          <button 
            className="btn btn-outline-secondary" 
            onClick={handleCheckDatabase}
            disabled={checkingDb}
          >
            {checkingDb ? 'Checking Database...' : 'Check Database Connection'}
          </button>
          
          {dbStatus && (
            <div className={`alert ${dbStatus.success ? 'alert-success' : 'alert-danger'} mt-3`}>
              <strong>{dbStatus.success ? 'Success:' : 'Error:'}</strong> {dbStatus.message}
              {dbStatus.counts && (
                <div className="mt-2">
                  <div>Comments count: {dbStatus.counts.comments}</div>
                  <div>Analyses count: {dbStatus.counts.analyses}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="container">
        <div className="alert alert-danger mb-4">Error loading comments: {error}</div>
        <div className="d-grid gap-2 col-6 mx-auto">
          <button 
            className="btn btn-outline-secondary" 
            onClick={handleCheckDatabase}
            disabled={checkingDb}
          >
            {checkingDb ? 'Checking Database...' : 'Check Database Connection'}
          </button>
          
          {dbStatus && (
            <div className={`alert ${dbStatus.success ? 'alert-success' : 'alert-danger'} mt-3`}>
              <strong>{dbStatus.success ? 'Success:' : 'Error:'}</strong> {dbStatus.message}
              {dbStatus.counts && (
                <div className="mt-2">
                  <div>Comments count: {dbStatus.counts.comments}</div>
                  <div>Analyses count: {dbStatus.counts.analyses}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (!comments || comments.length === 0) {
    return (
      <div className="container">
        <div className="alert alert-warning mb-4">No comments found. The database may be empty.</div>
        <div className="d-grid gap-2 col-6 mx-auto">
          <button 
            className="btn btn-outline-secondary" 
            onClick={handleCheckDatabase}
            disabled={checkingDb}
          >
            {checkingDb ? 'Checking Database...' : 'Check Database Connection'}
          </button>
          
          {dbStatus && (
            <div className={`alert ${dbStatus.success ? 'alert-success' : 'alert-danger'} mt-3`}>
              <strong>{dbStatus.success ? 'Success:' : 'Error:'}</strong> {dbStatus.message}
              {dbStatus.counts && (
                <div className="mt-2">
                  <div>Comments count: {dbStatus.counts.comments}</div>
                  <div>Analyses count: {dbStatus.counts.analyses}</div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="row mb-3">
        <div className="col-md-6">
          <StatisticsCard data={comments} />
        </div>
        <div className="col-md-6">
          <FilterSection onFilterChange={handleFilterChange} />
        </div>
      </div>
      <CommentTable data={comments} filters={filters} />
    </>
  );
}