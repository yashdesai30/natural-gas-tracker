import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://127.0.0.1:8000';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const page = searchParams.get('page') || '1';
    const page_size = searchParams.get('page_size') || '15';
    const symbol = searchParams.get('symbol');
    const start_date = searchParams.get('start_date');
    const end_date = searchParams.get('end_date');

    const params = new URLSearchParams();
    params.set('page', page);
    params.set('page_size', page_size);
    if (symbol) params.set('symbol', symbol);
    if (start_date) params.set('start_date', start_date);
    if (end_date) params.set('end_date', end_date);

    const apiUrl = `${PYTHON_API_URL}/data?${params.toString()}`;
    console.log(`[Next.js] Calling Python API: GET ${apiUrl}`);
    
    const response = await fetch(apiUrl, { cache: 'no-store' });
    
    console.log(`[Next.js] Python API response: ${response.status}`);
    
    if (!response.ok) {
      throw new Error(`Python API error: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Data fetch failed:', error);
    return NextResponse.json({ 
      success: false, 
      error: 'Python API is not reachable.',
      details: error.message 
    }, { status: 500 });
  }
}
