import Badge from '@/components/ui/Badge';

interface MultiLabelFieldProps {
  value: string;
  searchQuery: string;
  fieldKey: string;
}

export default function MultiLabelField({ value, searchQuery, fieldKey }: MultiLabelFieldProps) {
  const labels = value.split(',').map(label => label.trim()).filter(Boolean);
  
  return (
    <div className="flex flex-wrap gap-1">
      {labels.map((label, i) => (
        <Badge 
          key={i}
          type="primary" 
          label={label}
          highlight={searchQuery}
          filterType={fieldKey}
        />
      ))}
    </div>
  );
} 