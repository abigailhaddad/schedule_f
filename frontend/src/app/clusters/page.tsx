import { Metadata } from 'next';
import { getClusterData } from '@/lib/actions/clusters';
import ClusterVisualization from '@/components/ClusterVisualization';

export const metadata: Metadata = {
  title: 'Comment Clusters - Schedule F Analysis',
  description: 'Visualization of comment clusters using PCA analysis',
};

export default async function ClustersPage() {
  const clusterResponse = await getClusterData(); 
  
  // Server-side logging to debug
  console.log('Cluster data fetch result:', {
    success: clusterResponse.success,
    hasData: !!clusterResponse.data,
    clusterCount: clusterResponse.data?.clusters?.length,
    totalPoints: clusterResponse.data?.totalPoints,
    error: clusterResponse.error
  });

  // Pass the data with the correct prop names
  return (
    <main className="min-h-screen bg-gray-50">
      <div className="pb-12">
        <div className="container mx-auto px-4">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-3xl font-bold">Comment Cluster Analysis</h1>
          </div>
          <ClusterVisualization 
            initialData={clusterResponse.data || null}
            isLoading={false}
            error={clusterResponse.error || null}
          />
        </div>
      </div>
    </main>
  );
}