// components/CommentTable.tsx
'use client';

import { useState, useEffect, useRef } from 'react';
import { CommentWithAnalysis } from '@/lib/db/schema';
import { Field, datasetConfig } from '@/lib/config';
import { useDataTable } from '@/lib/hooks/useDataTable';

interface CommentTableProps {
  data: CommentWithAnalysis[];
  filters: Record<string, unknown>;
}

export default function CommentTable({ data, filters }: CommentTableProps) {
  const { 
    filteredData, 
    searchQuery, 
    setSearchQuery, 
    sorting, 
    handleSort, 
    exportCSV 
  } = useDataTable({ data, filters });
  
  const [visibleColumns, setVisibleColumns] = useState<Record<string, boolean>>(() => {
    // Initialize visible columns from config
    const initial: Record<string, boolean> = {};
    datasetConfig.fields.forEach(field => {
      initial[field.key] = field.visible !== false;
    });
    return initial;
  });
  
  const [showColumnsMenu, setShowColumnsMenu] = useState(false);
  
  // Toggle column visibility
  const toggleColumnVisibility = (key: string) => {
    setVisibleColumns(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };
  
  // Get visible fields based on current visibility state
  const getVisibleFields = () => {
    return datasetConfig.fields.filter(field => visibleColumns[field.key]);
  };
  
  // Setup tooltips for truncated content
  useEffect(() => {
    // Close dropdown when clicking outside
    const handleClickOutside = (e: MouseEvent) => {
      if (showColumnsMenu && !(e.target as Element).closest('.columns-dropdown')) {
        setShowColumnsMenu(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showColumnsMenu]);
  
  // Render cell content with appropriate formatting
  const renderCell = (item: CommentWithAnalysis, field: Field) => {
    let value: any;
    
    // Get the appropriate value based on the field key
    if (field.key === 'stance' || field.key === 'keyQuote' || 
        field.key === 'themes' || field.key === 'rationale') {
      value = item.analysis?.[field.key as keyof typeof item.analysis] || '';
    } else {
      value = item[field.key as keyof typeof item] || '';
    }
    
    if (value === null || value === undefined || value === '') {
      return <span className="text-gray-400 italic">—</span>;
    }
    
    // Handle different field formats
    if (field.format === 'multi-label' && typeof value === 'string') {
      const labels = value.split(',').map(label => label.trim()).filter(Boolean);
      return (
        <div className="flex flex-wrap gap-1">
          {labels.map((label, i) => (
            <span key={i} className="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800">
              {label}
            </span>
          ))}
        </div>
      );
    }
    
    if (field.format === 'link' && typeof value === 'string') {
      return (
        <a 
          href={value} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="text-blue-600 hover:text-blue-800 flex items-center hover:underline"
        >
          <span className="mr-1">🔗</span>View
        </a>
      );
    }
    
    if (field.badges && typeof value === 'string' && field.badges[value as keyof typeof field.badges]) {
      const badgeClass = field.badges[value as keyof typeof field.badges];
      const badgeColor = getBadgeColorClass(badgeClass);
      
      return (
        <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${badgeColor}`}>
          {value}
        </span>
      );
    }
    
    if (field.charLimit && typeof value === 'string' && value.length > field.charLimit) {
      const truncated = value.substring(0, field.charLimit) + '...';
      return (
        <span title={value} className="cursor-help">
          {truncated}
        </span>
      );
    }
    
    return value;
  };
  
  // Helper to get Tailwind color class for badges
  const getBadgeColorClass = (badgeClass: string) => {
    if (badgeClass.includes('success')) return 'bg-green-100 text-green-800';
    if (badgeClass.includes('danger')) return 'bg-red-100 text-red-800';
    if (badgeClass.includes('warning')) return 'bg-yellow-100 text-yellow-800';
    if (badgeClass.includes('primary')) return 'bg-blue-100 text-blue-800';
    return 'bg-gray-100 text-gray-800';
  };
  
  // Get column classes including sorting
  const getColumnClasses = (field: Field) => {
    const baseClasses = "cursor-pointer transition-colors duration-150";
    
    if (sorting?.column === field.key) {
      return `${baseClasses} ${sorting.direction === 'asc' ? 'text-blue-600' : 'text-blue-600'}`;
    }
    
    return `${baseClasses} hover:text-blue-500`;
  };
  
  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
      <div className="border-b border-gray-200 px-6 py-4 bg-gradient-to-r from-purple-500 to-purple-600">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <h5 className="text-lg font-bold text-white flex items-center">
            <span className="mr-2">📋</span>
            Comment Data
          </h5>
          <div className="flex flex-wrap items-center gap-2">
            {/* Search input */}
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                className="bg-white bg-opacity-20 placeholder-white placeholder-opacity-70 text-white border border-transparent rounded py-2 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-40 focus:border-transparent"
                placeholder="Search comments..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            
            {/* Column visibility dropdown */}
            <div className="relative inline-block columns-dropdown">
              <button 
                className="flex items-center px-3 py-2 text-sm font-medium bg-white bg-opacity-20 rounded hover:bg-opacity-30 focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-40 text-white transition-colors"
                onClick={() => setShowColumnsMenu(!showColumnsMenu)}
              >
                <span className="mr-1">👁️</span>Columns
              </button>
              {showColumnsMenu && (
                <div className="absolute right-0 z-50 mt-1 w-56 bg-white rounded-md shadow-lg border border-gray-200">
                  <div className="py-1 max-h-64 overflow-y-auto">
                    {datasetConfig.fields.map(field => (
                      <div 
                        key={field.key} 
                        className="px-4 py-2 hover:bg-gray-100 cursor-pointer flex items-center"
                        onClick={() => toggleColumnVisibility(field.key)}
                      >
                        <input
                          type="checkbox"
                          id={`col-${field.key}`}
                          className="mr-2 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                          checked={visibleColumns[field.key]}
                          onChange={() => {}}
                        />
                        <label htmlFor={`col-${field.key}`} className="text-sm text-gray-700 cursor-pointer">
                          {field.title}
                        </label>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            
            <button 
              className="flex items-center px-3 py-2 text-sm font-medium bg-white bg-opacity-20 rounded hover:bg-opacity-30 focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-40 text-white transition-colors"
              onClick={exportCSV}
            >
              <span className="mr-1">📥</span>Export CSV
            </button>
          </div>
        </div>
      </div>
      <div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {getVisibleFields().map(field => (
                  <th 
                    key={field.key} 
                    className={`px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider ${getColumnClasses(field)}`}
                    onClick={() => handleSort(field.key)}
                  >
                    <div className="flex items-center">
                      {field.title}
                      {sorting?.column === field.key && (
                        <span className="ml-1 text-blue-600">
                          {sorting.direction === 'asc' ? '↑' : '↓'}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredData.length === 0 ? (
                <tr>
                  <td 
                    colSpan={getVisibleFields().length} 
                    className="px-6 py-10 text-center text-gray-500 bg-gray-50"
                  >
                    <div className="flex flex-col items-center">
                      <svg className="w-12 h-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="mt-2 text-sm font-medium">No matching records found</p>
                      <p className="text-xs text-gray-400 mt-1">Try changing your search criteria</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredData.map(item => (
                  <tr key={item.id} className="hover:bg-blue-50 transition-colors">
                    {getVisibleFields().map(field => (
                      <td key={`${item.id}-${field.key}`} className="px-4 py-3 whitespace-normal text-sm text-gray-900">
                        {renderCell(item, field)}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Pagination/Length Controls */}
        <div className="flex justify-between items-center px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
          <div>
            Showing <span className="font-medium text-gray-700">{filteredData.length}</span> of <span className="font-medium text-gray-700">{data.length}</span> entries
          </div>
          <div className="flex items-center">
            <span className="mr-2">Show</span>
            <select className="form-select rounded-md border-gray-300 py-1 pl-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
              <option value="10">10</option>
              <option value="25">25</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
            <span className="ml-2">entries</span>
          </div>
        </div>
      </div>
    </div>
  );
}