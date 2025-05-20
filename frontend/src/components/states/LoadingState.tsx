'use client';

import { useState } from 'react';

interface LoadingStateProps {
  checkDatabase: () => Promise<void>;
  checkingDb: boolean;
  dbStatus: {success?: boolean, message?: string, counts?: {comments: number, analyses: number}} | null;
}

export default function LoadingState({ checkDatabase, checkingDb, dbStatus }: LoadingStateProps) {
  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-8">
          <div className="card">
            <div className="card-body text-center py-5">
              <div className="spinner-border text-primary mb-3" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <h3 className="mt-3">Loading comments...</h3>
              <p className="text-muted">Please wait while we fetch the data.</p>
            </div>
          </div>
          <div className="mt-3 text-center">
            <button 
              className="btn btn-outline-primary"
              onClick={checkDatabase}
              disabled={checkingDb}
            >
              {checkingDb ? (
                <>
                  <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                  Checking database...
                </>
              ) : (
                'Check Database Connection'
              )}
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
  );
} 