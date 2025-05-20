'use client';

import { useState, useEffect, useMemo } from 'react';
import { SortingState } from '@/components/ui/DataTable';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';

interface UseDataTableOptions<T> {
  data: T[];
  filters?: Record<string, unknown>;
  initialPageSize?: number;
  initialSorting?: SortingState;
  searchFields?: string[];
}

export function useDataTable<T extends Record<string, unknown>>({
  data,
  filters = {},
  initialPageSize = 10,
  initialSorting,
  searchFields = []
}: UseDataTableOptions<T>) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();

  // Initialize from URL params if available
  const urlSort = searchParams.get('sort');
  const urlSortDirection = searchParams.get('sortDirection') as 'asc' | 'desc' | null;
  const urlSearch = searchParams.get('search') || '';

  // Search state
  const [searchQuery, setSearchQuery] = useState(urlSearch);
  const [sorting, setSorting] = useState<SortingState | undefined>(
    urlSort && urlSortDirection 
      ? { column: urlSort, direction: urlSortDirection } 
      : initialSorting
  );
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [currentPage, setCurrentPage] = useState(1);
  const [isInitialMount, setIsInitialMount] = useState(true);
  
  // Update URL when sorting or search changes
  useEffect(() => {
    if (isInitialMount) {
      setIsInitialMount(false);
      return;
    }

    // Create a new URLSearchParams object
    const params = new URLSearchParams(searchParams.toString());
    
    // Update sorting parameters
    if (sorting) {
      params.set('sort', sorting.column);
      params.set('sortDirection', sorting.direction);
    } else {
      params.delete('sort');
      params.delete('sortDirection');
    }
    
    // Update search parameter
    if (searchQuery) {
      params.set('search', searchQuery);
    } else {
      params.delete('search');
    }
    
    // Update URL without refreshing page
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    
    // Log the current sorting state for debugging
    console.log('Sorting updated:', sorting);
  }, [searchQuery, sorting, router, pathname, searchParams, isInitialMount]);

  // Reset page when filters or search changes
  useEffect(() => {
    if (!isInitialMount) {
      setCurrentPage(1);
    }
  }, [searchQuery, filters, isInitialMount]);

  // Filter data based on filters and search query
  const filteredData = useMemo(() => {
    // Start with all data
    let result = [...data];

    // Apply filters
    Object.entries(filters).forEach(([key, filterValue]) => {
      if (filterValue !== undefined && filterValue !== null && filterValue !== '') {
        result = result.filter(item => {
          // Get the actual value from the item
          let itemValue: unknown;
          
          // Check if the filter is for nested fields (e.g., 'analysis.stance')
          if (key.includes('.')) {
            const [parent, child] = key.split('.');
            const parentObj = item[parent] as Record<string, unknown> | undefined;
            itemValue = parentObj ? parentObj[child] : undefined;
          } else {
            itemValue = item[key];
          }
          
          // Handle different filter value types
          if (Array.isArray(filterValue)) {
            // For array filters (like multi-select), check if the value is in the array
            if (filterValue.length === 0) return true; // Empty filter = show all
            
            // Special handling for themes - check if any selected theme is in the item's themes array
            if (key === 'themes' || key === 'analysis.themes') {
              // If itemValue is an array, check if any of the filter values is included
              if (Array.isArray(itemValue)) {
                return filterValue.some(theme => itemValue.includes(theme));
              }
              // If itemValue is a string, check if it equals any of the filter values
              return filterValue.includes(String(itemValue));
            }
            
            // Default array handling - exact match
            return filterValue.includes(String(itemValue));
          } else {
            // For single value filters, do direct comparison
            return String(itemValue) === String(filterValue);
          }
        });
      }
    });

    // Apply search query if provided
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(item => {
        // If searchFields are provided, only search in those fields
        if (searchFields.length > 0) {
          return searchFields.some(field => {
            const value = getNestedValue(item, field);
            return value !== undefined && String(value).toLowerCase().includes(query);
          });
        }
        
        // Otherwise search in all fields
        return Object.entries(item).some(([key, value]) => {
          // Skip searching in complex objects or arrays unless they're strings
          if (typeof value === 'object' && value !== null) {
            if (key === 'analysis') {
              // Special case for analysis object
              const analysisObj = value as Record<string, unknown>;
              return Object.values(analysisObj).some(
                v => v !== undefined && String(v).toLowerCase().includes(query)
              );
            }
            return false;
          }
          return value !== undefined && String(value).toLowerCase().includes(query);
        });
      });
    }

    return result;
  }, [data, filters, searchQuery, searchFields]);

  // Sort data if sorting is specified
  const sortedData = useMemo(() => {
    if (!sorting) return filteredData;
    
    return [...filteredData].sort((a, b) => {
      const aValue = getNestedValue(a, sorting.column);
      const bValue = getNestedValue(b, sorting.column);
      
      if (aValue === bValue) return 0;
      
      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;
      
      const modifier = sorting.direction === 'asc' ? 1 : -1;
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return aValue.localeCompare(bValue) * modifier;
      }
      
      return ((aValue < bValue) ? -1 : 1) * modifier;
    });
  }, [filteredData, sorting]);

  // Paginate data
  const totalItems = sortedData.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return sortedData.slice(start, end);
  }, [sortedData, currentPage, pageSize]);

  // Pagination controls
  const goToPage = (page: number) => {
    setCurrentPage(page);
  };
  
  const nextPage = () => {
    setCurrentPage(prev => Math.min(prev + 1, totalPages));
  };
  
  const previousPage = () => {
    setCurrentPage(prev => Math.max(prev - 1, 1));
  };
  
  const canNextPage = currentPage < totalPages;
  const canPreviousPage = currentPage > 1;

  // Handle sorting
  const handleSort = (column: string) => {
    setSorting(prev => {
      if (prev?.column === column) {
        return {
          column,
          direction: prev.direction === 'asc' ? 'desc' : 'asc'
        };
      }
      return {
        column,
        direction: 'asc'
      };
    });
    
    // Reset to first page when sorting changes
    setCurrentPage(1);
  };

  // Export to CSV
  const exportCSV = () => {
    // Get all unique keys from the data
    const keys = new Set<string>();
    filteredData.forEach(item => {
      Object.keys(item).forEach(key => {
        // Skip complex objects like 'analysis' for direct export
        if (typeof item[key] !== 'object' || item[key] === null) {
          keys.add(key);
        }
      });
      // Add analysis fields if they exist
      const analysis = item['analysis'] as Record<string, unknown> | undefined;
      if (analysis) {
        Object.keys(analysis).forEach(key => {
          keys.add(`analysis.${key}`);
        });
      }
    });
    
    // Convert Set to Array and sort
    const headers = Array.from(keys);
    
    // Create CSV header row
    let csv = headers.map(key => `"${key}"`).join(',') + '\n';
    
    // Add data rows
    filteredData.forEach(item => {
      const row = headers.map(key => {
        let value: unknown;
        if (key.includes('.')) {
          const [parent, child] = key.split('.');
          const parentObj = item[parent] as Record<string, unknown> | undefined;
          value = parentObj ? parentObj[child] : '';
        } else {
          value = item[key];
        }
        
        // Handle different value types
        if (value === null || value === undefined) {
          return '';
        }
        if (typeof value === 'string') {
          // Escape quotes in string values
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      });
      
      csv += row.join(',') + '\n';
    });
    
    // Create and download the CSV file
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'export.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Helper function to get nested values
  function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
    if (!path.includes('.')) {
      return obj[path];
    }
    
    const [parent, child] = path.split('.');
    const parentObj = obj[parent] as Record<string, unknown> | undefined;
    return parentObj ? parentObj[child] : undefined;
  }

  // Return all the table state and controls
  return {
    filteredData,
    sortedData,
    paginatedData,
    searchQuery,
    setSearchQuery,
    sorting,
    setSorting,
    handleSort,
    exportCSV,
    // Pagination
    pageSize,
    setPageSize,
    currentPage,
    setCurrentPage,
    totalPages,
    goToPage,
    nextPage,
    previousPage,
    canNextPage,
    canPreviousPage,
    totalItems
  };
} 