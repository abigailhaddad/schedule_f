// src/lib/actions.ts
'use server'

import { db, connectDb } from '@/lib/db'
import { comments, Comment } from '@/lib/db/schema'
import { eq, desc, sql } from 'drizzle-orm'
import { cache, getCachedData } from './cache'

// src/lib/actions.ts
export async function getComments(
  page: number = 1, 
  pageSize: number = 10
): Promise<{ success: boolean, data?: Comment[], total?: number, error?: string }> {
  const cacheKey = `comments-page-${page}-size-${pageSize}`;
  
  return getCachedData(
    cacheKey,
    async () => {
      try {
        const connection = await connectDb();
        if (!connection.success) {
          throw new Error("Failed to connect to database");
        }
        
        // Get total count
        const countResult = await db
          .select({ count: sql<number>`count(*)` })
          .from(comments);
        
        const total = countResult[0]?.count || 0;
        
        // Calculate offset
        const offset = (page - 1) * pageSize;
        
        // Get paginated results
        const results = await db
          .select()
          .from(comments)
          .orderBy(desc(comments.createdAt))
          .limit(pageSize)
          .offset(offset);

        return { 
          success: true, 
          data: results,
          total
        };
      } catch (error: unknown) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error("Error fetching comments:", errorMessage);
        return { success: false, error: `Failed to fetch comments: ${errorMessage}` };
      }
    }
  );
}
// Get all comments with cache
export async function getAllComments(): Promise<{ success: boolean, data?: Comment[], error?: string }> {
  const cacheKey = 'all-comments';
  
  return getCachedData(
    cacheKey,
    async () => {
      try {
        // Explicitly connect to database before running queries
        const connection = await connectDb();
        if (!connection.success) {
          throw new Error("Failed to connect to database");
        }
        
        const results = await db
          .select()
          .from(comments)
          .orderBy(desc(comments.createdAt));

        return { success: true, data: results };
      } catch (error: unknown) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error("Error fetching comments:", errorMessage);
        return { success: false, error: `Failed to fetch comments: ${errorMessage}` };
      }
    }
  );
}

// Get a comment by ID with cache
export async function getCommentById(id: string): Promise<{ success: boolean, data?: Comment, error?: string }> {
  const cacheKey = `comment-${id}`;
  
  return getCachedData(
    cacheKey,
    async () => {
      try {
        const connection = await connectDb();
        if (!connection.success) {
          throw new Error("Failed to connect to database");
        }
        
        const result = await db
          .select()
          .from(comments)
          .where(eq(comments.id, id))
          .limit(1);

        if (result.length === 0) {
          return { success: false, error: 'Comment not found' };
        }
        
        return { success: true, data: result[0] };
      } catch (error: unknown) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error("Error fetching comment by ID:", errorMessage);
        return { success: false, error: `Failed to fetch comment: ${errorMessage}` };
      }
    }
  );
}

// Add a function to clear cache when needed
export async function clearCommentsCache(): Promise<void> {
  console.log("Clearing comments cache");
  // Clear all comment-related cache entries
  cache.deletePattern(/^comment-/);
  cache.delete('all-comments');
}

// Simple diagnostic function to test database connectivity
export async function initDatabase(): Promise<{ success: boolean, message: string, count?: number }> {
  try {
    // First, explicitly connect the client
    const connection = await connectDb();
    if (!connection.success) {
      throw new Error("Failed to connect to database: " + (connection.error ? String(connection.error) : "Unknown error"));
    }
    
    // Test if we can connect by getting counts
    const result = await db.select({ count: sql<number>`count(*)` }).from(comments);
    
    return { 
      success: true, 
      message: "Database connection successful", 
      count: result[0]?.count || 0
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
