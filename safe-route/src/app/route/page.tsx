'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';

// Dynamically import the Map component with no SSR
const Map = dynamic(() => import('@/components/Map'), {
  ssr: false,
  loading: () => (
    <div className="fixed inset-0 w-full h-full bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center">
      <div className="text-center p-8 bg-white rounded-2xl shadow-2xl">
        <div className="animate-spin rounded-full h-16 w-16 border-4 border-green-500 border-t-transparent mx-auto mb-6"></div>
        <h3 className="text-xl font-semibold text-gray-800 mb-2">Loading Where2Liv</h3>
        <p className="text-gray-600">Preparing your safe route planner...</p>
      </div>
    </div>
  )
});

export default function RoutePage() {
  const [currentRoute, setCurrentRoute] = useState<any>(null);

  // Function to handle route updates from the Map component
  const handleRouteUpdate = (routeData: any) => {
    setCurrentRoute(routeData);
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Compact Fixed Header */}
      <header className="bg-white border-b minimal-border minimal-shadow z-[9999] relative">
        <div className="px-4 py-3">
          <div className="flex items-center justify-center relative">
            {/* Centered Logo and Brand */}
            <div className="flex items-center space-x-3">
              <img src="/WattsUpLogo.png" alt="Where2Liv" className="h-16 w-auto object-contain" />
              <div>
                <h1 className="text-2xl font-bold text-green-700">
                  Where2Liv
                </h1>
              </div>
            </div>

            {/* Status Indicator - positioned absolutely to the right */}
            <div className="absolute right-0 flex items-center space-x-1.5 text-xs text-muted-foreground">
              <div className="w-1.5 h-1.5 bg-green-300 rounded-full"></div>
              <span className="font-medium">Live Data</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 relative overflow-hidden">
        {/* Map Container */}
        <div className="absolute inset-0">
          <Map onRouteUpdate={handleRouteUpdate} />
        </div>



        {/* Compact Status Bar - moved to bottom left to avoid crime legend overlap */}
        <div className="absolute bottom-4 left-4 z-[9998]">
          <div className="bg-white/95 backdrop-blur-sm rounded border minimal-border minimal-shadow px-3 py-2">
            <div className="flex items-center space-x-3 text-xs">
              <div className="flex items-center space-x-1.5">
                <div className="w-1.5 h-1.5 bg-green-300 rounded-full"></div>
                <span className="text-muted-foreground font-medium">Ready to plan</span>
              </div>
              {currentRoute && (
                <>
                  <div className="w-px h-3 bg-border"></div>
                  <div className="flex items-center space-x-1.5">
                    <svg className="w-3 h-3 text-green-700" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                    <span className="text-muted-foreground">Route ready</span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
} 