'use client';

import Card from '@/components/ui/Card';

const NoDataMessage = () => {
  return (
    <Card>
      <Card.Header className="bg-gradient-to-r from-indigo-500 to-purple-600">
        <h5 className="text-lg font-bold text-white flex items-center">
          <span className="mr-2">📈</span>
          Comments Over Time
        </h5>
      </Card.Header>
      <Card.Body className="text-center py-8">
        <p className="text-gray-500">No time-series data available</p>
      </Card.Body>
    </Card>
  );
};

export default NoDataMessage; 