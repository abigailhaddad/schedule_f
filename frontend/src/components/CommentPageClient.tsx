'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getCommentById } from '@/lib/actions';
import { CommentWithAnalysis } from '@/lib/db/schema';
import Navbar from '@/components/Navbar';
import CommentDetail from '@/components/CommentDetail';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

interface CommentPageClientProps {
  id: string;
}

export default function CommentPageClient({ id }: CommentPageClientProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const returnUrl = searchParams.get('returnUrl') || '/';
  
  const [comment, setComment] = useState<CommentWithAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadComment() {
      try {
        const result = await getCommentById(id);
        if (result.success && result.data) {
          setComment(result.data);
        } else {
          setError(result.error || 'Failed to load comment');
        }
      } catch (err) {
        console.error("Error loading comment:", err);
        setError('An unexpected error occurred');
      } finally {
        setLoading(false);
      }
    }

    loadComment();
  }, [id]);

  const handleBack = () => {
    router.push(returnUrl);
  };

  return (
    <main className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="pt-20 pb-12">
        <div className="container mx-auto px-4 md:px-6">
          <button
            onClick={handleBack}
            className="mb-4 inline-flex items-center px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-md transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Results
          </button>

          {loading ? (
            <div className="flex justify-center items-center h-64">
              <LoadingSpinner size="large" />
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative" role="alert">
              <strong className="font-bold">Error: </strong>
              <span className="block sm:inline">{error}</span>
            </div>
          ) : comment ? (
            <CommentDetail comment={comment} />
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded relative" role="alert">
              <strong className="font-bold">Not Found: </strong>
              <span className="block sm:inline">The requested comment could not be found.</span>
            </div>
          )}
        </div>
      </div>
    </main>
  );
} 