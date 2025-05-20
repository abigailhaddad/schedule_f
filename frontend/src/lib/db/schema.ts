// lib/db/schema.ts
import { pgTable, serial, text, timestamp, varchar, boolean, pgEnum } from 'drizzle-orm/pg-core';

export const stanceEnum = pgEnum('stance', ['For', 'Against', 'Neutral/Unclear']);

export const comments = pgTable('comments', {
  id: varchar('id').primaryKey(),
  title: text('title'),
  category: varchar('category'),
  agencyId: varchar('agency_id'),
  comment: text('comment'),
  originalComment: text('original_comment'),
  hasAttachments: boolean('has_attachments').default(false),
  link: text('link'),
  createdAt: timestamp('created_at').defaultNow()
});

export const analyses = pgTable('analyses', {
  id: serial('id').primaryKey(),
  commentId: varchar('comment_id').references(() => comments.id),
  stance: stanceEnum('stance'),
  keyQuote: text('key_quote'),
  rationale: text('rationale'),
  themes: text('themes'),
  createdAt: timestamp('created_at').defaultNow()
});

// Type inference but without the circular references
export type Comment = typeof comments.$inferSelect;
export type NewComment = typeof comments.$inferInsert;
export type Analysis = typeof analyses.$inferSelect;
export type NewAnalysis = typeof analyses.$inferInsert;

// Type for joined data (flattened to avoid circular references)
export type CommentWithAnalysis = Comment & {
  analysis: Analysis | null;
};