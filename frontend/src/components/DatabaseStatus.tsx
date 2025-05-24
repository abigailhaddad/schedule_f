// src/components/DatabaseStatus.tsx
import { dbConfig } from '@/lib/db/config';

export default function DatabaseStatus() {
  // This is a server component, so it can access server-only modules
  
  if (process.env.NODE_ENV !== 'development') {
    return null;
  }
  
  return (
    <div className={`fixed bottom-4 right-4 px-3 py-1 rounded text-white text-sm z-50 ${
      dbConfig.isProd ? 'bg-red-600' : 'bg-green-600'
    }`}>
      DB: {dbConfig.environment.toUpperCase()}
    </div>
  );
}