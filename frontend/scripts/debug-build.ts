import { getPaginatedComments, getCommentStatistics, getTopCommentIds } from '../src/lib/actions/comments';

/**
 * Debug script to identify build bottlenecks
 * Run with: npm run debug:build
 */
async function main() {
  console.time('Total debug time');
  
  // Test each key function with timing
  try {
    // Test initial data fetch
    console.log('Testing initial data fetch...');
    console.time('Initial data fetch');
    const [commentsResponse, statsResponse] = await Promise.all([
      getPaginatedComments({
        page: 1,
        pageSize: 20,
        sort: { column: 'createdAt', direction: 'desc' }
      }),
      getCommentStatistics({})
    ]);
    console.timeEnd('Initial data fetch');
    console.log(`Fetched ${commentsResponse.data?.length || 0} comments`);
    
    // Test getTopCommentIds
    console.log('\nTesting getTopCommentIds...');
    console.time('getTopCommentIds');
    const ids = await getTopCommentIds(10); // Just test with 10 to avoid long runs
    console.timeEnd('getTopCommentIds');
    console.log(`Fetched ${ids.length} IDs`);
    
    // Test single comment fetch
    if (ids.length > 0) {
      console.log('\nTesting single comment fetch...');
      const { getCommentById } = await import('../src/lib/actions/comments');
      console.time('getCommentById');
      const comment = await getCommentById(ids[0]);
      console.timeEnd('getCommentById');
      console.log(`Fetched comment: ${comment.success}`);
    }
    
    console.log('\nAll tests completed successfully!');
  } catch (error) {
    console.error('Error during debugging:', error);
  }
  
  console.timeEnd('Total debug time');
  process.exit(0);
}

main(); 