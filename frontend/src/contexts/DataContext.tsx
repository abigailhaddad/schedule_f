"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  ReactNode,
} from "react";
import { Comment } from "@/lib/db/schema";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { SortingState } from "@/components/ui/DataTable";

interface DataContextProps {
  // Raw data
  data: Comment[];

  // State
  loading: boolean;
  error: string | null;

  // Filter state
  filters: Record<string, unknown>;
  setFilters: (filters: Record<string, unknown>) => void;

  // Search state
  searchQuery: string;
  setSearchQuery: (query: string) => void;

  // Sorting state
  sorting: SortingState | undefined;
  setSorting: (sorting: SortingState | undefined) => void;
  handleSort: (column: string) => void;

  // Pagination state
  pageSize: number;
  setPageSize: (size: number) => void;
  currentPage: number;
  setCurrentPage: (page: number) => void;
  totalPages: number;
  totalItems: number;
  goToPage: (page: number) => void;
  nextPage: () => void;
  previousPage: () => void;
  canNextPage: boolean;
  canPreviousPage: boolean;

  // Processed data
  filteredData: Comment[];
  sortedData: Comment[];
  paginatedData: Comment[];

  // Additional utilities
  exportCSV: () => void;
}

interface DataContextProviderProps {
  children: ReactNode;
  data: Comment[];
  initialLoading?: boolean;
  initialError?: string | null;
  searchFields?: string[];
  initialPageSize?: number;
}

const DataContext = createContext<DataContextProps | undefined>(undefined);

/**
 * Centralized data provider that manages:
 * - Filtering
 * - Sorting
 * - Pagination
 * - URL parameter syncing
 * - Data processing
 */
export function DataContextProvider({
  children,
  data,
  initialLoading = false,
  initialError = null,
  searchFields = [],
  initialPageSize = 10,
}: DataContextProviderProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();

  // Initialize state from URL params
  const urlSort = searchParams.get("sort");
  const urlSortDirection = searchParams.get("sortDirection") as
    | "asc"
    | "desc"
    | null;
  const urlSearch = searchParams.get("search") || "";

  // Extract filter params from URL
  const getInitialFilters = (): Record<string, unknown> => {
    const initialFilters: Record<string, unknown> = {};

    // Get all parameters that start with filter_
    for (const [key, value] of Array.from(searchParams.entries())) {
      if (key.startsWith("filter_")) {
        const filterKey = key.replace("filter_", "");

        // Try to parse JSON values (for arrays, etc)
        try {
          initialFilters[filterKey] = JSON.parse(value);
        } catch {
          // If not valid JSON, use as string
          initialFilters[filterKey] = value;
        }
      }
    }

    return initialFilters;
  };

  // Core state
  const [loading] = useState(initialLoading);
  const [error] = useState(initialError);

  // UI state
  const [searchQuery, setSearchQuery] = useState(urlSearch);
  const [filters, setFilters] = useState<Record<string, unknown>>(
    getInitialFilters()
  );
  const [sorting, setSorting] = useState<SortingState | undefined>(
    urlSort && urlSortDirection
      ? { column: urlSort, direction: urlSortDirection }
      : undefined
  );
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [currentPage, setCurrentPage] = useState(1);
  const [isInitialMount, setIsInitialMount] = useState(true);

  // Update URL when filters, sorting or search changes
  useEffect(() => {
    if (isInitialMount) {
      setIsInitialMount(false);
      return;
    }

    // Create a new URLSearchParams object
    const params = new URLSearchParams(searchParams.toString());

    // Update sorting parameters
    if (sorting) {
      params.set("sort", sorting.column);
      params.set("sortDirection", sorting.direction);
    } else {
      params.delete("sort");
      params.delete("sortDirection");
    }

    // Update search parameter
    if (searchQuery) {
      params.set("search", searchQuery);
    } else {
      params.delete("search");
    }

    // Update filter parameters
    // First, remove all existing filter parameters
    Array.from(params.keys())
      .filter((key) => key.startsWith("filter_"))
      .forEach((key) => params.delete(key));

    // Then add the current filters
    Object.entries(filters).forEach(([key, value]) => {
      if (
        value !== undefined &&
        value !== null &&
        !(Array.isArray(value) && value.length === 0) &&
        value !== ""
      ) {
        const stringValue =
          typeof value === "object" ? JSON.stringify(value) : String(value);
        params.set(`filter_${key}`, stringValue);
      }
    });

    // Update URL without refreshing page
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }, [
    searchQuery,
    sorting,
    filters,
    router,
    pathname,
    searchParams,
    isInitialMount,
  ]);

  // Reset page when filters or search changes
  useEffect(() => {
    if (!isInitialMount) {
      setCurrentPage(1);
    }
  }, [searchQuery, filters, isInitialMount]);

  // Helper function to get nested values (e.g., 'analysis.stance')
  const getNestedValue = (
    obj: Record<string, unknown>,
    path: string
  ): unknown => {
    if (path.includes(".")) {
      const [parent, child] = path.split(".");
      const parentObj = obj[parent] as Record<string, unknown> | undefined;
      return parentObj ? parentObj[child] : undefined;
    }
    return obj[path];
  };

  // Filter data based on filters and search query
  const filteredData = useMemo(() => {
    // Start with all data
    let result = [...data];

    // Apply filters
    Object.entries(filters).forEach(([key, filterValue]) => {
      if (
        filterValue !== undefined &&
        filterValue !== null &&
        filterValue !== ""
      ) {
        result = result.filter((item) => {
          // Get the actual value from the item
          const itemValue = getNestedValue(item, key);

          // Handle different filter value types
          if (Array.isArray(filterValue)) {
            // For array filters (like multi-select), check if the value is in the array
            if (filterValue.length === 0) return true; // Empty filter = show all

            // Special handling for themes - check if any selected theme is in the item's themes array
            if (key === "themes" || key === "analysis.themes") {
              // If itemValue is an array, check if any of the filter values is included
              if (Array.isArray(itemValue)) {
                return filterValue.some((theme) => itemValue.includes(theme));
              }
              // If itemValue is a string, check if it equals any of the filter values
              return filterValue.includes(String(itemValue));
            }

            // Default array handling - exact match
            return filterValue.includes(String(itemValue));
          } else {
            // For single value filters, do direct comparison
            return String(itemValue) === String(filterValue);
          }
        });
      }
    });

    // Apply search query if provided
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter((item) => {
        // If searchFields are provided, only search in those fields
        if (searchFields.length > 0) {
          return searchFields.some((field) => {
            const value = getNestedValue(item, field);
            return (
              value !== undefined && String(value).toLowerCase().includes(query)
            );
          });
        }

        // Otherwise search in all fields
        return Object.values(item).some((value) => {
          // Skip searching in complex objects or arrays unless they're strings
          if (typeof value === "object" && value !== null) {
            return false;
          }
          return (
            value !== undefined && String(value).toLowerCase().includes(query)
          );
        });
      });
    }

    return result;
  }, [data, filters, searchQuery, searchFields]);

  // Sort data if sorting is specified
  const sortedData = useMemo(() => {
    if (!sorting) return filteredData;

    return [...filteredData].sort((a, b) => {
      const aValue = getNestedValue(a, sorting.column);
      const bValue = getNestedValue(b, sorting.column);

      if (aValue === bValue) return 0;

      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;

      const modifier = sorting.direction === "asc" ? 1 : -1;

      if (typeof aValue === "string" && typeof bValue === "string") {
        return aValue.localeCompare(bValue) * modifier;
      }

      return (aValue < bValue ? -1 : 1) * modifier;
    });
  }, [filteredData, sorting]);

  // Paginate data
  const totalItems = sortedData.length;
  const totalPages = Math.ceil(totalItems / pageSize);

  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return sortedData.slice(start, end);
  }, [sortedData, currentPage, pageSize]);

  // Pagination controls
  const goToPage = (page: number) => {
    setCurrentPage(page);
  };

  const nextPage = () => {
    setCurrentPage((prev) => Math.min(prev + 1, totalPages));
  };

  const previousPage = () => {
    setCurrentPage((prev) => Math.max(prev - 1, 1));
  };

  const canNextPage = currentPage < totalPages;
  const canPreviousPage = currentPage > 1;

  // Handle sorting
  const handleSort = (column: string) => {
    setSorting((prev) => {
      if (prev?.column === column) {
        return {
          column,
          direction: prev.direction === "asc" ? "desc" : "asc",
        };
      }
      return {
        column,
        direction: "asc",
      };
    });

    // Reset to first page when sorting changes
    setCurrentPage(1);
  };

  // Export the currently-filtered table to CSV
  const exportCSV = () => {
    // ── 1. Collect headers (all scalar fields seen in the filtered data) ──
    const headerSet = new Set<string>();

    filteredData.forEach((item) => {
      const record = item as Record<string, unknown>; // ← cast once
      Object.keys(record).forEach((key) => {
        const value = record[key];
        if (typeof value !== "object" || value === null) {
          headerSet.add(key);
        }
      });
    });

    const headers = Array.from(headerSet);
    if (headers.length === 0) return; // nothing to export

    // ── 2. Build CSV text ──
    let csv = headers.map((h) => `"${h}"`).join(",") + "\n";

    filteredData.forEach((item) => {
      const record = item as Record<string, unknown>;
      const row = headers.map((header) => {
        const value = record[header];

        if (value == null) return "";
        if (typeof value === "string") {
          // escape double quotes inside cell text
          return `"${value.replace(/"/g, '""')}"`;
        }
        return String(value);
      });

      csv += row.join(",") + "\n";
    });

    // ── 3. Trigger a browser download ──
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = "export.csv";
    link.style.display = "none";

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Prepare context value
  const contextValue: DataContextProps = {
    // Raw data
    data,

    // State
    loading,
    error,

    // Filter state
    filters,
    setFilters,

    // Search state
    searchQuery,
    setSearchQuery,

    // Sorting state
    sorting,
    setSorting,
    handleSort,

    // Pagination state
    pageSize,
    setPageSize,
    currentPage,
    setCurrentPage,
    totalPages,
    totalItems,
    goToPage,
    nextPage,
    previousPage,
    canNextPage,
    canPreviousPage,

    // Processed data
    filteredData,
    sortedData,
    paginatedData,

    // Additional utilities
    exportCSV,
  };

  return (
    <DataContext.Provider value={contextValue}>{children}</DataContext.Provider>
  );
}

export function useDataContext() {
  const context = useContext(DataContext);
  if (context === undefined) {
    throw new Error("useDataContext must be used within a DataContextProvider");
  }
  return context;
}
