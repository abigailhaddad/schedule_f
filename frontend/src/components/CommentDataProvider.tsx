// components/CommentsDataProvider.tsx
'use client';

import { useState, useEffect } from 'react';
import { CommentWithAnalysis } from '@/lib/db/schema';
import { getComments, initDatabase } from '@/lib/actions';
import { LoadingState, ErrorState, DataState } from './states';

export default function CommentsDataProvider() {
  const [comments, setComments] = useState<CommentWithAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<string, unknown>>({});
  const [dbStatus, setDbStatus] = useState<{success?: boolean, message?: string, counts?: {comments: number, analyses: number}} | null>(null);
  const [checkingDb, setCheckingDb] = useState(false);

  // Fetch comments data
  useEffect(() => {
    console.log("🔵 Client: useEffect triggered, starting data fetch");
    
    (async () => {
      try {
        console.log("🔵 Client: Calling getComments server action");
        const result = await getComments();
        console.log("🔵 Client: Data fetched, success:", result.success);
        
        if (result.success && result.data) {
          setComments(result.data);
          setLoading(false);
          setError(null);
          console.log("🔵 Client: Data loaded, count:", result.data.length);
        } else {
          setLoading(false);
          setError(result.error || "Failed to fetch comments");
          console.error("🔵 Client: Error fetching comments:", result.error);
        }
      } catch (err) {
        console.error("🔵 Client: Exception in getComments:", err);
        setLoading(false);
        setError("An unexpected error occurred");
      }
    })();
  }, []);

  // Handle filter changes from FilterSection
  const handleFilterChange = (newFilters: Record<string, unknown>) => {
    setFilters(newFilters);
  };

  // Handle database check
  const checkDatabase = async () => {
    setCheckingDb(true);
    try {
      const result = await initDatabase();
      setDbStatus(result);
    } catch (err) {
      setDbStatus({ success: false, message: String(err) });
    } finally {
      setCheckingDb(false);
    }
  };

  // Render appropriate state
  if (loading) {
    return (
      <LoadingState 
        checkDatabase={checkDatabase}
        checkingDb={checkingDb}
        dbStatus={dbStatus}
      />
    );
  }

  if (error) {
    return (
      <ErrorState 
        error={error}
        checkDatabase={checkDatabase}
        checkingDb={checkingDb}
        dbStatus={dbStatus}
      />
    );
  }

  return (
    <DataState 
      comments={comments}
      filters={filters}
      onFilterChange={handleFilterChange}
    />
  );
}