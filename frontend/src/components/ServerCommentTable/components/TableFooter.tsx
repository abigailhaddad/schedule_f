import { PaginationControls } from './';

interface TableFooterProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  setPageSize: (size: number) => void;
  totalItems: number;
  visibleItems: number;
  canPreviousPage: boolean;
  canNextPage: boolean;
  goToPage: (page: number) => void;
  previousPage: () => void;
  nextPage: () => void;
  loading?: boolean;
}

export default function TableFooter(props: TableFooterProps) {
  return (
    <div className="p-4 border-t border-gray-200">
      <PaginationControls {...props} position="bottom" />
    </div>
  );
} 