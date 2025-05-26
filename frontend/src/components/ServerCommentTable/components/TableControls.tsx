import React from 'react';
import { SearchBar } from './SearchBar';
import { ColumnVisibilityMenu } from './ColumnVisibilityMenu';
import { ExportButton } from './ExportButton';

interface TableControlsProps {
  title: string;
  searchValue: string;
  onSearchChange: (value: string) => void;
  onExport: () => void;
  columnVisibility: {
    visibleColumns: Record<string, boolean>;
    toggleColumn: (key: string) => void;
    showMenu: boolean;
    setShowMenu: (show: boolean) => void;
  };
}

export function TableControls({ 
  title, 
  searchValue, 
  onSearchChange, 
  onExport, 
  columnVisibility 
}: TableControlsProps) {
  return (
    <div className="bg-gradient-to-r from-purple-500 to-purple-600 text-white p-4">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <h5 className="text-lg font-bold flex items-center">
          <span className="mr-2">📋</span>
          {title}
        </h5>
        
        <div className="flex flex-wrap items-center gap-2">
          <SearchBar value={searchValue} onChange={onSearchChange} />
          <ColumnVisibilityMenu 
            visibleColumns={columnVisibility.visibleColumns}
            onToggle={columnVisibility.toggleColumn}
            isOpen={columnVisibility.showMenu}
            onToggleMenu={() => columnVisibility.setShowMenu(!columnVisibility.showMenu)}
          />
          <ExportButton onClick={onExport} />
        </div>
      </div>
    </div>
  );
} 