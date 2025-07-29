import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

export async function POST(req: NextRequest) {
  try {
    const { startCoords, endCoords, transportMode } = await req.json();

    if (!startCoords || !endCoords || !transportMode) {
      return NextResponse.json(
        { success: false, message: 'Missing required parameters' },
        { status: 400 }
      );
    }
    
    const getRoutingEndpoint = (mode: string) => {
        switch (mode) {
          case 'walking': return 'https://routing.openstreetmap.de/routed-foot/route/v1/foot';
          case 'cycling': return 'https://routing.openstreetmap.de/routed-bike/route/v1/bike';
          case 'driving': return 'https://routing.openstreetmap.de/routed-car/route/v1/driving';
          default: throw new Error('Invalid transport mode');
        }
    };

    const routingEndpoint = getRoutingEndpoint(transportMode);

    const response = await axios.get(
      `${routingEndpoint}/${startCoords};${endCoords}`,
      {
        params: {
          alternatives: 'true',
          overview: 'full',
          geometries: 'geojson',
        },
        headers: {
          'User-Agent': 'WhatTheRent/1.0 (https://whattherent.app)',
        },
        timeout: 30000,
      }
    );

    return NextResponse.json({ success: true, data: response.data });
  } catch (error) {
    if (axios.isAxiosError(error)) {
      console.error('Routing API Error:', error.response?.status, error.response?.data);
      return NextResponse.json(
        { success: false, message: `Routing Error: ${error.message}` },
        { status: error.response?.status || 500 }
      );
    }
    console.error('Unknown Routing Error:', error);
    return NextResponse.json(
      { success: false, message: 'An unknown routing error occurred' },
      { status: 500 }
    );
  }
} 