import TextHighlighter from '@/components/ui/TextHighlighter';

interface StringFieldProps {
  value: string;
  searchQuery: string;
  fieldKey: string;
  charLimit?: number;
  smartTruncation?: boolean;
}

export default function StringField({ 
  value, 
  searchQuery, 
  fieldKey, 
  charLimit,
  smartTruncation = false 
}: StringFieldProps) {
  return (
    <TextHighlighter 
      text={value}
      searchTerm={searchQuery}
      highlightType={fieldKey}
      charLimit={charLimit}
      smartTruncation={smartTruncation}
    />
  );
} 