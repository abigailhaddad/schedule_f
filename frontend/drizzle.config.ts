// drizzle.config.ts
import { defineConfig } from 'drizzle-kit';
import dotenv from 'dotenv';

dotenv.config(); // This will load from .env by default

export default defineConfig({
  schema: './src/lib/db/schema.ts',
  out: './drizzle',
  driver: 'pg',
  dbCredentials: {
    connectionString: process.env.DATABASE_URL!
  }
});