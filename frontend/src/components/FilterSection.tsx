// components/FilterSection.tsx
// This component handles data filtering functionality and UI for the comments dataset
// It renders filter options, displays active filters, and manages filter state
'use client';

import { useState } from 'react';
import { Field, datasetConfig } from '@/lib/config';
import FilterModal from './FilterModal';
import { useDataContext } from '@/contexts/DataContext';

// FilterSection no longer needs props as it gets state from context
export default function FilterSection() {
  // Get filters and setFilters from the context
  const { filters, setFilters } = useDataContext();
  
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [activeField, setActiveField] = useState<Field | null>(null);
  
  // Note: All fields are now directly on the comments table, not nested
  
  // Handle filter change
  // Example: When selecting "For" in the stance filter:
  // 1. key="stance", value="For"
  // 2. newFilters becomes { "stance": "For" }
  // For themes with filter mode:
  // 1. key="themes", value={ values: ["Merit-based system concerns"], mode: "includes" }
  // 2. newFilters becomes { "themes": { values: ["Merit-based system concerns"], mode: "includes" } }
  const handleFilterChange = (key: string, value: unknown) => {
    const newFilters = { ...filters };
    
    // If value is empty or empty array, remove the filter
    if (!value ||
        (Array.isArray(value) && value.length === 0) ||
        (value && typeof value === 'object' && 'values' in value && Array.isArray(value.values) && value.values.length === 0)) {
      delete newFilters[key];
    } else {
      newFilters[key] = value;
    }
    
    // Update filters in the context
    setFilters(newFilters);
  };
  
  // Clear all filters
  // This removes all active filters and updates the URL to remove filter parameters
  const clearAllFilters = () => {
    setFilters({});
  };
  
  // Open filter modal
  // For example, when clicking the "Stance" filter button:
  // 1. activeField is set to the stance field configuration
  // 2. Modal opens showing options: "For", "Against", "Neutral/Unclear" (from stanceEnum in schema.ts)
  const openFilterModal = (field: Field) => {
    setActiveField(field);
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
  // Example: When filters = { "stance": "For", "category": "Agency Reform" }
  // This renders two tags: "Stance: For" and "Category: Agency Reform"
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
      // Find matching field
      const field = datasetConfig.fields.find(f => f.key === key);
      
      if (!field) return null;
      
      // Handle different filter types
      // For themes with filter mode object: { values: ["Transparency", "Accountability"], mode: "includes" }
      if (value && typeof value === 'object' && 'values' in value && Array.isArray(value.values)) {
        const filterValue = value as { values: unknown[], mode: 'exact' | 'includes' | 'at_least' };
        let modeText = '(Any Match)';
        if (filterValue.mode === 'at_least') {
          modeText = '(Must Include All)';
        } else if (filterValue.mode === 'exact') {
          modeText = '(Exact Match)';
        }
        
        return filterValue.values.map((v, i) => (
          <div 
            key={`${key}-${i}`}
            className="bg-blue-500 text-white rounded-full px-3 py-1.5 mr-2 mb-2 text-sm inline-flex items-center shadow-sm hover:bg-blue-600 transition-colors"
          >
            <span className="mr-1 font-medium">{field.title} {i === 0 ? modeText : ''}:</span> 
            <span>{String(v)}</span>
            <button 
              className="ml-2 inline-flex items-center justify-center w-5 h-5 bg-white bg-opacity-20 rounded-full text-xs hover:bg-opacity-30 transition-colors"
              onClick={() => {
                // Create new values array without this value
                const newValues = (filterValue.values as unknown[]).filter(item => item !== v);
                if (newValues.length === 0) {
                  // If removing the last value, remove the filter entirely
                  handleFilterChange(key, null);
                } else {
                  // Otherwise update the values array while keeping the mode
                  handleFilterChange(key, {
                    values: newValues,
                    mode: filterValue.mode
                  });
                }
              }}
              aria-label="Remove filter"
            >
              ×
            </button>
          </div>
        ));
      }
      // For array values like themes: ["Transparency", "Accountability"]
      // This creates multiple filter tags, one for each array value
      else if (Array.isArray(value)) {
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
        // For stance: "For", this creates a single filter tag "Stance: For"
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
  // Based on schema.ts and config, this might render buttons for:
  // - Stance (with options: For, Against, Neutral/Unclear)
  // - Category (with options from available categories in the data)
  // - Agency (filtered by agencyId)
  // - Themes (allowing multiple selection from available themes)
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
      {/* For example, when filtering by stance: */}
      {/* Modal shows radio buttons with options: For, Against, Neutral/Unclear */}
      {/* When filtering by themes: */}
      {/* Modal shows checkboxes with common themes found in comments */}
      {activeField && (
        <FilterModal 
          field={activeField}
          currentValue={filters[activeField.key] || null}
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