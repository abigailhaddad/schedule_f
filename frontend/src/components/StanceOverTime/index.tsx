'use client';

import { useMemo, useState, useEffect } from 'react';
import { useServerDataContext } from '@/contexts/ServerDataContext';
import { getPaginatedComments, parseUrlToQueryOptions } from '@/lib/actions/comments';
import { Comment } from '@/lib/db/schema';
import Card from '@/components/ui/Card';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import CustomTooltip from './CustomTooltip';
import LoadingSkeleton from './LoadingSkeleton';
import NoDataMessage from './NoDataMessage';

interface StanceData {
  date: string;
  For: number;
  Against: number;
  'Neutral/Unclear': number;
}

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
  const [allCommentsData, setAllCommentsData] = useState<Comment[]>([]);
  const [chartLoading, setChartLoading] = useState(true);

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
      } catch (error) {
        console.error('[StanceOverTimeCard] Error fetching comments:', error);
        setAllCommentsData([]);
      } finally {
        setChartLoading(false);
      }
    };

    // Only fetch when context is not loading
    if (!contextLoading) {
      fetchAllComments();
    }
  }, [contextLoading, filters, searchQuery, sorting]);

  console.log('[StanceOverTimeCard] Chart data state:', { 
    contextLoading, 
    chartLoading, 
    allCommentsCount: allCommentsData.length, 
    selectedDateType 
  });

  // Process data to group by date and stance
  const chartData = useMemo(() => {
    if (!allCommentsData || allCommentsData.length === 0) {
      console.log('[StanceOverTimeCard] chartData: No data available for processing.');
      return [];
    }
    console.log('[StanceOverTimeCard] chartData: Processing', allCommentsData.length, 'comments using date field:', selectedDateType);

    // Log the first comment to inspect its structure if data is available (debug mode)
    if (allCommentsData.length > 0 && process.env.NODE_ENV === 'development') {
      console.log('[StanceOverTimeCard] Sample comment fields:', Object.keys(allCommentsData[0]));
      console.log(`[StanceOverTimeCard] ${selectedDateType} sample:`, (allCommentsData[0] as any)[selectedDateType]);
    }

    const groupedData = allCommentsData.reduce((acc: Record<string, StanceCountMap>, comment: Comment) => {
      let dateStr: string;
      const dateValue = (comment as any)[selectedDateType]; // Use type assertion to access snake_case fields
      
      if (dateValue) {
        // Ensure dateValue is treated as a string or Date before passing to new Date()
        // Safely convert to Date object
        const parsedDate = dateValue instanceof Date ? dateValue : (typeof dateValue === 'string' ? new Date(dateValue) : null);
        if (parsedDate && !isNaN(parsedDate.getTime())) {
          dateStr = parsedDate.toISOString().split('T')[0];
          // Only log first few for debugging
          // console.log(`[StanceOverTimeCard] Comment ${comment.id}: ${selectedDateType} = "${dateValue}" -> dateStr = "${dateStr}"`);
        } else {
          console.log(`[StanceOverTimeCard] Skipping comment due to invalid ${selectedDateType} format. Comment ID:`, comment.id, 'Value:', dateValue);
          return acc;
        }
      } else {
        console.log(`[StanceOverTimeCard] Skipping comment due to missing ${selectedDateType}. Comment ID:`, comment.id);
        return acc;
      }

      if (!acc[dateStr]) {
        acc[dateStr] = { // Initialize with all keys for StanceCountMap
          'For': 0,
          'Against': 0,
          'Neutral/Unclear': 0
        };
      }

      const stance = comment.stance || 'Neutral/Unclear';
      // Only increment if stance is one of the expected keys
      if (stance === 'For' || stance === 'Against' || stance === 'Neutral/Unclear') {
        acc[dateStr][stance]++;
      }

      return acc;
    }, {} as Record<string, StanceCountMap>); // Type assertion for initial value

    // console.log('[StanceOverTimeCard] Grouped data by date:', groupedData); // Removed verbose logging
    console.log('[StanceOverTimeCard] Unique dates found:', Object.keys(groupedData).length, 'dates');
    if (Object.keys(groupedData).length <= 5) {
      console.log('[StanceOverTimeCard] Date breakdown:', Object.keys(groupedData));
    }

    // Convert to array format for recharts and fill in missing dates
    const dateKeys = Object.keys(groupedData).sort();
    
    if (dateKeys.length === 0) {
      console.log('[StanceOverTimeCard] No valid dates found in data');
      return [];
    }
    
    if (dateKeys.length === 1) {
      console.log('[StanceOverTimeCard] Only one date found, showing single data point');
      // For single date, just return the data as-is
      const result: StanceData[] = Object.entries(groupedData)
        .map(([date, stancesValue]) => ({ 
          date,
          ...stancesValue 
        }));
      return result;
    }

    // Fill in missing dates between earliest and latest
    const startDate = new Date(dateKeys[0]);
    const endDate = new Date(dateKeys[dateKeys.length - 1]);
    const filledData: StanceData[] = [];
    
    console.log('[StanceOverTimeCard] Filling date range from', startDate.toISOString().split('T')[0], 'to', endDate.toISOString().split('T')[0]);
    
    const currentDate = new Date(startDate);
    while (currentDate <= endDate) {
      const dateStr = currentDate.toISOString().split('T')[0];
      const existingData = groupedData[dateStr];
      
      if (existingData) {
        // Use existing data
        filledData.push({
          date: dateStr,
          ...existingData
        });
      } else {
        // Fill with zeros for missing dates
        filledData.push({
          date: dateStr,
          'For': 0,
          'Against': 0,
          'Neutral/Unclear': 0
        });
      }
      
      // Move to next day
      currentDate.setDate(currentDate.getDate() + 1);
    }

    console.log('[StanceOverTimeCard] Calculated chartData with filled dates:', filledData);
    return filledData;
  }, [allCommentsData, selectedDateType]);

  console.log('[StanceOverTimeCard] Final chartData for rendering:', chartData);
  console.log('[StanceOverTimeCard] chartData length:', chartData.length);
  
  // Detailed logging for debugging (uncomment if needed)
  // if (chartData.length > 0) {
  //   console.log('[StanceOverTimeCard] First chartData entry:', JSON.stringify(chartData[0], null, 2));
  //   console.log('[StanceOverTimeCard] chartData sample for recharts:');
  //   chartData.slice(0, 3).forEach((entry, index) => {
  //     console.log(`  Entry ${index}:`, entry);
  //   });
  // }

  // Custom tooltip component
  // const CustomTooltip = ({ active, payload, label }: any) => { // Removed inline component
  //   if (active && payload && payload.length) {
  //     return (
  //       <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
  //         <p className="text-sm font-semibold text-gray-700 mb-2">
  //           {new Date(label).toLocaleDateString('en-US', { 
  //             month: 'short', 
  //             day: 'numeric', 
  //             year: 'numeric' 
  //           })}
  //         </p>
  //         {payload.map((entry: any, index: number) => (
  //           <p key={index} className="text-sm" style={{ color: entry.color }}>
  //             {entry.name}: <span className="font-semibold">{entry.value}</span>
  //           </p>
  //         ))}
  //         <p className="text-xs text-gray-500 mt-1">
  //           Total: {payload.reduce((sum: number, entry: any) => sum + entry.value, 0)}
  //         </p>
  //       </div>
  //     );
  //   }
  //   return null;
  // };

  // Format date for X-axis
  const formatXAxis = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (chartLoading) {
    return <LoadingSkeleton />;
  }

  if (chartData.length === 0) {
    return <NoDataMessage />;
  }

  // Handle single data point case
  if (chartData.length === 1) {
    const singleEntry = chartData[0];
    return (
      <Card className="h-96">
        <Card.Header className="bg-gradient-to-r from-indigo-500 to-purple-600 flex justify-between items-center">
          <h5 className="text-lg font-bold text-white flex items-center">
            <span className="mr-2">📊</span>
            Comments Summary ({singleEntry.date})
          </h5>
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
        </Card.Header>
        <Card.Body className="p-6 text-center">
          <p className="text-sm text-gray-600 mb-4">
            All comments in the current dataset are from the same date. Time series requires multiple dates.
          </p>
          <div className="grid grid-cols-3 gap-4 max-w-md mx-auto">
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <div className="text-2xl font-bold text-green-600">{singleEntry.For}</div>
              <div className="text-sm text-green-800">For</div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="text-2xl font-bold text-red-600">{singleEntry.Against}</div>
              <div className="text-sm text-red-800">Against</div>
            </div>
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
              <div className="text-2xl font-bold text-gray-600">{singleEntry['Neutral/Unclear']}</div>
              <div className="text-sm text-gray-800">Neutral/Unclear</div>
            </div>
          </div>
        </Card.Body>
      </Card>
    );
  }

  return (
    <Card className="h-96">
      <Card.Header className="bg-gradient-to-r from-indigo-500 to-purple-600 flex justify-between items-center">
        <h5 className="text-lg font-bold text-white flex items-center">
          <span className="mr-2">📈</span>
          Comments Over Time
        </h5>
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
      </Card.Header>
      <Card.Body className="p-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 30, left: 0, bottom: 40 }}
          >
            <defs>
              <linearGradient id="colorFor" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.1}/>
              </linearGradient>
              <linearGradient id="colorAgainst" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1}/>
              </linearGradient>
              <linearGradient id="colorNeutral" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#64748b" stopOpacity={0.8}/>
                <stop offset="95%" stopColor="#64748b" stopOpacity={0.1}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="date" 
              tickFormatter={formatXAxis}
              tick={{ fontSize: 12 }}
              angle={-45}
              textAnchor="end"
              height={60}
            />
            <YAxis 
              tick={{ fontSize: 12 }}
              label={{ 
                value: 'Number of Comments', 
                angle: -90, 
                position: 'insideLeft',
                style: { fontSize: 14 }
              }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend 
              wrapperStyle={{ paddingTop: '20px' }}
              iconType="rect"
            />
            <Area
              type="monotone"
              dataKey="For"
              stackId="1"
              stroke="#10b981"
              fill="url(#colorFor)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="Against"
              stackId="1"
              stroke="#ef4444"
              fill="url(#colorAgainst)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="Neutral/Unclear"
              stackId="1"
              stroke="#64748b"
              fill="url(#colorNeutral)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card.Body>
    </Card>
  );
} 