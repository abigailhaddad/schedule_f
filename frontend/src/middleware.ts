// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;
  
  // Only apply to home page
  if (pathname === '/') {
    // Check if query parameters are missing
    const hasPage = searchParams.has('page');
    const hasPageSize = searchParams.has('pageSize');
    
    // If default parameters are missing, redirect with them
    if (!hasPage || !hasPageSize) {
      const url = request.nextUrl.clone();
      
      // Set default parameters
      if (!hasPage) {
        url.searchParams.set('page', '1');
      }
      if (!hasPageSize) {
        url.searchParams.set('pageSize', '10');
      }
      
      // Redirect to the URL with default parameters
      return NextResponse.redirect(url);
    }
  }
  
  return NextResponse.next();
}

// Configure which paths the middleware runs on
export const config = {
  matcher: '/',
};