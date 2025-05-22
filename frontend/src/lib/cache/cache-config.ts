// src/lib/cache-config.ts
export const cacheConfig = {
  // Cache for 23 hours since data updates daily
  maxAge: 60 * 60 * 23, // 23 hours
  
  // Enable caching in all environments for this use case
  disableCacheInDevelopment: false,
  
  // Different cache durations for different data types
  ttl: {
    // Comments data cached for 23 hours
    comments: 60 * 60 * 23,
    
    // Statistics cached for 23 hours
    stats: 60 * 60 * 23,
    
    // Individual comment details cached for 23 hours
    commentDetail: 60 * 60 * 23,
    
    // Search results cached for 1 hour (might have more variations)
    searchResults: 60 * 60,
  },
  
  // Cache size limits
  limits: {
    maxItems: 1000, // Increased for better performance
    maxMemoryMB: 100, // Approximate memory limit
  }
};