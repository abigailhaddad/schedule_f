// frontend/src/components/ServerCommentTable/renderers/index.ts
import React from 'react';
import { RendererProps } from '../types';
import { TitleRenderer } from './TitleRenderer';
import { BadgeRenderer } from './BadgeRenderer';
import { BooleanRenderer } from './BooleanRenderer';
import { DateRenderer } from './DateRenderer';
import { LinkRenderer } from './LinkRenderer';
import { MultiLabelRenderer } from './MultiLabelRenderer';
import { TextRenderer } from './TextRenderer';

export function createFieldRenderer(props: RendererProps): React.ReactElement {
  const { field, value } = props;
  
  // Special case for title
  if (field.key === 'title') {
    return (
      <TitleRenderer {...props} value={value as string} />
    );
  }
  
  // Handle null/undefined/empty values
  if (value === null || value === undefined || value === '') {
    return <span className="text-gray-400 italic">—</span>;
  }
  
  // Handle different field types
  if (typeof value === 'boolean') {
    return <BooleanRenderer {...props} value={value} />;
  }
  
  if (field.format === 'multi-label' && typeof value === 'string') {
    return <MultiLabelRenderer {...props} value={value} />;
  }
  
  if (field.format === 'date') {
    return <DateRenderer {...props} value={value as string | Date | null | undefined} />;
  }
  
  if (field.format === 'link' && typeof value === 'string') {
    return <LinkRenderer {...props} value={value} />;
  }
  
  if (field.badges) {
    // Special handling for commentCount field which stores numbers but displays as ranges
    if (field.key === 'commentCount' && typeof value === 'number') {
      let badgeKey: string;
      if (value === 1) {
        badgeKey = '1';
      } else if (value >= 2 && value <= 10) {
        badgeKey = '2-10';
      } else if (value >= 11 && value <= 50) {
        badgeKey = '11-50';
      } else {
        badgeKey = '50+';
      }
      return <BadgeRenderer {...props} value={badgeKey} />;
    }
    // Regular badge handling for string values
    else if (typeof value === 'string' && field.badges[value as keyof typeof field.badges]) {
      return <BadgeRenderer {...props} value={value} />;
    }
  }
  
  // Default to text renderer
  if (typeof value === 'string') {
    return <TextRenderer {...props} value={value} />;
  }
  
  // Fallback for other types
  return <span>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>;
}