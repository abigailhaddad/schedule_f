import React from 'react';

interface ExportButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

export function ExportButton({ onClick, disabled }: ExportButtonProps) {
  return (
    <button 
      className="flex items-center px-3 py-2 text-sm font-medium bg-white bg-opacity-20 rounded hover:bg-opacity-30 focus:outline-none focus:ring-2 focus:ring-white focus:ring-opacity-40 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      onClick={onClick}
      disabled={disabled}
    >
      <span className="mr-1">📥</span>
      Export CSV
    </button>
  );
} 