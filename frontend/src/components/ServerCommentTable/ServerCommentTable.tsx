'use client';

import { useState, useEffect } from 'react';
import { Comment } from '@/lib/db/schema';
import { datasetConfig } from '@/lib/config';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { Column } from '@/components/ServerCommentTable/DataTable';
import DataTable from '@/components/ServerCommentTable/DataTable';
import { useServerDataContext } from '@/contexts/ServerDataContext';
import {
  TitleField,
  BooleanField,
  MultiLabelField,
  LinkField,
  BadgeField,
  StringField,
  TableHeader,
  TableFooter
} from './components';

// Debounce function
const useDebounce = <T,>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
};

export default function ServerCommentTable() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  
  // Get data and state from context
  const {
    data,
    loading,
    searchQuery,
    setSearchQuery,
    sorting,
    handleSort,
    exportCSV,
    currentPage,
    totalPages,
    pageSize,
    setPageSize,
    goToPage,
    nextPage,
    previousPage,
    canNextPage,
    canPreviousPage,
    totalItems
  } = useServerDataContext();

  // State for the immediate search input value
  const [searchInputValue, setSearchInputValue] = useState(searchQuery);
  
  // Debounced search value that will be passed to context
  const debouncedSearchValue = useDebounce(searchInputValue, 500);
  
  // Update the context search query when the debounced value changes
  useEffect(() => {
    setSearchQuery(debouncedSearchValue);
  }, [debouncedSearchValue, setSearchQuery]);
  
  const [visibleColumns, setVisibleColumns] = useState<Record<string, boolean>>(() => {
    // Initialize visible columns from config
    const initial: Record<string, boolean> = {};
    datasetConfig.fields.forEach(field => {
      initial[field.key] = field.visible !== false;
    });
    return initial;
  });
  
  const [showColumnsMenu, setShowColumnsMenu] = useState(false);
  
  // Handle search input change - only updates the local state
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchInputValue(e.target.value);
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
  
  // Handle row click to navigate to detail page
  const handleRowClick = (comment: Comment) => {
    // Create the return URL with current filters, sorting, and search
    const currentParams = new URLSearchParams(searchParams.toString());
    
    // Navigate to the detail page with the current URL as the return URL
    router.push(`/comment/${comment.id}?returnUrl=${encodeURIComponent(`${pathname}?${currentParams.toString()}`)}`)
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
          return <TitleField value={String(value)} comment={item} onRowClick={handleRowClick} />;
        }
        
        if (value === null || value === undefined || value === '') {
          return <span className="text-gray-400 italic">—</span>;
        }
        
        // Handle boolean values
        if (typeof value === 'boolean') {
          return <BooleanField value={value} badges={field.badges} />;
        }
        
        // Handle different field formats
        if (field.format === 'multi-label' && typeof value === 'string') {
          return <MultiLabelField value={value} searchQuery={searchQuery} fieldKey={field.key} />;
        }
        
        if (field.format === 'link' && typeof value === 'string') {
          return <LinkField value={value} />;
        }
        
        if (field.badges && typeof value === 'string' && field.badges[value as keyof typeof field.badges]) {
          return (
            <BadgeField 
              value={value} 
              badges={field.badges} 
              searchQuery={searchQuery}
              fieldKey={field.key}
            />
          );
        }
        
        // Use StringField for strings with char limit or search highlighting
        if (typeof value === 'string') {
          return (
            <StringField 
              value={value}
              searchQuery={searchQuery}
              fieldKey={field.key}
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

  // Create pagination props for sharing between header and footer
  const paginationProps = {
    currentPage,
    totalPages,
    pageSize,
    setPageSize,
    totalItems,
    visibleItems: data.length,
    canPreviousPage,
    canNextPage,
    goToPage,
    previousPage,
    nextPage,
    loading
  };

  return (
    <div>
      <DataTable
        data={data}
        columns={columns}
        initialSorting={sorting}
        onSort={handleSort}
        pageSize={pageSize}
        className="bg-white rounded-lg shadow-md border border-gray-200"
        headerContent={
          <TableHeader
            searchQuery={searchInputValue}
            onSearchChange={handleSearchChange}
            showColumnsMenu={showColumnsMenu}
            setShowColumnsMenu={setShowColumnsMenu}
            visibleColumns={visibleColumns}
            toggleColumnVisibility={toggleColumnVisibility}
            exportCSV={exportCSV}
          />
        }
        paginationProps={ paginationProps}
        footerContent={<TableFooter {...paginationProps} />}
        onRowClick={handleRowClick}
        rowClassName={() => "cursor-pointer hover:bg-blue-50"}
        loading={loading}
      />
    </div>
  );
} 