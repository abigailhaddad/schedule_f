// components/CommentTable.tsx
'use client';

import { useState, useEffect } from 'react';
import { Comment, Analysis } from '@/lib/db/schema';
import { Field, datasetConfig } from '@/lib/config';
import  MiniSearch  from 'minisearch'

type CommentWithAnalysis = Comment & {
  analysis: Analysis | null;
};

interface CommentTableProps {
  data: CommentWithAnalysis[];
  filters: Record<string, any>;
}

export default function CommentTable({ data, filters }: CommentTableProps) {
  const [filteredData, setFilteredData] = useState<CommentWithAnalysis[]>(data);
  const [searchQuery, setSearchQuery] = useState('');
  const [miniSearch, setMiniSearch] = useState<MiniSearch | null>(null);
  
  // Initialize MiniSearch
  useEffect(() => {
    const search = new MiniSearch({
      fields: ['title', 'keyQuote', 'comment'],
      storeFields: ['id'],
      idField: 'id'
    });
    
    // Add documents to index
    search.addAll(data.map(item => ({
      id: item.id,
      title: item.title || '',
      keyQuote: item.analysis?.keyQuote || '',
      comment: item.comment || ''
    })));
    
    setMiniSearch(search);
  }, [data]);
  
  // Apply filters and search
  useEffect(() => {
    let result = [...data];
    
    // Apply filters
    if (Object.keys(filters).length > 0) {
      result = result.filter(item => {
        for (const [key, value] of Object.entries(filters)) {
          // Skip empty filters
          if (!value) continue;
          
          // Handle different filter types
          if (Array.isArray(value) && value.length > 0) {
            const fieldValue = key === 'stance' && item.analysis 
              ? item.analysis.stance 
              : key === 'themes' && item.analysis
                ? item.analysis.themes
                : item[key as keyof typeof item];
                
            const stringValue = String(fieldValue || '').toLowerCase();
            
            // For multi-label filters (e.g. themes)
            if (key === 'themes' && item.analysis && item.analysis.themes) {
              const themes = item.analysis.themes.split(',').map(t => t.trim().toLowerCase());
              const hasMatch = value.some(v => 
                themes.some(theme => theme.includes(v.toLowerCase()))
              );
              if (!hasMatch) return false;
            } 
            // For regular text/select filters
            else if (!value.some((v: string) => stringValue.includes(v.toLowerCase()))) {
              return false;
            }
          }
        }
        return true;
      });
    }
    
    // Apply search query
    if (searchQuery && miniSearch) {
      const searchResults = miniSearch.search(searchQuery, { fuzzy: 0.2 });
      const resultIds = new Set(searchResults.map(r => r.id));
      result = result.filter(item => resultIds.has(item.id));
    }
    
    setFilteredData(result);
  }, [data, filters, searchQuery, miniSearch]);
  
  const handleExportCSV = () => {
    // Get visible columns
    const visibleFields = datasetConfig.fields.filter(f => f.visible);
    
    // Create CSV header
    const headers = visibleFields.map(f => f.title);
    let csv = headers.join(',') + '\n';
    
    // Add data rows
    filteredData.forEach(item => {
      const line = visibleFields.map(field => {
        let value: any;
        
        // Get the appropriate value based on the field key
        if (field.key === 'stance' && item.analysis) {
          value = item.analysis.stance ?? '';
        } else if (field.key === 'keyQuote' && item.analysis) {
          value = item.analysis.keyQuote ?? '';
        } else if (field.key === 'themes' && item.analysis) {
          value = item.analysis.themes ?? '';
        } else if (field.key === 'rationale' && item.analysis) {
          value = item.analysis.rationale ?? '';
        } else {
          value = String(item[field.key as keyof typeof item] || '');
        }
        
        // Escape CSV special characters
        value = value.replace(/"/g, '""');
        if (value.includes(',') || value.includes('"') || value.includes('\n')) {
          value = `"${value}"`;
        }
        
        return value;
      });
      
      csv += line.join(',') + '\n';
    });
    
    // Download the CSV
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `comments-export-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  
  // Render a cell with appropriate formatting
  const renderCell = (item: CommentWithAnalysis, field: Field) => {
    let value: any;
    
    // Get the appropriate value based on the field key
    if (field.key === 'stance' && item.analysis) {
      value = item.analysis.stance ?? '';
    } else if (field.key === 'keyQuote' && item.analysis) {
      value = item.analysis.keyQuote ?? '';
    } else if (field.key === 'themes' && item.analysis) {
      value = item.analysis.themes ?? '';
    } else if (field.key === 'rationale' && item.analysis) {
      value = item.analysis.rationale ?? '';
    } else {
      value = item[field.key as keyof typeof item];
    }
    
    if (value === null || value === undefined) {
      return <span className="text-muted fst-italic">—</span>;
    }
    
    // Handle different field formats
    if (field.format === 'multi-label' && typeof value === 'string') {
      const labels = value ? value.split(',').map(label => label.trim()).filter(Boolean) : [];
      return (
        <>
          {labels.map((label, i) => (
            <span key={i} className="badge bg-secondary me-1 mb-1">{label}</span>
          ))}
        </>
      );
    }
    
    if (field.badges && typeof value === 'string' && field.badges[value as keyof typeof field.badges]) {
      return (
        <span className={`badge ${field.badges[value as keyof typeof field.badges]}`}>{value}</span>
      );
    }
    
    if (field.charLimit && typeof value === 'string' && value.length > field.charLimit) {
      const truncated = value.substring(0, field.charLimit) + '...';
      return (
        <span 
          className="char-limited" 
          data-bs-toggle="tooltip" 
          data-bs-placement="top" 
          title={value}
        >
          {truncated}
        </span>
      );
    }
    
    return value;
  };
  
  return (
    <div className="card">
      <div className="card-header">
        <div className="d-flex justify-content-between align-items-center">
          <h5 className="m-0"><i className="bi bi-table me-2"></i>Data Table</h5>
          <div className="d-flex align-items-center">
            {/* Search input */}
            <div className="me-3">
              <input
                type="text"
                className="form-control"
                placeholder="Search comments..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            
            <button 
              id="export-csv" 
              className="btn btn-sm btn-primary"
              onClick={handleExportCSV}
            >
              <i className="bi bi-download me-1"></i>Export CSV
            </button>
          </div>
        </div>
      </div>
      <div className="card-body p-0 border-top">
        <div className="table-responsive">
          <table className="table table-striped table-hover w-100">
            <thead>
              <tr>
                {datasetConfig.fields
                  .filter(field => field.visible)
                  .map(field => (
                    <th key={field.key}>
                      {field.title}
                      {field.filter && (
                        <button className="column-filter-btn">
                          <i className="bi bi-funnel"></i>
                        </button>
                      )}
                    </th>
                  ))
                }
              </tr>
            </thead>
            <tbody>
              {filteredData.length === 0 ? (
                <tr>
                  <td colSpan={datasetConfig.fields.filter(f => f.visible).length} className="text-center py-4">
                    No matching records found
                  </td>
                </tr>
              ) : (
                filteredData.map(item => (
                  <tr key={item.id}>
                    {datasetConfig.fields
                      .filter(field => field.visible)
                      .map(field => (
                        <td key={field.key}>
                          {renderCell(item, field)}
                        </td>
                      ))
                    }
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}