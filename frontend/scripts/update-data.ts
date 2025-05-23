// scripts/update-data.ts
import { config } from 'dotenv';
import path from 'path';

// Load environment variables
config({ path: path.resolve(process.cwd(), '.env') });

async function updateData() {
  console.log('Starting data update process...');
  
  try {
    // 1. Run your data update logic here
    // For example, run the seed script:
    // await import('../src/lib/db/seed');
    
    console.log('Data update completed successfully');
    
    // 2. Trigger revalidation if you have a deployment URL
    const deploymentUrl = process.env.DEPLOYMENT_URL || 'http://localhost:3000';
    const revalidationToken = process.env.REVALIDATION_TOKEN;
    
    if (deploymentUrl) {
      console.log('Triggering page revalidation...');
      
      const response = await fetch(`${deploymentUrl}/api/revalidate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(revalidationToken && { 'Authorization': `Bearer ${revalidationToken}` })
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Revalidation triggered successfully:', data);
      } else {
        console.error('Failed to trigger revalidation:', response.status);
      }
    }
    
    // 3. Update the LAST_DATA_UPDATE in your .env file
    // Note: In production, you might want to use a different approach
    // like updating an environment variable in your deployment platform
    console.log(`
Remember to update LAST_DATA_UPDATE in your .env file:
LAST_DATA_UPDATE=${new Date().toISOString()}
    `);
    
  } catch (error) {
    console.error('Error during data update:', error);
    process.exit(1);
  }
}

// Run the update
updateData();