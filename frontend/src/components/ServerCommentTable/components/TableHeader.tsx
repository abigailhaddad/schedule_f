import React from 'react';
import SearchInput from '@/components/ui/SearchInput';
import { datasetConfig } from '@/lib/config';

interface TableHeaderProps {
  searchQuery: string;
  onSearchChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  showColumnsMenu: boolean;
  setShowColumnsMenu: (show: boolean) => void;
  visibleColumns: Record<string, boolean>;
  toggleColumnVisibility: (key: string) => void;
  exportCSV: () => void;
}

export default function TableHeader({
  searchQuery,
  onSearchChange,
  showColumnsMenu,
  setShowColumnsMenu,
  visibleColumns,
  toggleColumnVisibility,
  exportCSV,
}: TableHeaderProps) {
  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <h5 className="text-lg font-bold text-white flex items-center">
          <span className="mr-2">📋</span>
          Comment Data
        </h5>
        <div className="flex flex-wrap items-center gap-2">
          {/* Search input */}
          <SearchInput
            value={searchQuery}
            onChange={onSearchChange}
            placeholder="Search comments..."
          />
          
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
  );
} 