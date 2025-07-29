'use client';

import React, { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.heat';
import CrimeHeatmap from './CrimeHeatmap';
import RouteSearch from './RouteSearch';

// Fix for default marker icons in Leaflet with Next.js
const DefaultIcon = L.icon({
  iconUrl: '/images/marker-icon.png',
  iconRetinaUrl: '/images/marker-icon-2x.png',
  shadowUrl: '/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

L.Marker.prototype.options.icon = DefaultIcon;

// Custom user location icon
const UserLocationIcon = L.divIcon({
  className: 'user-location-icon',
  html: `
    <div style="
      background: radial-gradient(circle at 50% 50%, #10b981 70%, #059669 100%);
      width: 20px;
      height: 20px;
      border-radius: 50%;
      border: 3px solid white;
      box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    ">
      <div style="
        width: 8px;
        height: 8px;
        background: white;
        border-radius: 50%;
        animation: pulse 2s infinite;
      "></div>
    </div>
    <style>
      @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.2); opacity: 0.7; }
        100% { transform: scale(1); opacity: 1; }
      }
    </style>
  `,
  iconSize: [20, 20],
  iconAnchor: [10, 10],
});

function LocationMarker() {
  const map = useMap();
  const [position, setPosition] = useState<L.LatLng | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Only try to get location if the browser supports it
    if (!navigator.geolocation) {
      console.log('Geolocation not supported by browser');
      return;
    }

    // Try to get location with a timeout
    const locationOptions = {
      enableHighAccuracy: false, // Don't need high accuracy for map
      timeout: 10000, // 10 second timeout
      maximumAge: 60000 // Accept cached location up to 1 minute old
    };

    map.locate({ 
      setView: false, // Don't automatically set view
      maxZoom: 16,
      timeout: 10000 // 10 second timeout
    });

    map.on('locationfound', (e) => {
      setPosition(e.latlng);
      setError(null);
      console.log('Location found:', e.latlng);
    });

    map.on('locationerror', (e) => {
      // Don't show error to user, just log it
      console.log('Geolocation not available or denied:', e.message);
      setError(null); // Don't set error state
    });
  }, [map]);

  return position === null ? null : (
    <Marker position={position} icon={UserLocationIcon}>
      <Popup>You are here</Popup>
    </Marker>
  );
}

interface MapProps {
  onRouteUpdate?: (routeData: any) => void;
}

const Map: React.FC<MapProps> = ({ onRouteUpdate }) => {
  const [routeData, setRouteData] = useState<any>(null);
  const initialRouteSet = useRef(false);

  // Commented out static example route that was causing persistent routes on map
  // useEffect(() => {
  //   if (initialRouteSet.current) return;
  //   
  //   // Example route data - replace with your actual route data
  //   const exampleRoute = {
  //     start: {
  //       lat: 40.7128,
  //       lng: -74.0060,
  //       address: "Starting Point"
  //     },
  //     end: {
  //       lat: 40.7589,
  //       lng: -73.9851,
  //       address: "Ending Point"
  //     },
  //     distance: "2.0 mi",
  //     duration: "42 min 16 sec",
  //     path: [
  //       [40.7128, -74.0060],
  //       [40.7589, -73.9851]
  //     ],
  //     safetyScore: 75,
  //     highRiskAreas: [
  //       {
  //         lat: 40.7300,
  //         lng: -73.9900,
  //         risk: "medium",
  //         description: "Area with moderate crime rate"
  //       }
  //     ],
  //     wellLitAreas: [
  //       {
  //         lat: 40.7200,
  //         lng: -73.9950,
  //         description: "Well-lit commercial area"
  //       }
  //     ]
  //   };

  //   setRouteData(exampleRoute);
  //   if (onRouteUpdate) {
  //     onRouteUpdate(exampleRoute);
  //   }
  //   initialRouteSet.current = true;
  // }, []); // Empty dependency array since we only want to set initial route once

  const handleRouteUpdate = (newRouteData: any) => {
    setRouteData(newRouteData);
    if (onRouteUpdate) {
      onRouteUpdate(newRouteData);
    }
  };

  return (
    <div className="h-screen w-full">
      <MapContainer
        center={[37.7749, -122.4194]} // San Francisco coordinates
        zoom={13}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        <LocationMarker />
        <CrimeHeatmap />
        <RouteSearch onRouteUpdate={handleRouteUpdate} />
      </MapContainer>
    </div>
  );
};

export default Map; 