'use client';

import { useMemo, useState, useEffect } from 'react';
import { useServerDataContext } from '@/contexts/ServerDataContext';
import { getPaginatedComments, parseUrlToQueryOptions } from '@/lib/actions/comments';
import { Comment } from '@/lib/db/schema';
import Card from '@/components/ui/Card';
import LoadingSkeleton from './LoadingSkeleton';
import NoDataMessage from './NoDataMessage';
import ChartSelector from './ChartSelector';
import { StanceData, ChartType } from './types';

// Define the type for date selection
type DateTypeOption = 'posted_date' | 'received_date';

// Define the specific shape for stance counts
type StanceCountMap = {
  'For': number;
  'Against': number;
  'Neutral/Unclear': number;
};

export default function StanceOverTimeCard() {
  const { loading: contextLoading, filters, searchQuery, sorting } = useServerDataContext();
  const [selectedDateType, setSelectedDateType] = useState<DateTypeOption>('posted_date');
  const [selectedChartType, setSelectedChartType] = useState<ChartType>('svg');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [allCommentsData, setAllCommentsData] = useState<Comment[]>([]);
  const [chartLoading, setChartLoading] = useState(true);
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false);

  // Fetch all comments for time series (using large page size to get everything)
  useEffect(() => {
    const fetchAllComments = async () => {
      setChartLoading(true);
      try {
        // Create params object from current context state
        const paramsObj: Record<string, string> = {};
        
        // Add search query if it exists
        if (searchQuery) {
          paramsObj.search = searchQuery;
        }
        
        // Add sorting if it exists
        if (sorting) {
          paramsObj.sort = sorting.column;
          paramsObj.sortDirection = sorting.direction;
        }
        
        // Add filters
        Object.entries(filters).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            const stringValue = typeof value === "object" ? JSON.stringify(value) : String(value);
            paramsObj[`filter_${key}`] = stringValue;
          }
        });

        const options = await parseUrlToQueryOptions(paramsObj);
        
        // Override pagination to get all data
        options.page = 1;
        options.pageSize = 10000; // Large page size to get all comments
        
        const response = await getPaginatedComments(options);
        
        if (response.success && response.data) {
          setAllCommentsData(response.data);
          console.log(`[StanceOverTimeCard] Fetched ${response.data.length} comments for time series`);
        } else {
          console.error('[StanceOverTimeCard] Failed to fetch comments:', response.error);
          setAllCommentsData([]);
        }
        setHasLoadedOnce(true);
      } catch (error) {
        console.error('[StanceOverTimeCard] Error fetching comments:', error);
        setAllCommentsData([]);
        setHasLoadedOnce(true);
      } finally {
        setChartLoading(false);
      }
    };

    // Only fetch when context is not loading
    if (!contextLoading) {
      fetchAllComments();
    }
  }, [contextLoading, filters, searchQuery, sorting]);

  // Process data to group by date and stance
  const chartData = useMemo(() => {
    if (!allCommentsData || allCommentsData.length === 0) {
      return [];
    }

    const groupedData = allCommentsData.reduce((acc: Record<string, StanceCountMap>, comment: Comment) => {
      let dateStr: string;
      const dateValue = (comment as any)[selectedDateType];
      
      if (dateValue) {
        const parsedDate = dateValue instanceof Date ? dateValue : (typeof dateValue === 'string' ? new Date(dateValue) : null);
        if (parsedDate && !isNaN(parsedDate.getTime())) {
          dateStr = parsedDate.toISOString().split('T')[0];
        } else {
          return acc;
        }
      } else {
        return acc;
      }

      if (!acc[dateStr]) {
        acc[dateStr] = {
          'For': 0,
          'Against': 0,
          'Neutral/Unclear': 0
        };
      }

      const stance = comment.stance || 'Neutral/Unclear';
      if (stance === 'For' || stance === 'Against' || stance === 'Neutral/Unclear') {
        acc[dateStr][stance]++;
      }

      return acc;
    }, {});

    // Convert to array format
    const dateKeys = Object.keys(groupedData).sort();
    
    if (dateKeys.length === 0) {
      return [];
    }
    
    // Fill in missing dates between earliest and latest
    const startDate = new Date(dateKeys[0]);
    const endDate = new Date(dateKeys[dateKeys.length - 1]);
    const filledData: StanceData[] = [];
    
    const currentDate = new Date(startDate);
    while (currentDate <= endDate) {
      const dateStr = currentDate.toISOString().split('T')[0];
      const existingData = groupedData[dateStr];
      
      if (existingData) {
        filledData.push({
          date: dateStr,
          ...existingData
        });
      } else {
        filledData.push({
          date: dateStr,
          'For': 0,
          'Against': 0,
          'Neutral/Unclear': 0
        });
      }
      
      currentDate.setDate(currentDate.getDate() + 1);
    }

    return filledData;
  }, [allCommentsData, selectedDateType]);

  // Show loading skeleton while either context or chart is loading
  if (contextLoading || chartLoading) {
    return <LoadingSkeleton />;
  }

  // Only show "no data" message after we've tried loading at least once
  if (hasLoadedOnce && chartData.length === 0) {
    return <NoDataMessage />;
  }

  return (
    <Card className="h-auto">
      <Card.Header className="bg-gradient-to-r from-indigo-500 to-purple-600 flex justify-between items-center">
        <h5 className="text-lg font-bold text-white flex items-center">
          <span className="mr-2">📈</span>
          Comments Over Time
        </h5>
        <div className="flex items-center gap-2">
          <div className="relative">
            <select 
              value={selectedDateType}
              onChange={(e) => setSelectedDateType(e.target.value as DateTypeOption)}
              className="bg-white bg-opacity-20 text-white text-sm px-3 py-1 rounded-md focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-50 appearance-none pr-8"
            >
              <option value="posted_date" className="text-gray-700">By Posted Date</option>
              <option value="received_date" className="text-gray-700">By Received Date</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-white">
              <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
            </div>
          </div>
          <button onClick={() => setIsCollapsed(!isCollapsed)} className="text-white text-lg">
            {isCollapsed ? '►' : '▼'}
          </button>
        </div>
      </Card.Header>
      {!isCollapsed && (
        <Card.Body className="p-4">
          <ChartSelector data={chartData} chartType={selectedChartType} />
        </Card.Body>
      )}
    </Card>
  );
} 