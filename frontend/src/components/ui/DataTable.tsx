'use client';

import React, { useState, ReactNode, useEffect } from 'react';
import Card from './Card';
import TablePagination from './TablePagination';

export interface Column<T> {
  key: string;
  title: string;
  render?: (item: T) => ReactNode;
  sortable?: boolean;
  className?: string;
}

export interface SortingState {
  column: string;
  direction: 'asc' | 'desc';
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  initialSorting?: SortingState;
  onSort?: (column: string) => void;
  pageSize?: number;
  className?: string;
  noResultsMessage?: string;
  emptyIcon?: ReactNode;
  onRowClick?: (item: T) => void;
  rowClassName?: (item: T) => string;
  headerContent?: ReactNode;
}

export default function DataTable<T extends { id: string | number }>({
  data,
  columns,
  initialSorting,
  onSort,
  pageSize: initialPageSize = 10,
  className = '',
  noResultsMessage = 'No matching records found',
  emptyIcon,
  onRowClick,
  rowClassName,
  headerContent
}: DataTableProps<T>) {
  // Pagination state
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [currentPage, setCurrentPage] = useState(1);
  
  // Sorting state
  const [sorting, setSorting] = useState<SortingState | undefined>(initialSorting);

  // Update sorting state when initialSorting changes
  useEffect(() => {
    if (JSON.stringify(sorting) !== JSON.stringify(initialSorting)) {
      setSorting(initialSorting);
      console.log('DataTable: Sorting updated from props:', initialSorting);
    }
  }, [initialSorting]);

  // Handle sort column click
  const handleSort = (column: string) => {
    console.log('DataTable: Column clicked:', column);
    
    if (onSort) {
      // If external sort handler provided, use it
      console.log('DataTable: Using external sort handler');
      onSort(column);
    } else {
      // Otherwise use internal sorting
      console.log('DataTable: Using internal sorting');
      setSorting(prev => {
        const newSorting = prev?.column === column
          ? {
              column,
              direction: prev.direction === 'asc' ? 'desc' : 'asc'
            } as SortingState
          : {
              column,
              direction: 'asc'
            } as SortingState;
            
        console.log('DataTable: New sorting state:', newSorting);
        return newSorting;
      });
      
      // Reset to first page when sorting changes
      setCurrentPage(1);
    }
  };

  // Apply sorting to data
  const sortedData = React.useMemo(() => {
    if (!sorting) return data;
    
    // If using external sorting, the data should already be sorted
    if (onSort) return data;
    
    return [...data].sort((a, b) => {
      const aValue = a[sorting.column as keyof T];
      const bValue = b[sorting.column as keyof T];
      
      if (aValue === bValue) return 0;
      
      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;
      
      const modifier = sorting.direction === 'asc' ? 1 : -1;
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return aValue.localeCompare(bValue) * modifier;
      }
      
      return ((aValue < bValue) ? -1 : 1) * modifier;
    });
  }, [data, sorting, onSort]);

  // Pagination calculations
  const totalItems = sortedData.length;
  const totalPages = Math.ceil(totalItems / pageSize);
  
  const paginatedData = React.useMemo(() => {
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

  // Get column classes including sorting
  const getColumnClasses = (column: Column<T>) => {
    if (!column.sortable) {
      return "px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider";
    }
    
    const baseClasses = "px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider cursor-pointer transition-colors duration-150";
    
    if (sorting?.column === column.key) {
      return `${baseClasses} text-blue-700 bg-blue-50`;
    }
    
    return `${baseClasses} text-gray-700 hover:text-blue-500 hover:bg-blue-50`;
  };

  // Create pagination props
  const paginationProps = {
    currentPage,
    totalPages,
    pageSize,
    totalItems,
    visibleItems: paginatedData.length,
    canPreviousPage,
    canNextPage,
    setPageSize: (size: number) => {
      setPageSize(size);
      setCurrentPage(1);
    },
    goToPage,
    previousPage,
    nextPage
  };

  return (
    <Card className={`overflow-hidden ${className}`}>
      {headerContent && (
        <Card.Header className="bg-gradient-to-r from-purple-500 to-purple-600 text-white">
          {headerContent}
        </Card.Header>
      )}
      
      {/* Top pagination controls */}
      <TablePagination {...paginationProps} position="top" />
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map(column => (
                <th 
                  key={column.key} 
                  className={`${getColumnClasses(column)} ${column.className || ''}`}
                  onClick={column.sortable ? () => handleSort(column.key) : undefined}
                >
                  <div className="flex items-center justify-between">
                    <span>{column.title}</span>
                    {column.sortable && (
                      <span className="ml-2">
                        {sorting?.column === column.key ? (
                          <span className="inline-flex items-center justify-center w-4">
                            {sorting.direction === 'asc' ? 
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                              </svg> : 
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            }
                          </span>
                        ) : (
                          <span className="inline-flex items-center justify-center w-4 text-gray-400">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4" />
                            </svg>
                          </span>
                        )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedData.length === 0 ? (
              <tr>
                <td 
                  colSpan={columns.length} 
                  className="px-6 py-10 text-center text-gray-500 bg-gray-50"
                >
                  <div className="flex flex-col items-center">
                    {emptyIcon || (
                      <svg className="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    )}
                    <p className="mt-2 text-sm font-medium">{noResultsMessage}</p>
                    <p className="text-xs text-gray-400 mt-1">Try changing your search criteria</p>
                  </div>
                </td>
              </tr>
            ) : (
              paginatedData.map(item => (
                <tr 
                  key={item.id} 
                  className={`hover:bg-blue-50 transition-colors ${onRowClick ? 'cursor-pointer' : ''} ${rowClassName?.(item) || ''}`}
                  onClick={onRowClick ? () => onRowClick(item) : undefined}
                >
                  {columns.map(column => (
                    <td 
                      key={`${item.id}-${column.key}`} 
                      className={`px-4 py-3 whitespace-normal text-sm text-gray-900 ${column.className || ''}`}
                    >
                      {column.render ? column.render(item) : String(item[column.key as keyof T] || '')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      
      {/* Bottom pagination controls */}
      <TablePagination {...paginationProps} position="bottom" />
    </Card>
  );
} 