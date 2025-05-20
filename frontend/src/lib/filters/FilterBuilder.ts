/**
 * A composable filter builder for creating reusable and testable filters.
 * This allows us to:
 * 1. Create complex filters as compositions of simpler ones
 * 2. Make filter logic more testable
 * 3. Share common filter patterns across components
 * 4. Easily switch between different filter implementations
 * 
 * Usage example with Comment schema:
 * ```typescript
 * // Create a builder for comments
 * const builder = new FilterBuilder<Comment>();
 * 
 * // Add filters for comments with "For" stance in the "Agency Reform" category
 * builder
 *   .addFilter('stanceFilter', item => item.stance === 'For')
 *   .addFilter('categoryFilter', item => item.category === 'Agency Reform');
 * 
 * // Apply the filter to an array of comments
 * const filteredComments = builder.build()(allComments);
 * ```
 */

type ItemPredicate<T> = (item: T) => boolean;

export class FilterBuilder<T> {
  private filters: Record<string, ItemPredicate<T>> = {};
  
  /**
   * Add a filter predicate with a key
   * @param key - Unique identifier for this filter
   * @param predicate - Function that takes an item and returns true if it passes the filter
   * @returns The FilterBuilder instance for chaining
   * 
   * Example:
   * ```typescript
   * builder.addFilter('stanceFilter', comment => comment.stance === 'For');
   * ```
   */
  addFilter(key: string, predicate: ItemPredicate<T>): FilterBuilder<T> {
    this.filters[key] = predicate;
    return this;
  }
  
  /**
   * Remove a filter by key
   * @param key - Key of the filter to remove
   * @returns The FilterBuilder instance for chaining
   * 
   * Example:
   * ```typescript
   * // Create a builder with multiple filters
   * const builder = new FilterBuilder<Comment>()
   *   .addFilter('stanceFilter', comment => comment.stance === 'For')
   *   .addFilter('categoryFilter', comment => comment.category === 'Agency Reform');
   * 
   * // Remove just the stance filter
   * builder.removeFilter('stanceFilter');
   * ```
   */
  removeFilter(key: string): FilterBuilder<T> {
    delete this.filters[key];
    return this;
  }
  
  /**
   * Check if a filter with the given key exists
   * @param key - Key to check
   * @returns True if the filter exists
   * 
   * Example:
   * ```typescript
   * if (builder.hasFilter('stanceFilter')) {
   *   // Do something with the knowledge that stance is being filtered
   * }
   * ```
   */
  hasFilter(key: string): boolean {
    return key in this.filters;
  }
  
  /**
   * Build a function that applies all filters to an array of items
   * All filters are combined with AND logic (all filters must pass)
   * @returns Function that takes an array of items and returns filtered items
   * 
   * Example:
   * ```typescript
   * // Create a filter for "For" stance comments in "Agency Reform" category
   * const builder = new FilterBuilder<Comment>()
   *   .addFilter('stanceFilter', comment => comment.stance === 'For')
   *   .addFilter('categoryFilter', comment => comment.category === 'Agency Reform');
   * 
   * // Build the filter function
   * const filterFunction = builder.build();
   * 
   * // Apply it to get filtered results
   * const filteredComments = filterFunction(allComments);
   * 
   * // Or more concisely:
   * const filteredComments = builder.build()(allComments);
   * ```
   */
  build(): (items: T[]) => T[] {
    return (items: T[]) => {
      // If no filters, return all items
      if (Object.keys(this.filters).length === 0) {
        return items;
      }
      
      // Apply all filters (AND logic)
      return items.filter(item => 
        Object.values(this.filters).every(predicate => predicate(item))
      );
    };
  }
}

/**
 * Create common filter predicates for reuse across the application
 * 
 * These predicates provide reusable filter functions for different comparison types.
 * They can be used with the FilterBuilder to create complex filters.
 * 
 * Examples:
 * ```typescript
 * // Filter comments with "For" stance
 * const forStanceFilter = FilterPredicates.equals<Comment>('stance', 'For');
 * 
 * // Filter comments with themes including "Scientific integrity"
 * const integrityFilter = FilterPredicates.includes<Comment>('themes', ['Scientific integrity']);
 * 
 * // Search for "accountability" in comment text
 * const accountabilityFilter = FilterPredicates.contains<Comment>('comment', 'accountability');
 * ```
 */
export class FilterPredicates {
  /**
   * Create a filter for exact equality
   * @param key - The property key in the item
   * @param value - The value to compare against
   * @returns A predicate function
   * 
   * Example with Comments schema:
   * ```typescript
   * // Create a filter for comments with "For" stance
   * const stanceFilter = FilterPredicates.equals<Comment>('stance', 'For');
   * 
   * // Create a filter for a specific category
   * const categoryFilter = FilterPredicates.equals<Comment>('category', 'Agency Reform');
   * 
   * // Apply the filter
   * const forStanceComments = allComments.filter(stanceFilter);
   * 
   * // Use with FilterBuilder
   * const builder = new FilterBuilder<Comment>()
   *   .addFilter('stance', stanceFilter)
   *   .addFilter('category', categoryFilter);
   * ```
   */
  static equals<T>(key: string, value: unknown): ItemPredicate<T> {
    return (item: T) => {
      const itemValue = FilterPredicates.getNestedValue(item, key);
      return String(itemValue) === String(value);
    };
  }
  
  /**
   * Create a filter for array includes
   * @param key - The property key in the item
   * @param values - Array of values to check for inclusion
   * @returns A predicate function
   * 
   * Example with Comments schema:
   * ```typescript
   * // Filter comments that have either "Scientific integrity" or "Merit-based system concerns" themes
   * const themesFilter = FilterPredicates.includes<Comment>('themes', [
   *   'Scientific integrity', 
   *   'Merit-based system concerns'
   * ]);
   * 
   * // This works whether themes is stored as:
   * // 1. An array: ['Scientific integrity', 'Merit-based system concerns']
   * // 2. A comma-separated string: 'Scientific integrity, Merit-based system concerns'
   * // 3. A single value that exactly matches one of the filter values
   * 
   * // Apply the filter
   * const filteredByThemes = allComments.filter(themesFilter);
   * ```
   */
  static includes<T>(key: string, values: unknown[]): ItemPredicate<T> {
    return (item: T) => {
      if (values.length === 0) return true; // Empty filter = show all
      
      const itemValue = FilterPredicates.getNestedValue(item, key);
      
      // Handle array item values (like themes)
      if (Array.isArray(itemValue)) {
        return values.some(value => itemValue.includes(value));
      }
      
      // Handle string values that might be comma-separated
      if (typeof itemValue === 'string' && itemValue.includes(',')) {
        const itemValues = itemValue.split(',').map(v => v.trim());
        return values.some(value => itemValues.includes(String(value)));
      }
      
      // Default - check if the value is in the filter values
      return values.includes(String(itemValue));
    };
  }
  
  /**
   * Create a filter for text search
   * @param key - The property key in the item
   * @param searchText - Text to search for
   * @returns A predicate function
   * 
   * Example with Comments schema:
   * ```typescript
   * // Search for comments containing "accountability" in their text
   * const accountabilityFilter = FilterPredicates.contains<Comment>('comment', 'accountability');
   * 
   * // Search for comments mentioning "scientific integrity" in the keyQuote field
   * const integrityQuoteFilter = FilterPredicates.contains<Comment>('keyQuote', 'scientific integrity');
   * 
   * // Apply the filter
   * const accountabilityComments = allComments.filter(accountabilityFilter);
   * ```
   */
  static contains<T>(key: string, searchText: string): ItemPredicate<T> {
    const lowerSearchText = searchText.toLowerCase();
    return (item: T) => {
      const itemValue = FilterPredicates.getNestedValue(item, key);
      
      if (itemValue === undefined || itemValue === null) {
        return false;
      }
      
      return String(itemValue).toLowerCase().includes(lowerSearchText);
    };
  }
  
  /**
   * Create a filter that searches across multiple fields
   * @param keys - Array of property keys to search in
   * @param searchText - Text to search for
   * @returns A predicate function
   * 
   * Example with Comments schema:
   * ```typescript
   * // Search for "due process" in comment, title, and keyQuote fields
   * const dueProcessFilter = FilterPredicates.containsAny<Comment>(
   *   ['comment', 'title', 'keyQuote'], 
   *   'due process'
   * );
   * 
   * // This will match comments where any of these fields contains "due process"
   * const matchingComments = allComments.filter(dueProcessFilter);
   * 
   * // Common use case: global search across main text fields
   * const globalSearchFilter = FilterPredicates.containsAny<Comment>(
   *   ['comment', 'title', 'keyQuote', 'rationale', 'themes'],
   *   'accountability'
   * );
   * ```
   */
  static containsAny<T>(keys: string[], searchText: string): ItemPredicate<T> {
    const lowerSearchText = searchText.toLowerCase();
    return (item: T) => {
      return keys.some(key => {
        const itemValue = FilterPredicates.getNestedValue(item, key);
        
        if (itemValue === undefined || itemValue === null) {
          return false;
        }
        
        if (typeof itemValue === 'object' && !Array.isArray(itemValue)) {
          return false;
        }
        
        return String(itemValue).toLowerCase().includes(lowerSearchText);
      });
    };
  }
  
  /**
   * Get a value from an item by key, supporting nested paths with dot notation
   * @param obj - The object to extract value from
   * @param path - The path to the value, e.g. "user.address.city"
   * @returns The value at the path
   * 
   * Example:
   * ```typescript
   * // For a flat object like { stance: 'For', category: 'Agency Reform' }
   * const stance = FilterPredicates.getNestedValue(comment, 'stance'); // Returns 'For'
   * 
   * // For a nested object like { analysis: { stance: 'For', keyQuote: '...' } }
   * const stance = FilterPredicates.getNestedValue(comment, 'analysis.stance'); // Returns 'For'
   * ```
   */
  private static getNestedValue<T>(obj: T, path: string): unknown {
    if (!path.includes('.')) {
      return (obj as Record<string, unknown>)[path];
    }
    
    const parts = path.split('.');
    let current: unknown = obj;
    
    for (const part of parts) {
      if (current === null || current === undefined || typeof current !== 'object') {
        return undefined;
      }
      
      current = (current as Record<string, unknown>)[part];
    }
    
    return current;
  }
}