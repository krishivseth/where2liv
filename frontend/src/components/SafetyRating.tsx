import { type JSX } from "react";

interface SafetyRatingProps {
  grade: string;
  score: number;
  description: string;
  totalComplaints: number;
  isLoading?: boolean;
}

export const SafetyRating = ({ 
  grade, 
  score, 
  description, 
  totalComplaints,
  isLoading = false 
}: SafetyRatingProps): JSX.Element => {
  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded mb-2"></div>
        <div className="h-4 bg-gray-200 rounded w-3/4"></div>
      </div>
    );
  }

  const getGradeStyles = (grade: string) => {
    switch (grade) {
      case 'A':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'B':
        return 'bg-lime-100 text-lime-800 border-lime-200';
      case 'C':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'D':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'F':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getScoreBarColor = (score: number) => {
    if (score >= 4.5) return 'bg-green-500';
    if (score >= 3.5) return 'bg-lime-500';
    if (score >= 2.5) return 'bg-yellow-500';
    if (score >= 1.5) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getEmoji = (grade: string) => {
    switch (grade) {
      case 'A': return '🟢';
      case 'B': return '🟡';
      case 'C': return '🟠';
      case 'D': return '🔴';
      case 'F': return '⚫';
      default: return '⚪';
    }
  };

  return (
    <div className="bg-gray-50 rounded-lg p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">{getEmoji(grade)}</span>
          <span className="text-sm font-medium text-gray-700">Safety Rating</span>
        </div>
        <div className={`px-2 py-1 rounded-md border text-sm font-bold ${getGradeStyles(grade)}`}>
          Grade {grade}
        </div>
      </div>
      
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Score</span>
          <span className="font-semibold text-gray-800">{score.toFixed(1)}/5.0</span>
        </div>
        
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all duration-300 ${getScoreBarColor(score)}`}
            style={{ width: `${(score / 5) * 100}%` }}
          ></div>
        </div>
        
        <div className="text-xs text-gray-600">
          <span className="font-medium">{description}</span>
          {totalComplaints > 0 && (
            <span className="block mt-1">
              Based on {totalComplaints.toLocaleString()} reported incidents
            </span>
          )}
        </div>
      </div>
    </div>
  );
}; 