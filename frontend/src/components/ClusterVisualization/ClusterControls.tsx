'use client';

interface ClusterControlsProps {
  clusters: number[];
  selectedCluster: number | null;
  onClusterSelect: (cluster: number | null) => void;
  showStanceColors: boolean;
  onStanceColorsToggle: (show: boolean) => void;
}

export default function ClusterControls({
  clusters,
  selectedCluster,
  onClusterSelect,
  showStanceColors,
  onStanceColorsToggle,
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
          onChange={(e) => onClusterSelect(e.target.value ? parseInt(e.target.value) : null)}
          className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Clusters</option>
          {clusters.sort((a, b) => a - b).map(clusterId => (
            <option key={clusterId} value={clusterId}>
              Cluster {clusterId}
            </option>
          ))}
        </select>
      </div>

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={showStanceColors}
          onChange={(e) => onStanceColorsToggle(e.target.checked)}
          className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
        />
        <span className="text-sm font-medium text-gray-700">Color by Stance</span>
      </label>
    </div>
  );
}