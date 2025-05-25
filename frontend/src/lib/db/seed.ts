import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';
import { NewComment, stanceEnum } from './schema';
import fs from 'fs';
import path from 'path';
import { sql } from 'drizzle-orm';
import { dbConfig } from './config';


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
  posted_date?: string;
  received_date?: string;
  occurrence_number?: number;
  duplicate_of?: string;
  cluster_id?: number;
  pca_x?: number;
  pca_y?: number;
}

const main = async () => {
  // Show which database we're seeding using dbConfig
  console.log(`\n🌱 Seeding ${dbConfig.isProd ? 'PRODUCTION' : 'DEVELOPMENT'} database`);
  
  if (dbConfig.isProd) {
    console.warn('\n⚠️  WARNING: You are about to seed the PRODUCTION database!');
    console.warn('This will modify production data. Press Ctrl+C to cancel.\n');
    
    // Give user 5 seconds to cancel
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  
  const databaseUrlForSeed = dbConfig.url;

  console.log(`\n🌱 Attempting to seed database using URL: ${databaseUrlForSeed}`);

  const client = postgres(databaseUrlForSeed, { max: 1 });
  const db = drizzle(client, { schema });

  console.log('Connected to database.');

  // Determine data path based on environment
  const devDataPath = path.resolve(__dirname, '../../__tests__/test-data-5-25.json');
  const prodDataPath = path.resolve(__dirname, '../../../../data/data.json');
  
  const dataPath = dbConfig.isDev ? devDataPath : prodDataPath;
  
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

  const processDuplicateOf = (dupString: string | undefined): string[] | undefined => {
    if (dupString === undefined || dupString === null) {
        return undefined; 
    }
    if (dupString.trim() === '') {
        return [];
    }
    return dupString.split(',').map(s => s.trim()).filter(s => s.length > 0);
  };

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
      stance: stance,
      keyQuote: item.key_quote,
      rationale: item.rationale,
      themes: item.themes,
      postedDate: item.posted_date ? new Date(item.posted_date) : null,
      receivedDate: item.received_date ? new Date(item.received_date) : null,
      occurrenceNumber: item.occurrence_number,
      duplicateOf: processDuplicateOf(item.duplicate_of),
      clusterId: item.cluster_id,
      pcaX: item.pca_x,
      pcaY: item.pca_y,
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
            duplicateOf: sql`excluded.duplicate_of`,
            clusterId: sql`excluded.cluster_id`,
            pcaX: sql`excluded.pca_x`,
            pcaY: sql`excluded.pca_y`
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

  // Verify insertion by counting records
  try {
    const result = await db.select({ count: sql`count(*)` }).from(schema.comments);
    const count = result[0]?.count || 0;
    console.log(`Verification: Found ${count} records in the comments table after seeding.`);
  } catch (error) {
    console.error('Error verifying comment count:', error);
  }

  await client.end();
  console.log('Database connection closed.');
};

main().catch((err) => {
  console.error('Error during seeding process:', err);
  process.exit(1);
});