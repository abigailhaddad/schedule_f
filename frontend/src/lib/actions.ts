// app/actions.ts
'use server'

import { db, connectDb } from '@/lib/db'
import { comments, Comment } from '@/lib/db/schema'
import { eq, desc, sql } from 'drizzle-orm'
import fs from 'fs/promises'

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

// Fetch comments from database
export async function getComments(): Promise<{ success: boolean, data?: Comment[], error?: string }> {
  try {
    // Explicitly connect to database before running queries
    const connection = await connectDb();
    if (!connection.success) {
      throw new Error("Failed to connect to database: " + (connection.error ? String(connection.error) : "Unknown error"));
    }
    
    const results = await db
      .select()
      .from(comments)
      .orderBy(desc(comments.createdAt));

    return { success: true, data: results };
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error("Error fetching comments:", errorMessage);
    return { success: false, error: `Failed to fetch comments: ${errorMessage || 'Unknown database error'}` };
  }
}

// Import data from JSON file into database
export async function importData(filePath: string) {
  try {
    // Read the JSON file
    const fileContent = await fs.readFile(filePath, 'utf8')
    const data = JSON.parse(fileContent)
    
    let imported = 0
    
    // Process in batches
    for (const item of data) {
      // Map the fields from the JSON structure to our database structure
      await db.insert(comments).values({
        id: item.id,
        title: item.title || '',
        category: item.category || '',
        agencyId: item.agencyId || '',
        comment: item.comment || '',
        originalComment: item.original_comment || item.originalComment || '',
        hasAttachments: item.has_attachments || item.hasAttachments || false,
        link: item.link || '',
        // Analysis fields now directly in comments table
        stance: item.stance || null,
        keyQuote: item.key_quote || item.keyQuote || '',
        rationale: item.rationale || '',
        themes: item.themes || '',
      }).onConflictDoUpdate({
        target: comments.id,
        set: {
          title: item.title || '',
          category: item.category || '',
          agencyId: item.agencyId || '',
          comment: item.comment || '',
          originalComment: item.original_comment || item.originalComment || '',
          hasAttachments: item.has_attachments || item.hasAttachments || false,
          link: item.link || '',
          stance: item.stance || null,
          keyQuote: item.key_quote || item.keyQuote || '',
          rationale: item.rationale || '',
          themes: item.themes || '',
        }
      })
      
      imported++
    }
    
    return { success: true, imported }
  } catch (error) {
    console.error('Error importing data:', error)
    return { success: false, error: 'Failed to import data' }
  }
}

// Fetch a single comment by ID
export async function getCommentById(id: string): Promise<{ success: boolean, data?: Comment, error?: string }> {
  try {
    // Explicitly connect to database before running queries
    const connection = await connectDb();
    if (!connection.success) {
      throw new Error("Failed to connect to database: " + (connection.error ? String(connection.error) : "Unknown error"));
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
    return { success: false, error: `Failed to fetch comment: ${errorMessage || 'Unknown database error'}` };
  }
}