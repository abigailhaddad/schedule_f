'use client';

interface ErrorStateProps {
  error: string;
  checkDatabase: () => Promise<void>;
  checkingDb: boolean;
  dbStatus: {success?: boolean, message?: string, counts?: {comments: number, analyses: number}} | null;
}

export default function ErrorState({ error, checkDatabase, checkingDb, dbStatus }: ErrorStateProps) {
  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-8">
          <div className="card border-danger">
            <div className="card-header bg-danger text-white">
              <h5 className="m-0">Error Loading Data</h5>
            </div>
            <div className="card-body">
              <p className="card-text">{error}</p>
              <button 
                className="btn btn-primary"
                onClick={() => window.location.reload()}
              >
                Retry
              </button>
              <button 
                className="btn btn-outline-primary ms-2"
                onClick={checkDatabase}
                disabled={checkingDb}
              >
                {checkingDb ? 'Checking...' : 'Check Database'}
              </button>
              
              {dbStatus && (
                <div className={`alert mt-3 ${dbStatus.success ? 'alert-success' : 'alert-danger'}`}>
                  <p className="mb-1"><strong>Status:</strong> {dbStatus.message}</p>
                  {dbStatus.counts && (
                    <div>
                      <p className="mb-0"><strong>Comments:</strong> {dbStatus.counts.comments}</p>
                      <p className="mb-0"><strong>Analyses:</strong> {dbStatus.counts.analyses}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 