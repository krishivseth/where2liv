import { type JSX } from "react";

interface ComplaintCategory {
  count: number;
  percentage: number;
  description: string;
  top_complaints: Record<string, number>;
}

interface IssueCard {
  type: string;
  title: string;
  count: number;
  severity: 'low' | 'medium' | 'high' | 'info';
  description: string;
  tip: string;
  action: string;
}

interface SafetyDetailsProps {
  summary: string;
  complaintBreakdown: Record<string, ComplaintCategory>;
  recommendations: string[];
  recentActivity: {
    recent_complaints: number;
    trend: string;
    days_analyzed: number;
  };
  dataSources?: string[];
  issueCards?: IssueCard[];
  isExpanded: boolean;
  onToggle: () => void;
}

export const SafetyDetails = ({
  summary,
  complaintBreakdown,
  recommendations,
  recentActivity,
  dataSources,
  issueCards,
  isExpanded,
  onToggle
}: SafetyDetailsProps): JSX.Element => {
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing': return '📈';
      case 'decreasing': return '📉';
      case 'stable': return '➡️';
      default: return '➡️';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'increasing': return 'text-red-600';
      case 'decreasing': return 'text-green-600';
      case 'stable': return 'text-gray-600';
      default: return 'text-gray-600';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'HIGH_CONCERN': return '🚨';
      case 'MEDIUM_CONCERN': return '⚠️';
      case 'LOW_CONCERN': return '🟡';
      case 'INFRASTRUCTURE': return '🔧';
      default: return '📊';
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'HIGH_CONCERN': return 'border-red-200 bg-red-50';
      case 'MEDIUM_CONCERN': return 'border-orange-200 bg-orange-50';
      case 'LOW_CONCERN': return 'border-yellow-200 bg-yellow-50';
      case 'INFRASTRUCTURE': return 'border-blue-200 bg-blue-50';
      default: return 'border-gray-200 bg-gray-50';
    }
  };

  const getIssueCardColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'border-red-200 bg-red-50';
      case 'medium': return 'border-orange-200 bg-orange-50';
      case 'low': return 'border-yellow-200 bg-yellow-50';
      case 'info': return 'border-blue-200 bg-blue-50';
      default: return 'border-gray-200 bg-gray-50';
    }
  };

  return (
    <div className="space-y-3">
      <button
        onClick={onToggle}
        className="w-full text-left bg-white border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors duration-150"
      >
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">Safety Details</span>
          <span className="text-gray-400 text-sm">
            {isExpanded ? '▼' : '▶'}
          </span>
        </div>
        <p className="text-xs text-gray-600 mt-1 line-clamp-2">
          {summary}
        </p>
      </button>

      {isExpanded && (
        <div className="space-y-4 bg-white border border-gray-200 rounded-lg p-4">
          {/* Summary */}
          <div>
            <h4 className="text-sm font-semibold text-gray-800 mb-2">Area Summary</h4>
            <p className="text-xs text-gray-700 leading-relaxed">{summary}</p>
          </div>

          {/* Issue Cards - NEW */}
          {issueCards && issueCards.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Specific Issues & Tips</h4>
              <div className="space-y-2">
                {issueCards.map((card, index) => (
                  <div 
                    key={index} 
                    className={`border rounded-lg p-3 ${getIssueCardColor(card.severity)}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-800">{card.title}</span>
                        <span className="text-xs px-2 py-1 rounded-full bg-white border border-gray-300 text-gray-600">
                          {card.count}
                        </span>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                        card.severity === 'high' ? 'bg-red-100 text-red-700' :
                        card.severity === 'medium' ? 'bg-orange-100 text-orange-700' :
                        card.severity === 'low' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-blue-100 text-blue-700'
                      }`}>
                        {card.severity.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mb-2">{card.description}</p>
                    <div className="space-y-1">
                      <div className="flex items-start gap-1">
                        <span className="text-xs text-green-600 mt-0.5">💡</span>
                        <span className="text-xs text-gray-600 font-medium">TIP:</span>
                        <span className="text-xs text-gray-600">{card.tip}</span>
                      </div>
                      <div className="flex items-start gap-1">
                        <span className="text-xs text-blue-600 mt-0.5">🔧</span>
                        <span className="text-xs text-gray-600 font-medium">ACTION:</span>
                        <span className="text-xs text-gray-600">{card.action}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Data Sources */}
          {dataSources && dataSources.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Data Sources</h4>
              <div className="space-y-1">
                {dataSources.map((source, index) => (
                  <div key={index} className="flex items-center gap-2 text-xs">
                    <span className="text-blue-500">📊</span>
                    <span className="text-gray-700">{source}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recent Activity */}
          <div>
            <h4 className="text-sm font-semibold text-gray-800 mb-2">Recent Activity</h4>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-lg">{getTrendIcon(recentActivity.trend)}</span>
              <span className={`font-medium ${getTrendColor(recentActivity.trend)}`}>
                {recentActivity.recent_complaints} complaints in last {recentActivity.days_analyzed} days
              </span>
              <span className="text-gray-500">
                ({recentActivity.trend} trend)
              </span>
            </div>
          </div>

          {/* Complaint Breakdown */}
          {Object.keys(complaintBreakdown).length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Complaint Categories</h4>
              <div className="space-y-2">
                {Object.entries(complaintBreakdown).map(([category, data]) => (
                  <div 
                    key={category} 
                    className={`border rounded-lg p-2 ${getCategoryColor(category)}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1">
                        <span className="text-sm">{getCategoryIcon(category)}</span>
                        <span className="text-xs font-medium text-gray-800">
                          {category.replace('_', ' ').toLowerCase().replace(/^./, str => str.toUpperCase())}
                        </span>
                      </div>
                      <span className="text-xs font-semibold text-gray-700">
                        {data.count} ({data.percentage.toFixed(0)}%)
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mb-1">{data.description}</p>
                    {Object.keys(data.top_complaints).length > 0 && (
                      <div className="text-xs text-gray-500">
                        Top: {Object.entries(data.top_complaints)
                          .slice(0, 2)
                          .map(([complaint, count]) => `${complaint} (${count})`)
                          .join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Safety Recommendations</h4>
              <ul className="space-y-1">
                {recommendations.slice(0, 3).map((rec, index) => (
                  <li key={index} className="flex items-start gap-2 text-xs text-gray-700">
                    <span className="text-blue-500 mt-0.5">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}; 