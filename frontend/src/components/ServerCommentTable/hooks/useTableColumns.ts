import { useMemo } from 'react';
import { Field } from '@/lib/config';
import { Column, RendererProps } from '../types';
import { Comment } from '@/lib/db/schema';
import { getColumnConfig } from '../utils/columnConfig';
import { createFieldRenderer } from '../renderers';

interface UseTableColumnsOptions {
  fields: Field[];
  searchQuery: string;
  onRowClick: (comment: Comment) => void;
}

export function useTableColumns({ 
  fields, 
  searchQuery, 
  onRowClick 
}: UseTableColumnsOptions): Column<Comment>[] {
  return useMemo(() => {
    return fields.map(field => {
      const config = getColumnConfig(field);
      
      return {
        key: field.key,
        title: field.title,
        sortable: config.sortable !== false,
        className: config.className,
        render: (comment: Comment) => {
          const rendererProps: RendererProps<unknown> = {
            field,
            value: comment[field.key as keyof Comment],
            comment,
            searchQuery,
            onAction: (action: string, data?: Comment | string | number | boolean | null) => {
              if (action === 'click' && field.key === 'title') {
                onRowClick(data as Comment);
              }
            }
          };
          return createFieldRenderer(rendererProps);
        }
      };
    });
  }, [fields, searchQuery, onRowClick]);
} 