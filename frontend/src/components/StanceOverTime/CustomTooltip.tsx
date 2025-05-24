'use client';

// Custom tooltip component for the StanceOverTime chart
const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-lg">
        <p className="text-sm font-semibold text-gray-700 mb-2">
          {new Date(label).toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
          })}
        </p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm" style={{ color: entry.color }}>
            {entry.name}: <span className="font-semibold">{entry.value}</span>
          </p>
        ))}
        <p className="text-xs text-gray-500 mt-1">
          Total: {payload.reduce((sum: number, entry: any) => sum + entry.value, 0)}
        </p>
      </div>
    );
  }
  return null;
};

export default CustomTooltip; 