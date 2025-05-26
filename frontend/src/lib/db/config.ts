// src/lib/db/config.ts
// import 'server-only'; // This ensures this file can only be imported server-side

import { config } from 'dotenv';
import path from 'path';

// Load environment variables
const envPath = process.env.ENV_PATH || path.resolve(process.cwd(), '.env');
config({ path: envPath });

// Database environment type
type DbEnvironment = 'dev' | 'prod';

// Get the database environment
const getDbEnvironment = (): DbEnvironment => {
  const dbEnv = process.env.DB_ENV?.toLowerCase();

  // Validate the environment
  if (dbEnv !== 'dev' && dbEnv !== 'prod') {
    console.warn(`Invalid DB_ENV: "${dbEnv}". Defaulting to "dev".`);
    return 'dev';
  }

  return dbEnv;
};

// Get the appropriate database URL
const getDatabaseUrl = (): string => {
  const dbEnv = getDbEnvironment();

  // Get the specific database URL
  const dbUrl = dbEnv === 'prod'
    ? process.env.DATABASE_URL_PROD
    : process.env.DATABASE_URL_DEV;

  if (!dbUrl) {
    throw new Error(`DATABASE_URL_${dbEnv.toUpperCase()} is not defined in environment variables`);
  }

  // Log which database we're using (but not the URL for security)
  // Only log on server-side
  if (typeof window === 'undefined') {
    if (process.env.NODE_ENV === 'development') {

      console.log(`🗄️  Using ${dbEnv.toUpperCase()} database`);
    }
  }

  return dbUrl;
};

// Export the configuration
const getDbConfig = () => {
  const dbUrl = getDatabaseUrl();
  const dbEnv = getDbEnvironment();

  return { url: dbUrl, isProd: dbEnv === 'prod', isDev: dbEnv === 'dev' };
};

export const dbConfig = getDbConfig();