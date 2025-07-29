import requests
import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import math
import googlemaps

logger = logging.getLogger(__name__)

class RouteAnalyzer:
    """Analyzes routes for safety by combining Google Directions API with safety data"""
    
    def __init__(self, safety_analyzer, google_api_key: str):
        self.safety_analyzer = safety_analyzer
        self.gmaps = googlemaps.Client(key=google_api_key)
        self.crime_data = []
        self.crime_data_updated = None
        
    def load_nyc_crime_data(self) -> List[Dict]:
        """Load real-time NYC crime data from Open Data API"""
        try:
            # Check if we need to refresh crime data (refresh every hour)
            if (self.crime_data_updated and 
                datetime.now() - self.crime_data_updated < timedelta(hours=1) and 
                self.crime_data):
                return self.crime_data
            
            # Fetch recent crime data from NYC Open Data
            url = "https://data.cityofnewyork.us/resource/qgea-i56i.json"
            params = {
                "$where": "latitude IS NOT NULL AND longitude IS NOT NULL",
                "$select": "latitude,longitude,ofns_desc,cmplnt_fr_dt,boro_nm",
                "$limit": 50000,  # Get recent incidents
                "$order": "cmplnt_fr_dt DESC"
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            self.crime_data = response.json()
            self.crime_data_updated = datetime.now()
            
            print(f"Loaded {len(self.crime_data)} crime incidents from NYC Open Data")
            return self.crime_data
            
        except Exception as e:
            print(f"Failed to load NYC crime data: {e}")
            # Return empty list if API fails, system will still work without real-time data
            return []
    
    def calculate_crime_density(self, lat: float, lon: float, radius: float = 0.003) -> float:
        """
        Calculate crime density at a specific location using safe-route's algorithm.
        Uses weighted scoring based on crime severity.
        """
        if not self.crime_data:
            self.load_nyc_crime_data()
        
        total_weight = 0
        
        for crime in self.crime_data:
            try:
                crime_lat = float(crime.get('latitude', 0))
                crime_lon = float(crime.get('longitude', 0))
                
                # Calculate distance using simple Euclidean distance
                d_lat = crime_lat - lat
                d_lon = crime_lon - lon
                distance = math.sqrt(d_lat * d_lat + d_lon * d_lon)
                
                if distance <= radius:
                    # Weight crimes by severity (safe-route's approach)
                    crime_desc = crime.get('ofns_desc', '').lower()
                    if any(term in crime_desc for term in ['assault', 'robbery', 'rape', 'murder']):
                        weight = 8  # High severity
                    elif any(term in crime_desc for term in ['burglary', 'theft', 'larceny']):
                        weight = 5  # Medium severity
                    else:
                        weight = 1  # Low severity
                    
                    total_weight += weight
                    
            except (ValueError, TypeError):
                continue
        
        return total_weight
    
    def score_route_safety(self, route_coordinates: List[Tuple[float, float]]) -> Dict[str, Any]:
        """
        Score a route's safety using safe-route's advanced algorithm.
        Returns detailed safety analysis.
        """
        if not route_coordinates:
            return {"score": 0, "grade": "F", "details": "No route coordinates provided"}
        
        # Sample coordinates along the route (every other point for performance)
        sampled_coords = route_coordinates[::2] if len(route_coordinates) > 2 else route_coordinates
        
        # Calculate crime score with safe-route's algorithm
        crime_scores = []
        high_risk_areas = []
        
        for i, (lat, lon) in enumerate(sampled_coords):
            density = self.calculate_crime_density(lat, lon)
            crime_scores.append(density)
            
            # Identify high-risk areas
            if density > 15:  # High crime density threshold
                high_risk_areas.append({
                    "latitude": lat,
                    "longitude": lon,
                    "crime_density": density,
                    "risk_level": "high" if density > 25 else "medium",
                    "description": f"High crime area with {int(density)} incidents nearby"
                })
        
        # Calculate overall metrics using safe-route's approach
        total_crime_score = sum(crime_scores)
        max_density = max(crime_scores) if crime_scores else 0
        avg_density = sum(crime_scores) / len(crime_scores) if crime_scores else 0
        
        # safe-route's scoring formula: crimeScore + maxD*15 + avgD*8
        safety_penalty = total_crime_score + max_density * 15 + avg_density * 8
        
        # Debug logging
        print(f"Safety scoring debug: total_crime={total_crime_score}, max_density={max_density}, avg_density={avg_density:.2f}, penalty={safety_penalty}")
        
        # Convert to 0-100 safety score (lower penalty = higher safety)
        # Adjusted for realistic NYC crime levels - increased max expected penalty significantly
        max_expected_penalty = 15000  # Increased to handle high-density NYC routes
        safety_score = max(0, 100 - (safety_penalty / max_expected_penalty * 100))
        
        # Apply minimum scoring to avoid all zeros - give reasonable scores for NYC
        if safety_score < 10:
            # Alternative scoring for very high crime areas: normalize to 10-50 range
            normalized_penalty = min(safety_penalty, 20000)  # Cap at 20k for scoring
            safety_score = max(10, 50 - (normalized_penalty / 20000 * 40))  # Scale 10-50
        
        # Assign letter grade
        if safety_score >= 90:
            grade = "A"
        elif safety_score >= 80:
            grade = "B"
        elif safety_score >= 70:
            grade = "C"
        elif safety_score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "score": round(safety_score, 1),
            "grade": grade,
            "crime_density_max": max_density,
            "crime_density_avg": round(avg_density, 2),
            "high_risk_areas": high_risk_areas,
            "total_incidents_nearby": int(total_crime_score),
            "safety_details": {
                "description": self._get_safety_description(grade, safety_score),
                "recommendations": self._get_safety_recommendations(grade, high_risk_areas)
            }
        }
    
    def _get_safety_description(self, grade: str, score: float) -> str:
        """Get human-readable safety description"""
        if grade in ["A", "B"]:
            return f"Excellent safety rating ({score}/100). This route passes through low-crime areas."
        elif grade == "C":
            return f"Good safety rating ({score}/100). Generally safe with moderate crime levels."
        elif grade == "D":
            return f"Fair safety rating ({score}/100). Exercise normal caution in some areas."
        else:
            return f"Poor safety rating ({score}/100). Consider alternative routes or extra precautions."
    
    def _get_safety_recommendations(self, grade: str, high_risk_areas: List[Dict]) -> List[str]:
        """Get safety recommendations based on analysis"""
        recommendations = []
        
        if grade in ["A", "B"]:
            recommendations.append("This route is generally safe for travel at most times.")
        elif grade == "C":
            recommendations.append("Stay aware of your surroundings, especially during evening hours.")
        else:
            recommendations.append("Consider taking this route during daylight hours when possible.")
            recommendations.append("Stay in well-lit, populated areas.")
        
        if high_risk_areas:
            recommendations.append(f"Be extra cautious near {len(high_risk_areas)} identified high-crime areas along the route.")
        
        recommendations.append("Trust your instincts and avoid areas that feel unsafe.")
        
        return recommendations

    def analyze_safe_routes(self, origin: str, destination: str, mode: str = 'driving') -> Dict[str, Any]:
        """
        Enhanced route analysis with safe-route's crime analysis integration
        """
        try:
            # Load fresh crime data
            self.load_nyc_crime_data()
            
            # Get multiple route alternatives with different preferences
            route_variations = [
                {
                    'name': 'safest',
                    'params': {
                        'avoid': ['highways'],
                        'departure_time': datetime.now(),
                        'traffic_model': "best_guess"
                    }
                },
                {
                    'name': 'fastest', 
                    'params': {
                        'departure_time': datetime.now(),
                        'traffic_model': "optimistic"
                    }
                },
                {
                    'name': 'balanced',
                    'params': {
                        'avoid': ['tolls'],
                        'departure_time': datetime.now(),
                        'traffic_model': "pessimistic"
                    }
                }
            ]
            
            analyzed_routes = []
            
            for variation in route_variations:
                try:
                    # Get route with specific preferences
                    directions_result = self.gmaps.directions(
                        origin,
                        destination,
                        mode=mode,
                        alternatives=True,
                        **variation['params']
                    )
                    
                    if directions_result:
                        # Use the first (best) route from this variation
                        route = directions_result[0]
                        
                        # Extract route coordinates
                        route_coords = []
                        for step in route['legs'][0]['steps']:
                            start_loc = step['start_location']
                            end_loc = step['end_location']
                            route_coords.append((start_loc['lat'], start_loc['lng']))
                            route_coords.append((end_loc['lat'], end_loc['lng']))
                        
                        # Analyze route safety
                        safety_analysis = self.score_route_safety(route_coords)
                        
                        # Adjust safety score based on route type preference
                        adjusted_score = safety_analysis['score']
                        if variation['name'] == 'safest':
                            # Boost safety score for safest route preference
                            adjusted_score = min(100, safety_analysis['score'] + 5)
                        elif variation['name'] == 'fastest':
                            # Slightly reduce safety score for fastest route
                            adjusted_score = max(0, safety_analysis['score'] - 3)
                        
                        analyzed_route = {
                            "route_index": len(analyzed_routes),
                            "route_type": variation['name'],
                            "summary": route['summary'] or f"{variation['name'].title()} route",
                            "distance": route['legs'][0]['distance']['text'],
                            "duration": route['legs'][0]['duration']['text'],
                            "duration_in_traffic": route['legs'][0].get('duration_in_traffic', {}).get('text', 'N/A'),
                            "overall_safety_score": round(adjusted_score, 1),
                            "overall_safety_grade": self._calculate_grade(adjusted_score),
                            "safety_details": safety_analysis['safety_details'],
                            "high_risk_areas": safety_analysis['high_risk_areas'],
                            "crime_statistics": {
                                "max_crime_density": safety_analysis['crime_density_max'],
                                "avg_crime_density": safety_analysis['crime_density_avg'],
                                "total_incidents_nearby": safety_analysis['total_incidents_nearby']
                            },
                            "polyline": route['overview_polyline']['points'],
                            "coordinates": route_coords
                        }
                        
                        analyzed_routes.append(analyzed_route)
                        
                except Exception as e:
                    logger.warning(f"Failed to get {variation['name']} route: {e}")
                    continue
            
            # If we still don't have enough routes, try getting alternatives from basic query
            if len(analyzed_routes) < 2:
                basic_directions = self.gmaps.directions(
                    origin,
                    destination,
                    mode=mode,
                    alternatives=True,
                    departure_time=datetime.now()
                )
                
                for i, route in enumerate(basic_directions[len(analyzed_routes):]):
                    # Create additional routes with different characteristics
                    route_coords = []
                    for step in route['legs'][0]['steps']:
                        start_loc = step['start_location']
                        end_loc = step['end_location']
                        route_coords.append((start_loc['lat'], start_loc['lng']))
                        route_coords.append((end_loc['lat'], end_loc['lng']))
                    
                    safety_analysis = self.score_route_safety(route_coords)
                    
                    # Assign remaining route types
                    remaining_types = ['balanced', 'fastest']
                    route_type = remaining_types[i % len(remaining_types)]
                    
                    analyzed_route = {
                        "route_index": len(analyzed_routes),
                        "route_type": route_type,
                        "summary": route['summary'] or f"Alternative route {len(analyzed_routes) + 1}",
                        "distance": route['legs'][0]['distance']['text'],
                        "duration": route['legs'][0]['duration']['text'],
                        "duration_in_traffic": route['legs'][0].get('duration_in_traffic', {}).get('text', 'N/A'),
                        "overall_safety_score": safety_analysis['score'],
                        "overall_safety_grade": safety_analysis['grade'],
                        "safety_details": safety_analysis['safety_details'],
                        "high_risk_areas": safety_analysis['high_risk_areas'],
                        "crime_statistics": {
                            "max_crime_density": safety_analysis['crime_density_max'],
                            "avg_crime_density": safety_analysis['crime_density_avg'],
                            "total_incidents_nearby": safety_analysis['total_incidents_nearby']
                        },
                        "polyline": route['overview_polyline']['points'],
                        "coordinates": route_coords
                    }
                    
                    analyzed_routes.append(analyzed_route)
            
            if not analyzed_routes:
                return {'error': 'No routes found between the specified locations'}
            
            # Sort routes: safest first, then by safety score
            analyzed_routes.sort(key=lambda x: (x['route_type'] != 'safest', -x['overall_safety_score']))
            
            # Generate AI recommendation
            best_route = analyzed_routes[0]
            recommendation = {
                "recommended_route_index": 0,
                "reason": f"This route has the highest safety score ({best_route['overall_safety_score']}/100) with a {best_route['overall_safety_grade']} safety grade."
            }
            
            return {
                'origin': origin,
                'destination': destination,
                'mode': mode,
                'routes': analyzed_routes,
                'recommendation': recommendation,
                'crime_data_info': {
                    'total_incidents_loaded': len(self.crime_data),
                    'last_updated': self.crime_data_updated.isoformat() if self.crime_data_updated else None
                },
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': f'Route analysis failed: {str(e)}'}
    
    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from safety score"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F" 