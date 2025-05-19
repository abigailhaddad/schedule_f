// app/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { db } from '@/lib/db';
import { eq } from 'drizzle-orm';
import { comments, analyses } from '@/lib/db/schema';
import Navbar from '@/components/Navbar';
import StatisticsCard from '@/components/StatisticsCard';
import FilterSection from '@/components/FilterSection';
import CommentTable from '@/components/CommentTable';
import { ThemeProvider } from '@/components/ThemeProvider';
import api from '@/lib/api';
import type { CommentWithAnalysis } from '@/lib/api';

export default function Home() {
  const [data, setData] = useState<CommentWithAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<Record<string, any>>({});
  const [error, setError] = useState<string | null>(null);
  
  // Fetch data 
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const comments = await api.getComments();
        setData(comments);
      } catch (err) {
        console.error('Error fetching data:', err);
        setError('Failed to load comments. Please try again later.');
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
  }, []);
  
  // Handle filter changes
  const handleFilterChange = (newFilters: Record<string, any>) => {
    setFilters(newFilters);
  };
  
  if (loading) {
    return (
      <ThemeProvider>
        <Navbar />
        <div className="container-fluid py-4">
          <div className="d-flex justify-content-center py-5">
            <div className="spinner-border text-primary" role="status">
              <span className="visually-hidden">Loading...</span>
            </div>
            <p className="ms-3">Loading comments data...</p>
          </div>
        </div>
      </ThemeProvider>
    );
  }
  
  if (error) {
    return (
      <ThemeProvider>
        <Navbar />
        <div className="container-fluid py-4">
          <div className="alert alert-danger">
            <i className="bi bi-exclamation-triangle me-2"></i>
            {error}
          </div>
        </div>
      </ThemeProvider>
    );
  }
  
  return (
    <ThemeProvider>
      <Navbar />
      <div className="container-fluid py-4">
        <div className="row mb-3">
          <div className="col-md-6">
            <StatisticsCard data={data} />
          </div>
          <div className="col-md-6">
            <FilterSection onFilterChange={handleFilterChange} />
          </div>
        </div>
        <CommentTable data={data} filters={filters} />
      </div>
    </ThemeProvider>
  );
}