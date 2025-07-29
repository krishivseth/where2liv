import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ReviewsAnalysisTool:
    """Tool for analyzing Google Reviews of apartment buildings"""
    
    def __init__(self, reviews_analyzer):
        """Initialize the reviews analysis tool"""
        self.reviews_analyzer = reviews_analyzer
        self.available = reviews_analyzer is not None
        
    def get_description(self) -> str:
        """Get tool description"""
        return "Analyzes Google Reviews for apartment buildings using Google Places API and OpenAI"
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Get the schema for tool parameters"""
        return {
            "type": "object",
            "properties": {
                "address": {
                    "type": "string",
                    "description": "The address of the apartment building"
                },
                "building_name": {
                    "type": "string",
                    "description": "Optional building name for more accurate search",
                    "optional": True
                }
            },
            "required": ["address"]
        }
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the reviews analysis tool"""
        try:
            if not self.available:
                return {
                    'success': False,
                    'error': 'Reviews analyzer not available',
                    'tool': 'reviews_analysis'
                }
            
            # Validate parameters
            if 'address' not in parameters:
                return {
                    'success': False,
                    'error': 'Address parameter is required',
                    'tool': 'reviews_analysis'
                }
            
            address = parameters['address']
            building_name = parameters.get('building_name', None)
            
            logger.info(f"Analyzing reviews for building at: {address}")
            
            # Get reviews analysis
            reviews_result = self.reviews_analyzer.analyze_building_reviews(
                address=address,
                building_name=building_name
            )
            
            # Check if analysis was successful
            if reviews_result.get('status') == 'error':
                return {
                    'success': False,
                    'error': reviews_result.get('error', 'Unknown error in reviews analysis'),
                    'tool': 'reviews_analysis',
                    'details': reviews_result
                }
            
            # Format the result for the agent
            formatted_result = {
                'success': True,
                'tool': 'reviews_analysis',
                'data': {
                    'building_info': reviews_result.get('building_info', {}),
                    'reviews_summary': reviews_result.get('reviews_summary', {}),
                    'ai_analysis': reviews_result.get('ai_analysis', {}),
                    'recent_reviews': reviews_result.get('recent_reviews', []),
                    'data_source': reviews_result.get('data_source', 'Google Places API'),
                    'analysis_timestamp': reviews_result.get('analysis_timestamp', datetime.now().isoformat())
                },
                'metadata': {
                    'address_searched': address,
                    'building_name': building_name,
                    'total_reviews_analyzed': reviews_result.get('reviews_summary', {}).get('total_reviews_analyzed', 0),
                    'average_rating': reviews_result.get('reviews_summary', {}).get('average_rating', 0),
                    'analysis_method': 'Google Places API + OpenAI' if reviews_result.get('ai_analysis', {}).get('analysis_method') != 'basic_keywords' else 'Google Places API + Basic Analysis'
                }
            }
            
            # Add interpretation for agent usage
            ai_analysis = reviews_result.get('ai_analysis', {})
            if ai_analysis:
                formatted_result['interpretation'] = {
                    'overall_sentiment': self._interpret_sentiment(ai_analysis.get('OVERALL_SUMMARY', '')),
                    'key_positives': ai_analysis.get('PROS', []),
                    'key_negatives': ai_analysis.get('CONS', []),
                    'living_experience': ai_analysis.get('LIVING_EXPERIENCE', ''),
                    'recommendation': self._generate_recommendation(reviews_result),
                    'should_visit': self._should_visit_recommendation(reviews_result)
                }
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"Reviews analysis tool execution failed: {e}")
            return {
                'success': False,
                'error': f'Reviews analysis failed: {str(e)}',
                'tool': 'reviews_analysis'
            }
    
    def _interpret_sentiment(self, summary: str) -> str:
        """Interpret overall sentiment from summary"""
        if not summary:
            return 'neutral'
        
        summary_lower = summary.lower()
        
        # Positive indicators
        positive_words = ['good', 'great', 'excellent', 'positive', 'satisfied', 'happy', 'recommend']
        negative_words = ['bad', 'terrible', 'awful', 'negative', 'dissatisfied', 'unhappy', 'avoid']
        
        positive_count = sum(1 for word in positive_words if word in summary_lower)
        negative_count = sum(1 for word in negative_words if word in summary_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'mixed'
    
    def _generate_recommendation(self, reviews_result: Dict[str, Any]) -> str:
        """Generate a recommendation based on reviews analysis"""
        try:
            reviews_summary = reviews_result.get('reviews_summary', {})
            ai_analysis = reviews_result.get('ai_analysis', {})
            
            total_reviews = reviews_summary.get('total_reviews_analyzed', 0)
            avg_rating = reviews_summary.get('average_rating', 0)
            
            if total_reviews == 0:
                return "No recent reviews available - consider visiting the building and asking current residents for feedback"
            
            if avg_rating >= 4.0:
                return "Highly recommended based on excellent recent reviews"
            elif avg_rating >= 3.5:
                return "Generally positive reviews suggest this is a good choice"
            elif avg_rating >= 3.0:
                return "Mixed reviews - consider the specific pros and cons carefully"
            elif avg_rating >= 2.0:
                return "Caution advised - significant issues mentioned in reviews"
            else:
                return "Not recommended based on poor recent reviews"
                
        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return "Unable to generate recommendation due to analysis error"
    
    def _should_visit_recommendation(self, reviews_result: Dict[str, Any]) -> bool:
        """Determine if an in-person visit is recommended"""
        try:
            reviews_summary = reviews_result.get('reviews_summary', {})
            avg_rating = reviews_summary.get('average_rating', 0)
            total_reviews = reviews_summary.get('total_reviews_analyzed', 0)
            
            # Always recommend visiting if no reviews or low rating
            if total_reviews == 0 or avg_rating < 3.0:
                return True
            
            # For mixed reviews, suggest visiting
            if 2.5 <= avg_rating < 3.5:
                return True
            
            # For good reviews, visiting is still recommended but less urgent
            return False
            
        except Exception as e:
            logger.error(f"Error determining visit recommendation: {e}")
            return True  # Default to recommending a visit
    
    def get_help(self) -> Dict[str, Any]:
        """Get help information for this tool"""
        return {
            'tool_name': 'reviews_analysis',
            'description': self.get_description(),
            'parameters': self.get_parameters_schema(),
            'example_usage': {
                'address': '123 Main St, Queens, NY',
                'building_name': 'Luxury Apartments'
            },
            'output_format': {
                'building_info': 'Google Places information about the building',
                'reviews_summary': 'Statistical summary of recent reviews',
                'ai_analysis': 'AI-generated analysis with pros/cons',
                'recent_reviews': 'List of recent individual reviews',
                'interpretation': 'Agent-friendly interpretation of the analysis'
            },
            'availability': self.available,
            'data_source': 'Google Places API',
            'analysis_method': 'OpenAI GPT-3.5 for review analysis'
        } 