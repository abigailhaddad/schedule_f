// drizzle.config.ts
import { defineConfig } from 'drizzle-kit';
import { config } from 'dotenv';
import path from 'path';

// Load environment variables
config({ path: path.resolve(process.cwd(), '.env') });

// Get the database environment
const dbEnv = process.env.DB_ENV?.toLowerCase() || 'dev';

// Get the appropriate database URL
const getDatabaseUrl = (): string => {
  const dbUrl = dbEnv === 'prod' 
    ? process.env.DATABASE_URL_PROD 
    : process.env.DATABASE_URL_DEV;
  
  if (!dbUrl) {
    throw new Error(`DATABASE_URL_${dbEnv.toUpperCase()} is not defined in environment variables`);
  }
  
  console.log(`🗄️  Drizzle using ${dbEnv.toUpperCase()} database`);
  
  return dbUrl;
};

export default defineConfig({
  schema: './src/lib/db/schema.ts',
  out: './drizzle',
  dialect: 'postgresql',
  dbCredentials: {
    url: getDatabaseUrl()
  }
});