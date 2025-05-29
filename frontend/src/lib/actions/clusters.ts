// src/lib/actions/clusters.ts
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
  clusterId: string;
  pcaX: number;
  pcaY: number;
  keyQuote: string | null;
  themes: string | null;
}

export interface ClusterData {
  clusters: Array<[string, ClusterPoint[]]>;
  bounds: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
  };
  totalPoints: number;
}

export interface ClusterDataResponse {
  success: boolean;
  data?: ClusterData;
  error?: string;
}

// Define an interface for the raw data returned by the database query
interface RawClusterPointRow {
  id: string;
  title: string | null;
  stance: string | null;
  clusterId: string | null;
  pcaX: number | null;
  pcaY: number | null;
  keyQuote: string | null;
  themes: string | null;
  // Allow for potential snake_case versions from direct SQL execution
  cluster_id?: string | null;
  pca_x?: number | null;
  pca_y?: number | null;
  key_quote?: string | null;
  // Allow for potential all-lowercase versions
  clusterid?: string | null;
  pcax?: number | null;
  pcay?: number | null;
  keyquote?: string | null;
}

export async function getClusterData(): Promise<ClusterDataResponse> {
  const fetchClusterData = async () => {
    try {
      const connection = await connectDb();
      if (!connection.success) {
        throw new Error("Failed to connect to database");
      }

      // Fetch all cluster data without sampling
      const result = await db
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

      // Group by cluster ID using a Map
      const clustersMap = new Map<string, ClusterPoint[]>();
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

        if (!clustersMap.has(point.clusterId)) {
          clustersMap.set(point.clusterId, []);
        }
        clustersMap.get(point.clusterId)!.push(point);

        // Update bounds
        minX = Math.min(minX, point.pcaX);
        maxX = Math.max(maxX, point.pcaX);
        minY = Math.min(minY, point.pcaY);
        maxY = Math.max(maxY, point.pcaY);
      });

      // Convert Map to Array for serialization
      const clustersArray = Array.from(clustersMap.entries());

      return {
        success: true,
        data: {
          clusters: clustersArray,
          bounds: { minX, maxX, minY, maxY },
          totalPoints: result.length,
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
    ['cluster-data'],
    {
      revalidate: 86400, // 24 hours
      tags: ['clusters']
    }
  );
  
  return getCachedClusterData();
}

// Get basic cluster statistics
export async function getClusterStats(): Promise<{
  success: boolean;
  stats?: {
    totalClusters: number;
    totalPoints: number;
    clusterSizes: { clusterId: string; size: number }[];
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