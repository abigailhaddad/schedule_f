import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';
import { NewComment, NewAnalysis, stanceEnum } from './schema';
import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';
import { sql } from 'drizzle-orm';

// Define interface for the JSON data structure
interface CommentDataItem {
  id: string;
  title: string;
  category: string;
  agencyId: string;
  comment: string;
  original_comment: string;
  has_attachments: boolean;
  link: string;
  stance?: string;
  key_quote?: string;
  rationale?: string;
  themes?: string;
}

// Load environment variables from .env file
dotenv.config({ path: path.resolve(__dirname, '../../../../.env') });

const main = async () => {
  if (!process.env.DATABASE_URL) {
    throw new Error('DATABASE_URL environment variable is not set.');
  }

  const client = postgres(process.env.DATABASE_URL, { max: 1 });
  const db = drizzle(client, { schema });

  console.log('Connected to database.');

  const dataPath = path.resolve(__dirname, '../../../../data/results/results_20250519_203826/data.json');
  
  console.log(`Reading data from: ${dataPath}`);

  let rawData;
  try {
    rawData = fs.readFileSync(dataPath, 'utf-8');
  } catch (error) {
    console.error('Error reading data file:', error);
    process.exit(1);
  }
  
  const jsonData: CommentDataItem[] = JSON.parse(rawData);

  console.log(`Found ${jsonData.length} records to process.`);

  const commentsToInsert: NewComment[] = [];
  const analysesToInsert: NewAnalysis[] = [];

  for (const item of jsonData) {
    const newComment: NewComment = {
      id: item.id,
      title: item.title,
      category: item.category,
      agencyId: item.agencyId,
      comment: item.comment,
      originalComment: item.original_comment,
      hasAttachments: item.has_attachments,
      link: item.link,
    };
    commentsToInsert.push(newComment);

    if (item.stance && item.key_quote && item.rationale) {
      // Validate the stance value is a valid enum value
      if (!stanceEnum.enumValues.includes(item.stance as (typeof stanceEnum.enumValues)[number])) {
        console.warn(`Invalid stance value: "${item.stance}" for comment ID: ${item.id}. Skipping analysis for this comment.`);
      } else {
        const newAnalysis: NewAnalysis = {
          commentId: item.id,
          stance: item.stance as typeof stanceEnum.enumValues[number],
          keyQuote: item.key_quote,
          rationale: item.rationale,
          themes: item.themes,
        };
        analysesToInsert.push(newAnalysis);
      }
    }
  }

  if (commentsToInsert.length > 0) {
    console.log(`Inserting ${commentsToInsert.length} comments into the database...`);
    const chunkSize = 100;
    for (let i = 0; i < commentsToInsert.length; i += chunkSize) {
        const chunk = commentsToInsert.slice(i, i + chunkSize);
        try {
            await db.insert(schema.comments).values(chunk).onConflictDoUpdate({ target: schema.comments.id, set: { title: sql`excluded.title`, category: sql`excluded.category`, agencyId: sql`excluded.agency_id`, comment: sql`excluded.comment`, originalComment: sql`excluded.original_comment`, hasAttachments: sql`excluded.has_attachments`, link: sql`excluded.link` } });
            console.log(`Upserted chunk ${i / chunkSize + 1} of ${Math.ceil(commentsToInsert.length / chunkSize)} for comments`);
        } catch (error) {
            console.error(`Error upserting comments chunk ${i / chunkSize + 1}:`, error);
        }
    }
    console.log('Upserting comments completed.');
  } else {
    console.log('No comments found to seed.');
  }

  if (analysesToInsert.length > 0) {
    console.log(`Inserting ${analysesToInsert.length} analyses into the database...`);
    const analysisChunkSize = 100;
    for (let i = 0; i < analysesToInsert.length; i += analysisChunkSize) {
        const chunk = analysesToInsert.slice(i, i + analysisChunkSize);
        try {
            await db.insert(schema.analyses).values(chunk).onConflictDoNothing();
            console.log(`Inserted analysis chunk ${i / analysisChunkSize + 1} of ${Math.ceil(analysesToInsert.length / analysisChunkSize)}`);
        } catch (error) {
            console.error(`Error inserting analysis chunk ${i / analysisChunkSize + 1}:`, error);
        }
    }
    console.log('Seeding analyses completed.');
  } else {
    console.log('No analyses found to seed.');
  }

  await client.end();
  console.log('Database connection closed.');
};

main().catch((err) => {
  console.error('Error during seeding process:', err);
  process.exit(1);
}); 