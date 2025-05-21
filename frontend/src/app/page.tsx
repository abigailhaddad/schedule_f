// app/page.tsx
import { Suspense } from 'react';
import ServerCommentDataProvider from "@/components/ServerCommentDataProvider";
import Navbar from "@/components/Navbar";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="pt-20 pb-12">
        <div className="container mx-auto px-4 md:px-6">
          <Suspense fallback={<div className="text-center py-12">Loading...</div>}>
            <ServerCommentDataProvider />
          </Suspense>
        </div>
      </div>
    </main>
  );
}