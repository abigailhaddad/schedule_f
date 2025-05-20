// components/FilterSection.tsx
'use client';

import { useState } from 'react';
import { Field, datasetConfig } from '@/lib/config';

interface FilterSectionProps {
  onFilterChange: (filters: Record<string, unknown>) => void;
}

export default function FilterSection({ onFilterChange }: FilterSectionProps) {
  const [filters, setFilters] = useState<Record<string, unknown>>({});
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [activeField] = useState<Field | null>(null);
  
  const handleFilterChange = (key: string, value: unknown) => {
    const newFilters = { ...filters, [key]: value };
    
    // If value is empty, remove the filter
    if (!value || (Array.isArray(value) && value.length === 0)) {
      delete newFilters[key];
    }
    
    setFilters(newFilters);
    onFilterChange(newFilters);
  };
  
  const clearAllFilters = () => {
    setFilters({});
    onFilterChange({});
  };
  
  // Check if we have any active filters
  const hasActiveFilters = Object.keys(filters).length > 0;
  
  // Helper to render filter tags for active filters
  const renderFilterTags = () => {
    if (!hasActiveFilters) {
      return (
        <div className="text-muted fst-italic w-100 text-center py-2">
          No filters applied. Click the <i className="bi bi-funnel"></i> icon next to any column header to filter.
        </div>
      );
    }
    
    return Object.entries(filters).map(([key, value]) => {
      const field = datasetConfig.fields.find(f => f.key === key);
      
      if (!field) return null;
      
      // Handle different filter types
      if (Array.isArray(value)) {
        return (value as unknown[]).map((v, i) => (
          <div className="filter-tag" key={`${key}-${i}`}>
            {field.title}: {String(v)}
            <span 
              className="remove-tag" 
              onClick={() => handleFilterChange(key, (value as unknown[]).filter(item => item !== v))}
            >
              ×
            </span>
          </div>
        ));
      }
      
      return null;
    });
  };
  
  return (
    <div className="card">
      <div className="card-header d-flex justify-content-between align-items-center">
        <h5 className="m-0">
          <i className={`bi ${hasActiveFilters ? 'bi-funnel-fill' : 'bi-funnel'} me-2`}></i>
          {hasActiveFilters ? 'Active Filters' : 'Filters'}
        </h5>
        <button 
          id="clear-filters" 
          className="btn btn-sm btn-primary"
          onClick={clearAllFilters}
          disabled={!hasActiveFilters}
        >
          Clear All
        </button>
      </div>
      <div className="card-body">
        <div className={`active-filters-container ${hasActiveFilters ? 'has-filters' : ''}`}>
          <label className="form-label fw-medium">Active Filters:</label>
          <div id="active-filters" className="d-flex flex-wrap mb-3">
            {renderFilterTags()}
          </div>
        </div>
      </div>
      
      {/* Filter Modal */}
      {activeField && showFilterModal && (
        <FilterModal 
          field={activeField}
          currentValue={filters[activeField.key] || null}
          onClose={() => setShowFilterModal(false)}
          onApply={(value) => {
            handleFilterChange(activeField.key, value);
            setShowFilterModal(false);
          }}
        />
      )}
    </div>
  );
}

// Filter Modal Component
interface FilterModalProps {
  field: Field;
  currentValue: unknown;
  onClose: () => void;
  onApply: (value: unknown) => void;
}

function FilterModal({ field, currentValue, onClose, onApply }: FilterModalProps) {
  const [value, setValue] = useState<unknown>(currentValue || (field.filter === 'select' || field.filter === 'multi-label' ? [] : ''));
  
  const renderFilterContent = () => {
    switch (field.filter) {
      case 'select':
        return (
          <div>
            <div className="mb-3">
              <input 
                type="text" 
                className="form-control form-control-sm" 
                placeholder="Search options..." 
              />
            </div>
            <div className="select-options-container">
              {field.badges && Object.keys(field.badges).map(option => (
                <div className="form-check checkbox-item" key={option}>
                  <input 
                    className="form-check-input" 
                    type="checkbox" 
                    id={`check-${option}`}
                    checked={Array.isArray(value) && (value as unknown[]).includes(option)}
                    onChange={e => {
                      if (e.target.checked) {
                        setValue([...(Array.isArray(value) ? (value as unknown[]) : []), option]);
                      } else {
                        setValue(Array.isArray(value) ? (value as unknown[]).filter((v) => v !== option) : []);
                      }
                    }}
                  />
                  <label className="form-check-label" htmlFor={`check-${option}`}>
                    {option}
                  </label>
                </div>
              ))}
            </div>
          </div>
        );
        
      case 'text':
        return (
          <div className="mb-3">
            <div className="input-group">
              <input 
                type="text" 
                className="form-control" 
                value={typeof value === 'string' ? value : ''}
                onChange={e => setValue(e.target.value)}
                placeholder="Type and press Enter" 
              />
              <button 
                className="btn btn-outline-primary" 
                type="button"
                onClick={() => {
                  if (typeof value === 'string' && value.trim()) {
                    onApply([value.trim()]);
                  }
                }}
              >
                Add
              </button>
            </div>
            <div className="form-text">Press Enter or click Add after typing</div>
          </div>
        );
        
      // Add other filter types as needed  
        
      default:
        return <p>Unsupported filter type</p>;
    }
  };
  
  return (
    <div className="modal fade show" style={{ display: 'block' }}>
      <div className="modal-dialog">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">
              <i className="bi bi-funnel me-2"></i>Filter by {field.title}
            </h5>
            <button type="button" className="btn-close" onClick={onClose}></button>
          </div>
          <div className="modal-body">
            {renderFilterContent()}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button 
              type="button" 
              className="btn btn-primary"
              onClick={() => onApply(value)}
            >
              Apply
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}