import { useState, useEffect, useRef } from "react";
import logo from "./assets/WattsUpLogo.png";
import { Tag } from "./components/Tag";
import { SafetyRating } from "./components/SafetyRating";
import { SafetyDetails } from "./components/SafetyDetails";
import { RouteInput } from "./components/RouteInput";
import type { SafetyAnalysis } from "./types/safety";

interface EnergyCostData {
  annual_summary: {
    average_monthly_bill: number;
    total_kwh: number;
    total_bill: number;
  }
}

interface ContentScriptResponse {
  address: string;
  numRooms: number;
  buildingName: string;
  rawAddress: string;
  sqFt: number | null;
  borough: string | null;
  source: string;
}

function App() {
  const [address, setAddress] = useState<string>("");
  const [buildingName, setBuildingName] = useState<string>("");
  const [rawAddress, setRawAddress] = useState<string>("");
  const [numRooms, setNumRooms] = useState<number>(1);
  const [sqFt, setSqFt] = useState<number | null>(null);
  const [borough, setBorough] = useState<string | null>(null);
  const [cost, setCost] = useState<number | null>(30);
  const [error, setError] = useState<string>("");
  const [safetyData, setSafetyData] = useState<SafetyAnalysis | null>(null);
  const [safetyLoading, setSafetyLoading] = useState<boolean>(false);
  const [safetyError, setSafetyError] = useState<string>("");
  const [showSafetyDetails, setShowSafetyDetails] = useState<boolean>(false);
  const [showPersonalSafety, setShowPersonalSafety] = useState<boolean>(true);
  const [showNeighborhoodQuality, setShowNeighborhoodQuality] = useState<boolean>(false);
  const [routeLoading, setRouteLoading] = useState<boolean>(false);
  
  // Use refs to prevent duplicate API calls
  const safetyRequestRef = useRef<AbortController | null>(null);
  const hasLoadedSafetyRef = useRef<boolean>(false);
  const lastSafetyAddressRef = useRef<string>("");
  const lastSafetyBoroughRef = useRef<string | null>(null);

  const extractAddressAndRooms = async (): Promise<{address: string, numRooms: number, buildingName: string, rawAddress: string, sqFt: number | null, borough: string | null}> => {
    try {
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });

      console.log('WattsUp: Current tab URL:', tab.url);

      if (!tab.url?.includes("streeteasy.com") && !tab.url?.includes("zillow.com")) {
        throw new Error("WattsUp is only supported on StreetEasy and Zillow listings");
      }

      if (!tab.id) {
        throw new Error("Unable to get tab ID");
      }

      // First, try to inject the content script if it's not already injected
      try {
        await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ['content.js']
        });
        console.log('WattsUp: Content script injected successfully');
      } catch (injectionError) {
        console.log('WattsUp: Content script already injected or injection failed:', injectionError);
        // This is ok - the script might already be injected
      }

      console.log('WattsUp: Sending message to content script...');
      
      // Add a timeout and retry mechanism for the message sending
      const response = await new Promise<ContentScriptResponse>((resolve, reject) => {
        let attempts = 0;
        const maxAttempts = 3;
        
        const attemptMessage = () => {
          attempts++;
          console.log(`WattsUp: Attempt ${attempts}/${maxAttempts} to contact content script`);
          
          const timeout = setTimeout(() => {
            if (attempts < maxAttempts) {
              console.log('WattsUp: Retrying message...');
              setTimeout(attemptMessage, 1000); // Wait 1 second before retry
            } else {
              reject(new Error("Content script did not respond after 3 attempts. Please refresh the page and try again."));
            }
          }, 5000); // 5 second timeout per attempt

          chrome.tabs.sendMessage(tab.id!, {
            action: "extractAddress",
          }, (response) => {
            clearTimeout(timeout);
            if (chrome.runtime.lastError) {
              console.log(`WattsUp: Attempt ${attempts} failed:`, chrome.runtime.lastError.message);
              if (attempts < maxAttempts) {
                // Try again after a short delay
                setTimeout(attemptMessage, 1000);
              } else {
                reject(new Error("Failed to communicate with content script. Please refresh the page and try again."));
              }
            } else {
              resolve(response);
            }
          });
        };
        
        attemptMessage();
      });

      console.log('WattsUp: Content script response:', response);

      if (!response || !response.address) {
        throw new Error("Could not find address on this page");
      }

      return {
        address: response.address,
        numRooms: response.numRooms || 1,
        buildingName: response.buildingName || "",
        rawAddress: response.rawAddress || response.address,
        sqFt: response.sqFt || null,
        borough: response.borough || null
      };
    } catch (err) {
      console.error('WattsUp: Error in extractAddressAndRooms:', err);
      throw new Error(
        `Failed to extract listing info: ${
          err instanceof Error ? err.message : "Unknown error"
        }`
      );
    }
  };

  const getEnergyCost = async (address: string, numRooms: number, sqFt: number | null): Promise<number> => {
    const API_ENDPOINT = "http://127.0.0.1:9005/api/estimate";

    try {
      const payload: any = { 
        address, 
        num_rooms: numRooms 
      };
      
      // Include square footage if available
      if (sqFt) {
        payload.sq_ft = sqFt;
      }

      const response = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      const data: EnergyCostData = await response.json();
      const cost = data.annual_summary.average_monthly_bill;
      
      // Better error handling - only return 0 if cost is actually 0, not if it's falsy
      if (typeof cost === 'number' && !isNaN(cost)) {
        return cost;
      }
      
      console.error('Invalid cost received from API:', cost);
      return 0;
    } catch (error) {
      console.error('Energy cost API error:', error);
      return 0;
    }
  };

  const getSafetyAnalysis = async (address: string, borough: string | null): Promise<SafetyAnalysis | null> => {
    const API_ENDPOINT = "http://127.0.0.1:9005/api/safety";

    try {
      // Cancel any existing request
      if (safetyRequestRef.current) {
        safetyRequestRef.current.abort();
      }

      // Create new abort controller
      const abortController = new AbortController();
      safetyRequestRef.current = abortController;

      setSafetyLoading(true);
      setSafetyError("");

      // Normalize address for consistent caching
      // Remove apartment numbers and floor info for area-based safety analysis
      const normalizedAddress = address
        .trim()
        .toLowerCase()
        .replace(/\s+/g, ' ')
        // Remove common apartment/unit patterns
        .replace(/\b(apt|apartment|unit|suite|ste|#)\s*\w+\b/gi, '')
        .replace(/\b\d+[a-z]?\s*(fl|floor)\b/gi, '')
        .replace(/\s*,\s*$/, '') // Remove trailing comma
        .trim();
      
      const payload: any = { address: normalizedAddress };
      if (borough) {
        payload.borough = borough.trim();
      }

      const response = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        signal: abortController.signal
      });

      if (!response.ok) {
        throw new Error(`Safety API request failed: ${response.status}`);
      }

      const data: SafetyAnalysis = await response.json();
      return data;
    } catch (err: any) {
      if (err.name === 'AbortError') {
        // Request was cancelled, don't set error
        return null;
      }
      setSafetyError(err instanceof Error ? err.message : "Failed to get safety data");
      return null;
    } finally {
      setSafetyLoading(false);
    }
  };

  const handleRouteRequest = async (destination: string) => {
    try {
      setRouteLoading(true);
      
      // For now, we'll just open the route planner
      // The actual route analysis will happen in the route planner page
      const params = new URLSearchParams({
        origin: address,
        destination: destination
      });
      
      // Use local safe-route interface on port 9006
      const url = `http://localhost:9006/route?${params.toString()}`;
      window.open(url, '_blank', 'width=1400,height=900');
    } catch (error) {
      console.error('Failed to open route planner:', error);
    } finally {
      setRouteLoading(false);
    }
  };

  useEffect(() => {
    extractAddressAndRooms()
      .then(({ address, numRooms, buildingName, rawAddress, sqFt, borough }) => {
        setAddress(address);
        setNumRooms(numRooms);
        setBuildingName(buildingName);
        setRawAddress(rawAddress);
        setSqFt(sqFt);
        setBorough(borough);
        getEnergyCost(address, numRooms, sqFt)
          .then(setCost)
          .catch((err: Error) => setError(err.message));
      })
      .catch((err: Error) =>
        setError(
          err instanceof Error ? err.message : "Failed to extract listing info"
        )
      );
  }, []);

  useEffect(() => {
    // Load safety data when we have a raw address
    // Use rawAddress for consistency in safety API
    const addressForSafety = rawAddress || address;
    
    // Check if either address or borough has changed
    const hasAddressChanged = addressForSafety && addressForSafety !== lastSafetyAddressRef.current;
    const hasBoroughChanged = borough !== lastSafetyBoroughRef.current;
    
    if (addressForSafety && (hasAddressChanged || hasBoroughChanged)) {
      // Reset states for new address/borough
      hasLoadedSafetyRef.current = false;
      lastSafetyAddressRef.current = addressForSafety;
      lastSafetyBoroughRef.current = borough;
      setSafetyData(null);
      setSafetyError("");
      
      // Add a small delay to ensure all data is loaded
      const timeoutId = setTimeout(() => {
        // Load new safety data
        getSafetyAnalysis(addressForSafety, borough)
          .then(data => {
            if (data) {
              setSafetyData(data);
            }
          })
          .catch(err => setSafetyError(err.message));
      }, 100);
      
      return () => clearTimeout(timeoutId);
    }
  }, [rawAddress, address, borough]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (safetyRequestRef.current) {
        safetyRequestRef.current.abort();
      }
    };
  }, []);

  return (
    <div className="w-80 min-h-96 max-h-[600px] overflow-y-auto p-4 bg-white shadow-lg border border-gray-200">
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3 mb-1">
          <img src={logo} alt="Where2Liv" className="h-10" />
          <div className="text-2xl font-bold h-10 text-center tracking-tight text-gray-800">
            Where2Liv
          </div>
        </div>
        <div className="border-b border-gray-200 mx-[-16px]" />
        <div className="bg-gray-50 rounded-lg text-xs px-3 py-2 text-gray-700 space-y-1">
          {buildingName && (
            <div className="flex items-center gap-1">
              <span className="text-gray-400">🏢</span>
              <span className="font-medium">{buildingName}</span>
            </div>
          )}
          <div className="flex items-center gap-1">
            <span className="text-gray-400">📍</span>
            {rawAddress || address || <span className="italic text-gray-400">Address will be detected automatically...</span>}
          </div>
          {borough && (
            <div className="flex items-center gap-1">
              <span className="text-gray-400">🗽</span>
              <span>{borough}</span>
            </div>
          )}
          <div className="flex items-center gap-1">
            <span className="text-gray-400">🏠</span>
            <span>{numRooms === 0 ? 'Studio' : `${numRooms} bedroom${numRooms > 1 ? 's' : ''}`}</span>
          </div>
          {sqFt && (
            <div className="flex items-center gap-1">
              <span className="text-gray-400">📐</span>
              <span>{sqFt.toLocaleString()} sq ft</span>
            </div>
          )}
        </div>
        <div className="mt-2">
          <div className="text-lg font-semibold text-gray-800 mb-1">Monthly Energy Estimate</div>
          {cost !== null ? (
            <div className="flex flex-col gap-1">
              <div className="text-3xl font-extrabold text-green-700">${cost}</div>
              <Tag efficiency={cost} />
            </div>
          ) : (
            <div className="text-sm opacity-80 mb-4 text-center animate-pulse text-gray-500">
              Calculating energy costs...
            </div>
          )}
        </div>
        <ul className="ml-2 list-disc list-inside mt-2 space-y-1 text-gray-700 text-sm">
          <li>Predicted monthly energy costs</li>
          <li>Based on building data and usage patterns</li>
          <li>Sustainability rating for this apartment</li>
        </ul>

        {/* Safety Analysis Sections */}
        <div className="border-t border-gray-200 pt-3 mt-3">
          <div className="text-lg font-semibold text-gray-800 mb-3">Area Analysis</div>
          
          {safetyData ? (
            <div className="space-y-4">
              {/* Personal Safety Section */}
              {safetyData.personal_safety && (
                <div className="border border-red-200 rounded-lg">
                  <div 
                    className="p-3 cursor-pointer flex items-center justify-between hover:bg-red-50 transition-colors"
                    onClick={() => setShowPersonalSafety(!showPersonalSafety)}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-red-600">🚨</span>
                      <span className="font-medium text-gray-800">Personal Safety</span>
                      {!showPersonalSafety && safetyData.personal_safety.available && (
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          safetyData.personal_safety.rating?.grade === 'A' ? 'bg-green-100 text-green-800' :
                          safetyData.personal_safety.rating?.grade === 'B' ? 'bg-yellow-100 text-yellow-800' :
                          safetyData.personal_safety.rating?.grade === 'C' ? 'bg-orange-100 text-orange-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          Grade {safetyData.personal_safety.rating?.grade}
                        </span>
                      )}
                    </div>
                    <span className="text-sm text-gray-500">
                      {showPersonalSafety ? '▼' : '▶'}
                    </span>
                  </div>
                  
                  {showPersonalSafety && safetyData.personal_safety.available && (
                    <div className="px-3 pb-3 space-y-3 border-t border-red-100">
                      {/* AI Insights for Personal Safety */}
                      {safetyData.personal_safety.ai_insights && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mt-3">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-red-600">🤖</span>
                            <span className="text-xs font-medium text-red-700">AI Crime Analysis</span>
                          </div>
                          <div 
                            className="text-sm text-gray-800 leading-relaxed whitespace-pre-line"
                            dangerouslySetInnerHTML={{ __html: safetyData.personal_safety.ai_insights.summary.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }}
                          />
                          <div className="text-xs text-red-600 mt-2 opacity-75">
                            Generated by {safetyData.personal_safety.ai_insights.generated_by}
                          </div>
                        </div>
                      )}
                      
                                             {safetyData.personal_safety.rating && safetyData.personal_safety.metrics && (
              <SafetyRating
                          grade={safetyData.personal_safety.rating.grade}
                          score={safetyData.personal_safety.rating.score}
                          description={safetyData.personal_safety.rating.description}
                          totalComplaints={safetyData.personal_safety.metrics.total_complaints || (safetyData.personal_safety.metrics as any).total_incidents || 0}
                          isLoading={false}
                        />
                       )}
                      
                                             {safetyData.personal_safety.complaint_breakdown && (
              <SafetyDetails
                          summary={safetyData.personal_safety.rating?.description || "Crime data analysis"}
                          complaintBreakdown={safetyData.personal_safety.complaint_breakdown}
                          recommendations={[]}
                          recentActivity={safetyData.personal_safety.recent_activity || {
                            recent_complaints: 0,
                            previous_period_complaints: 0,
                            trend: 'stable' as const,
                            days_analyzed: 90
                          }}
                          dataSources={safetyData.data_sources_used?.filter(source => source.includes('Police')) || []}
                          issueCards={safetyData.personal_safety.issue_cards || []}
                isExpanded={showSafetyDetails}
                onToggle={() => setShowSafetyDetails(!showSafetyDetails)}
              />
                       )}
                    </div>
                  )}
                </div>
              )}

              {/* Neighborhood Quality Section */}
              {safetyData.neighborhood_quality && (
                <div className="border border-blue-200 rounded-lg">
                  <div 
                    className="p-3 cursor-pointer flex items-center justify-between hover:bg-blue-50 transition-colors"
                    onClick={() => setShowNeighborhoodQuality(!showNeighborhoodQuality)}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-blue-600">🏘️</span>
                      <span className="font-medium text-gray-800">Neighborhood Quality</span>
                      {!showNeighborhoodQuality && safetyData.neighborhood_quality.available && (
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          safetyData.neighborhood_quality.rating?.grade === 'A' ? 'bg-green-100 text-green-800' :
                          safetyData.neighborhood_quality.rating?.grade === 'B' ? 'bg-yellow-100 text-yellow-800' :
                          safetyData.neighborhood_quality.rating?.grade === 'C' ? 'bg-orange-100 text-orange-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          Grade {safetyData.neighborhood_quality.rating?.grade}
                        </span>
                      )}
                    </div>
                    <span className="text-sm text-gray-500">
                      {showNeighborhoodQuality ? '▼' : '▶'}
                    </span>
                  </div>
                  
                  {showNeighborhoodQuality && safetyData.neighborhood_quality.available && (
                    <div className="px-3 pb-3 space-y-3 border-t border-blue-100">
                      {/* AI Insights for Neighborhood Quality */}
                      {safetyData.neighborhood_quality.ai_insights && (
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-3">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-blue-600">🤖</span>
                            <span className="text-xs font-medium text-blue-700">AI Quality Analysis</span>
                          </div>
                          <div 
                            className="text-sm text-gray-800 leading-relaxed whitespace-pre-line"
                            dangerouslySetInnerHTML={{ __html: safetyData.neighborhood_quality.ai_insights.summary.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }}
                          />
                          <div className="text-xs text-blue-600 mt-2 opacity-75">
                            Generated by {safetyData.neighborhood_quality.ai_insights.generated_by}
                          </div>
                        </div>
                      )}
                      
                                             {safetyData.neighborhood_quality.rating && safetyData.neighborhood_quality.metrics && (
                        <SafetyRating
                          grade={safetyData.neighborhood_quality.rating.grade}
                          score={safetyData.neighborhood_quality.rating.score}
                          description={safetyData.neighborhood_quality.rating.description}
                          totalComplaints={safetyData.neighborhood_quality.metrics.total_complaints || (safetyData.neighborhood_quality.metrics as any).total_incidents || 0}
                          isLoading={false}
                        />
                       )}
                      
                      {/* Add SafetyDetails for neighborhood quality to show issue cards */}
                      {safetyData.neighborhood_quality.complaint_breakdown && (
                        <SafetyDetails
                          summary={safetyData.neighborhood_quality.rating?.description || "Neighborhood quality analysis"}
                          complaintBreakdown={safetyData.neighborhood_quality.complaint_breakdown}
                          recommendations={[]}
                          recentActivity={safetyData.neighborhood_quality.recent_activity || {
                            recent_complaints: 0,
                            previous_period_complaints: 0,
                            trend: 'stable' as const,
                            days_analyzed: 90
                          }}
                          dataSources={safetyData.data_sources_used?.filter(source => source.includes('311')) || []}
                          issueCards={safetyData.neighborhood_quality.issue_cards || []}
                          isExpanded={showSafetyDetails}
                          onToggle={() => setShowSafetyDetails(!showSafetyDetails)}
                        />
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Data Sources Footer */}
              {safetyData.data_sources_used && (
                <div className="text-xs text-gray-500 mt-3">
                  <strong>Data Sources:</strong> {safetyData.data_sources_used.join(', ')}
                </div>
              )}
            </div>
          ) : safetyLoading ? (
            <div className="text-sm opacity-80 mb-4 text-center animate-pulse text-gray-500">
              Analyzing area safety and quality...
            </div>
          ) : safetyError ? (
            <div className="bg-yellow-500/10 border border-yellow-300 text-yellow-700 rounded-lg p-2 text-xs">
              {safetyError}
            </div>
          ) : (
            <div className="text-xs text-gray-500 italic">
              Safety and quality analysis will load automatically
            </div>
          )}
        </div>

        {/* Route Planning Section */}
        {address && (
          <RouteInput
            originAddress={address}
            onRouteRequest={handleRouteRequest}
            isLoading={routeLoading}
          />
        )}


        {error && (
          <div className="bg-red-500/10 border border-red-300 text-red-700 rounded-lg p-3 text-sm font-medium text-center mt-2">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
