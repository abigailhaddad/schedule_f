// app/page.tsx
import CommentDataProvider from "@/components/CommentDataProvider";
import Navbar from "@/components/Navbar";

export default function Home() {
  return (
    <main className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="pt-20 pb-12">
        <div className="container mx-auto px-4 md:px-6">
          <CommentDataProvider />
        </div>
      </div>
    </main>
  );
}
