'use server';

export * from './comments';

// Re-export existing functions from the old actions.ts
import { cache } from '../cache/cache';
import { db } from '../db';
import { comments } from '../db/schema';
import { sql } from 'drizzle-orm';

/**
 * Initializes and tests database connection
 */
export async function initDatabase(): Promise<{ success: boolean, message: string, counts?: {comments: number} }> {
  try {
    // Test if we can connect by getting counts
    const result = await db.select({ count: sql<number>`count(*)` }).from(comments);
    
    return { 
      success: true, 
      message: "Database connection successful", 
      counts: {
        comments: result[0]?.count || 0
      }
    };
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error("Database connection error:", errorMessage);
    
    return { 
      success: false, 
      message: `Database connection failed: ${errorMessage}` 
    };
  }
}

/**
 * Clears all comment-related cache entries
 */
export async function clearCommentsCache(): Promise<void> {
  console.log("Clearing comments cache");
  cache.deletePattern(/^comment-/);
  cache.deletePattern(/^comments-/);
  cache.deletePattern(/^stats-/);
}