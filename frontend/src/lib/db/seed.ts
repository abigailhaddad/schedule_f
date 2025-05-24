import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';
import { NewComment, stanceEnum } from './schema';
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
  postedDate?: string;
  receivedDate?: string;
  occurrence_number?: number;
  duplicate_of?: string;
}

// Load environment variables from .env file
dotenv.config({ path: path.resolve(__dirname, '../../../../.env') });

// Determine environment directly
const getDbEnvironment = (): 'dev' | 'prod' => {
  const dbEnv = process.env.DB_ENV?.toLowerCase();
  if (dbEnv !== 'dev' && dbEnv !== 'prod') {
    console.warn(`Invalid or missing DB_ENV: "${dbEnv}". Defaulting to "dev".`);
    return 'dev';
  }
  return dbEnv as 'dev' | 'prod';
};

const currentDbEnv = getDbEnvironment();
const isProdEnvironment = currentDbEnv === 'prod';

const main = async () => {
  // Show which database we're seeding
  console.log(`\n🌱 Seeding ${currentDbEnv.toUpperCase()} database`);
  
  if (isProdEnvironment) {
    console.warn('\n⚠️  WARNING: You are about to seed the PRODUCTION database!');
    console.warn('This will modify production data. Press Ctrl+C to cancel.\n');
    
    // Give user 5 seconds to cancel
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  
  if (!process.env.DATABASE_URL) {
    throw new Error('DATABASE_URL environment variable is not set.');
  }

  const client = postgres(process.env.DATABASE_URL, { max: 1 });
  const db = drizzle(client, { schema });

  console.log('Connected to database.');

  const dataPath = path.resolve(__dirname, '../../../../data/data.json');
  
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

  for (const item of jsonData) {
    // Validate the stance value is a valid enum value if present
    const stance = item.stance 
      ? stanceEnum.enumValues.includes(item.stance as typeof stanceEnum.enumValues[number]) 
        ? item.stance as typeof stanceEnum.enumValues[number]
        : null
      : null;

    if (item.stance && !stanceEnum.enumValues.includes(item.stance as typeof stanceEnum.enumValues[number])) {
      console.warn(`Invalid stance value: "${item.stance}" for comment ID: ${item.id}. Setting to null.`);
    }

    const newComment: NewComment = {
      id: item.id,
      title: item.title,
      category: item.category,
      agencyId: item.agencyId,
      comment: item.comment,
      originalComment: item.original_comment,
      hasAttachments: item.has_attachments,
      link: item.link,
      // Analysis fields now directly in comments table
      stance: stance,
      keyQuote: item.key_quote,
      rationale: item.rationale,
      themes: item.themes,
      postedDate: item.postedDate ? new Date(item.postedDate) : null,
      receivedDate: item.receivedDate ? new Date(item.receivedDate) : null,
      occurrenceNumber: item.occurrence_number,
      duplicateOf: item.duplicate_of,
    };
    commentsToInsert.push(newComment);
  }

  if (commentsToInsert.length > 0) {
    console.log(`Inserting ${commentsToInsert.length} comments into the database...`);
    const chunkSize = 100;
    for (let i = 0; i < commentsToInsert.length; i += chunkSize) {
      const chunk = commentsToInsert.slice(i, i + chunkSize);
      try {
        await db.insert(schema.comments).values(chunk).onConflictDoUpdate({ 
          target: schema.comments.id, 
          set: { 
            title: sql`excluded.title`, 
            category: sql`excluded.category`, 
            agencyId: sql`excluded.agency_id`, 
            comment: sql`excluded.comment`, 
            originalComment: sql`excluded.original_comment`, 
            hasAttachments: sql`excluded.has_attachments`, 
            link: sql`excluded.link`,
            stance: sql`excluded.stance`,
            keyQuote: sql`excluded.key_quote`,
            rationale: sql`excluded.rationale`,
            themes: sql`excluded.themes`,
            postedDate: sql`excluded.posted_date`,
            receivedDate: sql`excluded.received_date`,
            occurrenceNumber: sql`excluded.occurrence_number`,
            duplicateOf: sql`excluded.duplicate_of`
          } 
        });
        console.log(`Upserted chunk ${i / chunkSize + 1} of ${Math.ceil(commentsToInsert.length / chunkSize)} for comments`);
      } catch (error) {
        console.error(`Error upserting comments chunk ${i / chunkSize + 1}:`, error);
      }
    }
    console.log('Upserting comments completed.');
  } else {
    console.log('No comments found to seed.');
  }

  await client.end();
  console.log('Database connection closed.');
};

main().catch((err) => {
  console.error('Error during seeding process:', err);
  process.exit(1);
});