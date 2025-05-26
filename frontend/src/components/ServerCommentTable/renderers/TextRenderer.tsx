import React from 'react';
import TextHighlighter from '@/components/ui/TextHighlighter';
import { RendererProps } from '../types';

export function TextRenderer({ value, field, searchQuery }: RendererProps<string>) {
  return (
    <TextHighlighter 
      text={value}
      searchTerm={searchQuery}
      highlightType={field.key} // Pass field.key to TextHighlighter for context-specific highlighting
      charLimit={field.charLimit} // Pass charLimit if defined for the field
      smartTruncation={field.key === 'comment'} // Example: enable smart truncation for comment field
    />
  );
} 