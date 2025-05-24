// lib/db/schema.ts
import { pgTable, text, timestamp, varchar, boolean, pgEnum } from 'drizzle-orm/pg-core';

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
  // Analysis fields integrated directly into comments table
  stance: stanceEnum('stance'),
  keyQuote: text('key_quote'),
  rationale: text('rationale'),
  themes: text('themes'),
  postedDate: timestamp('posted_date'),
  createdAt: timestamp('created_at').defaultNow()
});

// Type inference
export type Comment = typeof comments.$inferSelect;
export type NewComment = typeof comments.$inferInsert;