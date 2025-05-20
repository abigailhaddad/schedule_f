import { Comment } from '@/lib/db/schema';
import { FilterBuilder, FilterPredicates } from './FilterBuilder';

/**
 * Factory functions to create common filters used throughout the application
 * 
 * These functions help create and compose filters for the Comments dataset.
 * 
 * Examples:
 * 
 * 1. Basic filtering by stance:
 *    const builder = createCommentFilterBuilder();
 *    builder.addFilter('stance', FilterPredicates.equals('stance', 'For'));
 *    const forComments = comments.filter(builder.build());
 * 
 * 2. Search across multiple fields:
 *    const searchFilter = createSearchFilter('transparency');
 *    const transparencyComments = comments.filter(searchFilter.build());
 * 
 * 3. Combined filtering:
 *    const builder = createCommentFilterBuilder()
 *      .addFilter('stance', FilterPredicates.equals('stance', 'Against'))
 *      .addFilter('category', FilterPredicates.equals('category', 'Agency Reform'));
 *    const againstAgencyReformComments = comments.filter(builder.build());
 */

/**
 * Create a filter builder for the Comments table
 * @returns A FilterBuilder instance for Comment objects
 * 
 * Example:
 * ```typescript
 * // Create a basic filter builder
 * const builder = createCommentFilterBuilder();
 * 
 * // Add a filter to find comments with "For" stance
 * builder.addFilter('stance', FilterPredicates.equals('stance', 'For'));
 * 
 * // Apply the filter to an array of comments
 * const filteredComments = comments.filter(builder.build());
 * ```
 */
export function createCommentFilterBuilder(): FilterBuilder<Comment> {
  return new FilterBuilder<Comment>();
}

/**
 * Create a filter builder with common search functionality
 * @param searchQuery - The search query
 * @param searchFields - Array of fields to search in
 * @returns A FilterBuilder instance with search filters
 * 
 * Example:
 * ```typescript
 * // Search for "accountability" in default fields (comment, title, keyQuote, themes, rationale)
 * const searchFilter = createSearchFilter('accountability');
 * const matchingComments = comments.filter(searchFilter.build());
 * 
 * // Search for "scientific integrity" only in title and keyQuote fields
 * const titleSearchFilter = createSearchFilter('scientific integrity', ['title', 'keyQuote']);
 * const titleMatches = comments.filter(titleSearchFilter.build());
 * ```
 */
export function createSearchFilter(
  searchQuery: string,
  searchFields: string[] = ['comment', 'title', 'keyQuote', 'themes', 'rationale']
): FilterBuilder<Comment> {
  const builder = createCommentFilterBuilder();
  
  if (!searchQuery) {
    return builder;
  }
  
  return builder.addFilter(
    'search',
    FilterPredicates.containsAny(searchFields, searchQuery)
  );
}

/**
 * Create a filter builder from URL search params
 * @param searchParams - URLSearchParams object
 * @returns A FilterBuilder instance with filters from URL
 * 
 * Example:
 * ```typescript
 * // URL: /comments?filter_stance=For&filter_category=Agency%20Reform&filter_themes=["Transparency","Accountability"]
 * const urlSearchParams = new URLSearchParams(window.location.search);
 * const filterBuilder = createFilterFromParams(urlSearchParams);
 * 
 * // This will create filters equivalent to:
 * // builder.addFilter('stance', FilterPredicates.equals('stance', 'For'))
 * //        .addFilter('category', FilterPredicates.equals('category', 'Agency Reform'))
 * //        .addFilter('themes', FilterPredicates.includes('themes', ['Transparency', 'Accountability']));
 * 
 * const filteredComments = comments.filter(filterBuilder.build());
 * ```
 */
export function createFilterFromParams(
  searchParams: URLSearchParams
): FilterBuilder<Comment> {
  const builder = createCommentFilterBuilder();
  
  // Process all filter_ parameters
  for (const [key, value] of Array.from(searchParams.entries())) {
    if (!key.startsWith('filter_')) continue;
    
    const filterKey = key.replace('filter_', '');
    let filterValue: unknown;
    
    // Try to parse JSON values (for arrays, etc)
    try {
      filterValue = JSON.parse(value);
    } catch {
      // If not valid JSON, use as string
      filterValue = value;
    }
    
    // Apply the appropriate filter type based on the value
    // For example, if the filterKey is 'themes' and the filterValue is an array, we want to use the includes filter
    if (Array.isArray(filterValue)) {
      builder.addFilter(
        filterKey,
        FilterPredicates.includes(filterKey, filterValue)
      );
    } else if (typeof filterValue === 'string') {
      if (filterKey === 'themes' || filterKey === 'analysis.themes') {
        // Themes are treated as multi-select
        // For example, filter_themes=Merit-based would filter for comments containing this theme
        builder.addFilter(
          filterKey,
          FilterPredicates.includes(filterKey, [filterValue])
        );
      } else {
        // Other string values use exact match
        // For example, filter_stance=For would filter for comments with stance exactly "For"
        builder.addFilter(
          filterKey,
          FilterPredicates.equals(filterKey, filterValue)
        );
      }
    }
  }
  
  return builder;
}

/**
 * Create a filter builder based on a filters object
 * @param filters - Object with filter key-value pairs
 * @returns A FilterBuilder instance with the specified filters
 * 
 * Example:
 * ```typescript
 * // Filter for "For" stance comments in the "Agency Reform" category
 * const filtersObject = {
 *   "stance": "For",
 *   "category": "Agency Reform"
 * };
 * const filterBuilder = createFilterFromObject(filtersObject);
 * const filteredComments = comments.filter(filterBuilder.build());
 * 
 * // Filter for comments with multiple themes
 * const themeFilters = {
 *   "themes": ["Due process/employee rights", "Merit-based system concerns"]
 * };
 * const themeFilterBuilder = createFilterFromObject(themeFilters);
 * // This returns comments that contain ANY of the specified themes
 * const themeFilteredComments = comments.filter(themeFilterBuilder.build());
 * 
 * // Complex multiple filters example
 * const complexFilters = {
 *   "stance": "Against",
 *   "category": "Agency Reform",
 *   "themes": ["Scientific integrity", "Politicization concerns"]
 * };
 * const complexBuilder = createFilterFromObject(complexFilters);
 * // Returns comments with stance "Against", category "Agency Reform", and containing 
 * // either "Scientific integrity" or "Politicization concerns" themes
 * const complexFilteredComments = comments.filter(complexBuilder.build());
 * ```
 */
export function createFilterFromObject(
  filters: Record<string, unknown>
): FilterBuilder<Comment> {
  const builder = createCommentFilterBuilder();
  
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    
    if (Array.isArray(value)) {
      if (value.length === 0) return;
      
      builder.addFilter(
        key,
        FilterPredicates.includes(key, value)
      );
    } else {
      builder.addFilter(
        key,
        FilterPredicates.equals(key, value)
      );
    }
  });
  
  return builder;
}