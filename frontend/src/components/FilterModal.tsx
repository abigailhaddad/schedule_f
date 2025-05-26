'use client';

import { useState, useEffect, useCallback } from 'react';
import { Field } from '@/lib/config';
import Modal from './ui/Modal';
import Button from './ui/Button';

// Define filter mode types
type FilterMode = 'exact' | 'includes' | 'at_least';

// Define date filter types
type DateFilterMode = 'exact' | 'range' | 'before' | 'after';

interface DateFilterValue {
  mode: DateFilterMode;
  startDate?: string;
  endDate?: string;
}

interface FilterModalProps {
  field: Field;
  currentValue: unknown;
  onApply: (value: unknown) => void;
  onClose: () => void;
  isOpen: boolean;
}

export default function FilterModal({ field, currentValue, onApply, onClose, isOpen }: FilterModalProps) {
  // Initialize value based on field type and current value
  const initialValue = useCallback((): string | string[] => {
    // For select filters, ensure we're working with arrays
    if (field.filter === 'select' || field.filter === 'multi-label') {
      // Handle filter objects with mode
      if (currentValue && typeof currentValue === 'object' && 'values' in currentValue) {
        return Array.isArray(currentValue.values) ? currentValue.values : [];
      }
      // Handle both string and array values from URL params
      if (typeof currentValue === 'string') {
        return [currentValue];
      }
      // If it's already an array, use it
      if (Array.isArray(currentValue)) {
        return currentValue;
      }
      // Default to empty array
      return [];
    }
    
    // For text filters, convert to array if needed
    if (field.filter === 'text') {
      if (typeof currentValue === 'string') {
        return [currentValue];
      }
      if (Array.isArray(currentValue)) {
        return currentValue;
      }
      return [];
    }
    
    // For other filters, use the value as is or empty string
    return typeof currentValue === 'string' ? currentValue : '';
  }, [field.filter, currentValue]);

  const [value, setValue] = useState<string | string[]>(initialValue());
  const [searchTerm, setSearchTerm] = useState('');
  
  // For filter mode (exact match vs must include)
  const [filterMode, setFilterMode] = useState<FilterMode>('includes');
  
  // For date filters
  const [dateFilterMode, setDateFilterMode] = useState<DateFilterMode>('range');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  
  // Initialize filter mode based on current value
  useEffect(() => {
    if (field.key === 'themes' && currentValue && typeof currentValue === 'object' && 'mode' in currentValue) {
      const mode = currentValue.mode as FilterMode;
      if (mode === 'exact' || mode === 'at_least' || mode === 'includes') {
        setFilterMode(mode);
      }
    }
  }, [currentValue, field.key]);
  
  // Initialize date values based on current value
  useEffect(() => {
    if (field.filter === 'date' && currentValue && typeof currentValue === 'object') {
      const dateValue = currentValue as DateFilterValue;
      setDateFilterMode(dateValue.mode || 'range');
      setStartDate(dateValue.startDate || '');
      setEndDate(dateValue.endDate || '');
    }
  }, [currentValue, field.filter]);
  
  // For text filter functionality
  const [textValues, setTextValues] = useState<string[]>([]);
  
  // Initialize text values based on current value
  useEffect(() => {
    if (field.filter === 'text') {
      if (currentValue && typeof currentValue === 'object' && 'values' in currentValue) {
        setTextValues(Array.isArray(currentValue.values) ? currentValue.values : []);
      } else if (Array.isArray(currentValue)) {
        setTextValues(currentValue);
      } else if (typeof currentValue === 'string') {
        setTextValues([currentValue]);
      } else {
        setTextValues([]);
      }
    }
  }, [currentValue, field.filter]);
  const [inputValue, setInputValue] = useState('');
  
  // Update local state when currentValue changes
  useEffect(() => {
    setValue(initialValue());
    
    // Also update textValues when currentValue changes for text filters
    if (field.filter === 'text') {
      setTextValues(Array.isArray(currentValue) ? currentValue : []);
    }
  }, [currentValue, field.filter, initialValue]);
  
  // Add text value function for text filter
  const addTextValue = () => {
    if (inputValue.trim() && !textValues.includes(inputValue.trim())) {
      const newValues = [...textValues, inputValue.trim()];
      setTextValues(newValues);
      setInputValue('');
      setValue(newValues);
    }
  };
  
  // Remove text value function for text filter
  const removeTextValue = (val: string) => {
    const newValues = textValues.filter(v => v !== val);
    setTextValues(newValues);
    setValue(newValues);
  };
  
  // Get all unique values for a field from the data
  const getUniqueValues = (field: Field) => {
    // This would usually come from the database
    // For the sake of this example, we'll use hardcoded values
    if (field.key === 'stance') {
      return ['For', 'Against', 'Neutral/Unclear'];
    }
    
    if (field.badges && Object.keys(field.badges).length) {
      return Object.keys(field.badges);
    }
    
    if (field.key === 'themes' ) {
      return [
        'Due process/employee rights',
        'Merit-based system concerns',
        'Politicization concerns',
        'Scientific integrity',
        'Institutional knowledge loss'
      ];
    }
    
    return [];
  };
  
  // Render date filter
  const renderDateFilter = () => {
    return (
      <div>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Filter Mode</label>
          <select
            className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            value={dateFilterMode}
            onChange={(e) => setDateFilterMode(e.target.value as DateFilterMode)}
          >
            <option value="exact">Exact Date</option>
            <option value="range">Date Range</option>
            <option value="before">Before Date</option>
            <option value="after">After Date</option>
          </select>
        </div>
        
        {dateFilterMode === 'exact' && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Date</label>
            <input
              type="date"
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
        )}
        
        {dateFilterMode === 'range' && (
          <>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Start Date</label>
              <input
                type="date"
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">End Date</label>
              <input
                type="date"
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                min={startDate}
              />
            </div>
          </>
        )}
        
        {dateFilterMode === 'before' && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">Before Date</label>
            <input
              type="date"
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        )}
        
        {dateFilterMode === 'after' && (
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">After Date</label>
            <input
              type="date"
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
        )}
        
        <div className="text-xs text-gray-500 mt-2">
          {dateFilterMode === 'exact' && 'Filter for comments on this exact date'}
          {dateFilterMode === 'range' && 'Filter for comments between these dates (inclusive)'}
          {dateFilterMode === 'before' && 'Filter for comments before this date (exclusive)'}
          {dateFilterMode === 'after' && 'Filter for comments after this date (exclusive)'}
        </div>
      </div>
    );
  };
  
  // Render select filter (checkboxes)
  const renderSelectFilter = () => {
    const options = getUniqueValues(field);
    const filteredOptions = searchTerm
      ? options.filter(option => 
          option.toLowerCase().includes(searchTerm.toLowerCase()))
      : options;
    
    // Show filter mode options only for themes field  
    const showFilterModeOptions = field.key === 'themes';
      
    return (
      <div>
        <div className="mb-4">
          <input 
            type="text" 
            className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Search options..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            autoFocus
          />
        </div>
        
        {/* Filter mode selection for themes */}
        {showFilterModeOptions && (
          <div className="mb-4">
            <div className="text-sm font-medium text-gray-700 mb-2">Filter Mode:</div>
            <div className="flex gap-2">
              <label className="flex items-center cursor-pointer">
                <input
                  type="radio"
                  className="mr-1"
                  checked={filterMode === 'includes'}
                  onChange={() => setFilterMode('includes')}
                />
                <span className="text-sm">Must Include Any</span>
              </label>
              <label className="flex items-center cursor-pointer">
                <input
                  type="radio"
                  className="mr-1"
                  checked={filterMode === 'at_least'}
                  onChange={() => setFilterMode('at_least')}
                />
                <span className="text-sm">Must Include At Least</span>
              </label>
              <label className="flex items-center cursor-pointer">
                <input
                  type="radio"
                  className="mr-1"
                  checked={filterMode === 'exact'}
                  onChange={() => setFilterMode('exact')}
                />
                <span className="text-sm">Exact Match</span>
              </label>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {filterMode === 'includes' 
                ? 'Find comments that include any of the selected themes' 
                : filterMode === 'at_least'
                  ? 'Find comments that include at least all of the selected themes'
                  : 'Find comments that match exactly these themes (no more, no less)'}
            </div>
          </div>
        )}
        
        <div className="max-h-[300px] overflow-y-auto border border-gray-200 rounded p-2 mt-2">
          {filteredOptions.length === 0 ? (
            <div className="text-center py-4 text-gray-500">
              No matching options
            </div>
          ) : (
            <div className="py-2">
              {filteredOptions.map(option => (
                <label 
                  key={option} 
                  className="flex items-center mb-2 cursor-pointer text-sm py-1 px-2 rounded hover:bg-gray-50"
                >
                  <input
                    type="checkbox"
                    className="mr-2"
                    checked={Array.isArray(value) && value.includes(option)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setValue([...(Array.isArray(value) ? value : []), option]);
                      } else {
                        setValue(Array.isArray(value) ? value.filter(item => item !== option) : []);
                      }
                    }}
                  />
                  {option}
                </label>
              ))}
            </div>
          )}
        </div>
        
        <div className="flex gap-2 mt-2">
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setValue(filteredOptions)}
          >
            Select All Visible
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={() => setValue([])}
          >
            Deselect All
          </Button>
        </div>
      </div>
    );
  };
  
  // Render text filter
  const renderTextFilter = () => {
    return (
      <div>
        <div className="mb-4">
          <div className="flex">
            <input
              type="text"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-l text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Type and press Enter"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addTextValue();
                }
              }}
              autoFocus
            />
            <Button 
              onClick={addTextValue}
              className="rounded-l-none"
            >
              Add
            </Button>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Press Enter or click Add after typing
          </div>
        </div>
        
        <div>
          {textValues.length === 0 ? (
            <div className="italic text-gray-400">
              No filters added yet
            </div>
          ) : (
            <div className="flex flex-wrap">
              {textValues.map((val, index) => (
                <div 
                  key={index} 
                  className="bg-gray-200 px-3 py-1 rounded-full inline-flex items-center mr-2 mb-2 text-sm"
                >
                  {val}
                  <span 
                    className="ml-2 cursor-pointer font-bold text-gray-500 hover:text-gray-700"
                    onClick={() => removeTextValue(val)}
                  >
                    ×
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };
  
  // Render the appropriate filter content based on filter type
  const renderFilterContent = () => {
    switch (field.filter) {
      case 'select':
      case 'multi-label':
        return renderSelectFilter();
      case 'text':
        return renderTextFilter();
      case 'date':
        return renderDateFilter();
      default:
        return <p>Unsupported filter type</p>;
    }
  };
  
  // Create modal footer with action buttons
  const modalFooter = (
    <>
      <Button 
        variant="secondary" 
        onClick={onClose}
      >
        Cancel
      </Button>
      <Button 
        onClick={() => {
          if (field.filter === 'date') {
            // For date filters, pass the date filter object
            const dateValue: DateFilterValue = {
              mode: dateFilterMode,
              startDate: dateFilterMode === 'exact' || dateFilterMode === 'after' ? startDate : 
                       dateFilterMode === 'range' ? startDate : undefined,
              endDate: dateFilterMode === 'exact' ? startDate : // For exact, use startDate as the value
                      dateFilterMode === 'before' ? endDate :
                      dateFilterMode === 'range' ? endDate : undefined
            };
            
            // Only apply if at least one date is set
            if (dateValue.startDate || dateValue.endDate) {
              onApply(dateValue);
            } else {
              onApply(null);
            }
          } else if (field.key === 'themes') {
            // For themes with filter mode, we need to pass an object with both values and mode
            onApply({
              values: value,
              mode: filterMode
            });
          } else {
            // For other fields, just pass the value directly
            onApply(value);
          }
        }}
      >
        Apply
      </Button>
    </>
  );
  
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Filter by ${field.title}`}
      footer={modalFooter}
    >
      {renderFilterContent()}
    </Modal>
  );
}