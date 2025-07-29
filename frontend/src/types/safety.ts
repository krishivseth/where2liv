export interface SafetyRating {
  score: number;
  grade: string;
  description: string;
  color: string;
}

export interface SafetyMetrics {
  total_complaints: number;
  weighted_safety_score: number;
  complaints_per_day: number;
  high_concern_ratio: number;
  category_distribution: Record<string, number>;
}

export interface ComplaintCategory {
  count: number;
  percentage: number;
  description: string;
  top_complaints: Record<string, number>;
}

export interface RecentActivity {
  recent_complaints: number;
  previous_period_complaints: number;
  trend: 'increasing' | 'decreasing' | 'stable';
  days_analyzed: number;
}

export interface IssueCard {
  type: string;
  title: string;
  count: number;
  severity: 'low' | 'medium' | 'high' | 'info';
  description: string;
  tip: string;
  action: string;
}

export interface AreaInfo {
  zip_code?: string;
  borough?: string;
  address?: string;
  radius_miles: number;
  data_points: number;
}

export interface DataSourceBreakdown {
  count: number;
  percentage: number;
  categories: Record<string, number>;
  description: string;
}

export interface SafetySection {
  available: boolean;
  message?: string;
  rating?: SafetyRating;
  metrics?: SafetyMetrics;
  complaint_breakdown?: Record<string, ComplaintCategory>;
  recent_activity?: RecentActivity;
  issue_cards?: IssueCard[];
  ai_insights?: {
    summary: string;
    generated_by: string;
    timestamp: string;
  };
}

export interface SafetyAnalysis {
  area_info: {
    zip_code: string | null;
    borough: string | null;
    address: string | null;
    latitude: number | null;
    longitude: number | null;
    radius_miles: number;
    data_points: number;
  };
  personal_safety: SafetySection;
  neighborhood_quality: SafetySection;
  data_source_breakdown?: Record<string, DataSourceBreakdown>;
  data_sources_used?: string[];
  
  // Legacy fields for backward compatibility (optional)
  safety_rating?: SafetyRating;
  safety_metrics?: SafetyMetrics;
  safety_summary?: string;
  complaint_breakdown?: Record<string, ComplaintCategory>;
  recent_activity?: RecentActivity;
  recommendations?: string[];
  ai_insights?: {
    summary: string;
    generated_by: string;
    timestamp: string;
  };
  llm_summary?: string;
  llm_recommendations?: string[];
}

export interface SafetyApiResponse extends SafetyAnalysis {}

export interface BoroughComparison {
  [borough: string]: {
    safety_score: number;
    grade: string;
    total_complaints: number;
    high_concern_ratio: number;
  };
} 