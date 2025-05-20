// app/page.tsx
import CommentDataProvider from "@/components/CommentDataProvider";
import Navbar from "@/components/Navbar";

export default function Home() {
  return (
    <main className="min-h-screen">
      <Navbar />
      <div className="w-full px-4 py-4">
        <CommentDataProvider />
      </div>
    </main>
  );
}
