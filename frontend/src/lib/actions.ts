// app/actions.ts
'use server'

import { db } from '@/lib/db'
import { comments, analyses, CommentWithAnalysis, Analysis } from '@/lib/db/schema'
import fs from 'fs/promises'

// Fetch comments from database
export async function getComments(): Promise<{ success: boolean, data?: CommentWithAnalysis[], error?: string }> {
    try {
      // First get all comments
      const commentsList = await db.select().from(comments);
      
      // Then get all analyses
      const analysesList = await db.select().from(analyses);
      
      // Create a map of analyses by commentId for quick lookup
      const analysesMap = new Map<string, Analysis>();
      for (const analysis of analysesList) {
        if (analysis.commentId) {
          analysesMap.set(analysis.commentId, analysis);
        }
      }
      
      // Join them manually (avoiding Drizzle's relations which can cause serialization issues)
      const commentsWithAnalyses: CommentWithAnalysis[] = commentsList.map(comment => {
        const analysis = analysesMap.get(comment.id) || null;
        return {
          ...comment,
          analysis
        };
      });
      
      return { success: true, data: commentsWithAnalyses };
    } catch (error) {
      console.error('Error fetching comments:', error);
      return { success: false, error: 'Failed to fetch comments' };
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