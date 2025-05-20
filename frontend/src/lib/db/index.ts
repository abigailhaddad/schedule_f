// lib/db/index.ts
import { drizzle } from 'drizzle-orm/neon-serverless';
import { Client } from '@neondatabase/serverless';
import * as schema from './schema';

// Use server-side only environment variable
const DATABASE_URL = process.env.DATABASE_URL;

if (!DATABASE_URL) {
  throw new Error('DATABASE_URL is not defined');
}

// Create client instance but don't connect yet
const client = new Client(DATABASE_URL);

// Flag to track connection status
let isConnected = false;

// Create Drizzle instance with the client
export const db = drizzle(client, { schema });

// Initialize database connection - must be called before executing queries
export const connectDb = async () => {
  try {
    // Check if already connected to avoid reconnection
    if (isConnected) {
      return { success: true };
    }
    
    await client.connect();
    isConnected = true;
    return { success: true };
  } catch (error) {
    console.error("Database connection failed:", error);
    return { success: false, error };
  }
};

// Export types
export * from './schema';