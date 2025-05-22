// components/ServerCommentDataProvider.tsx
'use client';

import { ServerDataState } from './states';
import { ServerDataContextProvider } from '@/contexts/ServerDataContext';
import { Comment } from '@/lib/db/schema';

interface InitialData {
  comments?: Comment[];
  total?: number;
  stats?: {
    total: number;
    for: number;
    against: number;
    neutral: number;
  };
  error?: string | null;
}

interface ServerCommentDataProviderProps {
  initialData?: InitialData;
}

export default function ServerCommentDataProvider({ initialData }: ServerCommentDataProviderProps) {
  return (
    <ServerDataContextProvider initialData={initialData}>
      <ServerDataState />
    </ServerDataContextProvider>
  );
}