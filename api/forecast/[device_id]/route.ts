import { NextRequest, NextResponse } from 'next/server'

const TUNNEL_URL = 'https://necessary-bent-sol-geology.trycloudflare.com'

// Create a simple logging function for Next.js API routes
const logError = (message: string, error?: unknown) => {
  const timestamp = new Date().toISOString()
  const errorMsg = error instanceof Error ? error.message : String(error)
  console.error(`[API] ${timestamp} | Proxy error: ${message}`, errorMsg)
}

export async function GET(request: NextRequest, { params }: { params: { device_id: string } }) {
  try {
    const { device_id } = params
    const url = new URL(request.url)
    
    const response = await fetch(`${TUNNEL_URL}/api/forecast/${device_id}${url.search}`, {
      method: 'GET',
    })

    if (!response.ok) {
      const errorData = await response.json()
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    
    return NextResponse.json(data, { status: 200 })
  } catch (error) {
    logError('Forecast API request failed', error)
    return NextResponse.json(
      { error: 'Could not reach backend' },
      { status: 502 }
    )
  }
}
