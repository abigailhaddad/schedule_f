'use server';

import { db, connectDb } from '@/lib/db';
import { Comment } from '@/lib/db/schema';
import { QueryOptions, buildCommentsQuery, buildStatsQueries } from '../queryBuilder';
import { getCachedData } from '../cache';
import { unstable_cache } from 'next/cache';
import { cacheConfig } from '../cache-config';

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
  // Core function that fetches comments
  const fetchComments = async () => {
    try {
      const connection = await connectDb();
      if (!connection.success) {
        throw new Error("Failed to connect to database");
      }

      // Build queries for data and count
      const queryResult = await buildCommentsQuery(options);

      // Execute count query first
      const countResult = await db.execute(queryResult.countQuery);
      const total = extractCountValue(countResult);

      // Execute data query
      const result = await db.execute(queryResult.query);
      const data = result.rows as Comment[];

      return {
        success: true,
        data,
        total,
      };
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("Error fetching paginated comments:", errorMessage);
      return { 
        success: false, 
        error: `Failed to fetch comments: ${errorMessage}` 
      };
    }
  };

  // Check if we should skip caching
  const shouldSkipCache = process.env.NODE_ENV === 'development' && cacheConfig.disableCacheInDevelopment;
  
  if (shouldSkipCache) {
    return fetchComments();
  }

  // Use Next.js unstable_cache for production or when cache is enabled
  const getCachedComments = unstable_cache(
    fetchComments,
    [`comments-${JSON.stringify(options)}`], // Cache key
    {
      revalidate: 86400, // 24 hours, matching your page revalidation
      tags: ['comments']
    }
  );
  
  return getCachedComments();
}

/**
 * Fetches ALL comments based on provided query options for time series analysis.
 * Manages pagination internally to retrieve all matching records.
 * TODO: This almost certainly needs to be totally refactored...
 */
export async function getAllCommentsForTimeSeries(
  options: QueryOptions
): Promise<CommentsPaginatedResponse> { // Reusing response type, but 'total' will be total fetched.
  
  // Core function that fetches all comments by looping through pages
  const fetchAllCommentsLoop = async () => {
    try {
      const connection = await connectDb();
      if (!connection.success) {
        throw new Error("Failed to connect to database for time series");
      }

      let allFetchedComments: Comment[] = [];
      let currentPage = 1;
      const internalPageSize = 500; // Sensible page size for internal looping
      let hasMoreData = true;

      // Clone options and remove any pre-existing pagination for internal loop
      const loopOptions = { ...options };
      delete loopOptions.page;
      delete loopOptions.pageSize;

      while (hasMoreData) {
        const currentOptions: QueryOptions = {
          ...loopOptions,
          page: currentPage,
          pageSize: internalPageSize,
        };

        const queryResult = await buildCommentsQuery(currentOptions);
        // We only need the data query for looping, not the count query for each page.
        const result = await db.execute(queryResult.query);
        const newComments = result.rows as Comment[];

        if (newComments.length > 0) {
          allFetchedComments = allFetchedComments.concat(newComments);
          if (newComments.length < internalPageSize) {
            hasMoreData = false; // Last page fetched
          } else {
            currentPage++;
          }
        } else {
          hasMoreData = false; // No more data
        }
      }

      return {
        success: true,
        data: allFetchedComments,
        total: allFetchedComments.length, // Total fetched comments
      };
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("Error fetching all comments for time series:", errorMessage);
      return { 
        success: false, 
        error: `Failed to fetch all comments: ${errorMessage}` 
      };
    }
  };

  // Determine cache key based on options (excluding pagination as it's handled internally)
  const cacheKeyOptions = { ...options };
  delete cacheKeyOptions.page;
  delete cacheKeyOptions.pageSize;

  const cacheKey = `all-comments-timeseries-${JSON.stringify(cacheKeyOptions)}`;
  
  // Check if we should skip caching
  const shouldSkipCache = process.env.NODE_ENV === 'development' && cacheConfig.disableCacheInDevelopment;
  
  if (shouldSkipCache) {
    console.log("[getAllCommentsForTimeSeries] Skipping cache in development.");
    return fetchAllCommentsLoop();
  }

  // Use Next.js unstable_cache for production or when cache is enabled
  const getCachedAllComments = unstable_cache(
    fetchAllCommentsLoop,
    [cacheKey], // Cache key array
    {
      revalidate: 86400, // 24 hours, matching your page revalidation
      tags: ['comments-timeseries', 'comments'] // Specific tag for this type of data
    }
  );
  
  console.log(`[getAllCommentsForTimeSeries] Using cache key: ${cacheKey}`);
  return getCachedAllComments();
}

/**
 * Fetches statistics based on current filters
 */
export async function getCommentStatistics(
  options: QueryOptions
): Promise<CommentsStatisticsResponse> {
  // Create cache key based on options (without pagination)
  const filterOptions = { ...options };
  delete filterOptions.page;
  delete filterOptions.pageSize;
  
  // Core function that fetches statistics
  const fetchStatistics = async () => {
    try {
      const connection = await connectDb();
      if (!connection.success) {
        throw new Error("Failed to connect to database");
      }

      // Build all stats queries
      const queryResults = await buildStatsQueries(options);

      // Execute all queries
      const [totalResult, forResult, againstResult, neutralResult] = await Promise.all([
        db.execute(queryResults.totalQuery),
        db.execute(queryResults.forQuery),
        db.execute(queryResults.againstQuery),
        db.execute(queryResults.neutralQuery)
      ]);

      // Parse results
      const totalCount = extractCountValue(totalResult);
      const forCount = extractCountValue(forResult);
      const againstCount = extractCountValue(againstResult);
      const neutralCount = extractCountValue(neutralResult);

      return {
        success: true,
        stats: {
          total: totalCount,
          for: forCount,
          against: againstCount,
          neutral: neutralCount
        }
      };
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("Error fetching comment statistics:", errorMessage);
      return { 
        success: false, 
        error: `Failed to fetch statistics: ${errorMessage}` 
      };
    }
  };

  // Check if we should skip caching
  const shouldSkipCache = process.env.NODE_ENV === 'development' && cacheConfig.disableCacheInDevelopment;
  
  if (shouldSkipCache) {
    return fetchStatistics();
  }

  // Use Next.js unstable_cache for production or when cache is enabled
  const getCachedStats = unstable_cache(
    fetchStatistics,
    [`stats-${JSON.stringify(filterOptions)}`], // Cache key
    {
      revalidate: 86400, // 24 hours, matching your page revalidation
      tags: ['stats']
    }
  );
  
  return getCachedStats();
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
        const connection = await connectDb();
        if (!connection.success) {
          throw new Error("Failed to connect to database");
        }

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