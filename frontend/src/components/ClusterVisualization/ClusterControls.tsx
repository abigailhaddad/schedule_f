'use client';

interface ClusterControlsProps {
  clusters: string[];
  selectedCluster: string | null;
  onClusterSelect: (cluster: string | null) => void;
}

export default function ClusterControls({
  clusters,
  selectedCluster,
  onClusterSelect,
}: ClusterControlsProps) {
  return (
    <div className="mb-4 flex flex-wrap gap-4 items-center">
      <div className="flex items-center gap-2">
        <label htmlFor="cluster-select" className="text-sm font-medium text-gray-700">
          Filter by Cluster:
        </label>
        <select
          id="cluster-select"
          value={selectedCluster ?? ''}
          onChange={(e) => onClusterSelect(e.target.value ? e.target.value : null)}
          className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Clusters</option>
          {clusters.sort((a, b) => a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' })).map(clusterId => (
            <option key={`cluster-option-${clusterId}`} value={clusterId}>
              Cluster {clusterId}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}