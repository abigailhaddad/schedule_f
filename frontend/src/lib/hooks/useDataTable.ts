import { useState, useEffect, useMemo, useRef } from 'react';
import { CommentWithAnalysis } from '@/lib/db/schema';
import { Field, datasetConfig } from '@/lib/config';
import MiniSearch from 'minisearch';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';

type UseDataTableOptions = {
  data: CommentWithAnalysis[];
  filters: Record<string, unknown>;
}

export function useDataTable({ data, filters }: UseDataTableOptions) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  
  // Track initial render
  const isInitialMount = useRef(true);
  
  const [filteredData, setFilteredData] = useState<CommentWithAnalysis[]>(data);
  const [searchQuery, setSearchQuery] = useState(() => {
    // Initialize search query from URL
    return searchParams.get('query') || '';
  });
  const [searchIndex, setSearchIndex] = useState<MiniSearch | null>(null);
  
  // Initialize sorting state from URL or defaults
  const [sorting, setSorting] = useState<{column: string, direction: 'asc' | 'desc'} | null>(() => {
    const sortColumn = searchParams.get('sort');
    const sortDir = searchParams.get('dir');
    
    if (sortColumn && (sortDir === 'asc' || sortDir === 'desc')) {
      return {
        column: sortColumn,
        direction: sortDir
      };
    }
    
    return null;
  });
  
  // Initialize pagination state from URL or defaults
  const [currentPage, setCurrentPage] = useState(() => {
    const pageParam = searchParams.get('page');
    return pageParam ? parseInt(pageParam, 10) : 1;
  });
  
  const [pageSize, setPageSize] = useState(() => {
    const sizeParam = searchParams.get('size');
    return sizeParam ? parseInt(sizeParam, 10) : 10;
  });
  
  // Update URL when pagination state changes
  useEffect(() => {
    // Skip URL updates on initial render since we're already getting values from URL
    if (isInitialMount.current) {
      isInitialMount.current = false;
      return;
    }
    
    const params = new URLSearchParams(searchParams.toString());
    params.set('page', currentPage.toString());
    params.set('size', pageSize.toString());
    
    // Don't update URL if it's already the same
    if (params.toString() === searchParams.toString()) {
      return;
    }
    
    // Update URL without forcing a navigation
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }, [currentPage, pageSize, pathname, router, searchParams]);
  
  // Update URL when sorting changes
  useEffect(() => {
    // Skip URL updates on initial render
    if (isInitialMount.current) {
      return;
    }
    
    const params = new URLSearchParams(searchParams.toString());
    
    if (sorting) {
      params.set('sort', sorting.column);
      params.set('dir', sorting.direction);
    } else {
      params.delete('sort');
      params.delete('dir');
    }
    
    // Don't update URL if it's already the same
    if (params.toString() === searchParams.toString()) {
      return;
    }
    
    // Update URL without forcing a navigation
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }, [sorting, pathname, router, searchParams]);
  
  // Initialize search index
  useEffect(() => {
    if (!data.length) return;
    
    // Create search index
    const index = new MiniSearch({
      fields: ['title', 'keyQuote', 'comment', 'originalComment'],
      storeFields: ['id'],
      idField: 'id',
      searchOptions: {
        fuzzy: 0.2,
        prefix: true,
        boost: { keyQuote: 2, title: 1.5 }
      }
    });
    
    // Format the data for search indexing
    const searchDocuments = data.map(item => ({
      id: item.id,
      title: item.title || '',
      keyQuote: item.analysis?.keyQuote || '',
      comment: item.comment || '',
      originalComment: item.originalComment || ''
    }));
    
    // Add documents to index
    index.addAll(searchDocuments);
    setSearchIndex(index);
  }, [data]);
  
  // Apply filters, search, and sorting
  useEffect(() => {
    let result = [...data];
    
    // Apply filters
    if (Object.keys(filters).length > 0) {
      result = applyFilters(result, filters);
    }
    
    // Apply search
    if (searchQuery && searchIndex) {
      result = applySearch(result, searchQuery, searchIndex);
    }
    
    // Apply sorting
    if (sorting) {
      result = applySorting(result, sorting);
    }
    
    // Only reset to first page when filters or search changes AFTER the initial render
    if (!isInitialMount.current) {
      // Reset to first page when filters or search query changes
      // Only if the current dependencies change, not on component mount
      if (searchQuery || Object.keys(filters).length > 0) {
        setCurrentPage(1);
      }
    }
    
    setFilteredData(result);
  }, [data, filters, searchQuery, searchIndex, sorting]);
  
  // Filter implementation
  const applyFilters = (items: CommentWithAnalysis[], filterValues: Record<string, unknown>) => {
    return items.filter(item => {
      for (const [key, value] of Object.entries(filterValues)) {
        if (!value) continue;
        
        const field = datasetConfig.fields.find(f => f.key === key);
        if (!field) continue;
        
        // Handle different filter types
        if (Array.isArray(value) && value.length > 0) {
          // For analysis fields like stance and themes
          if (key === 'stance' && item.analysis) {
            if (!value.includes(item.analysis.stance)) return false;
          } else if (key === 'themes' && item.analysis) {
            // Handle multi-label themes (comma-separated)
            const themes = item.analysis.themes?.split(',').map(t => t.trim().toLowerCase());
            if (!themes || !value.some(v => themes.includes(String(v).toLowerCase()))) return false;
          } else {
            // Standard string comparison for other fields
            const fieldValue = String(item[key as keyof typeof item] || '').toLowerCase();
            if (!value.some(v => fieldValue.includes(String(v).toLowerCase()))) return false;
          }
        }
      }
      return true;
    });
  };
  
  // Search implementation
  const applySearch = (items: CommentWithAnalysis[], query: string, index: MiniSearch) => {
    const searchResults = index.search(query);
    const resultIds = new Set(searchResults.map(r => r.id));
    return items.filter(item => resultIds.has(item.id));
  };
  
  // Sorting implementation
  const applySorting = (items: CommentWithAnalysis[], sortConfig: {column: string, direction: 'asc' | 'desc'}) => {
    return [...items].sort((a, b) => {
      const { column, direction } = sortConfig;
      
      // Handle analysis fields
      if (column === 'stance' || column === 'keyQuote' || column === 'themes' || column === 'rationale') {
        const valueA = a.analysis?.[column as keyof typeof a.analysis]?.toString().toLowerCase() || '';
        const valueB = b.analysis?.[column as keyof typeof b.analysis]?.toString().toLowerCase() || '';
        return direction === 'asc' 
          ? valueA.localeCompare(valueB)
          : valueB.localeCompare(valueA);
      }
      
      // Handle regular fields
      const valueA = String(a[column as keyof typeof a] || '').toLowerCase();
      const valueB = String(b[column as keyof typeof b] || '').toLowerCase();
      
      return direction === 'asc' 
        ? valueA.localeCompare(valueB)
        : valueB.localeCompare(valueA);
    });
  };
  
  // Calculate paginated data
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return filteredData.slice(start, end);
  }, [filteredData, currentPage, pageSize]);
  
  // Calculate total pages
  const totalPages = useMemo(() => {
    return Math.ceil(filteredData.length / pageSize);
  }, [filteredData, pageSize]);
  
  // Helper to check if can go to previous page
  const canPreviousPage = currentPage > 1;
  
  // Helper to check if can go to next page
  const canNextPage = currentPage < totalPages;
  
  // Handle page change with URL update
  const goToPage = (page: number) => {
    const newPage = Math.max(1, Math.min(page, totalPages || 1));
    setCurrentPage(newPage);
  };
  
  // Helper to go to next page
  const nextPage = () => {
    if (canNextPage) {
      setCurrentPage(prev => prev + 1);
    }
  };
  
  // Helper to go to previous page
  const previousPage = () => {
    if (canPreviousPage) {
      setCurrentPage(prev => prev - 1);
    }
  };
  
  // Handle page size change
  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    // Don't reset to first page on initial render
    if (!isInitialMount.current) {
      setCurrentPage(1); // Reset to first page when changing page size after initial render
    }
  };
  
  // Helper for CSV export
  const exportCSV = () => {
    if (filteredData.length === 0) {
      alert('No data to export');
      return;
    }
    
    const visibleFields = datasetConfig.fields.filter(f => f.visible);
    const headers = visibleFields.map(f => f.title);
    
    // Create CSV content
    let csv = headers.join(',') + '\n';
    
    filteredData.forEach(item => {
      const line = visibleFields.map(field => {
        // Get appropriate value based on field type
        let value: string;
        
        if (field.key === 'stance' || field.key === 'keyQuote' || 
            field.key === 'themes' || field.key === 'rationale') {
          value = String(item.analysis?.[field.key as keyof typeof item.analysis] || '');
        } else {
          value = String(item[field.key as keyof typeof item] || '');
        }
        
        // Format specific field types
        if (field.format === 'currency' && value) {
          const num = parseFloat(value);
          value = !isNaN(num) ? num.toFixed(2) : value;
        }
        
        // Escape special characters for CSV
        value = value.replace(/"/g, '""');
        if (value.includes(',') || value.includes('"') || value.includes('\n')) {
          value = `"${value}"`;
        }
        
        return value;
      });
      
      csv += line.join(',') + '\n';
    });
    
    // Download the file
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `comments-export-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };
  
  // Sort toggle handler with URL update
  const handleSort = (column: string) => {
    if (sorting?.column === column) {
      // Toggle direction if same column
      setSorting({
        column,
        direction: sorting.direction === 'asc' ? 'desc' : 'asc'
      });
    } else {
      // New column, default to ascending
      setSorting({
        column,
        direction: 'asc'
      });
    }
    
    // Only reset to first page when sorting changes AFTER the initial render
    if (!isInitialMount.current) {
      setCurrentPage(1); // Reset to first page when sort changes after initial render
    }
  };
  
  // Update search query
  const updateSearchQuery = (query: string) => {
    setSearchQuery(query);
    
    // Only reset to page 1 if we're past the initial render
    if (!isInitialMount.current) {
      setCurrentPage(1);
    }
  };
  
  return {
    filteredData,
    paginatedData,
    searchQuery,
    setSearchQuery: updateSearchQuery,
    sorting,
    handleSort,
    exportCSV,
    // Pagination props
    pageSize,
    setPageSize: handlePageSizeChange,
    currentPage,
    totalPages,
    goToPage,
    nextPage,
    previousPage,
    canNextPage,
    canPreviousPage
  };
} 