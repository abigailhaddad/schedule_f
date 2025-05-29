"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.comments = exports.lookupTable = exports.stanceEnum = void 0;
// lib/db/schema.ts
var pg_core_1 = require("drizzle-orm/pg-core");
exports.stanceEnum = (0, pg_core_1.pgEnum)('stance', ['For', 'Against', 'Neutral/Unclear']);
// Lookup table for grouping duplicate comments
exports.lookupTable = (0, pg_core_1.pgTable)('lookup_table', {
    lookupId: (0, pg_core_1.varchar)('lookup_id').primaryKey(),
    truncatedText: (0, pg_core_1.text)('truncated_text'),
    textSource: (0, pg_core_1.varchar)('text_source'),
    commentIds: (0, pg_core_1.json)('comment_ids').$type().notNull(),
    commentCount: (0, pg_core_1.integer)('comment_count').notNull(),
    stance: (0, exports.stanceEnum)('stance'),
    keyQuote: (0, pg_core_1.text)('key_quote'),
    rationale: (0, pg_core_1.text)('rationale'),
    themes: (0, pg_core_1.text)('themes'),
    corrected: (0, pg_core_1.boolean)('corrected').default(false),
    clusterId: (0, pg_core_1.text)('cluster_id'),
    pcaX: (0, pg_core_1.doublePrecision)('pca_x'),
    pcaY: (0, pg_core_1.doublePrecision)('pca_y'),
    createdAt: (0, pg_core_1.timestamp)('created_at').defaultNow().notNull()
});
exports.comments = (0, pg_core_1.pgTable)('comments', {
    id: (0, pg_core_1.varchar)('id').primaryKey(),
    title: (0, pg_core_1.text)('title'),
    category: (0, pg_core_1.varchar)('category'),
    agencyId: (0, pg_core_1.varchar)('agency_id'),
    comment: (0, pg_core_1.text)('comment'),
    // originalComment removed - not needed
    hasAttachments: (0, pg_core_1.boolean)('has_attachments').default(false),
    link: (0, pg_core_1.text)('link'),
    postedDate: (0, pg_core_1.timestamp)('posted_date'),
    receivedDate: (0, pg_core_1.timestamp)('received_date'),
    // Link to lookup table
    lookupId: (0, pg_core_1.varchar)('lookup_id').references(function () { return exports.lookupTable.lookupId; }),
    // These fields are now denormalized from lookup table for performance
    textSource: (0, pg_core_1.varchar)('text_source'),
    commentCount: (0, pg_core_1.integer)('comment_count').default(1),
    stance: (0, exports.stanceEnum)('stance'),
    keyQuote: (0, pg_core_1.text)('key_quote'),
    rationale: (0, pg_core_1.text)('rationale'),
    themes: (0, pg_core_1.text)('themes'),
    corrected: (0, pg_core_1.boolean)('corrected').default(false),
    clusterId: (0, pg_core_1.text)('cluster_id'),
    pcaX: (0, pg_core_1.doublePrecision)('pca_x'),
    pcaY: (0, pg_core_1.doublePrecision)('pca_y'),
    createdAt: (0, pg_core_1.timestamp)('created_at').defaultNow().notNull(),
    commentOn: (0, pg_core_1.varchar)('comment_on'),
    submitterName: (0, pg_core_1.varchar)('submitter_name'),
    organization: (0, pg_core_1.varchar)('organization'),
    city: (0, pg_core_1.varchar)('city'),
    state: (0, pg_core_1.varchar)('state'),
    country: (0, pg_core_1.varchar)('country'),
    documentType: (0, pg_core_1.varchar)('document_type'),
    attachmentCount: (0, pg_core_1.integer)('attachment_count'),
    attachments: (0, pg_core_1.json)('attachments').$type(),
    truncatedText: (0, pg_core_1.text)('truncated_text'),
});
