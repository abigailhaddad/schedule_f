import Badge, { getBadgeTypeFromClass } from '@/components/ui/Badge';

// Define a flexible type for badge mappings
interface BadgeMapping {
  [key: string]: string | undefined;
}

interface BadgeFieldProps {
  value: string;
  badges: BadgeMapping;
  searchQuery: string;
  fieldKey: string;
}

export default function BadgeField({ value, badges, searchQuery, fieldKey }: BadgeFieldProps) {
  const badgeClass = badges[value];
  const badgeType = getBadgeTypeFromClass(badgeClass);
  
  return (
    <Badge 
      type={badgeType}
      label={value}
      highlight={searchQuery}
      filterType={fieldKey}
    />
  );
} 