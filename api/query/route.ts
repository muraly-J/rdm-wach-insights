import { NextRequest, NextResponse } from 'next/server'

const TUNNEL_URL = 'https://necessary-bent-sol-geology.trycloudflare.com'

// Create a simple logging function for Next.js API routes
const logError = (message: string, error?: unknown) => {
  const timestamp = new Date().toISOString()
  const errorMsg = error instanceof Error ? error.message : String(error)
  console.error(`[API] ${timestamp} | Proxy error: ${message}`, errorMsg)
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    const response = await fetch(`${TUNNEL_URL}/api/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()
    
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    logError('POST request failed', error)
    return NextResponse.json(
      { error: 'Could not reach backend' },
      { status: 502 }
    )
  }
}

export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url)
    const response = await fetch(`${TUNNEL_URL}${url.pathname}`, {
      method: 'GET',
    })

    const data = await response.json()
    
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    logError('GET request failed', error)
    return NextResponse.json(
      { error: 'Could not reach backend' },
      { status: 502 }
    )
  }
}
