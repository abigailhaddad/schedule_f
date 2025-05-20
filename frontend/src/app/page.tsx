// app/page.tsx
import CommentsDataProvider from '@/components/CommentDataProvider';
import Navbar from '@/components/Navbar';
import { ThemeProvider } from '@/components/ThemeProvider';

// Keep as Server Component for better SEO and performance
export default function Home() {
  return (
    <ThemeProvider>
      <Navbar />
      <div className="container-fluid py-4">
        <CommentsDataProvider />
      </div>
    </ThemeProvider>
  );
}