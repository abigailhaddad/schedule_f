import Badge, { getBadgeTypeFromClass } from '@/components/ui/Badge';

// Define a more specific type for badge mappings that handles boolean values
interface BadgeMapping {
  'true'?: string;
  'false'?: string;
  [key: string]: string | undefined;
}

interface BooleanFieldProps {
  value: boolean;
  badges?: BadgeMapping;
}

export default function BooleanField({ value, badges }: BooleanFieldProps) {
  if (badges) {
    const valueStr = String(value) as 'true' | 'false';
    const badgeClass = badges[valueStr];
    const badgeType = getBadgeTypeFromClass(badgeClass);
    return (
      <Badge 
        type={badgeType}
        label={value ? 'Yes' : 'No'}
      />
    );
  }
  
  return (
    <Badge 
      type={value ? 'success' : 'default'}
      label={value ? 'Yes' : 'No'}
    />
  );
} 