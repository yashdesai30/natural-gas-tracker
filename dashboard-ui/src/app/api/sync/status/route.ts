import { NextResponse } from 'next/server';

const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://127.0.0.1:8000';

export async function GET() {
  try {
    const response = await fetch(`${PYTHON_API_URL}/sync/status`, {
      cache: 'no-store',
    });

    if (!response.ok) {
      throw new Error(`Python API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Failed to fetch sync status:', error);
    return NextResponse.json({ 
      success: false, 
      is_syncing: false,
      error: error.message 
    }, { status: 500 });
  }
}
