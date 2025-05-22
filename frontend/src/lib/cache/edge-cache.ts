// src/lib/cache/edge-cache.ts
import { cacheConfig } from './cache-config';

interface CacheEntry<T> {
  value: T;
  timestamp: number;
  expiresAt: number;
  size?: number;
}

class EdgeCache {
  private store: Map<string, CacheEntry<unknown>>;
  private readonly maxSize: number;
  private readonly maxMemory: number;
  private currentMemory: number;

  constructor(maxSize = 1000, maxMemoryMB = 100) {
    this.store = new Map();
    this.maxSize = maxSize;
    this.maxMemory = maxMemoryMB * 1024 * 1024; // Convert to bytes
    this.currentMemory = 0;
  }

  private estimateSize(value: unknown): number {
    // Rough estimation of object size in memory
    return JSON.stringify(value).length * 2; // 2 bytes per character
  }

  private evictLRU(): void {
    if (this.store.size === 0) return;

    // Find oldest entry
    let oldestKey: string | null = null;
    let oldestTime = Infinity;

    for (const [key, entry] of this.store.entries()) {
      if (entry.timestamp < oldestTime) {
        oldestTime = entry.timestamp;
        oldestKey = key;
      }
    }

    if (oldestKey) {
      const entry = this.store.get(oldestKey);
      if (entry?.size) {
        this.currentMemory -= entry.size;
      }
      this.store.delete(oldestKey);
    }
  }

  get<T>(key: string): T | undefined {
    const entry = this.store.get(key) as CacheEntry<T> | undefined;

    if (!entry) return undefined;

    // Check expiration
    if (Date.now() > entry.expiresAt) {
      this.delete(key);
      return undefined;
    }

    // Update timestamp for LRU
    entry.timestamp = Date.now();
    
    return entry.value;
  }

  set<T>(key: string, value: T, ttl?: number): void {
    const size = this.estimateSize(value);
    
    // Check memory limit
    while (this.currentMemory + size > this.maxMemory && this.store.size > 0) {
      this.evictLRU();
    }

    // Check size limit
    while (this.store.size >= this.maxSize) {
      this.evictLRU();
    }

    const now = Date.now();
    const ttlMs = (ttl ?? cacheConfig.maxAge) * 1000;

    // Remove old entry's memory if it exists
    const oldEntry = this.store.get(key);
    if (oldEntry?.size) {
      this.currentMemory -= oldEntry.size;
    }

    this.store.set(key, {
      value,
      timestamp: now,
      expiresAt: now + ttlMs,
      size
    });

    this.currentMemory += size;
  }

  delete(key: string): void {
    const entry = this.store.get(key);
    if (entry?.size) {
      this.currentMemory -= entry.size;
    }
    this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
    this.currentMemory = 0;
  }

  // Get cache statistics
  getStats() {
    return {
      size: this.store.size,
      maxSize: this.maxSize,
      memoryUsed: this.currentMemory,
      maxMemory: this.maxMemory,
      hitRate: 0, // Would need to track this
    };
  }
}

// Create singleton instance
export const edgeCache = new EdgeCache(
  cacheConfig.limits.maxItems,
  cacheConfig.limits.maxMemoryMB
);

// Cache warming utilities
export async function warmCache() {
  console.log('Starting cache warming...');
  
  try {
    // Import server-side only modules
    const { getPaginatedComments, getCommentStatistics } = await import('@/lib/actions/comments');
    
    // Warm up common queries
    const commonQueries = [
      { filters: {}, page: 1, pageSize: 25 },
      { filters: { stance: 'For' }, page: 1, pageSize: 25 },
      { filters: { stance: 'Against' }, page: 1, pageSize: 25 },
      { filters: { stance: 'Neutral/Unclear' }, page: 1, pageSize: 25 },
    ];

    const warmingPromises = commonQueries.map(async (query) => {
      const cacheKey = `comments-${JSON.stringify(query)}`;
      
      // Check if already cached
      if (edgeCache.get(cacheKey)) {
        return; // Skip if already cached
      }

      const [dataResult, statsResult] = await Promise.all([
        getPaginatedComments(query),
        getCommentStatistics(query)
      ]);

      if (dataResult.success) {
        edgeCache.set(cacheKey, dataResult, cacheConfig.ttl.comments);
      }
      
      if (statsResult.success) {
        const statsCacheKey = `stats-${JSON.stringify({ filters: query.filters })}`;
        edgeCache.set(statsCacheKey, statsResult, cacheConfig.ttl.stats);
      }
    });

    await Promise.all(warmingPromises);
    console.log('Cache warming completed');
  } catch (error) {
    console.error('Cache warming failed:', error);
  }
}

// Schedule cache warming (only on server)
if (typeof window === 'undefined' && process.env.NODE_ENV === 'production') {
  // Warm cache on startup
  warmCache();
  
  // Warm cache every 23 hours
  setInterval(warmCache, 23 * 60 * 60 * 1000);
}