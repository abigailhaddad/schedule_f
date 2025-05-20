// components/CommentTable.tsx
'use client';

import { useState, useEffect } from 'react';
import { CommentWithAnalysis } from '@/lib/db/schema';
import { datasetConfig } from '@/lib/config';
import { useDataTable } from '@/lib/hooks/useDataTable';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { Column, SortingState } from '@/components/ui/DataTable';
import DataTable from '@/components/ui/DataTable';
import Badge from '@/components/ui/Badge';
import SearchInput from '@/components/ui/SearchInput';

interface CommentTableProps {
  data: CommentWithAnalysis[];
  filters: Record<string, unknown>;
}

export default function CommentTable({ data, filters }: CommentTableProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  
  // Get initial sorting from URL if available
  const urlSort = searchParams.get('sort');
  const urlSortDirection = searchParams.get('sortDirection') as 'asc' | 'desc' | null;
  
  const initialSorting: SortingState | undefined = 
    urlSort && urlSortDirection 
      ? { column: urlSort, direction: urlSortDirection } 
      : undefined;
  
  const { 
    filteredData, 
    sortedData,
    searchQuery, 
    setSearchQuery,
    sorting,
    handleSort,
    exportCSV,
    pageSize
  } = useDataTable<CommentWithAnalysis>({ 
    data, 
    filters,
    initialSorting,
    searchFields: ['comment', 'originalComment', 'title', 'analysis.keyQuote', 'analysis.themes', 'analysis.rationale']
  });
  
  const [visibleColumns, setVisibleColumns] = useState<Record<string, boolean>>(() => {
    // Initialize visible columns from config
    const initial: Record<string, boolean> = {};
    datasetConfig.fields.forEach(field => {
      initial[field.key] = field.visible !== false;
    });
    return initial;
  });
  
  const [showColumnsMenu, setShowColumnsMenu] = useState(false);
  
  // Load initial search query from URL
  useEffect(() => {
    const queryParam = searchParams.get('query');
    if (queryParam) {
      setSearchQuery(queryParam);
    }
  }, []); // Only run once on mount
  
  // Handle search input change
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value;
    
    // Update state
    setSearchQuery(newQuery);
    
    // Update URL
    const params = new URLSearchParams(searchParams.toString());
    
    if (newQuery) {
      params.set('query', newQuery);
    } else {
      params.delete('query');
    }
    
    // Update URL without refreshing page
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };
  
  // Toggle column visibility
  const toggleColumnVisibility = (key: string) => {
    setVisibleColumns(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };
  
  // Get visible fields based on current visibility state
  const getVisibleFields = () => {
    return datasetConfig.fields.filter(field => visibleColumns[field.key]);
  };
  
  // Setup tooltips for truncated content
  useEffect(() => {
    // Close dropdown when clicking outside
    const handleClickOutside = (e: MouseEvent) => {
      if (showColumnsMenu && !(e.target as Element).closest('.columns-dropdown')) {
        setShowColumnsMenu(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showColumnsMenu]);
  
  // Highlight search match in text
  const highlightSearchMatch = (text: string, searchTerm: string, filterType?: string) => {
    if (!searchTerm || !text) return text;
    
    // Escape special characters in the search term
    const escapedSearchTerm = searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedSearchTerm})`, 'gi');
    
    // Split text by search term matches
    const parts = text.split(regex);
    
    if (parts.length <= 1) return text;
    
    // Get highlight color based on filter type
    const getHighlightColor = (filterType?: string): string => {
      if (!filterType) return 'bg-yellow-200 text-gray-900';
      
      switch (filterType) {
        case 'title':
          return 'bg-blue-200 text-blue-900';
        case 'comment':
          return 'bg-green-200 text-green-900';
        case 'themes':
          return 'bg-purple-200 text-purple-900';
        case 'keyQuote':
          return 'bg-orange-200 text-orange-900';
        case 'rationale':
          return 'bg-pink-200 text-pink-900';
        case 'stance':
          return 'bg-indigo-200 text-indigo-900';
        default:
          return 'bg-yellow-200 text-gray-900';
      }
    };
    
    const highlightClass = getHighlightColor(filterType);
    
    // Return text with highlighted spans
    return (
      <>
        {parts.map((part, i) => 
          regex.test(part) ? (
            <span key={i} className={`${highlightClass} font-medium px-1 rounded`}>
              {part}
            </span>
          ) : (
            part
          )
        )}
      </>
    );
  };
  
  // Find the index of the first search match in text
  const findFirstMatchIndex = (text: string, searchTerm: string): number => {
    if (!searchTerm || !text) return -1;
    
    const escapedSearchTerm = searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(escapedSearchTerm, 'gi');
    const match = regex.exec(text);
    
    return match ? match.index : -1;
  };
  
  // Create smart truncated text that ensures search matches are visible
  const createSmartTruncatedText = (text: string, limit: number, searchTerm: string, filterType?: string) => {
    if (text.length <= limit) {
      return searchTerm ? highlightSearchMatch(text, searchTerm, filterType) : text;
    }
    
    // If no search term or empty search term, just truncate
    if (!searchTerm) {
      return `${text.substring(0, limit)}...`;
    }
    
    // Find the first search match
    const matchIndex = findFirstMatchIndex(text, searchTerm);
    
    // If no match or match is within visible area, show normal truncation with highlighting
    if (matchIndex === -1 || matchIndex < limit) {
      return highlightSearchMatch(`${text.substring(0, limit)}...`, searchTerm, filterType);
    }
    
    // If match is outside visible area, show context around match
    const contextSize = Math.floor(limit / 2);
    const matchStart = Math.max(0, matchIndex - (contextSize / 2));
    const matchEnd = Math.min(text.length, matchStart + contextSize);
    
    // Create segments
    const firstSegment = text.substring(0, Math.floor(limit / 3));
    const matchSegment = text.substring(matchStart, matchEnd);
    
    return (
      <>
        {highlightSearchMatch(firstSegment, searchTerm, filterType)}
        <span className="text-gray-500 mx-1 font-bold">...</span>
        {highlightSearchMatch(matchSegment, searchTerm, filterType)}
        {matchEnd < text.length ? '...' : ''}
      </>
    );
  };

  // Determine badge type based on the badge class
  const getBadgeType = (badgeClass?: string): 'success' | 'danger' | 'warning' | 'primary' | 'default' => {
    if (!badgeClass) return 'default';
    if (badgeClass.includes('success')) return 'success';
    if (badgeClass.includes('danger')) return 'danger';
    if (badgeClass.includes('warning')) return 'warning';
    if (badgeClass.includes('primary')) return 'primary';
    return 'default';
  };
  
  // Map the visible columns to DataTable column format
  const columns: Column<CommentWithAnalysis>[] = getVisibleFields().map(field => {
    // Get the correct key for nested fields when sorting
    const sortKey = field.key === 'stance' || field.key === 'keyQuote' || 
                    field.key === 'themes' || field.key === 'rationale'
                    ? `analysis.${field.key}`
                    : field.key;
                    
    return {
      key: sortKey,
      title: field.title,
      sortable: true,
      // Set width for different columns
      className: field.key === 'comment' ? 'w-2/5 max-w-2xl' : 
                field.key === 'keyQuote' || field.key === 'rationale' ? 'w-1/5' :
                field.key === 'themes' ? 'w-1/6' :
                field.key === 'title' ? 'w-1/6' :
                undefined,
      render: (item: CommentWithAnalysis) => {
        let value: unknown;
        
        // Get the appropriate value based on the field key
        if (field.key === 'stance' || field.key === 'keyQuote' || 
            field.key === 'themes' || field.key === 'rationale') {
          value = item.analysis?.[field.key as keyof typeof item.analysis] || '';
        } else {
          value = item[field.key as keyof typeof item] || '';
        }
        
        if (value === null || value === undefined || value === '') {
          return <span className="text-gray-400 italic">—</span>;
        }
        
        // Handle boolean values
        if (typeof value === 'boolean') {
          if (field.badges) {
            const badgeClass = field.badges[String(value) as keyof typeof field.badges];
            const badgeType = getBadgeType(badgeClass);
            return (
              <Badge 
                type={badgeType}
                label={value ? 'Yes' : 'No'}
              />
            );
          }
          
          return (
            <Badge 
              type={value ? 'success' : 'default'}
              label={value ? 'Yes' : 'No'}
            />
          );
        }
        
        // Handle different field formats
        if (field.format === 'multi-label' && typeof value === 'string') {
          const labels = value.split(',').map(label => label.trim()).filter(Boolean);
          return (
            <div className="flex flex-wrap gap-1">
              {labels.map((label, i) => (
                <Badge 
                  key={i}
                  type="primary" 
                  label={label}
                  highlight={searchQuery && typeof searchQuery === 'string' ? searchQuery : ''}
                  filterType={field.key}
                />
              ))}
            </div>
          );
        }
        
        if (field.format === 'link' && typeof value === 'string') {
          return (
            <a 
              href={value} 
              target="_blank" 
              rel="noopener noreferrer" 
              className="text-blue-600 hover:text-blue-800 flex items-center hover:underline"
            >
              <span className="mr-1">🔗</span>View
            </a>
          );
        }
        
        if (field.badges && typeof value === 'string' && field.badges[value as keyof typeof field.badges]) {
          const badgeClass = field.badges[value as keyof typeof field.badges];
          const badgeType = getBadgeType(badgeClass);
          
          return (
            <Badge 
              type={badgeType}
              label={String(value)}
              highlight={searchQuery && typeof searchQuery === 'string' ? searchQuery : ''}
              filterType={field.key}
            />
          );
        }
        
        if (field.charLimit && typeof value === 'string' && value.length > field.charLimit) {
          // Use smart truncation for comment field
          if (field.key === 'comment' && searchQuery && typeof searchQuery === 'string') {
            return (
              <span title={value} className="cursor-help">
                {createSmartTruncatedText(value, field.charLimit, searchQuery, field.key)}
              </span>
            );
          }
          
          const truncated = value.substring(0, field.charLimit) + '...';
          return (
            <span title={value} className="cursor-help">
              {searchQuery && typeof searchQuery === 'string' ? highlightSearchMatch(truncated, searchQuery, field.key) : truncated}
            </span>
          );
        }
        
        // Apply highlighting for text fields if we have a search query
        if (typeof value === 'string' && searchQuery && typeof searchQuery === 'string') {
          return highlightSearchMatch(value, searchQuery, field.key);
        }
        
        // Convert value to string for rendering if it's not a React element
        return typeof value === 'object' ? JSON.stringify(value) : String(value);
      }
    };
  });

  // Create the table header with search and export functionality
  const tableHeader = (
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 p-4">
      <h5 className="text-lg font-bold text-white flex items-center">
        <span className="mr-2">📋</span>
        Comment Data
      </h5>
      <div className="flex flex-wrap items-center gap-2">
        {/* Search input */}
        <SearchInput
          value={searchQuery}
          onChange={handleSearchChange}
          placeholder="Search comments..."
        />
        
        {/* Column visibility dropdown */}
        <div className="relative inline-block columns-dropdown">
          <button 
            className="flex items-center px-3 py-2 text-sm font-medium bg-white bg-opacity-20 rounded hover:bg-opacity-30 focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-40 text-white transition-colors"
            onClick={() => setShowColumnsMenu(!showColumnsMenu)}
          >
            <span className="mr-1">👁️</span>Columns
          </button>
          {showColumnsMenu && (
            <div className="absolute right-0 z-50 mt-1 w-56 bg-white rounded-md shadow-lg border border-gray-200">
              <div className="py-1 max-h-64 overflow-y-auto">
                {datasetConfig.fields.map(field => (
                  <div 
                    key={field.key} 
                    className="px-4 py-2 hover:bg-gray-100 cursor-pointer flex items-center"
                    onClick={() => toggleColumnVisibility(field.key)}
                  >
                    <input
                      type="checkbox"
                      id={`col-${field.key}`}
                      className="mr-2 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      checked={visibleColumns[field.key]}
                      onChange={() => {}}
                    />
                    <label htmlFor={`col-${field.key}`} className="text-sm text-gray-700 cursor-pointer">
                      {field.title}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        <button 
          className="flex items-center px-3 py-2 text-sm font-medium bg-white bg-opacity-20 rounded hover:bg-opacity-30 focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-40 text-white transition-colors"
          onClick={exportCSV}
        >
          <span className="mr-1">📥</span>Export CSV
        </button>
      </div>
    </div>
  );

  return (
    <div>
      <DataTable
        data={sortedData}
        columns={columns}
        initialSorting={sorting}
        onSort={handleSort}
        pageSize={pageSize}
        className="bg-white rounded-lg shadow-md border border-gray-200"
        headerContent={tableHeader}
      />
    </div>
  );
}