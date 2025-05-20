// components/FilterSection.tsx
'use client';

import { useState } from 'react';
import { Field, datasetConfig } from '@/lib/config';
import FilterModal from './FilterModal';
import Card from './ui/Card';
import Button from './ui/Button';
import styled from 'styled-components';

interface FilterSectionProps {
  onFilterChange: (filters: Record<string, unknown>) => void;
}

const FilterTag = styled.div`
  background-color: #3b82f6;
  color: white;
  border-radius: 1rem;
  padding: 0.35rem 0.8rem;
  margin-right: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  display: inline-flex;
  align-items: center;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
`;

const FilterName = styled.span`
  margin-right: 0.25rem;
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  color: white;
  padding: 0;
  width: 1.15rem;
  height: 1.15rem;
  font-size: 0.75rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 0.25rem;
  cursor: pointer;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  transition: background-color 0.15s;
  
  &:hover {
    background-color: rgba(255, 255, 255, 0.3);
  }
`;

const FilterButtonsContainer = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
`;

const NoFiltersMessage = styled.div`
  color: #6b7280;
  font-style: italic;
  text-align: center;
  padding: 0.75rem 0;
  width: 100%;
`;

const FilterTagsContainer = styled.div<{ $hasFilters: boolean }>`
  display: flex;
  flex-wrap: wrap;
  margin-bottom: 1rem;
  padding: ${props => props.$hasFilters ? '0.5rem' : '0'};
  min-height: 3rem;
  background-color: ${props => props.$hasFilters ? 'rgba(59, 130, 246, 0.05)' : 'transparent'};
  border-radius: 0.375rem;
  transition: background-color 0.2s;
`;

const Icon = styled.span`
  margin-right: 0.375rem;
`;

export default function FilterSection({ onFilterChange }: FilterSectionProps) {
  const [filters, setFilters] = useState<Record<string, unknown>>({});
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [activeField, setActiveField] = useState<Field | null>(null);
  
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
  
  const openFilterModal = (field: Field) => {
    setActiveField(field);
    setShowFilterModal(true);
  };
  
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
        <NoFiltersMessage>
          No filters applied. Use the filter buttons below to filter data.
        </NoFiltersMessage>
      );
    }
    
    return Object.entries(filters).map(([key, value]) => {
      const field = datasetConfig.fields.find(f => f.key === key);
      
      if (!field) return null;
      
      // Handle different filter types
      if (Array.isArray(value)) {
        return (value as unknown[]).map((v, i) => (
          <FilterTag key={`${key}-${i}`}>
            <FilterName>{field.title}: {String(v)}</FilterName>
            <CloseButton 
              onClick={() => handleFilterChange(key, (value as unknown[]).filter(item => item !== v))}
              aria-label="Remove filter"
            >
              ×
            </CloseButton>
          </FilterTag>
        ));
      }
      
      return null;
    });
  };
  
  // Render available filters as buttons
  const renderFilterButtons = () => {
    const filterableFields = datasetConfig.fields.filter(field => field.filter);
    
    return (
      <FilterButtonsContainer>
        {filterableFields.map(field => (
          <Button 
            key={field.key}
            variant={filters[field.key] ? 'primary' : 'outline'}
            size="sm"
            onClick={() => openFilterModal(field)}
          >
            {field.title}
          </Button>
        ))}
      </FilterButtonsContainer>
    );
  };
  
  return (
    <Card>
      <Card.Header>
        <div style={{ fontWeight: 600 }}>
          <Icon>{hasActiveFilters ? '🔍' : '⚙️'}</Icon>
          {hasActiveFilters ? 'Active Filters' : 'Filters'}
        </div>
        <Button 
          variant="primary"
          size="sm"
          onClick={clearAllFilters}
          disabled={!hasActiveFilters}
        >
          Clear All
        </Button>
      </Card.Header>
      <Card.Body>
        <FilterTagsContainer $hasFilters={hasActiveFilters}>
          {renderFilterTags()}
        </FilterTagsContainer>
        
        {renderFilterButtons()}
      </Card.Body>
      
      {/* Filter Modal - only render when showFilterModal is true */}
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
    </Card>
  );
}