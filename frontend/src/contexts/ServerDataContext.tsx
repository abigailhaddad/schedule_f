"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
  useCallback,
  useRef,
  useMemo,
} from "react";
import { Comment } from "@/lib/db/schema";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { SortingState } from "@/components/ServerCommentTable/DataTable";
import {
  getPaginatedComments,
  getCommentStatistics,
  parseUrlToQueryOptions,
  CommentsPaginatedResponse,
  CommentsStatisticsResponse,
} from "@/lib/actions/comments";

interface InitialData {
  comments?: Comment[];
  total?: number;
  stats?: {
    total: number;
    for: number;
    against: number;
    neutral: number;
  };
  error?: string | null;
}

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
  initialData?: InitialData;
  initialPageSize?: number;
}

const ServerDataContext = createContext<ServerDataContextProps | undefined>(undefined);

// Define a type for the cached data
interface CachedData {
  data: Comment[];
  total: number;
  stats: {
    total: number;
    for: number;
    against: number;
    neutral: number;
  };
}

// Client-side cache for fetched data
const clientCache = new Map<string, { data: CachedData; timestamp: number }>();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes client-side cache

export function ServerDataContextProvider({
  children,
  initialData,
  initialPageSize = 25, // Increased default page size
}: ServerDataContextProviderProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();

  // Track if this is the first mount
  const isFirstMount = useRef(true);
  const lastFetchKey = useRef<string>("");

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

        try {
          initialFilters[filterKey] = JSON.parse(value);
        } catch {
          initialFilters[filterKey] = value;
        }
      }
    }

    return initialFilters;
  };

  // Core state - initialize with initial data if provided
  const [data, setData] = useState<Comment[]>(initialData?.comments || []);
  const [totalItems, setTotalItems] = useState(initialData?.total || 0);
  const [stats, setStats] = useState(initialData?.stats || {
    total: 0,
    for: 0,
    against: 0,
    neutral: 0
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(initialData?.error || null);

  // UI state
  const [searchQuery, setSearchQuery] = useState(urlSearch);
  const [filters, setFilters] = useState<Record<string, unknown>>(getInitialFilters());
  const [sorting, setSorting] = useState<SortingState | undefined>(
    urlSort && urlSortDirection
      ? { column: urlSort, direction: urlSortDirection }
      : { column: 'createdAt', direction: 'desc' }
  );
  const [pageSize, setPageSize] = useState(urlPageSize);
  const [currentPage, setCurrentPage] = useState(urlPage);
  const [isInitialMount, setIsInitialMount] = useState(true);

  // Create a cache key for the current query
  const createCacheKey = useCallback(() => {
    const params = {
      filters,
      search: searchQuery,
      sort: sorting,
      page: currentPage,
      pageSize
    };
    return JSON.stringify(params);
  }, [filters, searchQuery, sorting, currentPage, pageSize]);

  // Check if we have valid cached data
  const getCachedData = useCallback((key: string) => {
    const cached = clientCache.get(key);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      return cached.data;
    }
    return null;
  }, []);

  // Fetch data with client-side caching
  const fetchData = useCallback(async (force = false) => {
    const cacheKey = createCacheKey();
    
    // Skip if we're fetching the same data
    if (!force && lastFetchKey.current === cacheKey) {
      return;
    }

    // Check client-side cache first
    if (!force) {
      const cached = getCachedData(cacheKey);
      if (cached) {
        setData(cached.data);
        setTotalItems(cached.total);
        setStats(cached.stats);
        setError(null);
        lastFetchKey.current = cacheKey;
        return;
      }
    }

    setLoading(true);
    
    try {
      const paramsObj: Record<string, string> = {};
      searchParams.forEach((value, key) => {
        paramsObj[key] = value;
      });
      
      const options = await parseUrlToQueryOptions(paramsObj);
      
      // Only fetch stats if filters have changed (not pagination)
      const shouldFetchStats = force || 
        JSON.stringify(options.filters) !== JSON.stringify(lastFetchKey.current);

      const promises: Promise<CommentsPaginatedResponse | CommentsStatisticsResponse>[] = 
        [getPaginatedComments(options)];
      
      if (shouldFetchStats) {
        promises.push(getCommentStatistics(options));
      }

      const results = await Promise.all(promises);
      const dataResponse = results[0] as CommentsPaginatedResponse;
      const statsResponse = results.length > 1 ? results[1] as CommentsStatisticsResponse : undefined;

      if (dataResponse.success && dataResponse.data) {
        const responseData = {
          data: dataResponse.data,
          total: dataResponse.total || 0,
          stats: statsResponse?.success && statsResponse.stats ? statsResponse.stats : stats,
        };

        // Update state
        setData(responseData.data);
        setTotalItems(responseData.total);
        if (statsResponse?.success && statsResponse.stats) {
          setStats(statsResponse.stats);
        }
        setError(null);

        // Cache the response
        clientCache.set(cacheKey, {
          data: responseData,
          timestamp: Date.now()
        });

        lastFetchKey.current = cacheKey;
      } else {
        setError(dataResponse.error || "Failed to fetch comments");
      }
    } catch (err) {
      console.error("Exception in fetchData:", err);
      setError("An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  }, [createCacheKey, getCachedData, searchParams, stats]);

  // Refresh data function
  const refreshData = useCallback(async () => {
    await fetchData(true); // Force refresh
  }, [fetchData]);

  // Only update URL when filters, sorting, search, or pagination changes
  useEffect(() => {
    if (isInitialMount) {
      setIsInitialMount(false);
      return;
    }

    const params = new URLSearchParams(searchParams.toString());

    // Update all parameters
    if (sorting) {
      params.set("sort", sorting.column);
      params.set("sortDirection", sorting.direction);
    } else {
      params.delete("sort");
      params.delete("sortDirection");
    }

    if (searchQuery) {
      params.set("search", searchQuery);
    } else {
      params.delete("search");
    }

    params.set("page", currentPage.toString());
    params.set("pageSize", pageSize.toString());

    // Update filter parameters
    Array.from(params.keys())
      .filter((key) => key.startsWith("filter_"))
      .forEach((key) => params.delete(key));

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

  // Fetch data only when URL parameters change and we don't have cached data
  useEffect(() => {
    // Skip the first mount if we have initial data
    if (isFirstMount.current && initialData?.comments) {
      isFirstMount.current = false;
      return;
    }
    
    isFirstMount.current = false;
    fetchData();
  }, [searchParams, fetchData, initialData]);

  // Reset page when filters or search changes
  useEffect(() => {
    if (!isInitialMount) {
      setCurrentPage(1);
    }
  }, [searchQuery, filters, isInitialMount]);

  // Calculate total pages
  const totalPages = useMemo(() => Math.ceil(totalItems / pageSize), [totalItems, pageSize]);

  // Pagination controls
  const goToPage = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const nextPage = useCallback(() => {
    setCurrentPage((prev) => Math.min(prev + 1, totalPages));
  }, [totalPages]);

  const previousPage = useCallback(() => {
    setCurrentPage((prev) => Math.max(prev - 1, 1));
  }, []);

  const canNextPage = currentPage < totalPages;
  const canPreviousPage = currentPage > 1;

  // Handle sorting
  const handleSort = useCallback((column: string) => {
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

    setCurrentPage(1);
  }, []);

  // Export CSV
  const exportCSV = useCallback(() => {
    if (data.length === 0) return;

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

    let csv = headers.map((h) => `"${h}"`).join(",") + "\n";

    data.forEach((item) => {
      const record = item as Record<string, unknown>;
      const row = headers.map((header) => {
        const value = record[header];

        if (value == null) return "";
        if (typeof value === "string") {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return String(value);
      });

      csv += row.join(",") + "\n";
    });

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
  }, [data]);

  // Prepare context value
  const contextValue: ServerDataContextProps = {
    data,
    totalItems,
    stats,
    loading,
    error,
    filters,
    setFilters,
    searchQuery,
    setSearchQuery,
    sorting,
    setSorting,
    handleSort,
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