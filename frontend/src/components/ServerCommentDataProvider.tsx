// components/ServerCommentDataProvider.tsx
'use client';

import { ServerDataState } from './states';
import { ServerDataContextProvider } from '@/contexts/ServerDataContext';

export default function ServerCommentDataProvider() {
  return (
    <ServerDataContextProvider>
      <ServerDataState />
    </ServerDataContextProvider>
  );
}