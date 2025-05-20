'use client';

import React from 'react';

export type BadgeType = 'success' | 'danger' | 'warning' | 'primary' | 'default';

interface BadgeProps {
  type?: BadgeType;
  label: string;
  className?: string;
  highlight?: string;
  filterType?: string;
}

export default function Badge({ 
  type = 'default', 
  label, 
  className = '', 
  highlight = '',
  filterType
}: BadgeProps) {
  // Get badge color class based on type
  const getBadgeColorClass = (type: BadgeType): string => {
    switch (type) {
      case 'success':
        return 'bg-green-100 text-green-800';
      case 'danger':
        return 'bg-red-100 text-red-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'primary':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Get highlight color based on filter type
  const getHighlightColor = (filterType?: string): string => {
    if (!filterType) return 'bg-yellow-200 text-gray-900';
    
    switch (filterType) {
      case 'title':
        return 'bg-blue-200 text-blue-900';
      case 'comment':
        return 'bg-green-200 text-green-900';
      case 'themes':
        return 'bg-purple-200 text-purple-900';
      case 'keyQuote':
        return 'bg-orange-200 text-orange-900';
      case 'rationale':
        return 'bg-pink-200 text-pink-900';
      case 'stance':
        return 'bg-indigo-200 text-indigo-900';
      default:
        return 'bg-yellow-200 text-gray-900';
    }
  };

  // Highlight search match in text if highlight string is provided
  const highlightSearchMatch = (text: string, searchTerm: string) => {
    if (!searchTerm || !text) return text;
    
    // Escape special characters in the search term
    const escapedSearchTerm = searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedSearchTerm})`, 'gi');
    
    // Split text by search term matches
    const parts = text.split(regex);
    
    if (parts.length <= 1) return text;
    
    // Get the correct highlight color
    const highlightClass = getHighlightColor(filterType);
    
    // Return text with highlighted spans
    return (
      <>
        {parts.map((part, i) => 
          regex.test(part) ? (
            <span key={i} className={`${highlightClass} font-medium px-1 rounded`}>
              {part}
            </span>
          ) : (
            part
          )
        )}
      </>
    );
  };

  return (
    <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${getBadgeColorClass(type)} ${className}`}>
      {highlight ? highlightSearchMatch(label, highlight) : label}
    </span>
  );
} 