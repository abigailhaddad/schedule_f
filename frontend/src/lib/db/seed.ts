import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';
import { NewComment } from './schema';
import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';

// Load environment variables from .env file
//dotenv.config({ path: path.resolve(__dirname, '../../../../.env') });
dotenv.config();

const main = async () => {
  if (!process.env.DATABASE_URL) {
    throw new Error('DATABASE_URL environment variable is not set.');
  }

  const client = postgres(process.env.DATABASE_URL, { max: 1 });
  const db = drizzle(client, { schema });

  console.log('Connected to database.');

  const dataPath = path.resolve(__dirname, '../../../../data/results/results_20250519_203826/raw_data.json');
  
  console.log(`Reading data from: ${dataPath}`);

  let rawData;
  try {
    rawData = fs.readFileSync(dataPath, 'utf-8');
  } catch (error) {
    console.error('Error reading data file:', error);
    process.exit(1);
  }
  
  const jsonData: any[] = JSON.parse(rawData);

  console.log(`Found ${jsonData.length} records to seed.`);

  const commentsToInsert: NewComment[] = [];

  for (const item of jsonData) {
    if (item.type === 'comments' && item.attributes) {
      const attributes = item.attributes;
      const newComment: NewComment = {
        id: item.id,
        title: attributes.title,
        category: attributes.category,
        agencyId: attributes.agencyId,
        comment: attributes.comment,
        originalComment: attributes.attachment_texts && attributes.attachment_texts.length > 0 ? attributes.attachment_texts[0].text : null,
        hasAttachments: attributes.attachment_texts && attributes.attachment_texts.length > 0,
        link: item.links?.self,
        // createdAt will be set by default by the database
      };
      commentsToInsert.push(newComment);
    }
  }

  if (commentsToInsert.length > 0) {
    console.log(`Inserting ${commentsToInsert.length} comments into the database...`);
    // Insert in chunks to avoid issues with too many parameters or large queries
    const chunkSize = 100;
    for (let i = 0; i < commentsToInsert.length; i += chunkSize) {
        const chunk = commentsToInsert.slice(i, i + chunkSize);
        try {
            await db.insert(schema.comments).values(chunk).onConflictDoNothing(); // Or .onConflictDoUpdate if you want to update existing records
            console.log(`Inserted chunk ${i / chunkSize + 1} of ${Math.ceil(commentsToInsert.length / chunkSize)}`);
        } catch (error) {
            console.error(`Error inserting chunk ${i / chunkSize + 1}:`, error);
            // Optionally, log the problematic chunk data for debugging
            // console.error('Problematic chunk:', chunk);
        }
    }
    console.log('Seeding comments completed.');
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