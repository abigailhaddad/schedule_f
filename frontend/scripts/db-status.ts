// scripts/db-status.ts
import { dbConfig, connectDb, db } from '../src/lib/db';
import { sql } from 'drizzle-orm';
import { comments } from '../src/lib/db/schema';

async function checkDatabaseStatus() {
  console.log('🔍 Database Status Check\n');
  console.log(`Environment: ${dbConfig.environment.toUpperCase()}`);
  console.log(`Database URL: ${dbConfig.url.substring(0, 30)}...`);
  console.log('-------------------\n');

  try {
    // Try to connect
    console.log('Attempting connection...');
    const connection = await connectDb();
    
    if (!connection.success) {
      console.error('❌ Failed to connect to database');
      return;
    }
    
    console.log('✅ Successfully connected to database\n');
    
    // Get some basic stats
    console.log('📊 Database Statistics:');
    
    // Get comment count
    const commentCount = await db.select({ count: sql<number>`count(*)` }).from(comments);
    console.log(`   Comments: ${commentCount[0]?.count || 0}`);
    
    // Get stance distribution
    const stanceStats = await db
      .select({
        stance: comments.stance,
        count: sql<number>`count(*)`
      })
      .from(comments)
      .groupBy(comments.stance);
    
    console.log('\n   Stance Distribution:');
    stanceStats.forEach(stat => {
      console.log(`   - ${stat.stance || 'Unknown'}: ${stat.count}`);
    });
    
    console.log('\n✅ Database check complete!');
    
  } catch (error) {
    console.error('❌ Error during database check:', error);
  }
   
  process.exit(0);
}

// Run the check
checkDatabaseStatus();
