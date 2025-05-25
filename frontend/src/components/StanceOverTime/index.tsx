'use client';

import { useMemo, useState, useEffect } from 'react';
import { useServerDataContext } from '@/contexts/ServerDataContext';
import { getAllCommentsForTimeSeries, parseUrlToQueryOptions } from '@/lib/actions/comments';
import { Comment } from '@/lib/db/schema';
import Card from '@/components/ui/Card';
import LoadingSkeleton from './LoadingSkeleton';
import NoDataMessage from './NoDataMessage';
import ChartSelector from './ChartSelector';
import { StanceData } from './types';
import { QueryOptions } from '@/lib/queryBuilder';

// Define the type for date selection
type DateTypeOption = 'posted_date' | 'received_date';

// Define the specific shape for stance counts
type StanceCountMap = {
  'For': number;
  'Against': number;
  'Neutral/Unclear': number;
};

// Type for server-processed time series data
interface ServerProcessedTimeSeriesData {
  posted_date: StanceData[];
  received_date: StanceData[];
  error?: string;
  fetchedCommentCount?: number;
}

// Helper function to process comments into StanceData[] for a given date type
// This will be used on the server.
const processCommentsForDateType = (comments: Comment[], dateType: keyof Comment): StanceData[] => {
  if (!comments || comments.length === 0) return [];

  const groupedData = comments.reduce((acc: Record<string, StanceCountMap>, comment: Comment) => {
    let dateStr: string;
    const dateValue = comment[dateType];
    
    if (dateValue) {
      const parsedDate = dateValue instanceof Date ? dateValue : (typeof dateValue === 'string' ? new Date(dateValue) : null);
      if (parsedDate && !isNaN(parsedDate.getTime())) {
        dateStr = parsedDate.toISOString().split('T')[0];
      } else {
        return acc; // Skip if date is invalid
      }
    } else {
      return acc; // Skip if date is missing
    }

    if (!acc[dateStr]) {
      acc[dateStr] = { 'For': 0, 'Against': 0, 'Neutral/Unclear': 0 };
    }
    const stance = comment.stance || 'Neutral/Unclear';
    if (stance === 'For' || stance === 'Against' || stance === 'Neutral/Unclear') {
      acc[dateStr][stance]++;
    }
    return acc;
  }, {});

  const dateKeys = Object.keys(groupedData).sort();
  if (dateKeys.length === 0) return [];

  const startDate = new Date(dateKeys[0]);
  const endDate = new Date(dateKeys[dateKeys.length - 1]);
  const filledData: StanceData[] = [];
  const currentDate = new Date(startDate);

  while (currentDate <= endDate) {
    const dateStr = currentDate.toISOString().split('T')[0];
    const existingData = groupedData[dateStr];
    if (existingData) {
      filledData.push({ date: dateStr, ...existingData });
    } else {
      filledData.push({ date: dateStr, 'For': 0, 'Against': 0, 'Neutral/Unclear': 0 });
    }
    currentDate.setDate(currentDate.getDate() + 1);
  }
  return filledData;
};

// This component will now be an Async Server Component primarily, with client-side pieces.
// We pass the serverProcessedData to a client component that handles the state for date selection.
export default async function StanceOverTimeCardWrapper() {
  // These still come from client context, but are used to fetch data ON THE SERVER
  // For a true RSC, this context data would ideally be available during server render or passed differently.
  // However, for now, we'll construct options and fetch here. This implies StanceOverTimeCardWrapper
  // itself might need to be called from a parent that can await it if these context values are dynamic on first load.
  // For simplicity, let's assume these are stable enough for an initial server fetch.

  // This part needs careful consideration for RSC. If filters/searchQuery/sorting change on client,
  // this server component won't automatically re-run. A full page refresh or revalidation trigger would be needed.
  // The prompt implies initial static generation, so this fetch runs at build/revalidation time.
  const paramsObj: Record<string, string> = {}; // Placeholder, ideally get from server context if possible
  // To truly make this server-side based on filters, those filters need to be passed from URL or a server context.
  // For now, let's make a simplified options object or fetch without them for demonstration of server-side processing.
  // If `useServerDataContext` is used in a Server Component, it must be from a Server Context or a prop.
  // Since we can't directly use client context hooks in server components for fetching, let's assume for now
  // we are fetching based on some initial or global options.
  const initialOptions: QueryOptions = {
    filters: {}, // Populate with global/default filters if any
    // search: '', // Populate if there's a global search for this chart
    // sort: undefined // Sorting might not be as relevant for time-series aggregation
  };

  console.log('[StanceOverTimeCardWrapper] Fetching all comments on server...');
  const response = await getAllCommentsForTimeSeries(initialOptions);
  
  let serverProcessedData: ServerProcessedTimeSeriesData;

  if (response.success && response.data) {
    console.log(`[StanceOverTimeCardWrapper] Successfully fetched ${response.data.length} comments on server.`);
    const postedDateData = processCommentsForDateType(response.data, 'postedDate');
    const receivedDateData = processCommentsForDateType(response.data, 'receivedDate');
    serverProcessedData = {
      posted_date: postedDateData,
      received_date: receivedDateData,
      fetchedCommentCount: response.data.length
    };
  } else {
    console.error('[StanceOverTimeCardWrapper] Failed to fetch comments on server:', response.error);
    serverProcessedData = {
      posted_date: [],
      received_date: [],
      error: response.error || "Failed to load time series data.",
      fetchedCommentCount: 0
    };
  }

  return <StanceOverTimeClientComponent serverProcessedData={serverProcessedData} />;
}

interface StanceOverTimeClientComponentProps {
  serverProcessedData: ServerProcessedTimeSeriesData;
}

function StanceOverTimeClientComponent({ serverProcessedData }: StanceOverTimeClientComponentProps) {
  const [selectedDateType, setSelectedDateType] = useState<DateTypeOption>('posted_date');
  const [chartLoading, setChartLoading] = useState(false); // To handle brief loading on date type change
  const [hasLoadedOnce, setHasLoadedOnce] = useState(true); // Data is loaded on server, so true

  // Context for loading skeleton, not for data fetching itself here
  const { loading: contextLoading } = useServerDataContext(); 

  const chartData = useMemo(() => {
    if (serverProcessedData.error) return [];
    return serverProcessedData[selectedDateType] || [];
  }, [serverProcessedData, selectedDateType]);

  useEffect(() => {
    // If server-side fetch had an error, log it or handle as needed
    if (serverProcessedData.error) {
      console.warn("[StanceOverTimeClientComponent] Server fetch error:", serverProcessedData.error);
    }
    console.log("[StanceOverTimeClientComponent] Initial server fetched comment count:", serverProcessedData.fetchedCommentCount);
  }, [serverProcessedData]);

  if (contextLoading && !serverProcessedData.fetchedCommentCount) { // Show skeleton if main page is loading and no data yet
    return <LoadingSkeleton />;
  }

  if (serverProcessedData.error && chartData.length === 0) {
    return <NoDataMessage />;
  }
  
  if (chartData.length === 0 && hasLoadedOnce) { // Check chartData directly
     return <NoDataMessage />;
  }

  return (
    <Card className="h-auto">
      <Card.Header className="bg-gradient-to-r from-indigo-500 to-purple-600 flex justify-between items-center">
        <h5 className="text-lg font-bold text-white flex items-center">
          <span className="mr-2">📈</span>
          Comments Over Time
          {serverProcessedData.fetchedCommentCount !== undefined && 
            <span className="text-xs ml-2 opacity-80">({serverProcessedData.fetchedCommentCount} comments considered)</span>
          }
        </h5>
        <div className="flex items-center gap-2">
          <div className="relative">
            <select 
              value={selectedDateType}
              onChange={(e) => {
                setChartLoading(true);
                setSelectedDateType(e.target.value as DateTypeOption);
                setTimeout(() => setChartLoading(false), 50); // Simulate brief load for UI feedback
              }}
              className="bg-white bg-opacity-20 text-white text-sm px-3 py-1 rounded-md focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-50 appearance-none pr-8"
            >
              <option value="posted_date" className="text-gray-700">By Posted Date</option>
              <option value="received_date" className="text-gray-700">By Received Date</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-white">
              <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
            </div>
          </div>
          {/* Collapse button can be added here if needed, currently managed by parent */}
        </div>
      </Card.Header>
      {chartLoading ? (
        <div className="p-4 text-center text-gray-500">Updating chart...</div>
      ) : (
        <Card.Body className="p-4">
          <ChartSelector data={chartData} chartType={"svg"} />
        </Card.Body>
      )}
    </Card>
  );
} 