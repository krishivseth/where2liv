export interface RouteSegment {
  start_location: {
    lat: number;
    lng: number;
  };
  end_location: {
    lat: number;
    lng: number;
  };
  duration: {
    text: string;
    value: number; // seconds
  };
  distance: {
    text: string;
    value: number; // meters
  };
  safety_score: number;
  safety_grade: string;
  neighborhood_info?: {
    zip_code?: string;
    borough?: string;
    complaint_count: number;
  };
}

export interface SafeRoute {
  route_id: string;
  summary: string;
  total_duration: {
    text: string;
    value: number;
  };
  total_distance: {
    text: string;
    value: number;
  };
  overall_safety_score: number;
  overall_safety_grade: string;
  safety_description: string;
  segments: RouteSegment[];
  polyline: string;
  route_type: 'safest' | 'balanced' | 'fastest';
  warnings?: string[];
}

export interface RouteAnalysisRequest {
  origin: string;
  destination: string;
  mode?: 'driving' | 'walking' | 'transit';
  alternatives?: boolean;
}

export interface RouteAnalysisResponse {
  origin_address: string;
  destination_address: string;
  routes: SafeRoute[];
  analysis_timestamp: string;
  total_routes_analyzed: number;
  recommendation: {
    recommended_route_id: string;
    reason: string;
  };
}

export interface MapLocation {
  lat: number;
  lng: number;
  address?: string;
} 