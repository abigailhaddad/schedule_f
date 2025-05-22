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

// Revalidate every 24 hours (86400 seconds)
export const revalidate = 86400;

// Generate static params for common filter combinations
export async function generateStaticParams() {
  // Pre-generate pages for common filter combinations
  return [
    { params: {} }, // Default page
    { params: { filter_stance: 'For' } },
    { params: { filter_stance: 'Against' } },
    { params: { filter_stance: 'Neutral/Unclear' } },
  ];
}

// Fetch initial data on the server
async function getInitialData() {
  const [commentsResponse, statsResponse] = await Promise.all([
    getPaginatedComments({
      page: 1,
      pageSize: 25, // Larger initial page size
      sort: { column: 'createdAt', direction: 'desc' }
    }),
    getCommentStatistics({})
  ]);

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