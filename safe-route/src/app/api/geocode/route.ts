import { NextRequest, NextResponse } from 'next/server';
import axios from 'axios';

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const query = searchParams.get('query');

  if (!query || typeof query !== 'string') {
    return NextResponse.json(
      { success: false, message: 'Query parameter is required' },
      { status: 400 }
    );
  }

  try {
    const response = await axios.get('https://nominatim.openstreetmap.org/search', {
      params: {
        q: query,
        format: 'json',
        limit: 5,
        addressdetails: 1,
        countrycodes: 'us',
        viewbox: '-122.5,37.7,-122.4,37.8', // San Francisco bounding box
        bounded: 1,
      },
      headers: {
        'User-Agent': 'WhatTheRent/1.0 (https://whattherent.app)',
        'Accept-Language': 'en',
      },
      timeout: 10000, // Increased timeout to 10 seconds
    });

    const filteredData = response.data.filter((item: any) =>
      item.display_name.toLowerCase().includes('san francisco') || 
      item.display_name.toLowerCase().includes('sf') ||
      item.display_name.toLowerCase().includes('california')
    );

    return NextResponse.json({ success: true, data: filteredData });
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.error('Geocoding API Error:', error.response.status, error.response.data);
        return NextResponse.json(
          { success: false, message: `Error from Nominatim: ${error.response.status}` },
          { status: error.response.status }
        );
      } else if (error.request) {
        // The request was made but no response was received
        // `error.request` is an instance of XMLHttpRequest in the browser and an instance of
        // http.ClientRequest in node.js
        console.error('Geocoding Network Error:', error.message);
        return NextResponse.json(
          { success: false, message: 'Network error: Could not connect to Nominatim.' },
          { status: 504 } // Gateway Timeout
        );
      } else {
        // Something happened in setting up the request that triggered an Error
        console.error('Axios Geocoding Error:', error.message);
        return NextResponse.json(
          { success: false, message: `Axios setup error: ${error.message}` },
          { status: 500 }
        );
      }
    } else {
      console.error('Unknown geocoding error:', error);
      return NextResponse.json(
        { success: false, message: 'An unknown error occurred' },
        { status: 500 }
      );
    }
  }
} 