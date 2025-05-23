'use server';

import { and, or, SQL, sql } from 'drizzle-orm';
// import type { PgSelect } from 'drizzle-orm/pg-core'; // Temporarily removed to avoid unused-vars error
import { comments, stanceEnum } from './db/schema';
import { db } from './db';

const DEBUG = process.env.DEBUG_QUERIES === 'true';

export type FilterMode = 'exact' | 'includes' | 'at_least';
export type SortDirection = 'asc' | 'desc';

export interface FilterValue {
  values: unknown[];
  mode: FilterMode;
}

export interface SortOption {
  column: string;
  direction: SortDirection;
}

export interface QueryOptions {
  filters?: Record<string, unknown>;
  search?: string;
  searchFields?: string[];
  sort?: SortOption;
  page?: number;
  pageSize?: number;
}

/**
 * Gets the corresponding column from the comments table
 */
function getColumn(key: string) {
  if (key in comments) {
    return comments[key as keyof typeof comments];
  }
  return null;
}

/**
 * Builds filter conditions for the query
 */
function buildFilterConditions(filters?: Record<string, unknown>): SQL[] {
  const conditions: SQL[] = [];
  
  if (!filters) return conditions;
  
  // Process each filter
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === '') {
      continue;
    }

    // Get the column from the comments table
    const column = getColumn(key);
    if (!column) continue;

    // Handle different filter types
    if (value && typeof value === 'object' && 'values' in value && Array.isArray(value.values)) {
      // Filter objects with values and mode
      const filterValue = value as FilterValue;
      
      if (filterValue.values.length === 0) continue;
      
      if (key === 'stance') {
        // Special handling for stance enum
        if (filterValue.mode === 'at_least') {
          // Add each condition individually for "must include all" mode
          filterValue.values.forEach(stanceValue => {
            if (stanceValue === 'For') {
              conditions.push(sql`${column} = ${stanceEnum.enumValues[0]}`);
            } else if (stanceValue === 'Against') {
              conditions.push(sql`${column} = ${stanceEnum.enumValues[1]}`);
            } else if (stanceValue === 'Neutral/Unclear') {
              conditions.push(sql`${column} = ${stanceEnum.enumValues[2]}`);
            }
          });
        } 
        else if (filterValue.mode === 'exact' && filterValue.values.length === 1) {
          const stanceValue = filterValue.values[0];
          if (stanceValue === 'For') {
            conditions.push(sql`${column} = ${stanceEnum.enumValues[0]}`);
          } else if (stanceValue === 'Against') {
            conditions.push(sql`${column} = ${stanceEnum.enumValues[1]}`);
          } else if (stanceValue === 'Neutral/Unclear') {
            conditions.push(sql`${column} = ${stanceEnum.enumValues[2]}`);
          }
        } 
        else {
          // "includes" mode - any match is sufficient
          const stanceConditions: SQL[] = [];
          
          filterValue.values.forEach(stanceValue => {
            if (stanceValue === 'For') {
              stanceConditions.push(sql`${column} = ${stanceEnum.enumValues[0]}`);
            } else if (stanceValue === 'Against') {
              stanceConditions.push(sql`${column} = ${stanceEnum.enumValues[1]}`);
            } else if (stanceValue === 'Neutral/Unclear') {
              stanceConditions.push(sql`${column} = ${stanceEnum.enumValues[2]}`);
            }
          });
          
          if (stanceConditions.length > 0) {
            conditions.push(sql`(${or(...stanceConditions)})`);
          }
        }
      } 
      else if (key === 'themes') {
        // Special handling for themes with different modes
        const themeValues = filterValue.values;
        
        if (themeValues.length === 0) continue;
        
        if (filterValue.mode === 'at_least') {
          // "Must Include At Least" - ALL themes must be present (AND)
          themeValues.forEach(theme => {
            conditions.push(sql`${column} ILIKE ${`%${theme}%`}`);
          });
        } 
        else if (filterValue.mode === 'exact') {
          // "Exact Match" - exact string match
          const exactThemes = themeValues.join(',');
          conditions.push(sql`${column} = ${exactThemes}`);
        } 
        else {
          // "Must Include Any" (includes mode) - ANY theme must be present (OR)
          const themeConditions: SQL[] = [];
          
          themeValues.forEach(theme => {
            themeConditions.push(sql`${column} ILIKE ${`%${theme}%`}`);
          });
          
          if (themeConditions.length > 0) {
            conditions.push(sql`(${or(...themeConditions)})`);
          }
        }
      }
      else if (filterValue.mode === 'at_least') {
        // For "must include all" mode - add each condition
        filterValue.values.forEach(val => {
          conditions.push(sql`${column} ILIKE ${`%${val}%`}`);
        });
      } 
      else if (filterValue.mode === 'exact') {
        // For exact match mode
        const exactValue = filterValue.values.join(',');
        conditions.push(sql`${column} = ${exactValue}`);
      } 
      else {
        // For "includes" mode - any match is sufficient
        const likeConditions: SQL[] = [];
        
        filterValue.values.forEach(val => {
          likeConditions.push(sql`${column} ILIKE ${`%${val}%`}`);
        });
        
        if (likeConditions.length > 0) {
          conditions.push(sql`(${or(...likeConditions)})`);
        }
      }
    }
    else if (Array.isArray(value)) {
      // Handle array filters
      if (value.length === 0) continue;
      
      if (key === 'themes') {
        // For themes field (comma-separated string in database)
        // Default to OR (any match) behavior
        const themeConditions: SQL[] = [];
        
        value.forEach(theme => {
          if (typeof theme === 'string') {
            themeConditions.push(sql`${column} ILIKE ${`%${theme}%`}`);
          }
        });
        
        if (themeConditions.length > 0) {
          conditions.push(sql`(${or(...themeConditions)})`);
        }
      } else if (key === 'stance') {
        // Special handling for stance enum in array
        const stanceValues = value
          .map(stanceValue => {
            if (stanceValue === 'For') return stanceEnum.enumValues[0];
            if (stanceValue === 'Against') return stanceEnum.enumValues[1];
            if (stanceValue === 'Neutral/Unclear') return stanceEnum.enumValues[2];
            return null;
          })
          .filter(Boolean);
        
        if (stanceValues.length > 0) {
          conditions.push(sql`${column} IN (${stanceValues})`);
        }
      } else if (key === 'comment' || key === 'title' || key === 'keyQuote' || key === 'category' || key === 'rationale') {
        // For text fields, use ILIKE with OR for partial matches
        const textConditions: SQL[] = [];
        
        value.forEach(textValue => {
          textConditions.push(sql`${column} ILIKE ${`%${textValue}%`}`);
        });
        
        if (textConditions.length > 0) {
          conditions.push(sql`(${or(...textConditions)})`);
        }
      } else {
        // For regular array filters, use IN clause
        conditions.push(sql`${column} IN (${value})`);
      }
    }
    else {
      // Simple equality filter
      if (key === 'stance') {
        if (value === 'For') {
          conditions.push(sql`${column} = ${stanceEnum.enumValues[0]}`);
        } else if (value === 'Against') {
          conditions.push(sql`${column} = ${stanceEnum.enumValues[1]}`);
        } else if (value === 'Neutral/Unclear') {
          conditions.push(sql`${column} = ${stanceEnum.enumValues[2]}`);
        }
      } else {
        // Regular fields
        if (key === 'comment' || key === 'title' || key === 'keyQuote' || key === 'category' || key === 'rationale') {
          // Use ILIKE for text fields to search for partial matches
          conditions.push(sql`${column} ILIKE ${`%${value}%`}`);
        } else {
          // Use exact match for non-text fields
          conditions.push(sql`${column} = ${value}`);
        }
      }
    }
  }
  
  return conditions;
}

/**
 * Builds search conditions for the query
 */
function buildSearchConditions(search?: string, searchFields?: string[]): SQL[] {
  if (!search || search.trim() === '') {
    return [];
  }
  
  const searchValue = search.toLowerCase().trim();
  
  // If specific search fields are provided, only search in those
  if (searchFields && searchFields.length > 0) {
    const searchConditions: SQL[] = [];
    
    searchFields.forEach(field => {
      const column = getColumn(field);
      if (column) {
        searchConditions.push(sql`${column} ILIKE ${`%${searchValue}%`}`);
      }
    });
    
    if (searchConditions.length > 0) {
      return [sql`(${or(...searchConditions)})`];
    }
  } else {
    // If no specific fields, search in all text columns
    const textColumns = ['comment', 'title', 'keyQuote', 'themes', 'rationale', 'category'] as const;
    const searchConditions: SQL[] = [];
    
    textColumns.forEach(field => {
      const column = getColumn(field);
      if (column) {
        searchConditions.push(sql`${column} ILIKE ${`%${searchValue}%`}`);
      }
    });
    
    if (searchConditions.length > 0) {
      return [sql`(${or(...searchConditions)})`];
    }
  }
  
  return [];
}

/**
 * Builds the SQL query for fetching comments based on the provided options
 */
export async function buildCommentsQuery(options: QueryOptions): Promise<{
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  query: any; // Temporarily using any to bypass Drizzle typing issues for debugging build stalls
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  countQuery: any; // Temporarily using any
}> {
  const startTime = DEBUG ? Date.now() : 0;
  if (DEBUG) {
    console.log(`[DEBUG] Building query with options: ${JSON.stringify(options)}`);
  }
  
  // Build filter conditions
  const filterConditions = buildFilterConditions(options.filters);
  
  // Build search conditions
  const searchConditions = buildSearchConditions(options.search, options.searchFields);
  
  // Combine all conditions
  const allConditions = [...filterConditions, ...searchConditions];
  
  // Create base query
  const baseQuery = db.select().from(comments);
  
  // Create dynamic query for adding conditions
  const query = baseQuery.$dynamic();
  
  // Add where clause if there are conditions
  if (allConditions.length > 0) {
    query.where(and(...allConditions));
  }
  
  // Add sorting
  if (options.sort) {
    const { column, direction } = options.sort;
    const sortColumn = getColumn(column);
    
    if (sortColumn) {
      if (direction === 'asc') {
        query.orderBy(sql`${sortColumn} asc`);
      } else {
        query.orderBy(sql`${sortColumn} desc`);
      }
    }
  } else {
    // Default sorting
    query.orderBy(sql`${comments.createdAt} desc`);
  }
  
  // Add pagination
  if (options.page !== undefined && options.pageSize !== undefined) {
    const offset = (options.page - 1) * options.pageSize;
    query.limit(options.pageSize).offset(offset);
  }
  
  // Create count query
  const countBaseQuery = db.select({ count: sql`count(*)` }).from(comments);
  const countQuery = countBaseQuery.$dynamic();
  
  // Add where clause to count query if there are conditions
  if (allConditions.length > 0) {
    countQuery.where(and(...allConditions));
  }
  
  // Log queries for debugging
  console.log(query.toSQL());
  console.log(countQuery.toSQL());
  
  // Log before returning
  if (DEBUG) {
    console.log(`[DEBUG] Query built in ${Date.now() - startTime}ms`);
    // console.log(`[DEBUG] Data query SQL: ${query.toSQL().sql}`);
    // console.log(`[DEBUG] Count query SQL: ${countQuery.toSQL().sql}`);
  }
  
  // Return queries
  return { query, countQuery };
}

/**
 * Builds queries for statistics based on filters
 */
export async function buildStatsQueries(options: QueryOptions) {
  // Build filter conditions
  const filterConditions = buildFilterConditions(options.filters);
  
  // Build search conditions
  const searchConditions = buildSearchConditions(options.search, options.searchFields);
  
  // Combine all conditions
  const allConditions = [...filterConditions, ...searchConditions];
  
  // Create base count query
  const totalBaseQuery = db.select({ count: sql`count(*)` }).from(comments);
  const totalQuery = totalBaseQuery.$dynamic();
  
  // Add conditions to total query
  if (allConditions.length > 0) {
    totalQuery.where(and(...allConditions));
  }
  
  // Get stance column
  const stanceColumn = comments.stance;
  
  // Create stance queries
  const forBaseQuery = db.select({ count: sql`count(*)` }).from(comments);
  const againstBaseQuery = db.select({ count: sql`count(*)` }).from(comments);
  const neutralBaseQuery = db.select({ count: sql`count(*)` }).from(comments);
  
  const forQuery = forBaseQuery.$dynamic();
  const againstQuery = againstBaseQuery.$dynamic();
  const neutralQuery = neutralBaseQuery.$dynamic();
  
  // Define stance conditions
  const forCondition = sql`${stanceColumn} = ${stanceEnum.enumValues[0]}`;
  const againstCondition = sql`${stanceColumn} = ${stanceEnum.enumValues[1]}`;
  const neutralCondition = sql`${stanceColumn} = ${stanceEnum.enumValues[2]}`;
  
  // Add conditions based on whether allConditions exist
  if (allConditions.length > 0) {
    forQuery.where(and(...[...allConditions, forCondition]));
    againstQuery.where(and(...[...allConditions, againstCondition]));
    neutralQuery.where(and(...[...allConditions, neutralCondition]));
  } else {
    forQuery.where(forCondition);
    againstQuery.where(againstCondition);
    neutralQuery.where(neutralCondition);
  }
  
  return {
    totalQuery,
    forQuery,
    againstQuery,
    neutralQuery
  };
}