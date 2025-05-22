// app/comment/[id]/page.tsx
import { getCommentById, getAllCommentIds } from '@/lib/actions/comments';
import Navbar from '@/components/Navbar';
import CommentDetail from '@/components/CommentDetail';
import BackButton from '@/components/BackButton';
import { notFound } from 'next/navigation';
import { Metadata } from 'next';

interface PageProps {
  params: Promise<{
    id: string;
  }>;
  searchParams: Promise<{
    returnUrl?: string;
  }>;
}

// Revalidate every 24 hours
export const revalidate = 86400;

// Dynamic metadata generation
export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const result = await getCommentById(id);
  
  if (!result.success || !result.data) {
    return {
      title: 'Comment Not Found',
    };
  }
  
  return {
    title: result.data.title || 'Comment Detail',
    description: result.data.keyQuote || result.data.comment?.substring(0, 160),
  };
}

// Pre-generate static pages for all comments at build time
export async function generateStaticParams() {
  // Only generate top 100 most recent comments at build time
  // Others will be generated on-demand with ISR
  const ids = await getAllCommentIds(100);
  
  return ids.map((id) => ({
    id: id,
  }));
}

export default async function CommentPage({ params, searchParams }: PageProps) {
  const { id } = await params;
  const { returnUrl } = await searchParams;
  const lastUrl = returnUrl ? decodeURIComponent(returnUrl) : '/';
  
  // Fetch comment data
  const result = await getCommentById(id);
  
  if (!result.success || !result.data) {
    notFound();
  }
  
  return (
    <main className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="pt-28 pb-12">
        <div className="container mx-auto px-4 md:px-6">
          <BackButton returnUrl={lastUrl} />
          <CommentDetail comment={result.data} />
        </div>
      </div>
    </main>
  );
}