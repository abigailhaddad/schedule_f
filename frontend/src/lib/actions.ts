// app/actions.ts
'use server'

import { db, connectDb } from '@/lib/db'
import { comments, analyses, CommentWithAnalysis, stanceEnum } from '@/lib/db/schema'
import { eq, desc, sql } from 'drizzle-orm'
import fs from 'fs/promises'

// Simple diagnostic function to test database connectivity
export async function initDatabase(): Promise<{ success: boolean, message: string, counts?: { comments: number, analyses: number } }> {
  try {
    // First, explicitly connect the client
    const connection = await connectDb();
    if (!connection.success) {
      throw new Error("Failed to connect to database: " + (connection.error ? String(connection.error) : "Unknown error"));
    }
    
    // Test if we can connect by getting counts
    const commentsCount = await db.select({ count: sql<number>`count(*)` }).from(comments);
    const analysesCount = await db.select({ count: sql<number>`count(*)` }).from(analyses);
    
    return { 
      success: true, 
      message: "Database connection successful", 
      counts: { 
        comments: commentsCount[0]?.count || 0, 
        analyses: analysesCount[0]?.count || 0 
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

// Fetch comments from database
export async function getComments(): Promise<{ success: boolean, data?: CommentWithAnalysis[], error?: string }> {
    try {
      // Explicitly connect to database before running queries
      const connection = await connectDb();
      if (!connection.success) {
        throw new Error("Failed to connect to database: " + (connection.error ? String(connection.error) : "Unknown error"));
      }
      
      const results = await db
        .select({
          // Select all fields from comments
          id: comments.id,
          title: comments.title,
          category: comments.category,
          agencyId: comments.agencyId,
          comment: comments.comment,
          originalComment: comments.originalComment,
          hasAttachments: comments.hasAttachments,
          link: comments.link,
          createdAt: comments.createdAt,
          // Select all fields from analyses, they will be null if no match
          analysisId: analyses.id,
          analysisCommentId: analyses.commentId, // Need this for structuring
          analysisStance: analyses.stance,
          analysisKeyQuote: analyses.keyQuote,
          analysisRationale: analyses.rationale,
          analysisThemes: analyses.themes,
          analysisCreatedAt: analyses.createdAt,
        })
        .from(comments)
        .leftJoin(analyses, eq(comments.id, analyses.commentId))
        .orderBy(desc(comments.createdAt)); // Order by comment creation date

      const commentsWithAnalyses: CommentWithAnalysis[] = results.map(r => ({
        // Comment fields
        id: r.id!,
        title: r.title,
        category: r.category,
        agencyId: r.agencyId,
        comment: r.comment,
        originalComment: r.originalComment,
        hasAttachments: r.hasAttachments ?? false, // Provide default for boolean
        link: r.link,
        createdAt: r.createdAt,
        // Nested analysis object
        analysis: r.analysisId // If analysisId is null, there was no joined analysis
          ? {
              id: r.analysisId!, // analysisId is from analyses.id, which is serial, so it's a number
              commentId: r.analysisCommentId!, // This would be the same as r.id
              stance: r.analysisStance as typeof stanceEnum.enumValues[number] | null, // Cast to enum type or null
              keyQuote: r.analysisKeyQuote,
              rationale: r.analysisRationale,
              themes: r.analysisThemes,
              createdAt: r.analysisCreatedAt,
            }
          : null,
      }));
      
      return { success: true, data: commentsWithAnalyses };
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
      // Insert comment
      await db.insert(comments).values({
        id: item.id,
        title: item.title || '',
        category: item.category || '',
        agencyId: item.agencyId || '',
        comment: item.comment || '',
        originalComment: item.originalComment || '',
        hasAttachments: item.hasAttachments || false,
        link: item.link || '',
      }).onConflictDoUpdate({
        target: comments.id,
        set: {
          title: item.title || '',
          category: item.category || '',
          agencyId: item.agencyId || '',
          comment: item.comment || '',
          originalComment: item.originalComment || '',
          hasAttachments: item.hasAttachments || false,
          link: item.link || '',
        }
      })
      
      // Insert analysis if it exists
      if (item.analysis) {
        await db.insert(analyses).values({
          commentId: item.id,
          stance: item.analysis.stance || 'Neutral/Unclear',
          keyQuote: item.analysis.keyQuote || '',
          rationale: item.analysis.rationale || '',
          themes: item.analysis.themes || '',
        }).onConflictDoUpdate({
          target: [analyses.commentId],
          set: {
            stance: item.analysis.stance || 'Neutral/Unclear',
            keyQuote: item.analysis.keyQuote || '',
            rationale: item.analysis.rationale || '',
            themes: item.analysis.themes || '',
          }
        })
      }
      
      imported++
    }
    
    return { success: true, imported }
  } catch (error) {
    console.error('Error importing data:', error)
    return { success: false, error: 'Failed to import data' }
  }
}

// Run the Python script to fetch and analyze comments
export async function processComments(documentId: string) {
  try {
    // This is where you'd trigger the Python script execution
    // For example, using Node.js child_process to run the Python script
    // This is a simplified placeholder
    
    // Placeholder for now - in production, use exec or spawn to run Python
    return { success: true, message: `Started processing comments for ${documentId}` }
  } catch (error) {
    console.error('Error processing comments:', error)
    return { success: false, error: 'Failed to process comments' }
  }
}