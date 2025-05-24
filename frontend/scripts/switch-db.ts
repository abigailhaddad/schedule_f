// scripts/switch-db.ts
import fs from 'fs';
import path from 'path';
import { config } from 'dotenv';

// Load current environment
config();

const envPath = path.resolve(process.cwd(), '.env');

// Get the target environment from command line
const targetEnv = process.argv[2]?.toLowerCase();

if (targetEnv !== 'dev' && targetEnv !== 'prod') {
  console.error('❌ Please specify "dev" or "prod" as an argument');
  console.log('Usage: npm run db:switch dev   OR   npm run db:switch prod');
  process.exit(1);
}

// Read the current .env file
let envContent = '';
try {
  envContent = fs.readFileSync(envPath, 'utf8');
} catch (error) {
  console.error('❌ Could not read .env file:', error);
  process.exit(1);
}

// Update the DB_ENV line
const updatedContent = envContent.replace(
  /^DB_ENV=.*/m,
  `DB_ENV=${targetEnv}`
);

// Write back to .env
try {
  fs.writeFileSync(envPath, updatedContent);
  console.log(`✅ Switched to ${targetEnv.toUpperCase()} database`);
  console.log(`🗄️  DB_ENV is now set to: ${targetEnv}`);
  
  // Show a warning for production
  if (targetEnv === 'prod') {
    console.warn('\n⚠️  WARNING: You are now using the PRODUCTION database!');
    console.warn('Be careful with any operations that modify data.\n');
  }
} catch (error) {
  console.error('❌ Could not update .env file:', error);
  process.exit(1);
}