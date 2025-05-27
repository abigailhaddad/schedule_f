import { Metadata } from 'next';
import { getClusterData } from '@/lib/actions/clusters';
import ClusterVisualization from '@/components/ClusterVisualization';
import Navbar from '@/components/Navbar';

export const metadata: Metadata = {
  title: 'Comment Clusters - Schedule F Analysis',
  description: 'Visualization of comment clusters using PCA analysis',
};

export const revalidate = 86400; // 24 hours

export default async function ClustersPage() {
  const clusterResponse = await getClusterData();

  if (!clusterResponse.success || !clusterResponse.data) {
    return (
      <main className="min-h-screen bg-gray-50">
        <Navbar />
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

  return (
    <main className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="pt-24 pb-12">
        <div className="container mx-auto px-4">
          <h1 className="text-3xl font-bold mb-8">Comment Cluster Analysis</h1>
          <ClusterVisualization data={clusterResponse.data} />
        </div>
      </div>
    </main>
  );
}