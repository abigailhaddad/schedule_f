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
    <main className="min-h-screen bg-gray-50 flex flex-col">
      <div className="flex-1 flex flex-col">
        <div className="px-4 py-6">
          <h1 className="text-3xl font-bold">Comment Cluster Analysis</h1>
        </div>
        <div className="flex-1">
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