// lib/db/index.ts
// import 'server-only'; // This ensures this file can only be imported server-side

import { drizzle } from 'drizzle-orm/neon-serverless';
import { Client } from '@neondatabase/serverless';
import * as schema from './schema';
import { dbConfig } from './config';

// Use the database URL from our config
const DATABASE_URL = dbConfig.url;

if (!DATABASE_URL) {
  throw new Error('DATABASE_URL is not defined');
}

// Log database environment in development
if (process.env.NODE_ENV === 'development') {
  console.log(`Database: ${dbConfig.environment} environment`);
}

// Create client instance but don't connect yet
const client = new Client(DATABASE_URL);

// Promise to track connection status
let connectionPromise: Promise<{ success: boolean; error?: unknown }> | null = null;

// Create Drizzle instance with the client
export const db = drizzle(client, { schema });

// Initialize database connection - must be called before executing queries
export const connectDb = async () => {
  // If we're already connecting or connected, return the existing promise
  if (connectionPromise) {
    return connectionPromise;
  }

  // Create a new connection promise
  connectionPromise = (async () => {
    try {
      // Check if the client is already connected
      // The Neon client doesn't expose a direct way to check connection status,
      // so we'll rely on the connect() method to handle it properly
      await client.connect();
      return { success: true };
    } catch (error: unknown) {
      // If error is about already being connected, that's fine
      const errorMessage = error instanceof Error ? error.message : String(error);
      if (errorMessage.includes('already been connected')) {
        return { success: true };
      }
      console.error("Database connection failed:", error);
      // Reset the promise on failure so we can retry
      connectionPromise = null;
      return { success: false, error };
    }
  })();

  return connectionPromise;
};

// Export the config for use in other files
export { dbConfig };

// Export types
export * from './schema';