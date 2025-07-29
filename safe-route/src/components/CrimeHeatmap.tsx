'use client';

import { useEffect, useState } from 'react';
import { useMap } from 'react-leaflet';
import axios from 'axios';
import L from 'leaflet';
import 'leaflet.heat';

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

export default function CrimeHeatmap() {
  const map = useMap();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [crimeCount, setCrimeCount] = useState(0);

  // Function to calculate radius based on zoom level
  const getRadius = (zoom: number) => {
    // Scale radius with zoom to maintain physical size on map
    return 2 * Math.pow(2, zoom - 12);
  };

  useEffect(() => {
    const fetchCrimeData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await axios.get(
          'https://data.sfgov.org/resource/wg3w-h783.json',
          {
            params: {
              $where: "latitude IS NOT NULL AND longitude IS NOT NULL",
              $limit: 10000 // Limit to prevent overwhelming the API
            }
          }
        );

        const crimeData: CrimeData[] = response.data;
        setCrimeCount(crimeData.length);
        
        const heatPoints = crimeData.map(crime => {
          let intensity = 0.6;
          const crimeType = (crime.incident_category || '').toLowerCase();
          const crimeDesc = (crime.incident_description || '').toLowerCase();
          
          if (crimeType.includes('assault') || crimeType.includes('robbery')) {
            intensity = 1.0;
          } else if (crimeType.includes('burglary') || crimeType.includes('theft') || crimeType.includes('larceny')) {
            intensity = 0.8;
          } else if (crimeType.includes('arson')) {
            intensity = 0.9;
          } else if (crimeType.includes('fraud')) {
            intensity = 0.6;
          } else if (crimeType.includes('vehicle') || crimeType.includes('auto')) {
            intensity = 0.7;
          }
          
          return [
            parseFloat(crime.latitude),
            parseFloat(crime.longitude),
            intensity
          ] as [number, number, number];
        });

        // Create initial heatmap layer
        const initialHeatLayer = (L as any).heatLayer(heatPoints, {
          radius: getRadius(map.getZoom()),
          blur: 2,
          maxZoom: 18,
          max: 1.0,
          gradient: {
            0.2: 'rgba(44, 123, 182, 0.3)',
            0.4: 'rgba(0, 166, 202, 0.4)',
            0.6: 'rgba(127, 188, 65, 0.5)',
            0.8: 'rgba(244, 165, 130, 0.6)',
            1.0: 'rgba(215, 25, 28, 0.7)'
          },
          minOpacity: 0.2,
          pane: 'overlayPane' // Ensure heatmap is always on top of base map
        }).addTo(map);

        // Update heatmap on zoom
        const updateHeatmap = () => {
          if (initialHeatLayer) {
            initialHeatLayer.setOptions({
              radius: getRadius(map.getZoom()),
              blur: 2
            });
            initialHeatLayer.redraw(); // Force redraw to ensure visibility
          }
        };

        map.on('zoomend', updateHeatmap);
        map.on('moveend', updateHeatmap); // Update on pan as well

        return () => {
          map.off('zoomend', updateHeatmap);
          map.off('moveend', updateHeatmap);
          if (initialHeatLayer) {
            map.removeLayer(initialHeatLayer);
          }
        };
      } catch (err) {
        console.error('Error fetching crime data:', err);
        setError('Failed to load SF crime data. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchCrimeData();
  }, [map]);

  return (
    <>
      {isLoading && (
        <div className="absolute top-4 left-4 z-[1000] bg-white/90 backdrop-blur-sm p-4 rounded-lg shadow-lg">
          <p className="text-sm">Loading SF crime data...</p>
        </div>
      )}
      {error && (
        <div className="absolute top-4 left-4 z-[1000] bg-white/90 backdrop-blur-sm p-4 rounded-lg shadow-lg">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}
      <div className="absolute top-20 right-4 z-[1000] bg-white/95 backdrop-blur-sm p-4 rounded border minimal-border minimal-shadow">
        <h3 className="text-sm font-semibold mb-2 text-foreground">Crime Density</h3>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-4 h-4 bg-[rgba(44,123,182,0.3)] rounded"></div>
          <span className="text-xs text-muted-foreground">Low</span>
        </div>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-4 h-4 bg-[rgba(0,166,202,0.4)] rounded"></div>
          <span className="text-xs text-muted-foreground">Medium-Low</span>
        </div>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-4 h-4 bg-[rgba(127,188,65,0.5)] rounded"></div>
          <span className="text-xs text-muted-foreground">Medium</span>
        </div>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-4 h-4 bg-[rgba(244,165,130,0.6)] rounded"></div>
          <span className="text-xs text-muted-foreground">Medium-High</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-[rgba(215,25,28,0.7)] rounded"></div>
          <span className="text-xs text-muted-foreground">High</span>
        </div>
        <div className="mt-2 pt-2 border-t minimal-border">
          <p className="text-xs text-muted-foreground">Showing {crimeCount} recent SF incidents</p>
        </div>
      </div>
    </>
  );
} 