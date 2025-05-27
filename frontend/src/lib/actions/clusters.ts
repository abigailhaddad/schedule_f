// Export the functions
'use server';

import { db, connectDb } from '@/lib/db';
import { comments } from '@/lib/db/schema';
import { sql } from 'drizzle-orm';
import { unstable_cache } from 'next/cache';
import { cacheConfig } from '../cache-config';

export interface ClusterPoint {
  id: string;
  title: string;
  stance: string | null;
  clusterId: number;
  pcaX: number;
  pcaY: number;
  keyQuote: string | null;
  themes: string | null;
}

export interface ClusterData {
  clusters: Map<number, ClusterPoint[]>;
  bounds: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
  };
  isSampled: boolean;
  totalPoints: number;
  sampledPoints: number;
}

export interface ClusterDataResponse {
  success: boolean;
  data?: ClusterData;
  error?: string;
}

const MAX_POINTS_PER_CLUSTER = 50; // Limit points per cluster for performance
const MAX_TOTAL_POINTS = 500; // Maximum total points to render for smooth interaction

// Define an interface for the raw data returned by the database query
interface RawClusterPointRow {
  id: string;
  title: string | null; // Title can be null from DB
  stance: string | null;
  clusterId: number | null; // Nullable from DB before filtering
  pcaX: number | null;      // Nullable from DB before filtering
  pcaY: number | null;      // Nullable from DB before filtering
  keyQuote: string | null;
  themes: string | null;
  // Allow for potential snake_case versions from direct SQL execution
  cluster_id?: number | null;
  pca_x?: number | null;
  pca_y?: number | null;
  key_quote?: string | null;
  // Allow for potential all-lowercase versions
  clusterid?: number | null;
  pcax?: number | null;
  pcay?: number | null;
  keyquote?: string | null;
}

export async function getClusterData(sampleData: boolean = true): Promise<ClusterDataResponse> {
  const fetchClusterData = async () => {
    try {
      const connection = await connectDb();
      if (!connection.success) {
        throw new Error("Failed to connect to database");
      }

      // First, get cluster statistics
      const clusterStats = await db
        .select({
          clusterId: comments.clusterId,
          count: sql<number>`COUNT(*)`.mapWith(Number),
        })
        .from(comments)
        .where(sql`${comments.clusterId} IS NOT NULL`)
        .groupBy(comments.clusterId)
        .execute();

      const totalPointsCount = clusterStats.reduce((sum, stat) => sum + stat.count, 0);
      
      // Determine if we need to sample
      const shouldSample = sampleData && totalPointsCount > MAX_TOTAL_POINTS;
      
      let result: RawClusterPointRow[]; // Use the defined interface
      
      if (shouldSample) {
        // Use a more efficient sampling strategy
        // Sample proportionally from each cluster
        const samplingRatio = MAX_TOTAL_POINTS / totalPointsCount;
        
        // Build a UNION query to sample from each cluster
        const clusterQueries = clusterStats.map((stat) => {
          const sampleSize = Math.max(1, Math.floor(stat.count * samplingRatio));
          const limitedSize = Math.min(sampleSize, MAX_POINTS_PER_CLUSTER);
          
          return sql`
            (SELECT 
              ${comments.id},
              ${comments.title},
              ${comments.stance},
              ${comments.clusterId},
              ${comments.pcaX},
              ${comments.pcaY},
              ${comments.keyQuote},
              ${comments.themes}
            FROM ${comments}
            WHERE ${comments.clusterId} = ${stat.clusterId}
              AND ${comments.pcaX} IS NOT NULL 
              AND ${comments.pcaY} IS NOT NULL
            ORDER BY RANDOM()
            LIMIT ${limitedSize})
          `;
        });
        
        // Combine all cluster queries
        const queryResult = await db.execute(sql`
          ${sql.join(clusterQueries, sql` UNION ALL `)}
        `);
        
        // Extract rows from QueryResult
        result = queryResult.rows as unknown as RawClusterPointRow[]; // Assert via unknown for raw SQL
      } else {
        // Fetch all data if under the limit
        result = await db
          .select({
            id: comments.id,
            title: comments.title,
            stance: comments.stance,
            clusterId: comments.clusterId,
            pcaX: comments.pcaX,
            pcaY: comments.pcaY,
            keyQuote: comments.keyQuote,
            themes: comments.themes,
          })
          .from(comments)
          .where(sql`${comments.clusterId} IS NOT NULL AND ${comments.pcaX} IS NOT NULL AND ${comments.pcaY} IS NOT NULL`)
          .execute();
      }

      // Group by cluster ID
      const clusters = new Map<number, ClusterPoint[]>();
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

      result.forEach((row: RawClusterPointRow) => {
        const point: ClusterPoint = {
          id: row.id,
          title: row.title || 'Untitled',
          stance: row.stance,
          clusterId: (row.cluster_id || row.clusterId || row.clusterid)!,
          pcaX: (row.pca_x || row.pcaX || row.pcax)!,
          pcaY: (row.pca_y || row.pcaY || row.pcay)!,
          keyQuote: (row.key_quote || row.keyQuote || row.keyquote) || null,
          themes: row.themes,
        };

        if (!clusters.has(point.clusterId)) {
          clusters.set(point.clusterId, []);
        }
        clusters.get(point.clusterId)!.push(point);

        // Update bounds
        minX = Math.min(minX, point.pcaX);
        maxX = Math.max(maxX, point.pcaX);
        minY = Math.min(minY, point.pcaY);
        maxY = Math.max(maxY, point.pcaY);
      });

      return {
        success: true,
        data: {
          clusters,
          bounds: { minX, maxX, minY, maxY },
          isSampled: shouldSample,
          totalPoints: totalPointsCount,
          sampledPoints: result.length,
        }
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error("Error fetching cluster data:", errorMessage);
      return {
        success: false,
        error: `Failed to fetch cluster data: ${errorMessage}`
      };
    }
  };

  // Use caching in production
  const shouldSkipCache = process.env.NODE_ENV === 'development' && cacheConfig.disableCacheInDevelopment;
  
  if (shouldSkipCache) {
    return fetchClusterData();
  }

  const getCachedClusterData = unstable_cache(
    fetchClusterData,
    [`cluster-data-${sampleData}`],
    {
      revalidate: 86400, // 24 hours
      tags: ['clusters']
    }
  );
  
  return getCachedClusterData();
}

// Get basic cluster statistics without loading all points
export async function getClusterStats(): Promise<{
  success: boolean;
  stats?: {
    totalClusters: number;
    totalPoints: number;
    clusterSizes: { clusterId: number; size: number }[];
  };
  error?: string;
}> {
  const fetchStats = async () => {
    try {
      const connection = await connectDb();
      if (!connection.success) {
        throw new Error("Failed to connect to database");
      }

      const result = await db
        .select({
          clusterId: comments.clusterId,
          count: sql<number>`COUNT(*)`.mapWith(Number),
        })
        .from(comments)
        .where(sql`${comments.clusterId} IS NOT NULL`)
        .groupBy(comments.clusterId)
        .execute();

      const totalPoints = result.reduce((sum, row) => sum + row.count, 0);
      const clusterSizes = result.map(row => ({
        clusterId: row.clusterId!,
        size: row.count,
      }));

      return {
        success: true,
        stats: {
          totalClusters: result.length,
          totalPoints,
          clusterSizes,
        }
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      return {
        success: false,
        error: `Failed to fetch cluster stats: ${errorMessage}`
      };
    }
  };

  const shouldSkipCache = process.env.NODE_ENV === 'development' && cacheConfig.disableCacheInDevelopment;
  
  if (shouldSkipCache) {
    return fetchStats();
  }

  const getCachedStats = unstable_cache(
    fetchStats,
    ['cluster-stats'],
    {
      revalidate: 86400,
      tags: ['clusters']
    }
  );
  
  return getCachedStats();
}

