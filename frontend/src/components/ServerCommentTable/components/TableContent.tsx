import React from 'react';
import { Comment } from '@/lib/db/schema';
import { Column, SortingState } from '../types';

interface TableContentProps {
  data: Comment[];
  columns: Column<Comment>[];
  sorting?: SortingState;
  onSort: (column: string) => void;
  onRowClick: (item: Comment) => void;
  loading: boolean;
}

export function TableContent({ 
  data, 
  columns, 
  sorting, 
  onSort, 
  onRowClick, 
  loading 
}: TableContentProps) {
  return (
    <div className="flex-1 overflow-x-auto relative">
      {loading && <LoadingOverlay />}
      
      <table className="min-w-full divide-y divide-gray-200">
        <TableHead 
          columns={columns} 
          sorting={sorting} 
          onSort={onSort} 
        />
        <TableBody 
          data={data} 
          columns={columns} 
          onRowClick={onRowClick} 
        />
      </table>
    </div>
  );
}

function LoadingOverlay() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-70 z-10">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500" />
    </div>
  );
}

interface TableHeadProps {
  columns: Column<Comment>[];
  sorting?: SortingState;
  onSort: (column: string) => void;
}

function TableHead({ columns, sorting, onSort }: TableHeadProps) {
  return (
    <thead className="bg-gray-50">
      <tr>
        {columns.map((column) => (
          <th
            key={column.key}
            className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider ${
              column.sortable ? 'cursor-pointer hover:bg-blue-50' : ''
            } ${sorting?.column === column.key ? 'text-blue-700 bg-blue-50' : 'text-gray-700'}`}
            onClick={column.sortable ? () => onSort(column.key) : undefined}
          >
            <div className="flex items-center justify-between">
              <span>{column.title}</span>
              {column.sortable && sorting?.column === column.key && (
                <SortIcon direction={sorting.direction} />
              )}
            </div>
          </th>
        ))}
      </tr>
    </thead>
  );
}

interface TableBodyProps {
  data: Comment[];
  columns: Column<Comment>[];
  onRowClick: (item: Comment) => void;
}

function TableBody({ data, columns, onRowClick }: TableBodyProps) {
  if (data.length === 0) {
    return (
      <tbody>
        <tr>
          <td colSpan={columns.length} className="px-6 py-10 text-center text-gray-500 bg-gray-50">
            <EmptyState />
          </td>
        </tr>
      </tbody>
    );
  }

  return (
    <tbody className="bg-white divide-y divide-gray-200">
      {data.map((item) => (
        <tr
          key={item.id}
          className="cursor-pointer hover:bg-blue-50"
          onClick={() => onRowClick(item)}
        >
          {columns.map((column) => (
            <td key={`${item.id}-${column.key}`} className="px-4 py-3 text-sm">
              {column.render(item)}
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  );
}

function SortIcon({ direction }: { direction: 'asc' | 'desc' }) {
  return (
    <svg className="h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      {direction === 'asc' ? (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
      ) : (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      )}
    </svg>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center">
      <svg className="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
          d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p className="mt-2 text-sm font-medium">No matching records found</p>
      <p className="text-xs text-gray-400 mt-1">Try changing your search criteria</p>
    </div>
  );
} 