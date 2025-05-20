'use client';

import React from 'react';

export interface TablePaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  visibleItems: number;
  canPreviousPage: boolean;
  canNextPage: boolean;
  setPageSize: (size: number) => void;
  goToPage: (page: number) => void;
  previousPage: () => void;
  nextPage: () => void;
  position?: 'top' | 'bottom';
  pageSizeOptions?: number[];
}

export default function TablePagination({
  currentPage,
  totalPages,
  pageSize,
  totalItems,
  visibleItems,
  canPreviousPage,
  canNextPage,
  setPageSize,
  goToPage,
  previousPage,
  nextPage,
  position = 'bottom',
  pageSizeOptions = [10, 25, 50, 100]
}: TablePaginationProps) {
  // Adjust border classes based on position
  const containerClasses = 
    position === 'top'
    ? "flex flex-col sm:flex-row justify-between items-center px-6 py-3 bg-gray-50 border-b border-gray-200"
    : "flex flex-col sm:flex-row justify-between items-center px-6 py-3 bg-gray-50 border-t border-gray-200";
    
  // Calculate page numbers to show in pagination
  const getPageNumbers = () => {
    const pageNumbers: (number | string)[] = [];
    const maxPageButtons = 5; // Maximum number of page buttons to show
    
    if (totalPages <= maxPageButtons) {
      // Show all pages if total pages is less than max buttons
      for (let i = 1; i <= totalPages; i++) {
        pageNumbers.push(i);
      }
    } else {
      // Always include first page
      pageNumbers.push(1);
      
      // Calculate range of page numbers to display
      const leftSide = Math.floor(maxPageButtons / 2);
      const rightSide = maxPageButtons - leftSide - 1;
      
      if (currentPage > leftSide + 1) {
        pageNumbers.push('...');
      }
      
      // Calculate start and end of page numbers
      let start = Math.max(2, currentPage - leftSide);
      let end = Math.min(totalPages - 1, currentPage + rightSide);
      
      // Adjust if close to either end
      if (currentPage - leftSide < 2) {
        end = Math.min(totalPages - 1, maxPageButtons - 1);
      }
      
      if (currentPage + rightSide > totalPages - 1) {
        start = Math.max(2, totalPages - maxPageButtons + 1);
      }
      
      // Add middle page numbers
      for (let i = start; i <= end; i++) {
        pageNumbers.push(i);
      }
      
      // Add ellipsis if needed
      if (end < totalPages - 1) {
        pageNumbers.push('...');
      }
      
      // Always include last page if not already included
      if (end < totalPages) {
        pageNumbers.push(totalPages);
      }
    }
    
    return pageNumbers;
  };

  return (
    <div className={containerClasses}>
      <div className="flex items-center text-sm text-gray-500 mb-3 sm:mb-0">
        Showing <span className="font-medium mx-1 text-gray-700">{visibleItems > 0 ? (currentPage - 1) * pageSize + 1 : 0}</span> 
          to <span className="font-medium mx-1 text-gray-700">{Math.min(currentPage * pageSize, totalItems)}</span> 
          of <span className="font-medium mx-1 text-gray-700">{totalItems}</span> entries
      </div>
      
      <div className="flex items-center space-x-2">
        <div className="flex sm:items-center">
          <div className="mr-4 flex items-center">
            <select
              value={pageSize}
              onChange={(e) => setPageSize(Number(e.target.value))}
              className="rounded-md border-gray-300 py-1 pl-2 pr-8 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {pageSizeOptions.map(size => (
                <option key={size} value={size}>
                  {size} rows
                </option>
              ))}
            </select>
          </div>
          
          <div className="flex">
            <button
              onClick={() => goToPage(1)}
              disabled={!canPreviousPage}
              className={`px-2 py-1 text-sm rounded-l-md border border-gray-300 ${canPreviousPage ? 'text-gray-700 hover:bg-gray-100' : 'text-gray-400 cursor-not-allowed bg-gray-50'}`}
            >
              «
            </button>
            <button
              onClick={previousPage}
              disabled={!canPreviousPage}
              className={`px-2 py-1 text-sm border-t border-b border-gray-300 ${canPreviousPage ? 'text-gray-700 hover:bg-gray-100' : 'text-gray-400 cursor-not-allowed bg-gray-50'}`}
            >
              ‹
            </button>
            
            {getPageNumbers().map((page, i) => (
              typeof page === 'number' ? (
                <button
                  key={i}
                  onClick={() => goToPage(page)}
                  className={`px-3 py-1 text-sm border-t border-b border-gray-300 
                    ${currentPage === page ? 'bg-blue-100 text-blue-700 font-medium' : 'text-gray-700 hover:bg-gray-100'}`}
                >
                  {page}
                </button>
              ) : (
                <span key={i} className="px-2 py-1 text-sm border-t border-b border-gray-300 text-gray-500">
                  {page}
                </span>
              )
            ))}
            
            <button
              onClick={nextPage}
              disabled={!canNextPage}
              className={`px-2 py-1 text-sm border-t border-b border-gray-300 ${canNextPage ? 'text-gray-700 hover:bg-gray-100' : 'text-gray-400 cursor-not-allowed bg-gray-50'}`}
            >
              ›
            </button>
            <button
              onClick={() => goToPage(totalPages)}
              disabled={!canNextPage}
              className={`px-2 py-1 text-sm rounded-r-md border border-gray-300 ${canNextPage ? 'text-gray-700 hover:bg-gray-100' : 'text-gray-400 cursor-not-allowed bg-gray-50'}`}
            >
              »
            </button>
          </div>
        </div>
      </div>
    </div>
  );
} 