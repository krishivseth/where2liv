'use client';

import { useState, useEffect, useRef, useCallback, memo } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import axios from 'axios';
import { MapPin, Navigation, Clock, Route, History, Trash2, X, ArrowRight, Locate, ArrowUpDown, Mic } from 'lucide-react';
import { Marker, Popup } from 'react-leaflet';


interface Location {
  display_name: string;
  lat: string;
  lon: string;
}

interface CrimeData {
  row_id: string;
  incident_datetime: string;
  incident_date: string;
  incident_time: string;
  incident_year: string;
  incident_day_of_week: string;
  report_datetime: string;
  incident_id: string;
  incident_number: string;
  cad_number: string;
  report_type_code: string;
  report_type_description: string;
  incident_code: string;
  incident_category: string;
  incident_subcategory: string;
  incident_description: string;
  resolution: string;
  intersection: string;
  cnn: string;
  police_district: string;
  analysis_neighborhood: string;
  supervisor_district: string;
  supervisor_district_2012: string;
  latitude: string;
  longitude: string;
  point: {
    type: string;
    coordinates: number[];
  };
  data_as_of: string;
  data_loaded_at: string;
}

interface RouteInfo {
  duration: number;
  distance: number;
}

type TransportMode = 'walking' | 'cycling' | 'driving';

interface ScoredRoute {
  coords: [number, number][];
  duration: number;
  distance: number;
  score: number;
}

interface SavedRoute {
  startLocation: string;
  endLocation: string;
  transportMode: TransportMode;
  timestamp: number;
}

interface RouteSearchProps {
  onRouteUpdate?: (routeData: any) => void;
}

// Custom marker icons
const startIcon = L.divIcon({
  className: 'custom-div-icon',
  html: `
    <div style="
      background: linear-gradient(135deg, #10b981, #059669);
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 3px solid white;
      box-shadow: 0 4px 12px rgba(5, 150, 105, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    ">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="white">
        <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2Z"/>
        <circle cx="12" cy="16" r="4" fill="white"/>
      </svg>
      <div style="
        position: absolute;
        bottom: -8px;
        left: 50%;
        transform: translateX(-50%);
        width: 0;
        height: 0;
        border-left: 6px solid transparent;
        border-right: 6px solid transparent;
        border-top: 8px solid #059669;
      "></div>
    </div>
  `,
  iconSize: [24, 32],
  iconAnchor: [12, 32]
});

const endIcon = L.divIcon({
  className: 'custom-div-icon',
  html: `
    <div style="
      background: linear-gradient(135deg, #f43f5e, #dc2626);
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 3px solid white;
      box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    ">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="white">
        <path d="M12 2C15.31 2 18 4.69 18 8C18 12.5 12 22 12 22S6 12.5 6 8C6 4.69 8.69 2 12 2Z"/>
        <circle cx="12" cy="8" r="3" fill="#dc2626"/>
      </svg>
      <div style="
        position: absolute;
        bottom: -8px;
        left: 50%;
        transform: translateX(-50%);
        width: 0;
        height: 0;
        border-left: 6px solid transparent;
        border-right: 6px solid transparent;
        border-top: 8px solid #dc2626;
      "></div>
    </div>
  `,
  iconSize: [24, 32],
  iconAnchor: [12, 32]
});

// Add TypeScript interfaces for SpeechRecognition
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
  interpretation: string;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
  isFinal: boolean;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  grammars: any;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onaudioend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onaudiostart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onerror: ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => any) | null;
  onnomatch: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
  onsoundend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onsoundstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onspeechend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onspeechstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

// Define SpeechRecognition constructor type
interface SpeechRecognitionConstructor {
  new(): SpeechRecognition;
  prototype: SpeechRecognition;
}

declare global {
  interface Window {
    SpeechRecognition: SpeechRecognitionConstructor;
    webkitSpeechRecognition: SpeechRecognitionConstructor;
  }
}

const RouteSearch: React.FC<RouteSearchProps> = memo(({ onRouteUpdate }) => {
  const map = useMap();
  const [startLocation, setStartLocation] = useState('');
  const [endLocation, setEndLocation] = useState('');
  const [startSuggestions, setStartSuggestions] = useState<Location[]>([]);
  const [endSuggestions, setEndSuggestions] = useState<Location[]>([]);
  const [transportMode, setTransportMode] = useState<TransportMode>('walking');
  const [isCalculating, setIsCalculating] = useState(false);
  const [crimeData, setCrimeData] = useState<CrimeData[]>([]);
  const [routeInfo, setRouteInfo] = useState<RouteInfo | null>(null);
  const [savedRoutes, setSavedRoutes] = useState<SavedRoute[]>([]);
  const [showSavedRoutes, setShowSavedRoutes] = useState(false);
  const [routes, setRoutes] = useState<any[]>([]);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState<number>(0);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isGettingLocation, setIsGettingLocation] = useState(false);
  const currentRouteRef = useRef<L.Polyline | null>(null);
  const startMarkerRef = useRef<L.Marker | null>(null);
  const endMarkerRef = useRef<L.Marker | null>(null);
  const [startPoint, setStartPoint] = useState<[number, number] | null>(null);
  const [endPoint, setEndPoint] = useState<[number, number] | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [isProcessingSpeech, setIsProcessingSpeech] = useState(false);
  const speechRecognition = useRef<SpeechRecognition | null>(null);

  // Load saved routes on component mount
  useEffect(() => {
    const saved = localStorage.getItem('savedRoutes');
    if (saved) {
      setSavedRoutes(JSON.parse(saved));
    }
  }, []);

  // Clear the route when the transport mode changes
  useEffect(() => {
    console.log('Transport mode changed, clearing route.');
    clearCurrentRoute();
  }, [transportMode]);

  // Save routes to localStorage whenever savedRoutes changes
  useEffect(() => {
    localStorage.setItem('savedRoutes', JSON.stringify(savedRoutes));
  }, [savedRoutes]);

  // Handle URL parameters for automatic route population
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const origin = urlParams.get('origin');
    const destination = urlParams.get('destination');
    
    console.log('safe-route URL Parameters:', { origin, destination });
    
    if (origin && destination) {
      console.log('Auto-populating route from URL parameters');
      setStartLocation(decodeURIComponent(origin));
      setEndLocation(decodeURIComponent(destination));
      
      // Automatically start route calculation after a short delay to ensure state is set
      setTimeout(() => {
        console.log('Auto-starting route calculation...');
        calculateRoute();
      }, 1000);
    }
  }, []); // Run only once on component mount

  // Save route to localStorage
  const saveRoute = () => {
    if (!startLocation || !endLocation) return;
    
    const newRoute: SavedRoute = {
      startLocation,
      endLocation,
      transportMode,
      timestamp: Date.now()
    };
    
    setSavedRoutes(prev => [newRoute, ...prev.slice(0, 9)]); // Keep only 10 most recent
  };

  // Load a saved route
  const loadRoute = (route: SavedRoute) => {
    setStartLocation(route.startLocation);
    setEndLocation(route.endLocation);
    setTransportMode(route.transportMode);
    setShowSavedRoutes(false);
  };

  // Delete a saved route
  const deleteRoute = (timestamp: number) => {
    const updatedRoutes = savedRoutes.filter(route => route.timestamp !== timestamp);
    setSavedRoutes(updatedRoutes);
    localStorage.setItem('savedRoutes', JSON.stringify(updatedRoutes));
  };

  // Function to clear current route and markers
  const clearCurrentRoute = () => {
    console.log('ClearCurrentRoute called');
    
    // IMPROVED route clearing - collect polylines first, then remove them
    const polylinesToRemove: L.Polyline[] = [];
    map.eachLayer((layer: any) => {
      if (layer instanceof L.Polyline && !(layer instanceof L.Polygon)) {
        polylinesToRemove.push(layer);
      }
    });
    
    // Remove all collected polylines
    polylinesToRemove.forEach(polyline => {
      console.log('Removing polyline layer during clear');
      map.removeLayer(polyline);
    });

    // Clear route reference
    if (currentRouteRef.current) {
      map.removeLayer(currentRouteRef.current);
      currentRouteRef.current = null;
    }
    
    // Clear markers
    if (startMarkerRef.current) {
      map.removeLayer(startMarkerRef.current);
      startMarkerRef.current = null;
    }
    if (endMarkerRef.current) {
      map.removeLayer(endMarkerRef.current);
      endMarkerRef.current = null;
    }
    
    // Clear routes array and selection
    setRoutes([]);
    setSelectedRouteIndex(0);
    setRouteInfo(null); // This was the missing piece
    console.log('Route clearing completed');
  };

  // Fetch crime data
  useEffect(() => {
    const fetchCrimeData = async () => {
      try {
        // Get recent crime data (last 3 months) with valid coordinates
        const threeMonthsAgo = new Date();
        threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
        const dateFilter = threeMonthsAgo.toISOString().split('T')[0];

        console.log('🔍 Fetching SF crime data with date filter:', dateFilter);
        
        const response = await axios.get(
          'https://data.sfgov.org/resource/wg3w-h783.json',
          {
            params: {
              $where: `latitude IS NOT NULL AND longitude IS NOT NULL AND incident_date >= '${dateFilter}'`,
              $limit: 15000, // Increased limit for better coverage
              $order: 'incident_datetime DESC'
            }
          }
        );
        
        console.log(`📊 Loaded ${response.data.length} SF crime incidents from last 3 months`);
        if (response.data.length > 0) {
          console.log('📊 Sample crime data:', response.data[0]);
          console.log('📊 Available fields:', Object.keys(response.data[0]));
        } else {
          console.log('⚠️ No crime data returned from API');
        }
        setCrimeData(response.data);
      } catch (error) {
        console.error('❌ Error fetching SF crime data:', error);
        setCrimeData([]);
      }
    };
    fetchCrimeData();
  }, []);



  // Debounce function for search
  const debounce = (func: Function, wait: number) => {
    let timeout: NodeJS.Timeout;
    return (...args: any[]) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), wait);
    };
  };

  // Search for locations using our new API route
  const searchLocations = async (query: string) => {
    if (query.length < 2) return [];
    
    try {
      const response = await axios.get('/api/geocode', {
        params: { query }
      });
      
      if (response.data.success) {
        return response.data.data;
      } else {
        console.error('Geocoding search failed:', response.data.message);
        return [];
      }
    } catch (error) {
      console.error('Location search failed:', error);
      return [];
    }
  };

  // Debounced search functions
  const debouncedSearch = debounce(async (query: string, setSuggestions: (locations: Location[]) => void) => {
    if (query.length < 2) {
      setSuggestions([]);
      return;
    }
    const results = await searchLocations(query);
    setSuggestions(results);
  }, 300);

  // Handle location selection
  const handleLocationSelect = (location: Location, isStart: boolean) => {
    if (isStart) {
      setStartLocation(location.display_name);
      setStartSuggestions([]);
      map.setView([parseFloat(location.lat), parseFloat(location.lon)], 15);
    } else {
      setEndLocation(location.display_name);
      setEndSuggestions([]);
    }
  };

  // Handle input blur with delay to allow for suggestion clicks
  const handleInputBlur = (isStart: boolean) => {
    setTimeout(() => {
      if (isStart) {
        setStartSuggestions([]);
      } else {
        setEndSuggestions([]);
      }
    }, 500); // Increased delay to 500ms for easier clicking
  };

  // Calculate crime density for a point
  const calculateCrimeDensity = (lat: number, lon: number, radius: number = 0.005) => {
    const result = crimeData.reduce((sum, crime) => {
      const dLat = parseFloat(crime.latitude) - lat;
      const dLon = parseFloat(crime.longitude) - lon;
      const distance = Math.sqrt(dLat*dLat + dLon*dLon);
      if (distance > radius) return sum;
      const category = (crime.incident_category || '').toLowerCase();
      const desc = (crime.incident_description || '').toLowerCase();
      const weight = category.includes('assault') || category.includes('robbery') ? 8
                   : category.includes('burglary') || category.includes('theft') || category.includes('larceny') ? 5
                   : category.includes('arson') ? 6
                   : category.includes('fraud') ? 3
                   : category.includes('vehicle') || category.includes('auto') ? 3
                   : 1;
      return sum + weight;
    }, 0);
    
    // Debug logging for high crime areas
    if (result > 5) {
      console.log(`🚨 High crime density at [${lat.toFixed(4)}, ${lon.toFixed(4)}]: ${result}`);
    }
    
    return result;
  };

  // Calculate overall safety score for a route
  const calculateRouteSafetyScore = (coordinates: [number, number][]) => {
    console.log('🔍 SAFETY SCORE CALCULATION DEBUG:');
    console.log('  - Coordinates length:', coordinates.length);
    console.log('  - Crime data length:', crimeData.length);
    console.log('  - Sample crime data:', crimeData.slice(0, 3));
    
    if (!coordinates.length || !crimeData.length) {
      console.log('  - Returning default score: 85');
      return 85; // Default decent score
    }
    
    console.log('🔍 ROUTE SAFETY CALCULATION START');
    console.log('📍 Route coordinates:', coordinates.length, 'points');
    console.log('🚨 SF Crime data available:', crimeData.length, 'incidents');
    
    let totalCrimeScore = 0;
    let maxCrimeAtPoint = 0;
    const samplePoints = coordinates.filter((_, index) => index % 5 === 0); // Sample every 5th point for performance
    
    console.log('📊 Sampling', samplePoints.length, 'points from', coordinates.length, 'total points');
    
    samplePoints.forEach((coord, index) => {
      const crimeScore = calculateCrimeDensity(coord[0], coord[1]);
      totalCrimeScore += crimeScore;
      maxCrimeAtPoint = Math.max(maxCrimeAtPoint, crimeScore);
      
      if (index < 3 || crimeScore > 10) { // Log first 3 points and high-crime points
        console.log(`📍 Point ${index}: [${coord[0].toFixed(4)}, ${coord[1].toFixed(4)}] - Crime incidents: ${crimeScore}`);
      }
    });
    
    const avgCrimeScore = totalCrimeScore / samplePoints.length;
    
    console.log('📊 SF CRIME ANALYSIS RESULTS:');
    console.log('  - Total crime incidents along route:', totalCrimeScore);
    console.log('  - Average crime per sample point:', avgCrimeScore.toFixed(2));
    console.log('  - Maximum crime at any point:', maxCrimeAtPoint);
    
    // Convert to safety score (0-100, higher is safer)
    // Adjusted for SF crime patterns - extremely lenient scoring
    const normalizedAvg = Math.min(avgCrimeScore / 300, 1.5); // Extremely lenient average normalization
    const normalizedMax = Math.min(maxCrimeAtPoint / 500, 1.5); // Extremely lenient max normalization
    
    // Base score starts at 90 (very good) and gets reduced by crime
    const safetyScore = 90 - (normalizedAvg * 20 + normalizedMax * 25);
    const finalScore = Math.max(0, Math.min(100, safetyScore));
    
    console.log('🛡️ SAFETY SCORE CALCULATION:');
    console.log('  - Normalized average:', normalizedAvg.toFixed(2));
    console.log('  - Normalized maximum:', normalizedMax.toFixed(2));
    console.log('  - Raw safety score:', safetyScore.toFixed(2));
    console.log('  - Final safety score:', finalScore.toFixed(2));
    console.log('🔍 ROUTE SAFETY CALCULATION END\n');
    
    return finalScore;
  };

  // Convert safety score to letter grade
  const getSafetyGrade = (score: number): string => {
    if (score >= 90) return 'A';
    if (score >= 80) return 'B';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'F';
  };

  // Identify high-risk areas along the route
  const identifyHighRiskAreas = (coordinates: [number, number][]) => {
    const highRiskAreas: Array<{lat: number, lng: number, risk: string, description: string}> = [];
    
    console.log('🚨 HIGH-RISK AREA IDENTIFICATION START');
    
    coordinates.forEach((coord, index) => {
      if (index % 10 === 0) { // Check every 10th point
        const crimeScore = calculateCrimeDensity(coord[0], coord[1]);
        
        if (crimeScore > 15) { // Adjusted threshold for SF crime patterns
          const riskLevel = crimeScore > 50 ? 'high' : 'medium';
          const nearbyIncidents = crimeData.filter(crime => {
            const dLat = parseFloat(crime.latitude) - coord[0];
            const dLon = parseFloat(crime.longitude) - coord[1];
            const distance = Math.sqrt(dLat*dLat + dLon*dLon);
            return distance < 0.005; // Within small radius
          });
          
                      const commonCrimes = nearbyIncidents
              .map(c => c.incident_category || c.incident_description)
              .reduce((acc, crime) => {
                acc[crime] = (acc[crime] || 0) + 1;
                return acc;
              }, {} as Record<string, number>);
          
          const topCrime = Object.entries(commonCrimes)
            .sort(([,a], [,b]) => b - a)[0];
          
          const riskArea = {
            lat: coord[0],
            lng: coord[1],
            risk: riskLevel,
            description: topCrime ? `High ${topCrime[0].toLowerCase()} activity (${topCrime[1]} incidents)` : 'High crime activity detected'
          };
          
          highRiskAreas.push(riskArea);
          
          console.log(`🚨 High-risk area found at [${coord[0].toFixed(4)}, ${coord[1].toFixed(4)}]:`);
          console.log(`   - Risk level: ${riskLevel}`);
          console.log(`   - Crime incidents: ${crimeScore}`);
          console.log(`   - Description: ${riskArea.description}`);
        }
      }
    });
    
    console.log('🚨 HIGH-RISK AREAS FOUND:', highRiskAreas.length);
    console.log('🚨 HIGH-RISK AREA IDENTIFICATION END\n');
    
    return highRiskAreas;
  };

  // Calculate detailed crime statistics for the route
  const calculateCrimeStats = (coordinates: [number, number][]) => {
    if (!crimeData.length) return { total_incidents: 0, high_risk_areas: 0, crime_types: {} };
    
    console.log('📊 SF CRIME STATISTICS CALCULATION START');
    
    const routeCrimes = crimeData.filter(crime => {
      return coordinates.some(coord => {
        const dLat = parseFloat(crime.latitude) - coord[0];
        const dLon = parseFloat(crime.longitude) - coord[1];
        const distance = Math.sqrt(dLat*dLat + dLon*dLon);
        return distance < 0.005; // Within route corridor
      });
    });
    
          const crimeTypes = routeCrimes.reduce((acc, crime) => {
        const type = crime.incident_category || crime.incident_description;
        acc[type] = (acc[type] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);
    
    const highRiskAreas = coordinates.filter(coord => 
      calculateCrimeDensity(coord[0], coord[1]) > 15
    ).length;
    
    const topCrimes = Object.entries(crimeTypes)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5);
    
    console.log('📊 SF CRIME STATISTICS:');
    console.log('  - Total incidents along route:', routeCrimes.length);
    console.log('  - High-risk areas:', highRiskAreas);
    console.log('  - Crime types found:', Object.keys(crimeTypes).length);
    console.log('  - Top 5 crime types:', topCrimes);
    console.log('📊 SF CRIME STATISTICS CALCULATION END\n');
    
    return {
      total_incidents: routeCrimes.length,
      high_risk_areas: highRiskAreas,
      crime_types: crimeTypes
    };
  };

  // Format duration in minutes and seconds
  const formatDuration = (seconds: number) => {
    const walkingSpeedMph = 2.6;
    const distanceInMiles = seconds / 3600 * walkingSpeedMph;
    const minutes = Math.floor(distanceInMiles * 60 / walkingSpeedMph);
    const remainingSeconds = Math.round((distanceInMiles * 60 / walkingSpeedMph - minutes) * 60);
    return `${minutes} min ${remainingSeconds} sec`;
  };

  // Format distance in miles
  const formatDistance = (meters: number) => {
    const miles = meters * 0.000621371;
    return `${miles.toFixed(1)} mi`;
  };

  // Get routing API endpoint based on transport mode
  const getRoutingEndpoint = (mode: TransportMode) => {
    switch (mode) {
      case 'walking': return 'https://routing.openstreetmap.de/routed-foot/route/v1/foot';
      case 'cycling': return 'https://routing.openstreetmap.de/routed-bike/route/v1/bike';
      case 'driving': return 'https://routing.openstreetmap.de/routed-car/route/v1/driving';
    }
  };

  // HYBRID: Calculate routes using safe-route's native logic + enhanced safety analysis
  const calculateRoute = async () => {
    if (!startLocation || !endLocation || isCalculating) return;
    setIsCalculating(true);
    clearCurrentRoute();
    setRouteInfo(null);

    console.log('🚀 ROUTE CALCULATION START');
    console.log('📍 From:', startLocation);
    console.log('📍 To:', endLocation);
    console.log('🚶 Transport mode:', transportMode);

    try {
      // Clear existing routes array
      setRoutes([]);

      // STEP 1: Geocoding start and end locations
      console.log('\n🔍 STEP 1: Geocoding locations...');
      const [startResp, endResp] = await Promise.all([
        axios.get('/api/geocode', { params: { query: startLocation } }),
        axios.get('/api/geocode', { params: { query: endLocation } })
      ]);

      if (!startResp.data.success || startResp.data.data.length === 0) {
        throw new Error(`Could not find start location: "${startLocation}". Please try selecting from the dropdown suggestions.`);
      }
      if (!endResp.data.success || endResp.data.data.length === 0) {
        throw new Error(`Could not find end location: "${endLocation}". Please try selecting from the dropdown suggestions.`);
      }

      const start = startResp.data.data[0];
      const end = endResp.data.data[0];
      const startCoords = `${start.lon},${start.lat}`;
      const endCoords = `${end.lon},${end.lat}`;

      console.log('✅ Geocoding successful:');
      console.log('  - Start:', start.display_name, `[${start.lat}, ${start.lon}]`);
      console.log('  - End:', end.display_name, `[${end.lat}, ${end.lon}]`);

      // STEP 2: Get a pool of route alternatives via our own API
      console.log('  - Calculating up to 3 route alternatives via API...');
      const routeResponse = await axios.post('/api/route', {
        startCoords,
        endCoords,
        transportMode,
      });

      if (!routeResponse.data.success || !routeResponse.data.data.routes || routeResponse.data.data.routes.length === 0) {
        throw new Error('Could not calculate any routes via API.');
      }
      
      const routesData = routeResponse.data.data.routes;
      console.log(`  ✅ Found ${routesData.length} route alternatives.`);

      // HUNCH INVESTIGATION: Log raw route data from the server
      console.log('🕵️‍♂️ INVESTIGATING HUNCH: Raw data from routing server:');
      routesData.forEach((route: any, index: number) => {
        console.log(`  - Alternative ${index}: Distance = ${route.distance}m, Duration = ${route.duration}s`);
      });


      // STEP 3: Process all alternatives and add safety analysis
      console.log('\n🛡️ STEP 3: Processing all alternatives with safety analysis...');
      
      const processedRoutes = await Promise.all(
        routesData.map(async (route: any, index: number) => {
          const coordinates = route.geometry.coordinates.map((coord: number[]) => [coord[1], coord[0]]);
          
          const safetyScore = calculateRouteSafetyScore(coordinates);
          
          return {
            index,
            type: 'alternative',
            name: `Route Option ${index + 1}`,
            distance: `${(route.distance / 1609).toFixed(1)} mi`,
            duration: formatDuration(route.duration),
            safetyScore: Math.round(safetyScore),
            safetyGrade: getSafetyGrade(safetyScore),
            coordinates,
            highRiskAreas: identifyHighRiskAreas(coordinates),
            crimeStats: calculateCrimeStats(coordinates),
            details: {
              distance_meters: route.distance,
              duration_seconds: route.duration,
              legs: route.legs
            }
          };
        })
      );

      // STEP 4: Select the best routes from the processed alternatives
      console.log('\n🎯 STEP 4: Selecting fastest and safest from alternatives...');

      const fastestRoute = [...processedRoutes].sort((a, b) => a.details.duration_seconds - b.details.duration_seconds)[0];
      fastestRoute.type = 'fastest';
      fastestRoute.name = '⚡ Fastest Route';

      const safestRoute = [...processedRoutes].sort((a, b) => b.safetyScore - a.safetyScore)[0];
      safestRoute.type = 'safest';
      safestRoute.name = '🛡️ Safest Route';
      
      console.log('📊 Fastest Route selected:', fastestRoute.name, 'Duration:', fastestRoute.duration, 'Safety:', fastestRoute.safetyScore, 'Type:', fastestRoute.type);
      console.log('🛡️ Safest Route selected:', safestRoute.name, 'Duration:', safestRoute.duration, 'Safety:', safestRoute.safetyScore, 'Type:', safestRoute.type);

      // Create final list of unique routes (fastest and safest)
      const finalRoutes = [];
      finalRoutes.push(fastestRoute);
      // Add safest route only if it's a different route from the fastest
      if (fastestRoute.details.distance_meters !== safestRoute.details.distance_meters || fastestRoute.details.duration_seconds !== safestRoute.details.duration_seconds) {
        finalRoutes.push(safestRoute);
        console.log('✅ Fastest and safest routes are different, adding both to final list.');
      } else {
        console.log('🔄 Fastest and safest routes are identical, showing one route.');
        console.log('  - Before: type =', finalRoutes[0].type);
        // If they are the same, ensure the single route is marked as both
        finalRoutes[0].name = '⚡ Fastest & 🛡️ Safest';
        finalRoutes[0].type = 'fastest_safest';
        console.log('  - After: type =', finalRoutes[0].type);
      }
      
      // Re-index final routes
      finalRoutes.forEach((route, i) => route.index = i);

      console.log('\n✅ All routes processed successfully. Found', finalRoutes.length, 'unique routes.');

      setRoutes(finalRoutes);

      // Set markers for start/end points
      if (startMarkerRef.current) {
        map.removeLayer(startMarkerRef.current);
      }
      if (endMarkerRef.current) {
        map.removeLayer(endMarkerRef.current);
      }

      startMarkerRef.current = L.marker([parseFloat(start.lat), parseFloat(start.lon)], { icon: startIcon }).addTo(map);
      endMarkerRef.current = L.marker([parseFloat(end.lat), parseFloat(end.lon)], { icon: endIcon }).addTo(map);

      // Clear all existing polylines but keep the route data
      const allLayers: any[] = [];
      map.eachLayer((layer: any) => {
        allLayers.push(layer);
      });
      
      // Remove polylines but keep markers
      allLayers.forEach(layer => {
        if (layer instanceof L.Polyline && !(layer instanceof L.Polygon)) {
          try {
            map.removeLayer(layer);
          } catch (e) {
            console.error('Error removing layer:', e);
          }
        }
      });

      // Clear current route reference
      if (currentRouteRef.current) {
        try {
          map.removeLayer(currentRouteRef.current);
        } catch (e) {
          console.log('CurrentRouteRef already removed');
        }
        currentRouteRef.current = null;
      }
      
      // Select the safest route by default and display it
      console.log('\n🔍 DEBUG: Final routes before selection:');
      finalRoutes.forEach((route, i) => {
        console.log(`  - Route ${i}: type="${route.type}", name="${route.name}", safety=${route.safetyScore}`);
      });
      
      // Updated logic: prefer safest, then fastest_safest, then fastest, then fallback
      const defaultRoute = finalRoutes.find((r: any) => r.type === 'safest') || 
                          finalRoutes.find((r: any) => r.type === 'fastest_safest') || 
                          finalRoutes.find((r: any) => r.type === 'fastest') || 
                          finalRoutes[0];
      console.log('\n🎯 Default route selected:', defaultRoute.name, 'Type:', defaultRoute.type);
      setSelectedRouteIndex(defaultRoute.index);
      displayRoute(defaultRoute);

      console.log('🚀 ROUTE CALCULATION COMPLETE\n');

      // Save the route after successful calculation
      saveRoute();

      // Automatically minimize the route planner after successful route calculation
      setTimeout(() => {
        setIsMinimized(true);
      }, 1000);

    } catch (err: any) {
      console.error('Route calculation error:', err);
      
      // Show user-friendly error message
      if (err.message.includes('Could not find')) {
        alert(err.message + '\n\nTip: Type a few characters and select from the dropdown suggestions for best results.');
        setIsCalculating(false);
        return;
      }
      
      alert('Failed to calculate route. Please check your internet connection and try again.');
    } finally {
      setIsCalculating(false);
    }
  };

  // Add new function to decode Google's polyline format
  const decodePolyline = (encoded: string): [number, number][] => {
    const coordinates: [number, number][] = [];
    let index = 0;
    let lat = 0;
    let lng = 0;

    while (index < encoded.length) {
      let byte = 0;
      let shift = 0;
      let result = 0;

      do {
        byte = encoded.charCodeAt(index++) - 63;
        result |= (byte & 0x1f) << shift;
        shift += 5;
      } while (byte >= 0x20);

      const deltaLat = (result & 1) !== 0 ? ~(result >> 1) : result >> 1;
      lat += deltaLat;

      shift = 0;
      result = 0;

      do {
        byte = encoded.charCodeAt(index++) - 63;
        result |= (byte & 0x1f) << shift;
        shift += 5;
      } while (byte >= 0x20);

      const deltaLng = (result & 1) !== 0 ? ~(result >> 1) : result >> 1;
      lng += deltaLng;

      coordinates.push([lat / 1e5, lng / 1e5]);
    }

    return coordinates;
  };

  // Add new function to display a selected route
  const displayRoute = (route: any) => {
    console.log('🗺️ DisplayRoute called for:', route.type, 'Route index:', route.index);
    
    // ENHANCED route clearing with multiple passes to ensure all routes are removed
    // First pass: remove all polylines except polygons
    const allLayers: any[] = [];
    map.eachLayer((layer: any) => {
      allLayers.push(layer);
    });
    
    // Remove polylines in a separate loop to avoid iterator issues
    allLayers.forEach(layer => {
      if (layer instanceof L.Polyline && !(layer instanceof L.Polygon)) {
        try {
          map.removeLayer(layer);
          console.log('🗑️ Removed a polyline layer');
        } catch (e) {
          console.error('Error removing polyline layer:', e);
        }
      }
    });

    // Clear current route reference
    if (currentRouteRef.current) {
      try {
        map.removeLayer(currentRouteRef.current);
        console.log('🗑️ Removed current route reference');
      } catch (e) {
        console.log('CurrentRouteRef already removed or invalid');
      }
      currentRouteRef.current = null;
    }

    // Second pass: double-check for any remaining route layers
    map.eachLayer((layer: any) => {
      if (layer instanceof L.Polyline && !(layer instanceof L.Polygon)) {
        try {
          map.removeLayer(layer);
          console.log('🗑️ Removed remaining polyline in second pass');
        } catch (e) {
          console.error('Error in second pass removal:', e);
        }
      }
    });

    // Wait a moment then display the new route
    setTimeout(() => {
      const getRouteColor = (type: string) => {
        switch (type) {
          case 'safest': return '#10b981'; // Green
          case 'fastest': return '#f59e0b'; // Amber
          case 'fastest_safest': return '#3b82f6'; // Blue (when fastest and safest are the same)
          case 'balanced': return '#3b82f6'; // Blue
          default: return '#6b7280'; // Gray
        }
      };

      const routeColor = getRouteColor(route.type);
      
      // Create new polyline for the selected route
      const polyline = L.polyline(route.coordinates, {
        color: routeColor,
        weight: 4,
        opacity: 0.8,
        smoothFactor: 1
      }).addTo(map);

      // Store reference to current route
      currentRouteRef.current = polyline;

      // Fit map to route bounds with padding
      const bounds = polyline.getBounds();
      map.fitBounds(bounds, { padding: [20, 20] });

      console.log('✅ Route displayed successfully:', route.name);
      console.log('  - Color:', routeColor);
      console.log('  - Coordinates:', route.coordinates.length);
      console.log('  - Safety Score:', route.safetyScore);
      
      // Update route info for display
      setRouteInfo({
        duration: route.details.duration_seconds,
        distance: route.details.distance_meters
      });

      // Call the onRouteUpdate callback if provided
      if (onRouteUpdate) {
        onRouteUpdate(route);
      }
    }, 100);
  };

  // Add function to handle route card selection
  const selectRoute = (routeIndex: number) => {
    console.log('🎯 Route selection changed to index:', routeIndex);
    setSelectedRouteIndex(routeIndex);
    const selectedRoute = routes[routeIndex];
    if (selectedRoute) {
      console.log('Selected route:', selectedRoute.name, 'Type:', selectedRoute.type);
      displayRoute(selectedRoute);
    } else {
      console.error('No route found at index:', routeIndex);
    }
  };

  const getTransportIcon = (mode: TransportMode) => {
    switch (mode) {
      case 'walking': return '🚶‍♂️';
      case 'cycling': return '🚴‍♂️';
      case 'driving': return '🚗';
    }
  };

  const getRouteTypeColor = (type: 'fastest' | 'safest') => {
    return type === 'fastest' ? 'from-blue-500 to-cyan-500' : 'from-green-500 to-emerald-500';
  };

  const handleRouteUpdate = useCallback((start: [number, number], end: [number, number]) => {
    if (startPoint === start && endPoint === end) return;

    setStartPoint(start);
    setEndPoint(end);

    // Create route data object
    const routeData = {
      start: {
        lat: start[0],
        lng: start[1],
        address: "Starting Point" // You can add geocoding here to get actual addresses
      },
      end: {
        lat: end[0],
        lng: end[1],
        address: "Ending Point"
      },
      distance: "2.0 mi", // Calculate actual distance
      duration: "42 min 16 sec", // Calculate actual duration
      path: [start, end], // Add actual path points
      safetyScore: 75, // Calculate actual safety score
      highRiskAreas: [
        {
          lat: 40.7300,
          lng: -73.9900,
          risk: "medium",
          description: "Area with moderate crime rate"
        }
      ],
      wellLitAreas: [
        {
          lat: 40.7200,
          lng: -73.9950,
          description: "Well-lit commercial area"
        }
      ]
    };

    // Pass route data to parent component
    if (onRouteUpdate) {
      onRouteUpdate(routeData);
    }
  }, [onRouteUpdate, startPoint, endPoint]);

  // Get current location function
  const getCurrentLocation = async (isStart: boolean) => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by this browser.');
      return;
    }

    setIsGettingLocation(true);
    
    try {
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 60000
        });
      });

      const { latitude, longitude } = position.coords;
      
      // Reverse geocode to get address
      try {
        const response = await axios.get(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=18&addressdetails=1`
        );
        
        const address = response.data.display_name;
        
        if (isStart) {
          setStartLocation(address);
          setStartPoint([latitude, longitude]);
        } else {
          setEndLocation(address);
          setEndPoint([latitude, longitude]);
        }
        
        // Center map on the new location
        map.setView([latitude, longitude], 15);
        
      } catch (error) {
        // If reverse geocoding fails, use coordinates as fallback
        const fallbackAddress = `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
        
        if (isStart) {
          setStartLocation(fallbackAddress);
          setStartPoint([latitude, longitude]);
        } else {
          setEndLocation(fallbackAddress);
          setEndPoint([latitude, longitude]);
        }
        
        map.setView([latitude, longitude], 15);
      }
      
    } catch (error) {
      console.error('Error getting location:', error);
      alert('Unable to get your current location. Please check your browser permissions and try again.');
    } finally {
      setIsGettingLocation(false);
    }
  };

  // Switch locations function
  const switchLocations = () => {
    // Switch location strings
    const tempLocation = startLocation;
    setStartLocation(endLocation);
    setEndLocation(tempLocation);
    
    // Switch coordinates
    const tempPoint = startPoint;
    setStartPoint(endPoint);
    setEndPoint(tempPoint);
    
    // Switch suggestions
    const tempSuggestions = startSuggestions;
    setStartSuggestions(endSuggestions);
    setEndSuggestions(tempSuggestions);
    
    // Clear current route since locations changed
    clearCurrentRoute();
    setRouteInfo(null);
  };

  // Initialize speech recognition
  useEffect(() => {
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
      speechRecognition.current = new SpeechRecognitionAPI();
      speechRecognition.current.continuous = false;
      speechRecognition.current.interimResults = false;
      speechRecognition.current.lang = 'en-US';

      speechRecognition.current.onresult = async (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript;
        console.log('Voice input:', transcript);
        setIsListening(false);
        setIsProcessingSpeech(true);
        
        try {
          // Simple voice input processing - just set the transcript as start location
          setStartLocation(transcript);
          setStartSuggestions([]);
          setEndSuggestions([]);
        } catch (error) {
          console.error('Error processing speech:', error);
          alert('Error processing speech. Please try again.');
        } finally {
          setIsProcessingSpeech(false);
        }
      };

      speechRecognition.current.onerror = (event: SpeechRecognitionErrorEvent) => {
        console.error('Speech recognition error', event.error);
        setIsListening(false);
        setIsProcessingSpeech(false);
        alert('Error with speech recognition. Please try again or use text input.');
      };
    }
  }, []);

  const startVoiceInput = () => {
    if (speechRecognition.current) {
      setIsListening(true);
      speechRecognition.current.start();
    } else {
      alert('Speech recognition is not supported in your browser.');
    }
  };

  return (
    <div className="absolute left-4 top-20 bottom-6 z-[1000] w-80 flex flex-col">
      {/* Main Search Panel */}
      <div className="bg-white rounded border minimal-border minimal-shadow-lg flex flex-col max-h-full">
        {/* Header */}
        <div className="p-4 border-b minimal-border">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-green-50 rounded flex items-center justify-center">
                <svg className="w-4 h-4 text-green-700" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2Z"/>
                  <path d="M21 9V7L15 4L12 5.5L9 4L3 7V9L9 6L12 7.5L15 6L21 9Z"/>
                  <path d="M12 22C13.1 22 14 21.1 14 20C14 18.9 13.1 18 12 18C10.9 18 10 18.9 10 20C10 21.1 10.9 22 12 22Z"/>
                  <path d="M12 7.5L12 18" stroke="currentColor" strokeWidth="2" fill="none"/>
                </svg>
              </div>
              <div>
                <h2 className="text-base font-bold text-foreground">Route Planner</h2>
                <p className="text-xs text-muted-foreground">Find your safe path</p>
              </div>
            </div>
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-1.5 hover:bg-accent rounded transition-colors"
            >
              {isMinimized ? (
                <ArrowRight className="w-4 h-4 text-muted-foreground rotate-90" />
              ) : (
                <ArrowRight className="w-4 h-4 text-muted-foreground -rotate-90" />
              )}
            </button>
          </div>

          {/* Transport Mode and Route Type */}
          <div className="flex gap-2">
            <select
              value={transportMode}
              onChange={(e) => setTransportMode(e.target.value as TransportMode)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
            >
              <option value="walking">🚶 Walking</option>
              <option value="cycling">🚴 Cycling</option>
              <option value="driving">🚗 Driving</option>
            </select>
            <button
              onClick={() => {
                console.log('🔍 Current crime data:', crimeData.length, 'incidents');
                console.log('🔍 Sample crime:', crimeData[0] || 'No data');
                // Force re-fetch crime data
                const threeMonthsAgo = new Date();
                threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
                const dateFilter = threeMonthsAgo.toISOString().split('T')[0];
                console.log('🔍 Date filter:', dateFilter);
                // Force page reload to refresh crime data
                window.location.reload();
              }}
              className="px-2 py-2 bg-blue-500 text-white rounded text-xs hover:bg-blue-600"
              title="Debug crime data and refresh"
            >
              🔄
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className={`flex-1 overflow-y-auto ${isMinimized ? 'hidden' : ''}`}>
          <div className="p-4 space-y-4">
            {/* Location Inputs */}
            <div className="space-y-3">
              {/* From Input */}
              <div className="relative">
                <label className="block text-xs font-medium text-muted-foreground mb-1">From</label>
                <div className="relative">
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2 w-2.5 h-2.5 bg-green-500 rounded"></div>
                  <input
                    type="text"
                    value={startLocation}
                    onChange={(e) => {
                      setStartLocation(e.target.value);
                      debouncedSearch(e.target.value, setStartSuggestions);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && startSuggestions.length > 0) {
                        handleLocationSelect(startSuggestions[0], true);
                      }
                    }}
                    onBlur={() => handleInputBlur(true)}
                    placeholder="Enter starting location"
                    className="w-full pl-8 pr-10 py-2.5 text-sm border minimal-border rounded text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary/30 focus:border-primary"
                  />
                  <button
                    onClick={() => getCurrentLocation(true)}
                    disabled={isGettingLocation}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1 hover:bg-green-50 rounded transition-colors"
                    title="Use current location"
                  >
                    {isGettingLocation ? (
                      <div className="w-3.5 h-3.5 border-2 border-green-200 border-t-green-400 rounded-full animate-spin"></div>
                    ) : (
                      <Locate className="w-3.5 h-3.5 text-green-700" />
                    )}
                  </button>
                </div>
                {startSuggestions.length > 0 && (
                  <div className="absolute z-[9999] w-full mt-1 bg-white rounded border minimal-border minimal-shadow-lg max-h-40 overflow-y-auto">
                    {startSuggestions.map((location, index) => (
                      <div
                        key={index}
                        className="p-3 hover:bg-green-50 cursor-pointer text-foreground border-b minimal-border last:border-b-0 flex items-center gap-3 text-sm transition-colors"
                        onClick={() => handleLocationSelect(location, true)}
                        onMouseDown={(e) => e.preventDefault()}
                      >
                        <MapPin className="w-4 h-4 text-green-700 flex-shrink-0" />
                        <span className="truncate font-medium">{location.display_name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Switch Button */}
              <div className="flex justify-center">
                <button
                  onClick={switchLocations}
                  disabled={!startLocation || !endLocation}
                  className="p-1.5 bg-accent hover:bg-accent/80 rounded transition-colors disabled:opacity-50"
                  title="Switch locations"
                >
                  <ArrowUpDown className="w-3.5 h-3.5 text-muted-foreground" />
                </button>
              </div>

              {/* To Input */}
              <div className="relative">
                <label className="block text-xs font-medium text-muted-foreground mb-1">To</label>
                <div className="relative">
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2 w-2.5 h-2.5 bg-red-500 rounded"></div>
                  <input
                    type="text"
                    value={endLocation}
                    onChange={(e) => {
                      setEndLocation(e.target.value);
                      debouncedSearch(e.target.value, setEndSuggestions);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && endSuggestions.length > 0) {
                        handleLocationSelect(endSuggestions[0], false);
                      }
                    }}
                    onBlur={() => handleInputBlur(false)}
                    placeholder="Enter destination"
                    className="w-full pl-8 pr-10 py-2.5 text-sm border minimal-border rounded text-foreground placeholder-muted-foreground focus:ring-2 focus:ring-primary/30 focus:border-primary"
                  />
                  <button
                    onClick={() => getCurrentLocation(false)}
                    disabled={isGettingLocation}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1 hover:bg-green-50 rounded transition-colors"
                    title="Use current location"
                  >
                    {isGettingLocation ? (
                      <div className="w-3.5 h-3.5 border-2 border-green-200 border-t-green-400 rounded-full animate-spin"></div>
                    ) : (
                      <Locate className="w-3.5 h-3.5 text-green-700" />
                    )}
                  </button>
                </div>
                {endSuggestions.length > 0 && (
                  <div className="absolute z-[9999] w-full mt-1 bg-white rounded border minimal-border minimal-shadow-lg max-h-40 overflow-y-auto">
                    {endSuggestions.map((location, index) => (
                      <div
                        key={index}
                        className="p-3 hover:bg-green-50 cursor-pointer text-foreground border-b minimal-border last:border-b-0 flex items-center gap-3 text-sm transition-colors"
                        onClick={() => handleLocationSelect(location, false)}
                        onMouseDown={(e) => e.preventDefault()}
                      >
                        <MapPin className="w-4 h-4 text-green-700 flex-shrink-0" />
                        <span className="truncate font-medium">{location.display_name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Calculate Route Button */}
            <button
              onClick={calculateRoute}
              disabled={!startLocation || !endLocation || isCalculating}
              className="w-full py-3 px-4 bg-primary text-primary-foreground rounded font-semibold hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-all duration-200 minimal-shadow flex items-center justify-center gap-2 text-sm border border-primary/20"
            >
              {isCalculating ? (
                <>
                  <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin"></div>
                  <span>Finding Routes...</span>
                </>
              ) : (
                <>
                  <Navigation className="w-4 h-4" />
                  <span>Find Safe Routes</span>
                </>
              )}
            </button>

            {/* Route Options */}
            {routes.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-semibold text-muted-foreground flex items-center gap-2">
                  <Route className="w-3.5 h-3.5" />
                  Available Routes
                </h3>
                <div className="space-y-1.5">
                  {routes.map((route: any, index: number) => (
                    <div
                      key={index}
                      onClick={() => selectRoute(index)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                        selectedRouteIndex === index
                          ? 'border-green-500 bg-green-50 shadow-sm' 
                          : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-1.5">
                          <span className="text-sm">{route.name.split(' ')[0]}</span>
                          <span className="font-medium text-foreground text-sm">{route.name.substring(2)}</span>
                        </div>
                        <div className={`w-2.5 h-2.5 rounded-full border ${
                          selectedRouteIndex === index 
                            ? 'bg-green-500 border-green-500' 
                            : 'border-gray-300'
                        }`}></div>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mb-1.5">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {route.duration}
                        </span>
                        <span className="flex items-center gap-1">
                          <Route className="w-3 h-3" />
                          {route.distance}
                        </span>
                      </div>
                      <div className={`px-2 py-0.5 rounded text-xs font-medium text-center ${
                        route.safetyGrade === 'A' ? 'bg-green-100 text-green-800' :
                        route.safetyGrade === 'B' ? 'bg-blue-100 text-blue-800' :
                        route.safetyGrade === 'C' ? 'bg-yellow-100 text-yellow-800' :
                        route.safetyGrade === 'D' ? 'bg-orange-100 text-orange-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        Safety: {route.safetyGrade} ({route.safetyScore}/100)
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Current Route Info */}
            {routeInfo && (
              <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-4 rounded-xl text-white">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">{getTransportIcon(transportMode)}</span>
                  <div>
                    <p className="text-green-100 text-sm font-medium">
                      {routes[selectedRouteIndex]?.name || 'Route'}
                    </p>
                    <div className="flex items-center gap-4 mt-1">
                      <div className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        <span className="font-semibold">{formatDuration(routeInfo.duration)}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Route className="w-4 h-4" />
                        <span className="font-semibold">{formatDistance(routeInfo.distance)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        {!isMinimized && (
          <div className="p-4 border-t minimal-border bg-secondary rounded-b-2xl">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                Live safety data
              </span>
              <button
                onClick={() => setShowSavedRoutes(!showSavedRoutes)}
                className="flex items-center gap-2 hover:text-green-600 transition-colors"
              >
                <History className="w-4 h-4" />
                History
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Saved Routes Panel */}
      {showSavedRoutes && savedRoutes.length > 0 && (
        <div className="mt-4 bg-white rounded-2xl minimal-shadow-lg border minimal-border max-h-64 flex flex-col">
          <div className="p-4 border-b minimal-border flex items-center justify-between">
            <h3 className="font-semibold text-foreground flex items-center gap-2">
              <History className="w-4 h-4" />
              Recent Routes
            </h3>
            <button
              onClick={() => setShowSavedRoutes(false)}
              className="p-1 hover:bg-accent rounded-lg transition-colors"
            >
              <X className="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
          <div className="overflow-y-auto flex-1">
            {savedRoutes.map((route) => (
              <div
                key={route.timestamp}
                className="p-4 border-b minimal-border last:border-b-0 hover:bg-accent transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div 
                    className="flex-1 cursor-pointer"
                    onClick={() => loadRoute(route)}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">{getTransportIcon(route.transportMode)}</span>
                      <span className="px-2 py-1 rounded-full text-xs font-medium text-white bg-gradient-to-r from-green-600 to-emerald-600">
                        {/* routeType is removed, so this will always show "Fastest" */}
                        Fastest
                      </span>
                    </div>
                    <div className="space-y-1 text-sm">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-foreground truncate">{route.startLocation.split(',')[0]}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                        <span className="text-foreground truncate">{route.endLocation.split(',')[0]}</span>
                      </div>
                    </div>
                    <div className="text-xs text-muted-foreground mt-2">
                      {new Date(route.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                  <button
                    onClick={() => deleteRoute(route.timestamp)}
                    className="p-1.5 text-muted-foreground hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Markers */}
      {startPoint && (
        <Marker position={startPoint} icon={startIcon}>
          <Popup>Starting Point</Popup>
        </Marker>
      )}
      {endPoint && (
        <Marker position={endPoint} icon={endIcon}>
          <Popup>Destination</Popup>
        </Marker>
      )}
    </div>
  );
});

RouteSearch.displayName = 'RouteSearch';

export default RouteSearch; 