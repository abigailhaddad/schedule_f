import { Suspense } from "react";
import { Metadata } from "next";
import ServerCommentDataProvider from "@/components/ServerCommentDataProvider";
import Navbar from "@/components/Navbar";
import { datasetConfig } from "@/lib/config";
import { redirect } from "next/navigation";

// Disable caching in development if configured to do so
export const revalidate = 86400;

// Generate metadata
export const metadata: Metadata = {
  title: datasetConfig.title,
  description: 'Public Comments on "Schedule F" Regulation',
};

// Statically generate common page size combinations at build time
export async function generateStaticParams() {
  const commonPageSizes = [10, 25, 50, 100];
  const pagesToPreGenerate = [1, 2, 3]; // First 3 pages

  const params = [];

  // Generate first few pages for each common size
  for (const size of commonPageSizes) {
    for (const page of pagesToPreGenerate) {
      params.push({
        page: page.toString(),
        size: size.toString(),
      });
    }
  }

  // Optionally, add a few more specific high-traffic combinations
  // For example, if you know users often jump to page 5 with 50 items
  //   params.push({ page: '5', size: '50' });

  return params;
}

interface PageProps {
  params: Promise<{
    page: string;
    size: string;
  }>;
}

export default async function CommentPage({ params }: PageProps) {
  // Await params as required in Next.js 15
  const { page: pageParam, size: sizeParam } = await params;

  // Validate page and size params
  const page = parseInt(pageParam, 10);
  const size = parseInt(sizeParam, 10);

  // Log when this page is being rendered (only in dev)
  if (process.env.NODE_ENV === "development") {
    console.log(
      `Rendering page ${page} with size ${size} at ${new Date().toISOString()}`
    );
  }

  // Redirect to valid values if invalid
  if (isNaN(page) || page < 1 || isNaN(size) || size < 1) {
    // redirects to /page/1/size/10
    redirect(`/page/1/size/10`);
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="pt-20 pb-12">
        <div className="container mx-auto px-4 md:px-6">
          <Suspense
            fallback={<div className="text-center py-12">Loading Dashboard...</div>} >
            <ServerCommentDataProvider
              initialPage={page}
              initialPageSize={size}
            />
          </Suspense>

          {/* Optional: Show when page was last generated in development */}
          {process.env.NODE_ENV === "development" && (
            <div className="text-xs text-gray-500 text-center mt-4">
              Page will revalidate every {revalidate} seconds
              {process.env.LAST_DATA_UPDATE && (
                <>
                  {" "}
                  | Last data update:{" "}
                  {new Date(process.env.LAST_DATA_UPDATE).toLocaleString()}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
