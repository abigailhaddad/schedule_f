// app/page.tsx
import { Suspense } from 'react';
import { Metadata } from 'next';
import ServerCommentDataProvider from "@/components/ServerCommentDataProvider";
import Navbar from "@/components/Navbar";
import { datasetConfig } from '@/lib/config';

// Set revalidation time based on data freshness
// export const revalidate = getRevalidateTime(); // Cannot be dynamic for segment config
export const revalidate = 86400; // 24 hours - static default revalidation period

// Generate metadata
export const metadata: Metadata = {
  title: datasetConfig.title,
  description: 'Public Comments on "Schedule F" Regulation',
};

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="pt-20 pb-12">
        <div className="container mx-auto px-4 md:px-6">
          <Suspense fallback={<div className="text-center py-12">Loading...</div>}>
            <ServerCommentDataProvider />
          </Suspense>
          
          {/* Optional: Show when page was last generated in development */}
          {process.env.NODE_ENV === 'development' && (
            <div className="text-xs text-gray-500 text-center mt-4">
              Page will revalidate every {revalidate} seconds
              {process.env.LAST_DATA_UPDATE && (
                <> | Last data update: {new Date(process.env.LAST_DATA_UPDATE).toLocaleString()}</>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}