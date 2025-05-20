// components/CommentsDataProvider.tsx
'use client';

import { useState, useEffect } from 'react';
import { CommentWithAnalysis } from '@/lib/db/schema';
import FilterSection from './FilterSection';
import CommentTable from './CommentTable';
import StatisticsCard from './StatisticsCard';
import { getComments } from '@/lib/actions';

export default function CommentsDataProvider() {
  const [comments, setComments] = useState<CommentWithAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<string, unknown>>({});

  useEffect(() => {
    (async () => {
      try {
        const result = await getComments();
        if (result.success) {
          setComments(result.data || []);
        } else {
          setError(result.error || 'Unknown error');
        }
      } catch {
        setError('Failed to fetch comments');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Handle filter changes
  const handleFilterChange = (newFilters: Record<string, unknown>) => {
    setFilters(newFilters);
  };

  if (loading) {
    return <div>Loading comments...</div>;
  }
  if (error) {
    return <div className="alert alert-danger">Error loading comments: {error}</div>;
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