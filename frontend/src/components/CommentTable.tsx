// components/CommentTable.tsx
'use client';

import { useState, useEffect, useRef } from 'react';
import { Comment } from '@/lib/db/schema';
import { datasetConfig } from '@/lib/config';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { Column } from '@/components/ServerCommentTable/DataTable';
import DataTable from '@/components/ServerCommentTable/DataTable';
import Badge from '@/components/ui/Badge';
import SearchInput from '@/components/ui/SearchInput';
import TextHighlighter from '@/components/ui/TextHighlighter';
import { useDataContext } from '@/contexts/DataContext';

// CommentTable no longer needs props as it gets data from context
export default function CommentTable() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const columnsMenuRef = useRef<HTMLDivElement>(null);
  
  // Get data and state from context
  const {
    sortedData,
    searchQuery,
    setSearchQuery,
    sorting,
    handleSort,
    exportCSV,
    pageSize
  } = useDataContext();
  
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
  }, [searchParams, setSearchQuery]);
  
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

  // Handle keyboard events for column visibility items
  const handleColumnKeyDown = (e: React.KeyboardEvent, key: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggleColumnVisibility(key);
    }
  };
  
  // Get visible fields based on current visibility state
  const getVisibleFields = () => {
    return datasetConfig.fields.filter(field => visibleColumns[field.key]);
  };
  
  // Setup tooltips for truncated content
  useEffect(() => {
    // Close dropdown when clicking outside
    const handleClickOutside = (e: MouseEvent) => {
      if (showColumnsMenu && columnsMenuRef.current && !columnsMenuRef.current.contains(e.target as Node)) {
        setShowColumnsMenu(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    
    // Close dropdown when pressing Escape
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && showColumnsMenu) {
        setShowColumnsMenu(false);
      }
    };
    
    document.addEventListener('keydown', handleEscape);
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [showColumnsMenu]);
  
  // Handle row click to navigate to detail page
  const handleRowClick = (comment: Comment) => {
    // Create the return URL with current filters, sorting, and search
    const currentParams = new URLSearchParams(searchParams.toString());
    
    // Navigate to the detail page with the current URL as the return URL
    router.push(`/comment/${comment.id}?returnUrl=${encodeURIComponent(`${pathname}?${currentParams.toString()}`)}`);
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
  const columns: Column<Comment>[] = [
    // Add the rest of the columns
    ...getVisibleFields().map(field => {
    // Get the correct key for nested fields when sorting
    const sortKey = field.key;
                    
    return {
      key: sortKey,
      title: field.title,
      sortable: true,
      // Set width for different columns
      className: field.key === 'comment' ? 'w-1/2 max-w-3xl' : 
                field.key === 'keyQuote' || field.key === 'rationale' ? 'w-1/6' :
                field.key === 'themes' ? 'w-1/8' :
                field.key === 'title' ? 'w-1/8' :
                undefined,
      render: (item: Comment) => {
        // Get the value directly from the item
        const value = item[field.key as keyof typeof item] || '';
        
        // Special case for the title field - make it a clickable link
        if (field.key === 'title') {
          return (
            <div className="flex items-center">
              <button 
                onClick={(e) => {
                  e.stopPropagation(); // Prevent row click
                  handleRowClick(item);
                }}
                className="font-medium text-blue-600 hover:text-blue-800 hover:underline text-left cursor-pointer flex items-center focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded"
                aria-label={`View details for ${String(value) || 'Untitled Comment'}`}
              >
                <svg 
                  xmlns="http://www.w3.org/2000/svg" 
                  className="h-4 w-4 mr-1 text-blue-500" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" 
                  />
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" 
                  />
                </svg>
                <span className="underline">{String(value) || 'Untitled Comment'}</span>
              </button>
            </div>
          );
        }
        
        if (value === null || value === undefined || value === '') {
          return <span className="text-gray-400 italic" aria-label="No value">—</span>;
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
                id={`badge-${field.key}-${item.id}`}
              />
            );
          }
          
          return (
            <Badge 
              type={value ? 'success' : 'default'}
              label={value ? 'Yes' : 'No'}
              id={`badge-${field.key}-${item.id}`}
            />
          );
        }
        
        // Handle different field formats
        if (field.format === 'multi-label' && typeof value === 'string') {
          const labels = value.split(',').map(label => label.trim()).filter(Boolean);
          return (
            <div className="flex flex-wrap gap-1" role="list" aria-label={`${field.title} tags`}>
              {labels.map((label, i) => (
                <Badge 
                  key={i}
                  type="primary" 
                  label={label}
                  highlight={searchQuery}
                  filterType={field.key}
                  id={`badge-${field.key}-${item.id}-${i}`}
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
              className="text-blue-600 hover:text-blue-800 flex items-center hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-1"
              aria-label={`Open external link for ${field.title} (opens in new tab)`}
            >
              <span className="mr-1" aria-hidden="true">🔗</span>View
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
              highlight={searchQuery}
              filterType={field.key}
              id={`badge-${field.key}-${item.id}`}
            />
          );
        }
        
        // Use TextHighlighter for field types with char limit or search highlighting
        if (typeof value === 'string') {
          return (
            <TextHighlighter 
              text={value}
              searchTerm={searchQuery}
              highlightType={field.key}
              charLimit={field.charLimit}
              smartTruncation={field.key === 'comment'} // Use smart truncation only for comments
            />
          );
        }
        
        // Convert value to string for rendering if it's not a React element
        return typeof value === 'object' ? JSON.stringify(value) : String(value);
      }
    };
  })];

  // Create the table header with search and export functionality
  const tableHeader = (
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 p-4">
      <h2 className="text-lg font-bold text-white flex items-center" id="comment-table-heading">
        <span className="mr-2" aria-hidden="true">📋</span>
        Comment Data
      </h2>
      <div className="flex flex-wrap items-center gap-2">
        {/* Search input */}
        <SearchInput
          value={searchQuery}
          onChange={handleSearchChange}
          placeholder="Search comments..."
          id="comment-search"
          ariaLabel="Search comments"
        />
        
        {/* Column visibility dropdown */}
        <div className="relative inline-block" ref={columnsMenuRef}>
          <button 
            className="flex items-center px-3 py-2 text-sm font-medium bg-white bg-opacity-20 rounded hover:bg-opacity-30 focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-40 text-white transition-colors"
            onClick={() => setShowColumnsMenu(!showColumnsMenu)}
            aria-haspopup="true"
            aria-expanded={showColumnsMenu}
            aria-controls="columns-menu"
          >
            <span className="mr-1" aria-hidden="true">👁️</span>Columns
          </button>
          {showColumnsMenu && (
            <div 
              id="columns-menu"
              className="absolute right-0 z-50 mt-1 w-56 bg-white rounded-md shadow-lg border border-gray-200"
              role="menu"
              aria-labelledby="columns-button"
            >
              <div className="py-1 max-h-64 overflow-y-auto">
                {datasetConfig.fields.map(field => (
                  <div 
                    key={field.key} 
                    className="px-4 py-2 hover:bg-gray-100 cursor-pointer flex items-center"
                    onClick={() => toggleColumnVisibility(field.key)}
                    onKeyDown={(e) => handleColumnKeyDown(e, field.key)}
                    tabIndex={0}
                    role="menuitemcheckbox"
                    aria-checked={visibleColumns[field.key]}
                  >
                    <input
                      type="checkbox"
                      id={`col-${field.key}`}
                      className="mr-2 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      checked={visibleColumns[field.key]}
                      onChange={() => {}}
                      aria-labelledby={`col-label-${field.key}`}
                    />
                    <label 
                      id={`col-label-${field.key}`}
                      htmlFor={`col-${field.key}`} 
                      className="text-sm text-gray-700 cursor-pointer"
                    >
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
          aria-label="Export data to CSV file"
        >
          <span className="mr-1" aria-hidden="true">📥</span>Export CSV
        </button>
      </div>
    </div>
  );

  return (
    <section 
      aria-labelledby="comment-table-heading"
    >
      <DataTable
        data={sortedData}
        columns={columns}
        initialSorting={sorting}
        onSort={handleSort}
        pageSize={pageSize}
        className="bg-white rounded-lg shadow-md border border-gray-200"
        headerContent={tableHeader}
        onRowClick={handleRowClick}
        rowClassName={() => "cursor-pointer hover:bg-blue-50"}
      />
    </section>
  );
}