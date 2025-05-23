// src/lib/serverLogger.ts
/**
 * Simple server-side logger that only logs in server context
 * In production, these logs will appear in your hosting provider's logs (Vercel, etc)
 */
export function serverLog(message: string, data?: unknown) {
    if (typeof window === 'undefined') {
      const timestamp = new Date().toISOString();
      const env = process.env.NODE_ENV;
      
      console.log(`[${timestamp}] [${env}] ${message}`, data ? JSON.stringify(data, null, 2) : '');
    }
  }
  
  export function serverError(message: string, error?: unknown) {
    if (typeof window === 'undefined') {
      const timestamp = new Date().toISOString();
      const env = process.env.NODE_ENV;
      
      console.error(`[${timestamp}] [${env}] ERROR: ${message}`, error);
    }
  }