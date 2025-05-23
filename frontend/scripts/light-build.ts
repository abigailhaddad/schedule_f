import { execSync } from 'child_process';

/**
 * Script to run a lighter build process
 * Run with: npm run build:light
 */

console.log('Starting light build process...');

// Set environment variables to skip non-essential steps
process.env.SKIP_STATIC_GENERATION = 'true';
process.env.NEXT_TELEMETRY_DISABLED = '1';
process.env.NEXT_MINIMAL_BUILD = 'true';

try {
  // Build step
  console.log('\nRunning Next.js build with minimal settings...');
  execSync('next build', { 
    env: { 
      ...process.env,
      NODE_ENV: 'production',
      NEXT_TELEMETRY_DISABLED: '1',
      SKIP_STATIC_GENERATION: 'true',
      NEXT_MINIMAL_BUILD: 'true'
    },
    stdio: 'inherit' 
  });
  
  console.log('\nLight build completed successfully!');
  process.exit(0);
} catch (error) {
  console.error('\nBuild failed:', error);
  process.exit(1);
} 