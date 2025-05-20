import { getCommentById } from '@/lib/actions';
import Navbar from '@/components/Navbar';
import CommentDetail from '@/components/CommentDetail';
import BackButton from '@/components/BackButton';

interface PageProps {
  params: Promise<{
    id: string;
  }>;
  searchParams: Promise<{
    returnUrl?: string;
  }>;
}

export default async function CommentPage({ params, searchParams }: PageProps) {
  const { id }  = await params;
  const { returnUrl } = await searchParams;
  const lastUrl = returnUrl ? decodeURIComponent(returnUrl) : '/';
  
  // Server-side data fetching
  const result = await getCommentById(id);
  
  return (
    <main className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="pt-20 pb-12">
        <div className="container mx-auto px-4 md:px-6">
          <BackButton returnUrl={lastUrl} />

          {!result.success || !result.data ? (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded relative" role="alert">
              <strong className="font-bold">Error: </strong>
              <span className="block sm:inline">{result.error || 'Failed to load comment'}</span>
            </div>
          ) : (
            <CommentDetail comment={result.data} />
          )}
        </div>
      </div>
    </main>
  );
} 