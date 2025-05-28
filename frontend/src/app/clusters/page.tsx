import { Metadata } from 'next';
import { getClusterData } from '@/lib/actions/clusters';
import ClusterVisualization from '@/components/ClusterVisualization';

export const metadata: Metadata = {
  title: 'Comment Clusters - Schedule F Analysis',
  description: 'Visualization of comment clusters using PCA analysis',
};
// Allow users to control sampling via URL parameter
export default async function ClustersPage() {
  // Check if user wants full data (no sampling)
  const clusterResponse = await getClusterData(); // sample by default

  if (!clusterResponse.success || !clusterResponse.data) {
    return (
      <main className="min-h-screen bg-gray-50">
        <div className="pt-24 pb-12">
          <div className="container mx-auto px-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-8 text-center">
              <h1 className="text-2xl font-bold text-red-800 mb-2">
                Error Loading Cluster Data
              </h1>
              <p className="text-red-600">
                {clusterResponse.error || 'Unable to load cluster visualization'}
              </p>
            </div>
          </div>
        </div>
      </main>
    );
  }

  const displayData = clusterResponse.data;

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="pb-12">
        <div className="container mx-auto px-4">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-3xl font-bold">Comment Cluster Analysis</h1>
          </div>
          <ClusterVisualization data={displayData} />
        </div>
      </div>
    </main>
  );
}