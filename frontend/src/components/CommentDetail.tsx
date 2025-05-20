'use client';

import { CommentWithAnalysis } from '@/lib/db/schema';
import Badge from './ui/Badge';

interface CommentDetailProps {
  comment: CommentWithAnalysis;
}

export default function CommentDetail({ comment }: CommentDetailProps) {
  // Helper function to determine badge type
  const getBadgeType = (value: string): 'success' | 'danger' | 'warning' | 'primary' | 'default' => {
    if (value === 'For') return 'success';
    if (value === 'Against') return 'danger';
    if (value === 'Neutral/Unclear') return 'warning';
    return 'primary';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-4 text-gray-800">
          {comment.title || 'Untitled Comment'}
        </h1>
        {comment.analysis?.stance && (
          <div className="mb-4">
            <Badge 
              type={getBadgeType(comment.analysis.stance)}
              label={comment.analysis.stance}
            />
          </div>
        )}
      </div>

      {/* Original Comment */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-2 text-gray-700 border-b pb-2">Original Comment</h2>
        <div className="whitespace-pre-wrap text-gray-700 bg-gray-50 p-4 rounded-md border border-gray-200">
          {comment.originalComment || comment.comment || 'No comment text available'}
        </div>
      </div>

      {/* Analysis Section */}
      {comment.analysis && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-4 text-gray-700 border-b pb-2">Analysis</h2>
          
          {/* Key Quote */}
          {comment.analysis.keyQuote && (
            <div className="mb-6">
              <h3 className="text-md font-medium mb-2 text-gray-600">Key Quote</h3>
              <div className="italic bg-blue-50 p-4 rounded-md border-l-4 border-blue-300 text-gray-700">
                &ldquo;{comment.analysis.keyQuote}&rdquo;
              </div>
            </div>
          )}
          
          {/* Themes */}
          {comment.analysis.themes && (
            <div className="mb-6">
              <h3 className="text-md font-medium mb-2 text-gray-600">Themes</h3>
              <div className="flex flex-wrap gap-2">
                {comment.analysis.themes.split(',').map((theme, index) => (
                  <Badge key={index} type="primary" label={theme.trim()} />
                ))}
              </div>
            </div>
          )}
          
          {/* Rationale */}
          {comment.analysis.rationale && (
            <div className="mb-6">
              <h3 className="text-md font-medium mb-2 text-gray-600">Rationale</h3>
              <div className="text-gray-700 bg-gray-50 p-4 rounded-md border border-gray-200">
                {comment.analysis.rationale}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Metadata Section */}
      <div>
        <h2 className="text-lg font-semibold mb-4 text-gray-700 border-b pb-2">Metadata</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
          {comment.id && (
            <div>
              <span className="text-sm font-medium text-gray-500">ID:</span>
              <div className="text-gray-700">{comment.id}</div>
            </div>
          )}
          {comment.category && (
            <div>
              <span className="text-sm font-medium text-gray-500">Category:</span>
              <div className="text-gray-700">{comment.category}</div>
            </div>
          )}
          {comment.agencyId && (
            <div>
              <span className="text-sm font-medium text-gray-500">Agency ID:</span>
              <div className="text-gray-700">{comment.agencyId}</div>
            </div>
          )}
          {comment.createdAt && (
            <div>
              <span className="text-sm font-medium text-gray-500">Created Date:</span>
              <div className="text-gray-700">{new Date(comment.createdAt).toLocaleDateString()}</div>
            </div>
          )}
          {comment.link && (
            <div>
              <span className="text-sm font-medium text-gray-500">External Link:</span>
              <div>
                <a 
                  href={comment.link} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center"
                >
                  <span className="mr-1">🔗</span>View Original
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
} 