import { Comment } from '@/lib/db/schema';
import Badge from './ui/Badge';

interface CommentDetailProps {
  comment: Comment;
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
    <article 
      className="bg-white rounded-lg shadow-md p-6"
      aria-labelledby="comment-title"
    >
      <header className="mb-8">
        <h1 id="comment-title" className="text-2xl font-bold mb-4 text-gray-800">
          {comment.title || 'Untitled Comment'}
        </h1>
        {comment.stance && (
          <div className="mb-4">
            <Badge 
              type={getBadgeType(comment.stance)}
              label={comment.stance}
              id="comment-stance"
              aria-label={`Stance: ${comment.stance}`}
            />
          </div>
        )}
      </header>

      {/* Original Comment */}
      <section 
        className="mb-8"
        aria-labelledby="original-comment-heading"
      >
        <h2 id="original-comment-heading" className="text-lg font-semibold mb-2 text-gray-700 border-b pb-2">Original Comment</h2>
        <div 
          className="whitespace-pre-wrap text-gray-700 bg-gray-50 p-4 rounded-md border border-gray-200"
          aria-label="Original comment text"
        >
          {comment.originalComment || comment.comment || 'No comment text available'}
        </div>
      </section>

      {/* Analysis Section */}
      <section 
        className="mb-8"
        aria-labelledby="analysis-heading"
      >
        <h2 id="analysis-heading" className="text-lg font-semibold mb-4 text-gray-700 border-b pb-2">Analysis</h2>
        
        {/* Key Quote */}
        {comment.keyQuote && (
          <div 
            className="mb-6"
            aria-labelledby="key-quote-heading"
          >
            <h3 id="key-quote-heading" className="text-md font-medium mb-2 text-gray-600">Key Quote</h3>
            <blockquote className="italic bg-blue-50 p-4 rounded-md border-l-4 border-blue-300 text-gray-700">
              &ldquo;{comment.keyQuote}&rdquo;
            </blockquote>
          </div>
        )}
        
        {/* Themes */}
        {comment.themes && (
          <div 
            className="mb-6"
            aria-labelledby="themes-heading"
          >
            <h3 id="themes-heading" className="text-md font-medium mb-2 text-gray-600">Themes</h3>
            <div 
              className="flex flex-wrap gap-2"
              role="list"
              aria-label="Comment themes"
            >
              {comment.themes.split(',').map((theme, index) => (
                <Badge 
                  key={index} 
                  type="primary" 
                  label={theme.trim()} 
                  id={`theme-${index}`}
                />
              ))}
            </div>
          </div>
        )}
        
        {/* Rationale */}
        {comment.rationale && (
          <div 
            className="mb-6"
            aria-labelledby="rationale-heading"
          >
            <h3 id="rationale-heading" className="text-md font-medium mb-2 text-gray-600">Rationale</h3>
            <div 
              className="text-gray-700 bg-gray-50 p-4 rounded-md border border-gray-200"
              aria-label="Comment rationale"
            >
              {comment.rationale}
            </div>
          </div>
        )}
      </section>

      {/* Metadata Section */}
      <section 
        aria-labelledby="metadata-heading"
      >
        <h2 id="metadata-heading" className="text-lg font-semibold mb-4 text-gray-700 border-b pb-2">Metadata</h2>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
          {comment.id && (
            <div>
              <dt className="text-sm font-medium text-gray-500">ID:</dt>
              <dd className="text-gray-700">{comment.id}</dd>
            </div>
          )}
          {comment.category && (
            <div>
              <dt className="text-sm font-medium text-gray-500">Category:</dt>
              <dd className="text-gray-700">{comment.category}</dd>
            </div>
          )}
          {comment.agencyId && (
            <div>
              <dt className="text-sm font-medium text-gray-500">Agency ID:</dt>
              <dd className="text-gray-700">{comment.agencyId}</dd>
            </div>
          )}
          {comment.createdAt && (
            <div>
              <dt className="text-sm font-medium text-gray-500">Created Date:</dt>
              <dd className="text-gray-700">
                <time dateTime={new Date(comment.createdAt).toISOString()}>
                  {new Date(comment.createdAt).toLocaleDateString()}
                </time>
              </dd>
            </div>
          )}
          {comment.link && (
            <div>
              <dt className="text-sm font-medium text-gray-500">External Link:</dt>
              <dd>
                <a 
                  href={comment.link} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="text-blue-600 hover:text-blue-800 hover:underline inline-flex items-center focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-1"
                  aria-label="View original comment on external site (opens in new tab)"
                >
                  <span className="mr-1" aria-hidden="true">🔗</span>View Original
                </a>
              </dd>
            </div>
          )}
        </dl>
      </section>
    </article>
  );
} 