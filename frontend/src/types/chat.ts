export interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isLoading?: boolean;
  error?: string;
}

export interface PlaceReview {
  author: string;
  rating: number;
  text: string;
  time: string;
  authorUri?: string;
}

export interface PlaceInfo {
  placeId: string;
  displayName: string;
  formattedAddress: string;
  location: {
    lat: number;
    lng: number;
  };
  rating?: number;
  totalReviews?: number;
  businessStatus?: string;
  types?: string[];
}

export interface NearbyPlace extends PlaceInfo {
  distance?: number;
  reviews?: PlaceReview[];
}

export interface ChatQuery {
  query: string;
  address: string;
  buildingName?: string;
  coordinates?: {
    lat: number;
    lng: number;
  };
}

export interface ChatResponse {
  success: boolean;
  response: string;
  data?: {
    places?: NearbyPlace[];
    reviews?: PlaceReview[];
    placeInfo?: PlaceInfo;
  };
  error?: string;
  queryType?: 'reviews' | 'nearby' | 'general';
}

export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  isOpen: boolean;
}

export type ChatQueryType = 'reviews' | 'nearby' | 'general' | 'unknown';

export interface PlaceSearchRequest {
  query: string;
  location?: {
    lat: number;
    lng: number;
  };
  radius?: number;
  type?: string;
  maxResults?: number;
}

export interface ReviewAnalysis {
  buildingInfo: {
    name: string;
    address: string;
    placeId: string;
    rating?: number;
    totalReviews: number;
  };
  reviewsSummary: {
    totalReviewsAnalyzed: number;
    averageRating: number;
    ratingDistribution: Record<string, number>;
    analysisPeriod: string;
    lastUpdated: string;
  };
  aiAnalysis: {
    summary: string;
    pros: string[];
    cons: string[];
    recommendations: string[];
  };
  recentReviews: PlaceReview[];
  dataSource: string;
  analysisTimestamp: string;
} 