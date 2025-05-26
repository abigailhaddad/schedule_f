import React, { useState, useEffect } from 'react';
import { datasetConfig } from '@/lib/config';
import { useServerDataContext } from '@/contexts/ServerDataContext';
import { useDebounce } from './hooks/useDebounce';
import { useColumnVisibility } from './hooks/useColumnVisibility';
import { useTableColumns } from './hooks/useTableColumns';
import { useTableNavigation } from './hooks/useTableNavigation';
import { exportToCSV } from './utils/exportUtils';
import { TableContainer } from './components/TableContainer';
import { TableControls } from './components/TableControls';
import { TableContent } from './components/TableContent';
import { TablePagination } from './components/TablePagination';
import { Comment } from '@/lib/db/schema';
import { Column } from './types';

export default function ServerCommentTable() {
  const context = useServerDataContext();
  const [searchInput, setSearchInput] = useState(context.searchQuery);
  const debouncedSearch = useDebounce(searchInput, 500);
  
  useEffect(() => {
    context.setSearchQuery(debouncedSearch);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch, context.setSearchQuery]);
  
  const columnVisibility = useColumnVisibility(datasetConfig.fields);
  const { handleRowClick } = useTableNavigation();
  
  const columns: Column<Comment>[] = useTableColumns({
    fields: columnVisibility.visibleFields,
    searchQuery: context.searchQuery,
    onRowClick: handleRowClick
  });
  
  const handleExport = () => {
    exportToCSV(context.data, `comments-${new Date().toISOString().split('T')[0]}.csv`);
  };

  // Prepare pagination props for both top and bottom pagination instances
  const paginationSharedProps = {
    currentPage: context.currentPage,
    totalPages: context.totalPages,
    pageSize: context.pageSize,
    setPageSize: context.setPageSize,
    totalItems: context.totalItems,
    visibleItems: context.data.length, // Number of items currently visible in the table
    canPreviousPage: context.canPreviousPage,
    canNextPage: context.canNextPage,
    goToPage: context.goToPage,
    previousPage: context.previousPage,
    nextPage: context.nextPage,
    loading: context.loading,
  };

  return (
    <TableContainer>
      <TableControls
        title="Comment Data"
        searchValue={searchInput}
        onSearchChange={setSearchInput}
        onExport={handleExport}
        columnVisibility={columnVisibility}
      />
      
      <TablePagination
        {...paginationSharedProps}
        position="top"
        instanceId="sct-pagination-top" // Unique instanceId for top pagination
      />
      
      <TableContent
        data={context.data}
        columns={columns}
        sorting={context.sorting}
        onSort={context.handleSort}
        onRowClick={handleRowClick}
        loading={context.loading}
      />
      
      <TablePagination
        {...paginationSharedProps}
        position="bottom"
        instanceId="sct-pagination-bottom" // Unique instanceId for bottom pagination
      />
    </TableContainer>
  );
} 