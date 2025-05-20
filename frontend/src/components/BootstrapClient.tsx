'use client';
import { useEffect } from 'react';

// This component loads Bootstrap's JavaScript on the client side
export default function BootstrapClient() {
  useEffect(() => {
    // Import Bootstrap's JS bundle dynamically
    import('bootstrap/dist/js/bootstrap.bundle.min.js')
      .then(() => {
        console.log('Bootstrap JS loaded');
      })
      .catch((err) => {
        console.error('Failed to load Bootstrap JS', err);
      });
  }, []);

  // This component doesn't render anything
  return null;
} 