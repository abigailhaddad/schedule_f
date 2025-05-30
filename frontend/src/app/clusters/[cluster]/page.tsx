import { Metadata } from 'next';
import { getClusterData } from '@/lib/actions/clusters';
import ClusterVisualization from '@/components/ClusterVisualization';

// Next.js 13+ App Router revalidation
export const revalidate = 86400; // 24 hours in seconds

// Pre-generate static pages for some clusters at build time
export async function generateStaticParams() {
  try {
    const clusterResponse = await getClusterData();
    
    if (!clusterResponse.success || !clusterResponse.data) {
      return [];
    }

    // Generate params for all clusters (or limit to first N if there are many)
    const clusters = clusterResponse.data.clusters.slice(0, 50); // Limit to first 50 clusters
    
    return clusters.map(([clusterId]) => ({
      cluster: clusterId,
    }));
  } catch (error) {
    console.error('Error generating static params for clusters:', error);
    return [];
  }
}

interface PageProps {
  params: Promise<{ cluster: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { cluster } = await params;
  return {
    title: `Cluster ${cluster} - Schedule F Analysis`,
    description: `Visualization of comment cluster ${cluster} using PCA analysis`,
  };
}

export default async function ClusterPage({ params }: PageProps) {
  const { cluster } = await params;
  const clusterResponse = await getClusterData();
  
  // Server-side logging to debug
  console.log('Cluster data fetch result:', {
    success: clusterResponse.success,
    hasData: !!clusterResponse.data,
    selectedCluster: cluster,
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
            initialSelectedCluster={cluster}
          />
        </div>
      </div>
    </main>
  );
}