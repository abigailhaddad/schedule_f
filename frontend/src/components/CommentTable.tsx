// components/CommentTable.tsx
'use client';

import { useState, useEffect, useRef } from 'react';
import { CommentWithAnalysis } from '@/lib/db/schema';
import { Field, datasetConfig } from '@/lib/config';
import { useDataTable } from '@/lib/hooks/useDataTable';
import styled from 'styled-components';
import Button from './ui/Button';
import Card from './ui/Card';

interface CommentTableProps {
  data: CommentWithAnalysis[];
  filters: Record<string, unknown>;
}

// Styled components for table
const StyledTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  
  thead th {
    background-color: #f8f9fa;
    font-weight: 600;
    border-bottom: 2px solid #e5e7eb;
    padding: 0.75rem;
    text-align: left;
    cursor: pointer;
    transition: background-color 0.2s;
    
    &:hover {
      background-color: #f1f5f9;
    }
    
    &.sorting_asc::after {
      content: " ↑";
      opacity: 0.7;
    }
    
    &.sorting_desc::after {
      content: " ↓";
      opacity: 0.7;
    }
  }
  
  tbody tr {
    border-top: 1px solid #e5e7eb;
    
    &:nth-child(even) {
      background-color: rgba(0, 0, 0, 0.02);
    }
    
    &:hover {
      background-color: rgba(59, 130, 246, 0.05);
    }
  }
  
  td {
    padding: 0.75rem;
    vertical-align: top;
  }
`;

const SearchInput = styled.input`
  padding: 0.5rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  margin-right: 0.75rem;
  width: 200px;
  
  &:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
  }
`;

const ColumnsMenu = styled.div`
  position: relative;
  display: inline-block;
`;

const ColumnsButton = styled(Button)`
  margin-right: 0.5rem;
`;

const ColumnsDropdown = styled.div<{ $isOpen: boolean }>`
  position: absolute;
  right: 0;
  top: 100%;
  z-index: 1000;
  min-width: 10rem;
  padding: 0.5rem 0;
  background-color: white;
  border-radius: 0.375rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  border: 1px solid #e5e7eb;
  display: ${props => props.$isOpen ? 'block' : 'none'};
`;

const ColumnCheckboxItem = styled.div`
  padding: 0.375rem 1rem;
  display: flex;
  align-items: center;
  cursor: pointer;
  
  &:hover {
    background-color: #f7fafc;
  }
  
  input {
    margin-right: 0.5rem;
  }
`;

const Badge = styled.span`
  display: inline-block;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1;
  text-align: center;
  white-space: nowrap;
  vertical-align: baseline;
  border-radius: 0.25rem;
  background-color: #64748b;
  color: white;
  margin-right: 0.25rem;
  margin-bottom: 0.25rem;
`;

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
      return <span style={{ color: '#6c757d', fontStyle: 'italic' }}>—</span>;
    }
    
    // Handle different field formats
    if (field.format === 'multi-label' && typeof value === 'string') {
      const labels = value.split(',').map(label => label.trim()).filter(Boolean);
      return (
        <>
          {labels.map((label, i) => (
            <Badge key={i}>{label}</Badge>
          ))}
        </>
      );
    }
    
    if (field.format === 'link' && typeof value === 'string') {
      return (
        <a href={value} target="_blank" rel="noopener noreferrer">
          Link
        </a>
      );
    }
    
    if (field.badges && typeof value === 'string' && field.badges[value as keyof typeof field.badges]) {
      return (
        <Badge style={{ backgroundColor: getBackgroundColor(field.badges[value as keyof typeof field.badges]) }}>
          {value}
        </Badge>
      );
    }
    
    if (field.charLimit && typeof value === 'string' && value.length > field.charLimit) {
      const truncated = value.substring(0, field.charLimit) + '...';
      return (
        <span 
          title={value}
        >
          {truncated}
        </span>
      );
    }
    
    return value;
  };
  
  // Helper to get background color for badges
  const getBackgroundColor = (badgeClass: string) => {
    if (badgeClass.includes('success')) return '#10b981';
    if (badgeClass.includes('danger')) return '#ef4444';
    if (badgeClass.includes('warning')) return '#f59e0b';
    if (badgeClass.includes('primary')) return '#3b82f6';
    return '#64748b'; // Default secondary color
  };
  
  // Get column classes including sorting
  const getColumnClasses = (field: Field) => {
    const classes = [];
    
    if (sorting?.column === field.key) {
      classes.push(sorting.direction === 'asc' ? 'sorting_asc' : 'sorting_desc');
    } else {
      classes.push('sorting');
    }
    
    return classes.join(' ');
  };
  
  return (
    <Card>
      <Card.Header>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h5 style={{ margin: 0 }}>Data Table</h5>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            {/* Search input */}
            <SearchInput
              type="text"
              placeholder="Search comments..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            
            {/* Column visibility dropdown */}
            <ColumnsMenu className="columns-dropdown">
              <ColumnsButton 
                variant="outline"
                size="sm"
                onClick={() => setShowColumnsMenu(!showColumnsMenu)}
              >
                Columns
              </ColumnsButton>
              <ColumnsDropdown $isOpen={showColumnsMenu}>
                {datasetConfig.fields.map(field => (
                  <ColumnCheckboxItem key={field.key} onClick={() => toggleColumnVisibility(field.key)}>
                    <input
                      type="checkbox"
                      id={`col-${field.key}`}
                      checked={visibleColumns[field.key]}
                      onChange={() => {}}
                    />
                    <label htmlFor={`col-${field.key}`}>
                      {field.title}
                    </label>
                  </ColumnCheckboxItem>
                ))}
              </ColumnsDropdown>
            </ColumnsMenu>
            
            <Button 
              size="sm"
              onClick={exportCSV}
            >
              Export CSV
            </Button>
          </div>
        </div>
      </Card.Header>
      <Card.Body noPadding>
        <div style={{ overflowX: 'auto' }}>
          <StyledTable>
            <thead>
              <tr>
                {getVisibleFields().map(field => (
                  <th 
                    key={field.key} 
                    className={getColumnClasses(field)}
                    onClick={() => handleSort(field.key)}
                  >
                    {field.title}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredData.length === 0 ? (
                <tr>
                  <td colSpan={getVisibleFields().length} style={{ textAlign: 'center', padding: '1.5rem' }}>
                    No matching records found
                  </td>
                </tr>
              ) : (
                filteredData.map(item => (
                  <tr key={item.id}>
                    {getVisibleFields().map(field => (
                      <td key={`${item.id}-${field.key}`}>
                        {renderCell(item, field)}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </StyledTable>
        </div>
        
        {/* Pagination/Length Controls */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', borderTop: '1px solid #e5e7eb' }}>
          <div>
            Showing {filteredData.length} of {data.length} entries
          </div>
          <div>
            <label>
              Show 
              <select style={{ margin: '0 0.5rem', padding: '0.25rem', borderRadius: '0.25rem', border: '1px solid #e5e7eb' }}>
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
              entries
            </label>
          </div>
        </div>
      </Card.Body>
    </Card>
  );
}