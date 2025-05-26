'use client';

import Card from '@/components/ui/Card';

const LoadingSkeleton = () => {
  return (
    <Card className="h-96" collapsible={false}>
      <Card.Body className="flex items-center justify-center h-full">
        <div className="animate-pulse">
          <div className="h-64 bg-gray-200 rounded-lg w-full"></div>
        </div>
      </Card.Body>
    </Card>
  );
};

export default LoadingSkeleton; 