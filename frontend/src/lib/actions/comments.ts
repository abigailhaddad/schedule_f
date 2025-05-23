'use server';

import { db } from '@/lib/db';
import { Comment } from '@/lib/db/schema';
import { QueryOptions, buildCommentsQuery, buildStatsQueries } from '../queryBuilder';
import { getCachedData } from '../cache/cache';
import { unstable_cache } from 'next/cache';
import { comments } from '@/lib/db/schema';
import { asc, inArray } from 'drizzle-orm';

// Response types
export interface CommentsPaginatedResponse {
  success: boolean;
  data?: Comment[];
  total?: number;
  error?: string;
}

export interface CommentsStatisticsResponse {
  success: boolean;
  stats?: {
    total: number;
    for: number;
    against: number;
    neutral: number;
  };
  error?: string;
}

/**
 * Parses URL search params into QueryOptions
 */
export async function parseUrlToQueryOptions(
  searchParams: URLSearchParams | Record<string, string>
): Promise<QueryOptions> {
  const options: QueryOptions = {
    filters: {},
    page: 1,
    pageSize: 10,
  };

  // Helper function to handle both URLSearchParams and plain objects
  const getParam = (key: string): string | null => {
    if (searchParams instanceof URLSearchParams) {
      return searchParams.get(key);
    } else if (typeof searchParams === 'object' && searchParams !== null) {
      return searchParams[key] || null;
    }
    return null;
  };

  // Helper function to get entries from either URLSearchParams or plain object
  const getEntries = (): [string, string][] => {
    if (searchParams instanceof URLSearchParams) {
      return Array.from(searchParams.entries());
    } else if (typeof searchParams === 'object' && searchParams !== null) {
      return Object.entries(searchParams);
    }
    return [];
  };

  // Parse search query
  const search = getParam('search');
  if (search) {
    options.search = search;
  }

  // Parse sorting
  const sort = getParam('sort');
  const sortDirection = getParam('sortDirection') as 'asc' | 'desc' | null;
  if (sort && sortDirection) {
    options.sort = {
      column: sort,
      direction: sortDirection,
    };
  }

  // Parse pagination
  const page = getParam('page');
  if (page) {
    options.page = parseInt(page, 10);
  }

  const pageSize = getParam('pageSize');
  if (pageSize) {
    options.pageSize = parseInt(pageSize, 10);
  }

  // Parse filters
  for (const [key, value] of getEntries()) {
    if (key.startsWith('filter_')) {
      const filterKey = key.replace('filter_', '');
      
      // Try to parse JSON for complex filters
      try {
        options.filters![filterKey] = JSON.parse(value);
      } catch {
        // If not valid JSON, use as string
        options.filters![filterKey] = value;
      }
    }
  }

  return options;
}

/**
 * Helper function to safely extract count value from DB result
 */
function extractCountValue(result: { rows?: Array<Record<string, unknown>> }): number {
  if (!result.rows || !Array.isArray(result.rows) || !result.rows[0]) return 0;
  
  const row = result.rows[0] as Record<string, unknown>;
  // Try to access the count property directly first
  if (typeof row.count === 'number') return row.count;
  if (typeof row.count === 'string') return parseInt(row.count, 10);
  
  // If that fails, get the first property (which should be the count)
  const firstKey = Object.keys(row)[0];
  if (!firstKey) return 0;
  
  const value = row[firstKey];
  if (typeof value === 'number') return value;
  if (typeof value === 'string') return parseInt(value, 10);
  
  return 0;
}

/**
 * Fetches paginated comments based on provided query options
 */
export async function getPaginatedComments(
  options: QueryOptions
): Promise<CommentsPaginatedResponse> {
  const cacheKey = `comments-${JSON.stringify(options)}`;
  console.log(`[DEBUG] getPaginatedComments called with options: ${JSON.stringify(options)}`);
  const startTime = Date.now();
  const QUERY_TIMEOUT = 30000; // 30 seconds timeout for these queries

  return getCachedData(
    cacheKey,
    async () => {
      try {
        console.log(`[DEBUG] Cache miss for getPaginatedComments, fetching from DB`);
        
        const queryResult = await buildCommentsQuery(options);
        console.log(`[DEBUG] Queries built in ${Date.now() - startTime}ms`);

        const timeoutPromise = (operationName: string) => 
          new Promise<never>((_, reject) => {
            setTimeout(() => reject(new Error(`${operationName} query timed out after ${QUERY_TIMEOUT / 1000}s`)), QUERY_TIMEOUT);
          });

        let total = 0;
        let data: Comment[] = [];
        let success = false;
        let error: string | undefined;

        try {
          console.log(`[DEBUG] Executing count query with ${QUERY_TIMEOUT / 1000}s timeout...`);
          const countStart = Date.now();
          const countResult = await Promise.race([
            db.execute(queryResult.countQuery),
            timeoutPromise('Count')
          ]);
          total = extractCountValue(countResult);
          console.log(`[DEBUG] Count query executed in ${Date.now() - countStart}ms, total: ${total}`);

          console.log(`[DEBUG] Executing data query with ${QUERY_TIMEOUT / 1000}s timeout...`);
          const dataStart = Date.now();
          const result = await Promise.race([
            db.execute(queryResult.query),
            timeoutPromise('Data')
          ]);
          data = result.rows as Comment[];
          console.log(`[DEBUG] Data query executed in ${Date.now() - dataStart}ms, rows: ${data.length}`);
          success = true;
        } catch (e) {
          if (e instanceof Error && e.message.includes('timed out')) {
            console.warn(`[WARN] In getPaginatedComments: ${e.message}`);
            error = `Failed to fetch comments: Query timed out. Op: ${e.message.includes("Count") ? "count" : "data"}`;
          } else {
            const errorMessage = e instanceof Error ? e.message : String(e);
            console.error("[ERROR] Error executing query in getPaginatedComments:", errorMessage);
            error = `Failed to fetch comments: ${errorMessage}`;
          }
          success = false;
          // Ensure data and total are in their default empty/zero state
          data = [];
          total = 0;
        }

        return {
          success,
          data,
          total,
          error
        };
      } catch (error: unknown) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error("[ERROR] Error in getPaginatedComments (outer try-catch):", errorMessage);
        return { 
          success: false, 
          error: `Failed to fetch comments: ${errorMessage}`,
          data: [],
          total: 0
        };
      } finally {
        console.log(`[DEBUG] getPaginatedComments total time: ${Date.now() - startTime}ms`);
      }
    }
  );
}

/**
 * Fetches statistics based on current filters
 */
export async function getCommentStatistics(
  options: QueryOptions
): Promise<CommentsStatisticsResponse> {
  const filterOptions = { ...options };
  delete filterOptions.page;
  delete filterOptions.pageSize;
  
  const cacheKey = `stats-${JSON.stringify(filterOptions)}`;
  console.log(`[DEBUG] getCommentStatistics called with options: ${JSON.stringify(options)}`);
  const startTime = Date.now();
  const QUERY_TIMEOUT = 30000; // 30 seconds timeout for stats queries

  return getCachedData(
    cacheKey,
    async () => {
      try {
        console.log(`[DEBUG] Cache miss for getCommentStatistics, fetching from DB`);
        const queryResults = await buildStatsQueries(options);
        console.log(`[DEBUG] Stats queries built in ${Date.now() - startTime}ms`);

        const timeoutPromise = (operationName: string) => 
          new Promise<never>((_, reject) => {
            setTimeout(() => reject(new Error(`Stats query (${operationName}) timed out after ${QUERY_TIMEOUT / 1000}s`)), QUERY_TIMEOUT);
          });

        let totalCount = 0, forCount = 0, againstCount = 0, neutralCount = 0;
        let success = false;
        let error: string | undefined;

        try {
          console.log(`[DEBUG] Executing stats queries with ${QUERY_TIMEOUT / 1000}s timeout...`);
          const queriesStart = Date.now();

          const [totalResult, forResult, againstResult, neutralResult] = await Promise.all([
            Promise.race([db.execute(queryResults.totalQuery), timeoutPromise('total')]),
            Promise.race([db.execute(queryResults.forQuery), timeoutPromise('for')]),
            Promise.race([db.execute(queryResults.againstQuery), timeoutPromise('against')]),
            Promise.race([db.execute(queryResults.neutralQuery), timeoutPromise('neutral')])
          ]);
          console.log(`[DEBUG] All stats queries completed or timed out in ${Date.now() - queriesStart}ms`);

          totalCount = extractCountValue(totalResult);
          forCount = extractCountValue(forResult);
          againstCount = extractCountValue(againstResult);
          neutralCount = extractCountValue(neutralResult);
          success = true;

        } catch (e) {
          if (e instanceof Error && e.message.includes('timed out')) {
            console.warn(`[WARN] In getCommentStatistics: ${e.message}`);
            error = `Failed to fetch statistics: A stats query timed out.`;
          } else {
            const errorMessage = e instanceof Error ? e.message : String(e);
            console.error("[ERROR] Error executing query in getCommentStatistics:", errorMessage);
            error = `Failed to fetch statistics: ${errorMessage}`;
          }
          success = false;
          // Default counts remain 0
        }

        return {
          success,
          stats: {
            total: totalCount,
            for: forCount,
            against: againstCount,
            neutral: neutralCount
          },
          error
        };
      } catch (error: unknown) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error("[ERROR] Error in getCommentStatistics (outer try-catch):", errorMessage);
        return { 
          success: false, 
          error: `Failed to fetch statistics: ${errorMessage}`,
          stats: { total: 0, for: 0, against: 0, neutral: 0 }
        };
      } finally {
        console.log(`[DEBUG] getCommentStatistics total time: ${Date.now() - startTime}ms`);
      }
    }
  );
}

/**
 * Fetches a single comment by ID
 */
export async function getCommentById(
  id: string
): Promise<{ success: boolean; data?: Comment; error?: string }> {
  const cacheKey = `comment-${id}`;

  return getCachedData(
    cacheKey,
    async () => {
      try {
        // const connection = await connectDb(); // Removed
        // if (!connection.success) { // Removed
        //   throw new Error("Failed to connect to database"); // Removed
        // } // Removed

        const queryResult = await buildCommentsQuery({
          filters: { id }
        });

        const result = await db.execute(queryResult.query);
        const comments = result.rows as Comment[];

        if (comments.length === 0) {
          return { success: false, error: "Comment not found" };
        }

        return {
          success: true,
          data: comments[0]
        };
      } catch (error: unknown) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        console.error("Error fetching comment by ID:", errorMessage);
        return { 
          success: false, 
          error: `Failed to fetch comment: ${errorMessage}` 
        };
      }
    }
  );
}


/**
 * Get all comment IDs for static generation
 * @param limit - Maximum number of IDs to return
 */
export const getAllCommentIds = unstable_cache(
  async (limit = 100): Promise<string[]> => {
    try {
      // const connection = await connectDb(); // Removed
      // if (!connection.success) { // Removed
      //   throw new Error("Failed to connect to database"); // Removed
      // } // Removed

      // Get most recent comment IDs
      const query = db
        .select({ id: comments.id })
        .from(comments)
        .orderBy(asc(comments.createdAt))
        .limit(limit);

      const result = await db.execute(query);
      return result.rows.map((row: Record<string, unknown>) => (row as { id: string }).id);
    } catch (error) {
      console.error("Error fetching comment IDs:", error);
      return [];
    }
  },
  ['comment-ids'],
  {
    revalidate: 86400, // 24 hours
    tags: ['comments']
  }
);

/**
 * Optimized batch comment fetching for better performance
 */
export const getCommentsByIds = unstable_cache(
  async (ids: string[]): Promise<Comment[]> => {
    if (ids.length === 0) return [];

    try {
      // const connection = await connectDb(); // Removed
      // if (!connection.success) { // Removed
      //   throw new Error("Failed to connect to database"); // Removed
      // } // Removed

      const query = db
        .select()
        .from(comments)
        .where(inArray(comments.id, ids));

      const result = await db.execute(query);
      return result.rows as Comment[];
    } catch (error) {
      console.error("Error fetching comments by IDs:", error);
      return [];
    }
  },
  ['comments-batch'],
  {
    revalidate: 86400,
    tags: ['comments']
  }
);

/**
 * Revalidate cache for specific paths
 */
export async function revalidateComments() {
  const { revalidateTag, revalidatePath } = await import('next/cache');
  
  // Revalidate all comment-related caches
  revalidateTag('comments');
  revalidateTag('statistics');
  
  // Revalidate specific paths
  revalidatePath('/');
  revalidatePath('/comment/[id]', 'page');
}

/**
 * Get top comment IDs for static generation
 * @param limit - Maximum number of IDs to return
 */
export async function getTopCommentIds(limit = 100): Promise<string[]> {
  console.log(`[DEBUG] getTopCommentIds called with limit: ${limit}`);
  const startTime = Date.now();
  const QUERY_TIMEOUT = 30000; // 30 seconds timeout for this specific query

  try {
    console.log(`[DEBUG] Building query for getTopCommentIds`);
    const query = db
      .select({ id: comments.id })
      .from(comments)
      .orderBy(asc(comments.createdAt))
      .limit(limit);

    console.log(`[DEBUG] Executing query for getTopCommentIds with a ${QUERY_TIMEOUT / 1000}s timeout.`);
    const queryStart = Date.now();

    const resultPromise = db.execute(query);
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error(`getTopCommentIds query timed out after ${QUERY_TIMEOUT / 1000}s`)), QUERY_TIMEOUT);
    });

    let result;
    try {
      result = await Promise.race([resultPromise, timeoutPromise]);
    } catch (e) {
      if (e instanceof Error && e.message.includes('timed out')) {
        console.warn(`[WARN] ${e.message}`);
        return []; // Return empty on timeout
      } 
      throw e; // Re-throw other errors
    }
    
    console.log(`[DEBUG Query executed with results: ${JSON.stringify(result)}`);

    const rows = result.rows.map((row: Record<string, unknown>) => (row as { id: string }).id);
    console.log(`[DEBUG] Query processed in ${Date.now() - queryStart}ms, got ${rows.length} rows`);
    
    return rows;
  } catch (error) {
    console.error("[ERROR] Error fetching top comment IDs:", error);
    return []; // Return empty array on other errors as well to prevent build hangs
  } finally {
    console.log(`[DEBUG] getTopCommentIds total time: ${Date.now() - startTime}ms`);
  }
}

/**
 * Warm the cache with common queries during build
 */
export async function warmCache() {
  console.log('[DEBUG] Starting cache warming...');
  const startTime = Date.now();
  
  // Only warm essential queries to avoid build timeouts
  try {
    // Rather than doing all in parallel, which could overload the DB,
    // do them sequentially
    console.log('[DEBUG] Warming main page data...');
    const mainDataStart = Date.now();
    await getPaginatedComments({ 
      page: 1, 
      pageSize: 20, 
      filters: {},
      sort: { column: 'createdAt', direction: 'desc' }
    });
    console.log(`[DEBUG] Main page data warmed in ${Date.now() - mainDataStart}ms`);
    
    console.log('[DEBUG] Warming statistics...');
    const statsStart = Date.now();
    await getCommentStatistics({ filters: {} });
    console.log(`[DEBUG] Statistics warmed in ${Date.now() - statsStart}ms`);
    
    // Skip warming filtered views for now - too slow
    
    console.log(`[DEBUG] Cache warming completed in ${Date.now() - startTime}ms`);
  } catch (error) {
    console.error('Error warming cache:', error);
  }
}