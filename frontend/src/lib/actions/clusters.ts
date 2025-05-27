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
}

export interface ClusterDataResponse {
  success: boolean;
  data?: ClusterData;
  error?: string;
}

export async function getClusterData(): Promise<ClusterDataResponse> {
  const fetchClusterData = async () => {
    try {
      const connection = await connectDb();
      if (!connection.success) {
        throw new Error("Failed to connect to database");
      }

      // Fetch all comments with cluster data
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

      // Group by cluster ID
      const clusters = new Map<number, ClusterPoint[]>();
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

      result.forEach(row => {
        const point: ClusterPoint = {
          id: row.id,
          title: row.title || 'Untitled',
          stance: row.stance,
          clusterId: row.clusterId!,
          pcaX: row.pcaX!,
          pcaY: row.pcaY!,
          keyQuote: row.keyQuote,
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
          bounds: { minX, maxX, minY, maxY }
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