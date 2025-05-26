import React from 'react';
import { datasetConfig } from '@/lib/config';

interface ColumnVisibilityMenuProps {
  visibleColumns: Record<string, boolean>;
  onToggle: (key: string) => void;
  isOpen: boolean;
  onToggleMenu: () => void;
}

export function ColumnVisibilityMenu({ 
  visibleColumns, 
  onToggle, 
  isOpen, 
  onToggleMenu 
}: ColumnVisibilityMenuProps) {
  return (
    <div className="relative inline-block column-visibility-menu">
      <button 
        className="flex items-center px-3 py-2 text-sm font-medium bg-white bg-opacity-20 rounded hover:bg-opacity-30 focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-40 text-white transition-colors"
        onClick={onToggleMenu}
      >
        <span className="mr-1">👁️</span>
        Columns
      </button>
      
      {isOpen && (
        <div className="absolute right-0 z-50 mt-1 w-56 bg-white rounded-md shadow-lg border border-gray-200">
          <div className="py-1 max-h-64 overflow-y-auto">
            {datasetConfig.fields.map(field => (
              <div 
                key={field.key} 
                className="px-4 py-2 hover:bg-gray-100 cursor-pointer flex items-center"
                onClick={() => onToggle(field.key)}
              >
                <input
                  type="checkbox"
                  id={`col-${field.key}`}
                  className="mr-2 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  checked={visibleColumns[field.key]}
                  onChange={() => {}} // Controlled by onClick
                  onClick={(e) => e.stopPropagation()}
                />
                <label 
                  htmlFor={`col-${field.key}`} 
                  className="text-sm text-gray-700 cursor-pointer flex-1"
                >
                  {field.title}
                </label>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
} 