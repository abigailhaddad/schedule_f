'use server';

import { SQL, sql } from 'drizzle-orm';
import { comments, stanceEnum } from './db/schema';

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
 * Builds a SQL query for the comments table based on provided filters and options
 */
export async function buildCommentsQuery(options: QueryOptions): Promise<{
  query: SQL;
  countQuery: SQL;
  params: Record<string, unknown>;
}> {
  const params: Record<string, unknown> = {};
  const whereClause = sql.empty();
  let whereConditionsCount = 0;

  // Process filters
  if (options.filters) {
    Object.entries(options.filters).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') {
        return;
      }

      // Get the column from the comments table
      const column = comments[key as keyof typeof comments];
      if (!column) return;

      // Handle different filter types
      if (value && typeof value === 'object' && 'values' in value && Array.isArray(value.values)) {
        // Handle filter objects with values and mode
        const filterValue = value as FilterValue;
        
        if (filterValue.values.length === 0) return;
        
        if (key === 'stance') {
          // Special handling for stance enum in complex filters
          if (filterValue.mode === 'at_least') {
            // For "must include all" mode - requires all conditions to be true
            const conditions = filterValue.values.map((stanceValue) => {
              if (stanceValue === 'For') {
                return sql`${column} = ${stanceEnum.enumValues[0]}`;
              } else if (stanceValue === 'Against') {
                return sql`${column} = ${stanceEnum.enumValues[1]}`;
              } else if (stanceValue === 'Neutral/Unclear') {
                return sql`${column} = ${stanceEnum.enumValues[2]}`;
              }
              return sql`1=0`; // Default to false condition for unknown values
            });
            
            if (conditions.length > 0) {
              const andCondition = sql.join(conditions, sql` AND `);
              
              if (whereConditionsCount > 0) {
                whereClause.append(sql` AND (`);
                whereClause.append(andCondition);
                whereClause.append(sql`)`);
              } else {
                whereClause.append(sql` WHERE (`);
                whereClause.append(andCondition);
                whereClause.append(sql`)`);
                whereConditionsCount++;
              }
            }
          } 
          else if (filterValue.mode === 'exact') {
            if (filterValue.values.length === 1) {
              const stanceValue = filterValue.values[0];
              if (stanceValue === 'For') {
                if (whereConditionsCount > 0) {
                  whereClause.append(sql` AND ${column} = ${stanceEnum.enumValues[0]}`);
                } else {
                  whereClause.append(sql` WHERE ${column} = ${stanceEnum.enumValues[0]}`);
                  whereConditionsCount++;
                }
              } else if (stanceValue === 'Against') {
                if (whereConditionsCount > 0) {
                  whereClause.append(sql` AND ${column} = ${stanceEnum.enumValues[1]}`);
                } else {
                  whereClause.append(sql` WHERE ${column} = ${stanceEnum.enumValues[1]}`);
                  whereConditionsCount++;
                }
              } else if (stanceValue === 'Neutral/Unclear') {
                if (whereConditionsCount > 0) {
                  whereClause.append(sql` AND ${column} = ${stanceEnum.enumValues[2]}`);
                } else {
                  whereClause.append(sql` WHERE ${column} = ${stanceEnum.enumValues[2]}`);
                  whereConditionsCount++;
                }
              }
            }
          } 
          else {
            // For includes mode (default) - any match is sufficient
            const stanceConditions = filterValue.values.map((stanceValue) => {
              if (stanceValue === 'For') {
                return sql`${column} = ${stanceEnum.enumValues[0]}`;
              } else if (stanceValue === 'Against') {
                return sql`${column} = ${stanceEnum.enumValues[1]}`;
              } else if (stanceValue === 'Neutral/Unclear') {
                return sql`${column} = ${stanceEnum.enumValues[2]}`;
              }
              return sql`1=0`; // Default to false condition for unknown values
            });
            
            if (stanceConditions.length > 0) {
              const orCondition = sql.join(stanceConditions, sql` OR `);
              
              if (whereConditionsCount > 0) {
                whereClause.append(sql` AND (`);
                whereClause.append(orCondition);
                whereClause.append(sql`)`);
              } else {
                whereClause.append(sql` WHERE (`);
                whereClause.append(orCondition);
                whereClause.append(sql`)`);
                whereConditionsCount++;
              }
            }
          }
        } 
        else if (filterValue.mode === 'at_least') {
          // For "must include all" mode - requires all conditions to be true
          const conditions = filterValue.values.map((val, index) => {
            const paramName = `${key}_${index}`;
            params[paramName] = `%${val}%`;
            return sql`${column} LIKE ${sql.param(paramName)}`;
          });
          
          if (conditions.length > 0) {
            const andCondition = sql.join(conditions, sql` AND `);
            
            if (whereConditionsCount > 0) {
              whereClause.append(sql` AND (`);
              whereClause.append(andCondition);
              whereClause.append(sql`)`);
            } else {
              whereClause.append(sql` WHERE (`);
              whereClause.append(andCondition);
              whereClause.append(sql`)`);
              whereConditionsCount++;
            }
          }
        } 
        else if (filterValue.mode === 'exact') {
          // For exact match mode
          const exactValue = filterValue.values.join(',');
          params[key] = exactValue;
          
          if (whereConditionsCount > 0) {
            whereClause.append(sql` AND ${column} = ${sql.param(key)}`);
          } else {
            whereClause.append(sql` WHERE ${column} = ${sql.param(key)}`);
            whereConditionsCount++;
          }
        } 
        else {
          // For includes mode (default) - any match is sufficient
          const orConditions = filterValue.values.map((val, index) => {
            const paramName = `${key}_${index}`;
            params[paramName] = `%${val}%`;
            return sql`${column} LIKE ${sql.param(paramName)}`;
          });
          
          if (orConditions.length > 0) {
            const orCondition = sql.join(orConditions, sql` OR `);
            
            if (whereConditionsCount > 0) {
              whereClause.append(sql` AND (`);
              whereClause.append(orCondition);
              whereClause.append(sql`)`);
            } else {
              whereClause.append(sql` WHERE (`);
              whereClause.append(orCondition);
              whereClause.append(sql`)`);
              whereConditionsCount++;
            }
          }
        }
      }
      else if (Array.isArray(value)) {
        // Handle array filters
        if (value.length === 0) return;
        
        if (key === 'themes') {
          // For themes field (which is a comma-separated string in the database)
          const orConditions = value.map((theme, index) => {
            const paramName = `${key}_${index}`;
            params[paramName] = `%${theme}%`;
            return sql`${column} LIKE ${sql.param(paramName)}`;
          });
          
          if (orConditions.length > 0) {
            const orCondition = sql.join(orConditions, sql` OR `);
            
            if (whereConditionsCount > 0) {
              whereClause.append(sql` AND (`);
              whereClause.append(orCondition);
              whereClause.append(sql`)`);
            } else {
              whereClause.append(sql` WHERE (`);
              whereClause.append(orCondition);
              whereClause.append(sql`)`);
              whereConditionsCount++;
            }
          }
        } else if (key === 'stance') {
          // Special handling for stance enum in array
          const stanceConditions = value.map((stanceValue) => {
            if (stanceValue === 'For') {
              return sql`${column} = ${stanceEnum.enumValues[0]}`;
            } else if (stanceValue === 'Against') {
              return sql`${column} = ${stanceEnum.enumValues[1]}`;
            } else if (stanceValue === 'Neutral/Unclear') {
              return sql`${column} = ${stanceEnum.enumValues[2]}`;
            }
            return sql`1=0`; // Default to false condition for unknown values
          });
          
          if (stanceConditions.length > 0) {
            const orCondition = sql.join(stanceConditions, sql` OR `);
            
            if (whereConditionsCount > 0) {
              whereClause.append(sql` AND (`);
              whereClause.append(orCondition);
              whereClause.append(sql`)`);
            } else {
              whereClause.append(sql` WHERE (`);
              whereClause.append(orCondition);
              whereClause.append(sql`)`);
              whereConditionsCount++;
            }
          }
        } else {
          // For regular array filters, use IN clause with string parameters
          const placeholders = value.map((_, index) => {
            const paramName = `${key}_${index}`;
            params[paramName] = value[index];
            return sql`${sql.param(paramName)}`;
          });
          
          if (placeholders.length > 0) {
            const inListSql = sql.join(placeholders, sql`, `);
            
            if (whereConditionsCount > 0) {
              whereClause.append(sql` AND ${column} IN (`);
              whereClause.append(inListSql);
              whereClause.append(sql`)`);
            } else {
              whereClause.append(sql` WHERE ${column} IN (`);
              whereClause.append(inListSql);
              whereClause.append(sql`)`);
              whereConditionsCount++;
            }
          }
        }
      }
      else {
        // Simple equality filter
        
        // Special handling for stance enum
        if (key === 'stance') {
          if (whereConditionsCount > 0) {
            if (value === 'For') {
              whereClause.append(sql` AND ${column} = ${stanceEnum.enumValues[0]}`);
            } else if (value === 'Against') {
              whereClause.append(sql` AND ${column} = ${stanceEnum.enumValues[1]}`);
            } else if (value === 'Neutral/Unclear') {
              whereClause.append(sql` AND ${column} = ${stanceEnum.enumValues[2]}`);
            }
          } else {
            if (value === 'For') {
              whereClause.append(sql` WHERE ${column} = ${stanceEnum.enumValues[0]}`);
            } else if (value === 'Against') {
              whereClause.append(sql` WHERE ${column} = ${stanceEnum.enumValues[1]}`);
            } else if (value === 'Neutral/Unclear') {
              whereClause.append(sql` WHERE ${column} = ${stanceEnum.enumValues[2]}`);
            }
            whereConditionsCount++;
          }
        } else {
          // Regular fields
          params[key] = value;
          
          if (whereConditionsCount > 0) {
            whereClause.append(sql` AND ${column} = ${sql.param(key)}`);
          } else {
            whereClause.append(sql` WHERE ${column} = ${sql.param(key)}`);
            whereConditionsCount++;
          }
        }
      }
    });
  }

  // Process search
  if (options.search && options.search.trim() !== '') {
    const searchValue = options.search.toLowerCase().trim();
    params.search = `%${searchValue}%`;
    
    // If specific search fields are provided, only search in those
    if (options.searchFields && options.searchFields.length > 0) {
      const searchConditions = options.searchFields
        .map(field => {
          const column = comments[field as keyof typeof comments];
          if (!column) return null;
          return sql`${column} ILIKE ${sql.param('search')}`;
        })
        .filter(Boolean);
      
      if (searchConditions.length > 0) {
        const orCondition = sql.join(searchConditions as SQL[], sql` OR `);
        
        if (whereConditionsCount > 0) {
          whereClause.append(sql` AND (`);
          whereClause.append(orCondition);
          whereClause.append(sql`)`);
        } else {
          whereClause.append(sql` WHERE (`);
          whereClause.append(orCondition);
          whereClause.append(sql`)`);
          whereConditionsCount++;
        }
      }
    } else {
      // If no specific fields, search in all text columns
      const textColumns = ['comment', 'title', 'keyQuote', 'themes', 'rationale', 'category'] as const;
      const searchConditions = textColumns
        .map(field => sql`${comments[field]} ILIKE ${sql.param('search')}`)
        .filter(Boolean);
      
      if (searchConditions.length > 0) {
        const orCondition = sql.join(searchConditions, sql` OR `);
        
        if (whereConditionsCount > 0) {
          whereClause.append(sql` AND (`);
          whereClause.append(orCondition);
          whereClause.append(sql`)`);
        } else {
          whereClause.append(sql` WHERE (`);
          whereClause.append(orCondition);
          whereClause.append(sql`)`);
          whereConditionsCount++;
        }
      }
    }
  }

  // Build the base queries
  const query = sql`SELECT * FROM ${comments}`;
  const countQuery = sql`SELECT COUNT(*) FROM ${comments}`;
  
  // Add where clause if there are conditions
  if (whereConditionsCount > 0) {
    query.append(whereClause);
    countQuery.append(whereClause);
  }
  
  // Build sorting
  if (options.sort) {
    const { column, direction } = options.sort;
    const sortColumn = comments[column as keyof typeof comments];
    
    if (sortColumn) {
      if (direction === 'asc') {
        query.append(sql` ORDER BY ${sortColumn} ASC`);
      } else {
        query.append(sql` ORDER BY ${sortColumn} DESC`);
      }
    }
  } else {
    // Default sorting
    query.append(sql` ORDER BY ${comments.createdAt} DESC`);
  }
  
  // Add pagination
  if (options.page !== undefined && options.pageSize !== undefined) {
    const offset = (options.page - 1) * options.pageSize;
    
    // Use direct integer values instead of named parameters
    query.append(sql` LIMIT ${options.pageSize} OFFSET ${offset}`);
  }

  return { query, countQuery, params };
}

/**
 * Builds SQL queries for statistics based on filters
 */
export async function buildStatsQueries(options: QueryOptions): Promise<{
  totalQuery: SQL;
  forQuery: SQL;
  againstQuery: SQL;
  neutralQuery: SQL;
  params: Record<string, unknown>;
}> {
  // Build a base query first to get the WHERE conditions
  const baseQueryResult = await buildCommentsQuery({ ...options, page: undefined, pageSize: undefined });
  const params = baseQueryResult.params;
  
  // Base query for total count (already has WHERE clause if needed)
  const totalQuery = baseQueryResult.countQuery;
  
  // Create stance-specific queries by adding to the WHERE clause
  let forQuery, againstQuery, neutralQuery;
  
  // Create new queries for each stance using the enum values
  const baseWhere = baseQueryResult.countQuery.toString().replace('SELECT COUNT(*) FROM comments', '');
  
  // Create separate queries instead of trying to modify the original SQL
  if (baseWhere.includes('WHERE')) {
    forQuery = sql`SELECT COUNT(*) FROM ${comments} WHERE ${comments.stance} = ${stanceEnum.enumValues[0]}${sql.raw(baseWhere.replace('WHERE', 'AND'))}`;
    againstQuery = sql`SELECT COUNT(*) FROM ${comments} WHERE ${comments.stance} = ${stanceEnum.enumValues[1]}${sql.raw(baseWhere.replace('WHERE', 'AND'))}`;
    neutralQuery = sql`SELECT COUNT(*) FROM ${comments} WHERE ${comments.stance} = ${stanceEnum.enumValues[2]}${sql.raw(baseWhere.replace('WHERE', 'AND'))}`;
  } else {
    forQuery = sql`SELECT COUNT(*) FROM ${comments} WHERE ${comments.stance} = ${stanceEnum.enumValues[0]}`;
    againstQuery = sql`SELECT COUNT(*) FROM ${comments} WHERE ${comments.stance} = ${stanceEnum.enumValues[1]}`;
    neutralQuery = sql`SELECT COUNT(*) FROM ${comments} WHERE ${comments.stance} = ${stanceEnum.enumValues[2]}`;
  }
  
  return {
    totalQuery,
    forQuery,
    againstQuery,
    neutralQuery,
    params
  };
}