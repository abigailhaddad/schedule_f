interface LinkFieldProps {
  value: string;
}

export default function LinkField({ value }: LinkFieldProps) {
  return (
    <a 
      href={value} 
      target="_blank" 
      rel="noopener noreferrer" 
      className="text-blue-600 hover:text-blue-800 flex items-center hover:underline"
    >
      <span className="mr-1">🔗</span>View
    </a>
  );
} 