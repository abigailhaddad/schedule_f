import { Metadata } from 'next';
import { getClusterData } from '@/lib/actions/clusters';
import ClusterVisualization from '@/components/ClusterVisualization';
import Navbar from '@/components/Navbar';

export const metadata: Metadata = {
  title: 'Comment Clusters - Schedule F Analysis',
  description: 'Visualization of comment clusters using PCA analysis',
};

export const revalidate = 86400; // 24 hours

// Allow users to control sampling via URL parameter
export default async function ClustersPage({
  searchParams
}: {
  searchParams: Promise<{ full?: string }>
}) {
  // Check if user wants full data (no sampling)
  const { full } = await searchParams;
  const showFullData = full === 'true';
  
  const clusterResponse = await getClusterData(!showFullData); // sample by default

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
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-3xl font-bold">Comment Cluster Analysis</h1>
            
            {clusterResponse.data.isSampled && (
              <div className="text-sm text-gray-600 bg-yellow-50 px-4 py-2 rounded-lg border border-yellow-200">
                <span className="font-medium">Performance Mode:</span> Showing {clusterResponse.data.sampledPoints} of {clusterResponse.data.totalPoints} points
                {' '}
                <a 
                  href="/clusters?full=true" 
                  className="text-blue-600 hover:underline ml-2"
                >
                  Load all points
                </a>
              </div>
            )}
            
            {!clusterResponse.data.isSampled && clusterResponse.data.totalPoints > 1000 && (
              <div className="text-sm text-gray-600">
                <span className="font-medium">Full Dataset:</span> {clusterResponse.data.totalPoints} points
                {' '}
                <a 
                  href="/clusters" 
                  className="text-blue-600 hover:underline ml-2"
                >
                  Use performance mode
                </a>
              </div>
            )}
          </div>
          
          <ClusterVisualization data={clusterResponse.data} />
        </div>
      </div>
    </main>
  );
}