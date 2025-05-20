'use client';

import { useRouter } from 'next/navigation';

interface BackButtonProps {
  returnUrl: string;
}

export default function BackButton({ returnUrl }: BackButtonProps) {
  const router = useRouter();

  const handleBack = () => {
    router.push(returnUrl);
  };

  return (
    <button
      onClick={handleBack}
      className="mb-4 inline-flex items-center px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-800 rounded-md transition-colors"
    >
      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
      </svg>
      Back to Results
    </button>
  );
} 