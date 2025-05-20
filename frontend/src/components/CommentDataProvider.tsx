// components/CommentsDataProvider.tsx
'use client';

import { useState, useEffect } from 'react';
import { Comment } from '@/lib/db/schema';
import { getAllComments, initDatabase } from '@/lib/actions';
import { LoadingState, ErrorState, DataState } from './states';
import { DataContextProvider } from '@/contexts/DataContext';

export default function CommentsDataProvider() {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dbStatus, setDbStatus] = useState<{success?: boolean, message?: string, counts?: {comments: number, analyses: number}} | null>(null);
  const [checkingDb, setCheckingDb] = useState(false);

  // Fetch all comments data
  useEffect(() => {
    (async () => {
      try {
        // Use getAllComments to fetch the full dataset
        const result = await getAllComments();
        
        if (result.success && result.data) {
          setComments(result.data);
          setLoading(false);
          setError(null);
          console.log("🔵 Client: All data loaded, count:", result.data.length);
        } else {
          setLoading(false);
          setError(result.error || "Failed to fetch comments");
          console.error("🔵 Client: Error fetching comments:", result.error);
        }
      } catch (err) {
        console.error("🔵 Client: Exception in getAllComments:", err);
        setLoading(false);
        setError("An unexpected error occurred");
      }
    })();
  }, []);

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

  // Wrap DataState with DataContextProvider
  return (
    <DataContextProvider 
      data={comments}
      initialLoading={false}
      initialError={null}
      searchFields={['comment', 'title', 'keyQuote', 'themes', 'rationale']}
    >
      <DataState />
    </DataContextProvider>
  );
}