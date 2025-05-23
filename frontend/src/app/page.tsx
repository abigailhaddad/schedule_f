// app/page.tsx
import { Suspense } from 'react';
import ServerCommentDataProvider from "@/components/ServerCommentDataProvider";
import Navbar from "@/components/Navbar";
import { getPaginatedComments, getCommentStatistics } from '@/lib/actions/comments';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Schedule F Analysis',
  description: 'Public Comments on "Schedule F" Regulation',
};

// Force static generation with daily revalidation
export const dynamic = 'force-static';
export const revalidate = 86400; // 24 hours

// Skip static params generation to make build faster
// We'll generate pages on-demand instead

// Fetch minimal initial data on the server
async function getInitialData() {
  // Reduced page size for faster initial load
  const pageSize = 10;

  try {
    // Get comments and stats separately to avoid timing out
    const commentsResponse = await getPaginatedComments({
      page: 1,
      pageSize,
      sort: { column: 'createdAt', direction: 'desc' }
    });
    
    const statsResponse = await getCommentStatistics({});
    
    return {
      comments: commentsResponse.success ? commentsResponse.data : [],
      total: commentsResponse.success ? commentsResponse.total : 0,
      stats: statsResponse.success ? statsResponse.stats : {
        total: 0,
        for: 0,
        against: 0,
        neutral: 0
      },
      error: !commentsResponse.success ? commentsResponse.error : null
    };
  } catch (error) {
    console.error('Error fetching initial data:', error);
    // Return empty data on error to avoid build failures
    return {
      comments: [],
      total: 0,
      stats: {
        total: 0,
        for: 0,
        against: 0,
        neutral: 0
      },
      error: 'Failed to fetch initial data'
    };
  }
}

export default async function Home() {
  // Fetch initial data on the server
  const initialData = await getInitialData();

  return (
    <main className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="pt-20 pb-12">
        <div className="container mx-auto px-4 md:px-6">
          <Suspense fallback={
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading comments...</p>
            </div>
          }>
            <ServerCommentDataProvider initialData={initialData} />
          </Suspense>
        </div>
      </div>
    </main>
  );
}