// components/FilterSection.tsx
'use client';

import { useState, useEffect } from 'react';
import { Field, datasetConfig } from '@/lib/config';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import FilterModal from './FilterModal';

interface FilterSectionProps {
  onFilterChange: (filters: Record<string, unknown>) => void;
}

export default function FilterSection({ onFilterChange }: FilterSectionProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  
  const [filters, setFilters] = useState<Record<string, unknown>>({});
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [activeField, setActiveField] = useState<Field | null>(null);
  
  // Load filters from URL on mount
  useEffect(() => {
    const initialFilters: Record<string, unknown> = {};
    const filterableFields = datasetConfig.fields.filter(field => field.filter);
    
    // Process URL parameters
    filterableFields.forEach(field => {
      const filterKey = getFilterKey(field.key);
      const filterParam = searchParams.get(`filter_${filterKey}`);
      
      if (filterParam) {
        try {
          // Try parsing as JSON for arrays
          const parsedValue = JSON.parse(filterParam);
          initialFilters[filterKey] = parsedValue;
        } catch {
          // If not valid JSON, use as string
          initialFilters[filterKey] = filterParam;
        }
      }
    });
    
    // Only update if filters actually changed
    if (JSON.stringify(initialFilters) !== JSON.stringify(filters)) {
      setFilters(initialFilters);
      onFilterChange(initialFilters);
    }
  }, [searchParams, onFilterChange]);
  
  // Map field keys to their full path for nested fields
  const getFilterKey = (key: string) => {
    // Map analysis fields to their proper nested path
    if (['stance', 'keyQuote', 'themes', 'rationale'].includes(key)) {
      return `analysis.${key}`;
    }
    return key;
  };
  
  // Function to update filters and URL
  const updateFilters = (newFilters: Record<string, unknown>) => {
    setFilters(newFilters);
    onFilterChange(newFilters);
    const params = new URLSearchParams(searchParams.toString());
    Array.from(params.keys())
      .filter(key => key.startsWith('filter_'))
      .forEach(key => params.delete(key));
    Object.entries(newFilters).forEach(([key, value]) => {
      if (value === null || value === undefined || 
         (Array.isArray(value) && value.length === 0) || 
         value === '') {
        return;
      }
      const stringValue = typeof value === 'object' 
        ? JSON.stringify(value) 
        : String(value);
      params.set(`filter_${key}`, stringValue);
    });
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };
  
  // Handle filter change
  const handleFilterChange = (key: string, value: unknown) => {
    const newFilters = { ...filters };
    
    // Use the appropriate filter key (mapping to nested fields if needed)
    const filterKey = getFilterKey(key);
    
    // If value is empty, remove the filter
    if (!value || (Array.isArray(value) && value.length === 0)) {
      delete newFilters[filterKey];
    } else {
      newFilters[filterKey] = value;
    }
    
    // Update filters and URL
    updateFilters(newFilters);
  };
  
  // Clear all filters
  const clearAllFilters = () => {
    updateFilters({});
  };
  
  // Open filter modal
  const openFilterModal = (field: Field) => {
    setActiveField(field);
    // Get the filter key for this field
    getFilterKey(field.key);
    // Set showFilterModal after activeField is set to ensure proper modal rendering
    setShowFilterModal(true);
  };
  
  // Close filter modal
  const closeFilterModal = () => {
    setShowFilterModal(false);
    setActiveField(null);
  };
  
  // Check if we have any active filters
  const hasActiveFilters = Object.keys(filters).length > 0;
  
  // Helper to render filter tags for active filters
  const renderFilterTags = () => {
    if (!hasActiveFilters) {
      return (
        <div className="text-center py-4 bg-blue-50 rounded-lg border border-blue-100">
          <div className="text-blue-600 font-medium mb-1">No filters applied</div>
          <div className="text-blue-500 text-sm">Use the filter buttons below to refine your data view</div>
        </div>
      );
    }
    
    return Object.entries(filters).map(([key, value]) => {
      // Find matching field, checking both direct and nested keys
      const field = datasetConfig.fields.find(f => {
        const mappedKey = getFilterKey(f.key);
        return mappedKey === key || f.key === key;
      });
      
      if (!field) return null;
      
      // Handle different filter types
      if (Array.isArray(value)) {
        return (value as unknown[]).map((v, i) => (
          <div 
            key={`${key}-${i}`}
            className="bg-blue-500 text-white rounded-full px-3 py-1.5 mr-2 mb-2 text-sm inline-flex items-center shadow-sm hover:bg-blue-600 transition-colors"
          >
            <span className="mr-1 font-medium">{field.title}:</span> 
            <span>{String(v)}</span>
            <button 
              className="ml-2 inline-flex items-center justify-center w-5 h-5 bg-white bg-opacity-20 rounded-full text-xs hover:bg-opacity-30 transition-colors"
              onClick={() => handleFilterChange(key, (value as unknown[]).filter(item => item !== v))}
              aria-label="Remove filter"
            >
              ×
            </button>
          </div>
        ));
      } else {
        // Handle non-array values
        return (
          <div 
            key={key}
            className="bg-blue-500 text-white rounded-full px-3 py-1.5 mr-2 mb-2 text-sm inline-flex items-center shadow-sm hover:bg-blue-600 transition-colors"
          >
            <span className="mr-1 font-medium">{field.title}:</span> 
            <span>{String(value)}</span>
            <button 
              className="ml-2 inline-flex items-center justify-center w-5 h-5 bg-white bg-opacity-20 rounded-full text-xs hover:bg-opacity-30 transition-colors"
              onClick={() => handleFilterChange(key, null)}
              aria-label="Remove filter"
            >
              ×
            </button>
          </div>
        );
      }
    });
  };
  
  // Render available filters as buttons
  const renderFilterButtons = () => {
    const filterableFields = datasetConfig.fields.filter(field => field.filter);
    
    return (
      <div className="flex flex-wrap gap-2 mt-4">
        {filterableFields.map(field => (
          <button 
            key={field.key}
            className={`px-3 py-2 rounded-md text-sm font-medium transition-colors 
              ${filters[field.key] 
                ? 'bg-blue-500 text-white hover:bg-blue-600' 
                : 'bg-gray-100 text-gray-800 hover:bg-gray-200 border border-gray-300'}`}
            onClick={() => openFilterModal(field)}
          >
            {field.title}
          </button>
        ))}
      </div>
    );
  };
  
  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
      <div className="border-b border-gray-200 px-6 py-4 bg-gradient-to-r from-indigo-500 to-indigo-600 flex justify-between items-center">
        <h5 className="text-lg font-bold text-white flex items-center">
          <span className="mr-2">{hasActiveFilters ? '🔍' : '⚙️'}</span>
          {hasActiveFilters ? 'Active Filters' : 'Filters'}
        </h5>
        {hasActiveFilters && (
          <button 
            className="bg-white bg-opacity-20 hover:bg-opacity-30 text-white text-sm px-3 py-1 rounded transition-colors"
            onClick={clearAllFilters}
          >
            Clear All
          </button>
        )}
      </div>
      <div className="p-4">
        <div className={`flex flex-wrap mb-4 ${
          hasActiveFilters ? '' : 'hidden'
        }`}>
          {renderFilterTags()}
        </div>
        
        {!hasActiveFilters && renderFilterTags()}
        
        <div className="mt-4 pt-4 border-t border-gray-200">
          <h6 className="font-medium text-gray-700 mb-2">Filter Options</h6>
          {renderFilterButtons()}
        </div>
      </div>
      
      {/* Filter Modal - only render when showFilterModal is true */}
      {activeField && (
        <FilterModal 
          field={activeField}
          currentValue={filters[getFilterKey(activeField.key)] || null}
          onClose={closeFilterModal}
          onApply={(value) => {
            handleFilterChange(activeField.key, value);
            closeFilterModal();
          }}
          isOpen={showFilterModal}
        />
      )}
    </div>
  );
}