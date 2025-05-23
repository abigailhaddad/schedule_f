import { revalidatePath, revalidateTag } from 'next/cache';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const token = request.headers.get('x-revalidate-token');
  
  if (token !== process.env.REVALIDATE_TOKEN) {
    return NextResponse.json(
      { success: false, message: 'Invalid token' }, 
      { status: 401 }
    );
  }
  
  try {
    // Get the request body which might contain specific paths to revalidate
    const body = await request.json().catch(() => ({}));
    const { path, tag } = body;

    if (tag) {
      // Revalidate a specific tag
      revalidateTag(tag);
    } else if (path) {
      // Revalidate a specific path
      revalidatePath(path);
    } else {
      // Revalidate essential paths and tags
      revalidateTag('comments');
      revalidatePath('/');
      revalidatePath('/comment', 'page');
    }
    
    return NextResponse.json({ 
      success: true, 
      message: 'Revalidation triggered successfully' 
    });
  } catch (error) {
    console.error('Error during revalidation:', error);
    return NextResponse.json(
      { 
        success: false, 
        message: 'Error during revalidation',
        error: error instanceof Error ? error.message : String(error)
      }, 
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json(
    { success: false, message: 'Method not allowed' }, 
    { status: 405 }
  );
} 