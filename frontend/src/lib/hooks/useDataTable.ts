import { useState, useEffect, useMemo } from 'react';
import { CommentWithAnalysis } from '@/lib/db/schema';
import { Field, datasetConfig } from '@/lib/config';
import MiniSearch from 'minisearch';

type UseDataTableOptions = {
  data: CommentWithAnalysis[];
  filters: Record<string, unknown>;
}

export function useDataTable({ data, filters }: UseDataTableOptions) {
  const [filteredData, setFilteredData] = useState<CommentWithAnalysis[]>(data);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchIndex, setSearchIndex] = useState<MiniSearch | null>(null);
  const [sorting, setSorting] = useState<{column: string, direction: 'asc' | 'desc'} | null>(null);
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  
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
    
    // Reset to first page when filters or search changes
    setCurrentPage(1);
    
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
  
  // Handle page change
  const goToPage = (page: number) => {
    const newPage = Math.max(1, Math.min(page, totalPages));
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
    setCurrentPage(1); // Reset to first page when changing page size
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
  
  // Sort toggle handler
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
  };
  
  return {
    filteredData,
    paginatedData,
    searchQuery,
    setSearchQuery,
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