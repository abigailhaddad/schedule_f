// lib/db/index.ts
import { drizzle } from 'drizzle-orm/neon-serverless';
import { Client } from '@neondatabase/serverless';
import * as schema from './schema';

// Use server-side only environment variable
const DATABASE_URL = process.env.DATABASE_URL;

if (!DATABASE_URL) {
  throw new Error('DATABASE_URL is not defined');
}

// Create Drizzle instance. The client will be instantiated and managed by Drizzle.
export const db = drizzle(new Client(DATABASE_URL), { schema });

// Export types
export * from './schema';