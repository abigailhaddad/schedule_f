'use client';

import Card from '@/components/ui/Card';

const LoadingSkeleton = () => {
  return (
    <Card className="h-96">
      <Card.Header className="bg-gradient-to-r from-indigo-500 to-purple-600">
        <h5 className="text-lg font-bold text-white flex items-center">
          <span className="mr-2">📈</span>
          Comments Over Time
        </h5>
      </Card.Header>
      <Card.Body className="flex items-center justify-center h-full">
        <div className="animate-pulse">
          <div className="h-64 bg-gray-200 rounded-lg w-full"></div>
        </div>
      </Card.Body>
    </Card>
  );
};

export default LoadingSkeleton; 