// lib/db/index.ts
import { drizzle } from 'drizzle-orm/neon-http';
import { neon } from '@neondatabase/serverless';
import * as schema from './schema';

// Create a Neon connection
const sql = neon(process.env.DATABASE_URL!);

// Create a Drizzle client
export const db = drizzle(sql, { schema });

// Export type-safe queries and schemas
export * from './schema';