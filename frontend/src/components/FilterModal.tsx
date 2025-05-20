'use client';

import { useState, useEffect } from 'react';
import { Field, datasetConfig } from '@/lib/config';
import styled from 'styled-components';
import Modal from './ui/Modal';
import Button from './ui/Button';

interface FilterModalProps {
  field: Field;
  currentValue: any;
  onApply: (value: any) => void;
  onClose: () => void;
  isOpen: boolean;
}

const Input = styled.input`
  padding: 0.5rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  width: 100%;
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
  
  &:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
  }
`;

const CheckboxContainer = styled.div`
  padding: 0.5rem 0;
`;

const CheckboxLabel = styled.label`
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  transition: background-color 0.15s;
  
  &:hover {
    background-color: #f7fafc;
  }
`;

const Checkbox = styled.input`
  margin-right: 0.5rem;
`;

const OptionsContainer = styled.div`
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem;
  padding: 0.5rem;
  margin-top: 0.5rem;
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
`;

const TextFilterTag = styled.div`
  background-color: #edf2f7;
  padding: 0.25rem 0.75rem;
  border-radius: 1rem;
  display: inline-flex;
  align-items: center;
  margin-right: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
`;

const RemoveTag = styled.span`
  margin-left: 0.5rem;
  cursor: pointer;
  font-weight: bold;
  color: #64748b;
`;

const InputGroup = styled.div`
  display: flex;
`;

export default function FilterModal({ field, currentValue, onApply, onClose, isOpen }: FilterModalProps) {
  const [value, setValue] = useState<any>(
    currentValue || 
    (field.filter === 'select' || field.filter === 'multi-label' ? [] : '')
  );
  
  const [searchTerm, setSearchTerm] = useState('');
  
  // Update local value when currentValue changes
  useEffect(() => {
    setValue(
      currentValue || 
      (field.filter === 'select' || field.filter === 'multi-label' ? [] : '')
    );
  }, [currentValue, field.filter]);
  
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
    
    if (field.key === 'themes') {
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
        <div style={{ marginBottom: '1rem' }}>
          <Input 
            type="text" 
            placeholder="Search options..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            autoFocus
          />
        </div>
        
        <OptionsContainer>
          {filteredOptions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '1rem', color: '#718096' }}>
              No matching options
            </div>
          ) : (
            <CheckboxContainer>
              {filteredOptions.map(option => (
                <CheckboxLabel key={option}>
                  <Checkbox
                    type="checkbox"
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
                </CheckboxLabel>
              ))}
            </CheckboxContainer>
          )}
        </OptionsContainer>
        
        <ButtonGroup>
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
        </ButtonGroup>
      </div>
    );
  };
  
  // Render text filter
  const renderTextFilter = () => {
    // For tracking multiple text values
    const [textValues, setTextValues] = useState<string[]>(Array.isArray(currentValue) ? currentValue : []);
    const [inputValue, setInputValue] = useState('');
    
    const addTextValue = () => {
      if (inputValue.trim() && !textValues.includes(inputValue.trim())) {
        const newValues = [...textValues, inputValue.trim()];
        setTextValues(newValues);
        setInputValue('');
        setValue(newValues);
      }
    };
    
    const removeTextValue = (val: string) => {
      const newValues = textValues.filter(v => v !== val);
      setTextValues(newValues);
      setValue(newValues);
    };
    
    return (
      <div>
        <div style={{ marginBottom: '1rem' }}>
          <InputGroup>
            <Input
              type="text"
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
              style={{ borderTopRightRadius: 0, borderBottomRightRadius: 0 }}
            />
            <Button 
              onClick={addTextValue}
              style={{ borderTopLeftRadius: 0, borderBottomLeftRadius: 0 }}
            >
              Add
            </Button>
          </InputGroup>
          <div style={{ fontSize: '0.75rem', color: '#718096', marginTop: '0.25rem' }}>
            Press Enter or click Add after typing
          </div>
        </div>
        
        <div>
          {textValues.length === 0 ? (
            <div style={{ fontStyle: 'italic', color: '#94a3b8' }}>
              No filters added yet
            </div>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap' }}>
              {textValues.map((val, index) => (
                <TextFilterTag key={index}>
                  {val}
                  <RemoveTag onClick={() => removeTextValue(val)}>
                    ×
                  </RemoveTag>
                </TextFilterTag>
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