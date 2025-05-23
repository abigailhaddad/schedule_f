// scripts/warm-cache.ts
import { warmCache } from '../src/lib/actions/comments';

/**
 * Simple script to warm the cache after build
 * Run with: npm run warm-cache
 */
async function main() {
  console.log('Starting cache warming process...');
  try {
    await warmCache();
    console.log('Cache warming completed successfully');
    process.exit(0);
  } catch (error) {
    console.error('Error during cache warming:', error);
    process.exit(1);
  }
}

main(); 