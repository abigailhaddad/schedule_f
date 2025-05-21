"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import { Comment } from "@/lib/db/schema";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { SortingState } from "@/components/ServerCommentTable/DataTable";
import { getPaginatedComments, getCommentStatistics, parseUrlToQueryOptions } from "@/lib/actions/comments";

interface ServerDataContextProps {
  // Data
  data: Comment[];
  totalItems: number;
  
  // Statistics
  stats: {
    total: number;
    for: number;
    against: number;
    neutral: number;
  };

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
  goToPage: (page: number) => void;
  nextPage: () => void;
  previousPage: () => void;
  canNextPage: boolean;
  canPreviousPage: boolean;

  // Additional utilities
  refreshData: () => Promise<void>;
  exportCSV: () => void;
}

interface ServerDataContextProviderProps {
  children: ReactNode;
  initialPageSize?: number;
}

const ServerDataContext = createContext<ServerDataContextProps | undefined>(undefined);

/**
 * Provider that fetches data from the server based on URL parameters
 * and provides it to the application
 */
export function ServerDataContextProvider({
  children,
  initialPageSize = 10,
}: ServerDataContextProviderProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();

  // Extract URL parameters
  const urlSort = searchParams.get("sort");
  const urlSortDirection = searchParams.get("sortDirection") as "asc" | "desc" | null;
  const urlSearch = searchParams.get("search") || "";
  const urlPage = searchParams.get("page") ? parseInt(searchParams.get("page")!, 10) : 1;
  const urlPageSize = searchParams.get("pageSize") ? parseInt(searchParams.get("pageSize")!, 10) : initialPageSize;

  // Extract filter params from URL
  const getInitialFilters = (): Record<string, unknown> => {
    const initialFilters: Record<string, unknown> = {};

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
  const [data, setData] = useState<Comment[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [stats, setStats] = useState({
    total: 0,
    for: 0,
    against: 0,
    neutral: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // UI state
  const [searchQuery, setSearchQuery] = useState(urlSearch);
  const [filters, setFilters] = useState<Record<string, unknown>>(getInitialFilters());
  const [sorting, setSorting] = useState<SortingState | undefined>(
    urlSort && urlSortDirection
      ? { column: urlSort, direction: urlSortDirection }
      : undefined
  );
  const [pageSize, setPageSize] = useState(urlPageSize);
  const [currentPage, setCurrentPage] = useState(urlPage);
  const [isInitialMount, setIsInitialMount] = useState(true);

  // Fetch data based on current parameters
  const fetchData = async () => {
    setLoading(true);
    
    try {
      // Create a simple object from search params, to avoid issues with URLSearchParams
      const paramsObj: Record<string, string> = {};
      searchParams.forEach((value, key) => {
        paramsObj[key] = value;
      });
      
      const options = await parseUrlToQueryOptions(paramsObj);
      
      // Fetch data and stats in parallel
      const [dataResponse, statsResponse] = await Promise.all([
        getPaginatedComments(options),
        getCommentStatistics(options)
      ]);

      if (dataResponse.success && dataResponse.data) {
        setData(dataResponse.data);
        setTotalItems(dataResponse.total || 0);
        setError(null);
      } else {
        setError(dataResponse.error || "Failed to fetch comments");
        console.error("Error fetching comments:", dataResponse.error);
      }

      if (statsResponse.success && statsResponse.stats) {
        setStats(statsResponse.stats);
      } else {
        console.error("Error fetching stats:", statsResponse.error);
      }
    } catch (err) {
      console.error("Exception in fetchData:", err);
      setError("An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  // Refresh data function that can be called by consumers
  const refreshData = async () => {
    await fetchData();
  };

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

    // Update pagination parameters
    params.set("page", currentPage.toString());
    params.set("pageSize", pageSize.toString());

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
    currentPage,
    pageSize,
    router,
    pathname,
    searchParams,
    isInitialMount,
  ]);

  // Fetch data when URL parameters change
  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // Reset page when filters or search changes
  useEffect(() => {
    if (!isInitialMount) {
      setCurrentPage(1);
    }
  }, [searchQuery, filters, isInitialMount]);

  // Calculate total pages based on total items
  const totalPages = Math.ceil(totalItems / pageSize);

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
    if (data.length === 0) return;

    // Get all unique keys from the data
    const headerSet = new Set<string>();

    data.forEach((item) => {
      const record = item as Record<string, unknown>;
      Object.keys(record).forEach((key) => {
        const value = record[key];
        if (typeof value !== "object" || value === null) {
          headerSet.add(key);
        }
      });
    });

    const headers = Array.from(headerSet);
    if (headers.length === 0) return;

    // Build CSV text
    let csv = headers.map((h) => `"${h}"`).join(",") + "\n";

    data.forEach((item) => {
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

    // Trigger a browser download
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
  const contextValue: ServerDataContextProps = {
    // Data
    data,
    totalItems,
    
    // Statistics
    stats,

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
    goToPage,
    nextPage,
    previousPage,
    canNextPage,
    canPreviousPage,

    // Additional utilities
    refreshData,
    exportCSV,
  };

  return (
    <ServerDataContext.Provider value={contextValue}>
      {children}
    </ServerDataContext.Provider>
  );
}

export function useServerDataContext() {
  const context = useContext(ServerDataContext);
  if (context === undefined) {
    throw new Error(
      "useServerDataContext must be used within a ServerDataContextProvider"
    );
  }
  return context;
}