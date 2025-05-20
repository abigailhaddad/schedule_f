'use client';

import { useState, useEffect, useCallback } from 'react';
import { Field } from '@/lib/config';
import Modal from './ui/Modal';
import Button from './ui/Button';

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
  
  // For text filter functionality
  const [textValues, setTextValues] = useState<string[]>(
    Array.isArray(currentValue) ? currentValue : []
  );
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
    if (field.key === 'stance' || field.key === 'analysis.stance') {
      return ['For', 'Against', 'Neutral/Unclear'];
    }
    
    if (field.badges && Object.keys(field.badges).length) {
      return Object.keys(field.badges);
    }
    
    if (field.key === 'themes' || field.key === 'analysis.themes') {
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
  
  // Render select filter (checkboxes)
  const renderSelectFilter = () => {
    const options = getUniqueValues(field);
    const filteredOptions = searchTerm
      ? options.filter(option => 
          option.toLowerCase().includes(searchTerm.toLowerCase()))
      : options;
      
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
        onClick={() => onApply(value)}
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