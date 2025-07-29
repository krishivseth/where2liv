import requests
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import googlemaps
import openai
import os
import time

logger = logging.getLogger(__name__)

class ReviewsAnalyzer:
    """Analyzes Google Reviews for apartment buildings using Places API and OpenAI"""
    
    def __init__(self, google_api_key: str, openai_api_key: str = None):
        self.gmaps = googlemaps.Client(key=google_api_key)
        self.google_api_key = google_api_key
        
        # Initialize OpenAI
        if openai_api_key:
            openai.api_key = openai_api_key
        else:
            # Try to get from environment
            openai.api_key = os.getenv('OPENAI_API_KEY')
        
        self.reviews_cache = {}
        self.cache_duration = 3600  # Cache for 1 hour
        
    def analyze_building_reviews(self, address: str, building_name: str = None) -> Dict[str, Any]:
        """
        Main method to analyze reviews for an apartment building
        
        Args:
            address: Building address
            building_name: Optional building name for more accurate search
            
        Returns:
            Dictionary with reviews analysis, summary, and pros/cons
        """
        try:
            logger.info(f"Analyzing reviews for: {address}")
            
            # Step 1: Find the building using Google Places API
            place_info = self._find_building_place(address, building_name)
            if not place_info:
                return self._create_no_reviews_response("Building not found in Google Places")
            
            # Step 2: Get reviews from Google Places
            reviews_data = self._get_place_reviews(place_info['place_id'])
            if not reviews_data or not reviews_data.get('reviews'):
                return self._create_no_reviews_response("No reviews found for this building")
            
            # Step 3: Filter recent reviews (last 90 days)
            recent_reviews = self._filter_recent_reviews(reviews_data['reviews'], days=90)
            if not recent_reviews:
                return self._create_no_reviews_response("No recent reviews found (last 90 days)")
            
            # Step 4: Analyze reviews with OpenAI
            analysis = self._analyze_reviews_with_ai(recent_reviews, address)
            
            # Step 5: Create comprehensive response
            return {
                'building_info': {
                    'name': place_info.get('name', 'Unknown Building'),
                    'address': place_info.get('formatted_address', address),
                    'place_id': place_info['place_id'],
                    'rating': place_info.get('rating'),
                    'total_reviews': place_info.get('user_ratings_total', 0)
                },
                'reviews_summary': {
                    'total_reviews_analyzed': len(recent_reviews),
                    'average_rating': self._calculate_average_rating(recent_reviews),
                    'rating_distribution': self._get_rating_distribution(recent_reviews),
                    'analysis_period': '90 days',
                    'last_updated': datetime.now().isoformat()
                },
                'ai_analysis': analysis,
                'recent_reviews': self._format_reviews_for_display(recent_reviews[:5]),  # Show top 5
                'data_source': 'Google Places API',
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing building reviews: {e}")
            return self._create_error_response(str(e))
    
    def _find_building_place(self, address: str, building_name: str = None) -> Optional[Dict]:
        """Find building using Google Places API"""
        try:
            # Create search query
            if building_name:
                query = f"{building_name} {address}"
            else:
                query = address
            
            # Search for places
            places_result = {}
            # self.gmaps.places(query=query, type='establishment')
            
            if not places_result.get('results'):
                # Try text search if places search fails
                text_search = self.gmaps.places(query=f"apartment building {address}")
                if not text_search.get('results'):
                    return None
                places_result = text_search
            
            # Get the most relevant result
            place = places_result['results'][0]
            
            # Get detailed place information
            place_details = self.gmaps.place(place['place_id'], fields=[
                'place_id', 'name', 'formatted_address', 'rating', 
                'user_ratings_total', 'reviews'
            ])
            
            return place_details['result']
            
        except Exception as e:
            logger.error(f"Error finding building place: {e}")
            return None
    
    def _get_place_reviews(self, place_id: str) -> Optional[Dict]:
        """Get reviews for a specific place"""
        try:
            # Check cache first
            cache_key = f"reviews_{place_id}"
            if cache_key in self.reviews_cache:
                cached_data, timestamp = self.reviews_cache[cache_key]
                if time.time() - timestamp < self.cache_duration:
                    logger.info("Using cached reviews data")
                    return cached_data
            
            # Get detailed place information with reviews
            place_details = self.gmaps.place(place_id, fields=[
                'reviews', 'rating', 'user_ratings_total'
            ])
            
            result = place_details.get('result', {})
            
            # Cache the result
            self.reviews_cache[cache_key] = (result, time.time())
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting place reviews: {e}")
            return None
    
    def _filter_recent_reviews(self, reviews: List[Dict], days: int = 90) -> List[Dict]:
        """Filter reviews to only include recent ones"""
        if not reviews:
            return []
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_reviews = []
        
        for review in reviews:
            # Google Places API provides 'time' as Unix timestamp
            review_date = datetime.fromtimestamp(review.get('time', 0))
            if review_date >= cutoff_date:
                recent_reviews.append(review)
        
        # Sort by date (most recent first)
        recent_reviews.sort(key=lambda x: x.get('time', 0), reverse=True)
        
        return recent_reviews
    
    def _analyze_reviews_with_ai(self, reviews: List[Dict], address: str) -> Dict[str, Any]:
        """Use OpenAI to analyze and summarize reviews"""
        try:
            if not openai.api_key:
                logger.warning("OpenAI API key not available, using basic analysis")
                return self._basic_reviews_analysis(reviews)
            
            # Prepare reviews text for AI analysis
            reviews_text = self._prepare_reviews_for_ai(reviews)
            
            # Create prompt for OpenAI
            prompt = f"""
            Analyze the following Google Reviews for an apartment building at {address}. 
            Provide a comprehensive analysis with the following structure:

            1. OVERALL_SUMMARY: A 2-3 sentence summary of the overall sentiment and key themes
            2. PROS: List of positive aspects mentioned by residents (bullet points)
            3. CONS: List of negative aspects mentioned by residents (bullet points)  
            4. KEY_THEMES: Main themes that come up repeatedly in reviews
            5. LIVING_EXPERIENCE: Summary of what it's like to live in this building
            6. RECOMMENDATIONS: Any recommendations for potential residents

            Reviews to analyze:
            {reviews_text}

            Respond in JSON format with the structure above.
            """
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert real estate analyst specializing in apartment building reviews. Provide detailed, balanced analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            # Parse AI response
            ai_content = response.choices[0].message.content
            
            try:
                # Try to parse as JSON
                analysis = json.loads(ai_content)
                return analysis
            except json.JSONDecodeError:
                # If JSON parsing fails, return structured response
                return self._parse_ai_response_text(ai_content)
                
        except Exception as e:
            logger.error(f"Error with OpenAI analysis: {e}")
            return self._basic_reviews_analysis(reviews)
    
    def _prepare_reviews_for_ai(self, reviews: List[Dict]) -> str:
        """Prepare reviews text for AI analysis"""
        reviews_text = ""
        
        for i, review in enumerate(reviews[:10], 1):  # Limit to 10 most recent
            rating = review.get('rating', 'N/A')
            text = review.get('text', '')
            author = review.get('author_name', 'Anonymous')
            date = datetime.fromtimestamp(review.get('time', 0)).strftime('%Y-%m-%d')
            
            reviews_text += f"\nReview {i}:\n"
            reviews_text += f"Rating: {rating}/5\n"
            reviews_text += f"Author: {author}\n"
            reviews_text += f"Date: {date}\n"
            reviews_text += f"Text: {text}\n"
            reviews_text += "-" * 50 + "\n"
        
        return reviews_text
    
    def _basic_reviews_analysis(self, reviews: List[Dict]) -> Dict[str, Any]:
        """Basic analysis when AI is not available"""
        if not reviews:
            return {}
        
        # Calculate basic metrics
        ratings = [review.get('rating', 0) for review in reviews]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        
        # Simple keyword analysis for pros/cons
        all_text = " ".join([review.get('text', '') for review in reviews]).lower()
        
        positive_keywords = ['good', 'great', 'excellent', 'nice', 'clean', 'quiet', 'friendly', 'convenient']
        negative_keywords = ['bad', 'terrible', 'awful', 'dirty', 'noisy', 'rude', 'problem', 'issue']
        
        pros = [keyword for keyword in positive_keywords if keyword in all_text]
        cons = [keyword for keyword in negative_keywords if keyword in all_text]
        
        return {
            'OVERALL_SUMMARY': f"Based on {len(reviews)} recent reviews with an average rating of {avg_rating:.1f}/5.",
            'PROS': pros,
            'CONS': cons,
            'KEY_THEMES': ['Basic analysis - AI analysis not available'],
            'LIVING_EXPERIENCE': f"Average rating suggests {'positive' if avg_rating >= 3.5 else 'mixed' if avg_rating >= 2.5 else 'negative'} resident experience.",
            'RECOMMENDATIONS': ['Consider reading individual reviews for detailed insights'],
            'analysis_method': 'basic_keywords'
        }
    
    def _parse_ai_response_text(self, ai_content: str) -> Dict[str, Any]:
        """Parse AI response if JSON parsing fails"""
        try:
            # Simple text parsing as fallback
            sections = {}
            current_section = None
            current_content = []
            
            for line in ai_content.split('\n'):
                line = line.strip()
                if any(keyword in line.upper() for keyword in ['OVERALL_SUMMARY', 'PROS', 'CONS', 'KEY_THEMES', 'LIVING_EXPERIENCE', 'RECOMMENDATIONS']):
                    if current_section:
                        sections[current_section] = current_content
                    current_section = line.split(':')[0].upper().strip()
                    current_content = [line.split(':', 1)[1].strip() if ':' in line else '']
                elif current_section and line:
                    current_content.append(line)
            
            if current_section:
                sections[current_section] = current_content
            
            return sections
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            return {'error': 'Failed to parse AI response'}
    
    def _calculate_average_rating(self, reviews: List[Dict]) -> float:
        """Calculate average rating from reviews"""
        if not reviews:
            return 0.0
        
        ratings = [review.get('rating', 0) for review in reviews]
        return sum(ratings) / len(ratings) if ratings else 0.0
    
    def _get_rating_distribution(self, reviews: List[Dict]) -> Dict[str, int]:
        """Get distribution of ratings"""
        distribution = {str(i): 0 for i in range(1, 6)}
        
        for review in reviews:
            rating = str(review.get('rating', 0))
            if rating in distribution:
                distribution[rating] += 1
        
        return distribution
    
    def _format_reviews_for_display(self, reviews: List[Dict]) -> List[Dict]:
        """Format reviews for frontend display"""
        formatted_reviews = []
        
        for review in reviews:
            formatted_reviews.append({
                'author': review.get('author_name', 'Anonymous'),
                'rating': review.get('rating'),
                'text': review.get('text', ''),
                'date': datetime.fromtimestamp(review.get('time', 0)).strftime('%Y-%m-%d'),
                'relative_time': review.get('relative_time_description', 'Unknown'),
                'author_url': review.get('author_url', '')
            })
        
        return formatted_reviews
    
    def _create_no_reviews_response(self, message: str) -> Dict[str, Any]:
        """Create response when no reviews are found"""
        return {
            'building_info': {'name': 'Unknown', 'address': 'Unknown'},
            'reviews_summary': {
                'total_reviews_analyzed': 0,
                'average_rating': 0,
                'rating_distribution': {},
                'analysis_period': '90 days'
            },
            'ai_analysis': {
                'OVERALL_SUMMARY': message,
                'PROS': [],
                'CONS': [],
                'KEY_THEMES': [],
                'LIVING_EXPERIENCE': 'No review data available',
                'RECOMMENDATIONS': ['Consider visiting the building in person', 'Ask for references from current residents']
            },
            'recent_reviews': [],
            'status': 'no_reviews',
            'message': message
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create response when an error occurs"""
        return {
            'building_info': {'name': 'Error', 'address': 'Error'},
            'reviews_summary': {'total_reviews_analyzed': 0},
            'ai_analysis': {
                'OVERALL_SUMMARY': f'Error analyzing reviews: {error_message}',
                'PROS': [],
                'CONS': [],
                'KEY_THEMES': [],
                'LIVING_EXPERIENCE': 'Analysis unavailable due to error',
                'RECOMMENDATIONS': ['Try again later', 'Check building address accuracy']
            },
            'recent_reviews': [],
            'status': 'error',
            'error': error_message
        } 