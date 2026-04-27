import { NextResponse } from 'next/server';

const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://127.0.0.1:8000';

export async function POST() {
  try {
    console.log('Triggering Sync via Python API...');
    
    const apiUrl = `${PYTHON_API_URL}/sync?days=30`;
    console.log(`[Next.js] Calling Python API: POST ${apiUrl}`);
    
    const response = await fetch(apiUrl, {
      method: 'POST',
    });

    console.log(`[Next.js] Python API response: ${response.status} ${response.statusText}`);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Python API error: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Failed to trigger sync:', error);
    return NextResponse.json({ 
      success: false, 
      error: 'Python API is not reachable. Ensure uvicorn is running on port 8000.',
      details: error.message 
    }, { status: 500 });
  }
}
