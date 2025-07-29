from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime
import os
import socket
from functools import lru_cache
import time

from data_processor import DataProcessor
from bill_estimator import BillEstimator
from address_matcher import AddressMatcher
from safety_analyzer import SafetyAnalyzer
from route_analyzer import RouteAnalyzer
from reviews_analyzer import ReviewsAnalyzer
from agent import SafetyAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=['*'], allow_headers=['Content-Type'], methods=['GET', 'POST', 'OPTIONS'])  # Enable CORS for web extension

# Initialize components
data_processor = None
bill_estimator = None
address_matcher = None
safety_analyzer = None
route_analyzer = None
reviews_analyzer = None

# Get the directory of the current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def initialize_system():
    """Initialize all system components"""
    global data_processor, bill_estimator, address_matcher, safety_analyzer, route_analyzer, reviews_analyzer
    
    try:
        logger.info("Initializing backend system...")
        
        # Define Google API Key from environment variable
        google_api_key = os.getenv('GOOGLE_API_KEY')
        if not google_api_key:
            logger.error("GOOGLE_API_KEY environment variable not set")
            return False
        
        # Load and process CSV data - now using SF data
        csv_path = os.path.join(BASE_DIR, 'SF_Building_Energy_Filtered_Clean.csv')
        logger.info(f"Attempting to load data from: {csv_path}")
        if not os.path.exists(csv_path):
            logger.error(f"Data file not found at {csv_path}")
            return False

        data_processor = DataProcessor(csv_path)
        data_processor.load_data()
        
        # Initialize address matcher
        address_matcher = AddressMatcher(data_processor.get_building_data())
        
        # Initialize bill estimator
        bill_estimator = BillEstimator(data_processor)
        
        # Get city configuration from environment variable (default to SF for San Francisco setup)
        city = os.getenv('CITY', 'SF').upper()
        logger.info(f"Initializing safety analyzer for city: {city}")
        
        # Initialize safety analyzer with API key and city configuration
        safety_analyzer = SafetyAnalyzer(google_api_key=google_api_key, city=city)
        
        # PRE-LOAD safety data at startup for instant extension responses
        logger.info("Pre-loading safety data for fast extension responses...")
        try:
            data_loaded = safety_analyzer.load_data()
            if data_loaded:
                total_records = len(safety_analyzer.crime_data) if safety_analyzer.crime_data is not None else 0
                logger.info(f"✅ Safety data pre-loaded successfully: {total_records:,} records ready")
                
                # Show data source breakdown
                if safety_analyzer.crime_data is not None:
                    source_counts = safety_analyzer.crime_data['data_source'].value_counts().to_dict()
                    logger.info(f"📊 Data sources ready: {source_counts}")
            else:
                logger.warning("⚠️ Safety data pre-loading failed, will use fallback mode")
        except Exception as e:
            logger.error(f"❌ Safety data pre-loading error: {e}")
            logger.info("Will continue with on-demand loading (slower)")
        
        # Initialize route analyzer with the safety analyzer instance
        route_analyzer = RouteAnalyzer(safety_analyzer, google_api_key)
        
        # Initialize reviews analyzer with Google API key and OpenAI key
        openai_api_key = os.getenv('OPENAI_API_KEY')  # Get from environment variables
        reviews_analyzer = ReviewsAnalyzer(google_api_key, openai_api_key)
        
        logger.info("Backend system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}", exc_info=True)
        return False

# Initialize system when app starts
try:
    logger.info("--- Starting System Initialization ---")
    initialize_system()
    logger.info("--- System Initialization Successful ---")
except Exception as e:
    logger.error(f"--- FATAL: System Initialization Failed: {e} ---")
    # Continue without initialization - endpoints will handle None components gracefully

# Caching layer for performance optimization
class SimpleCache:
    def __init__(self, ttl=3600):  # 1 hour default TTL
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key, value):
        self.cache[key] = (value, time.time())
    
    def clear(self):
        self.cache.clear()

# Initialize caches
address_cache = SimpleCache(ttl=7200)  # 2 hours for address lookups
bill_cache = SimpleCache(ttl=3600)     # 1 hour for bill estimates
safety_cache = SimpleCache(ttl=7200)   # 2 hours for safety data (increased from 30 min)

def find_free_port():
    """Find an available port on the host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Simple health check that doesn't depend on full initialization
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'message': 'Backend is running'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/estimate', methods=['POST'])
def estimate_bill():
    """
    Main endpoint for AC-based electricity bill estimation
    
    Expected JSON payload:
    {
        "address": "123 Main St, Queens, NY",
        "num_rooms": 3,
        "num_bathrooms": 1, // optional - will be estimated if not provided
        "apartment_type": "2br", // optional
        "building_type": "residential", // optional
        "include_demand_charges": true // optional (legacy parameter)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['address', 'num_rooms']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        address = data['address']
        num_rooms = int(data['num_rooms'])
        num_bathrooms = data.get('num_bathrooms', None)
        apartment_type = data.get('apartment_type', None)
        building_type = data.get('building_type', 'residential')
        include_demand_charges = data.get('include_demand_charges', False)  # Legacy parameter
        sq_ft = data.get('sq_ft', None)  # Get scraped square footage if available
        
        # Check if address_matcher is initialized
        if address_matcher is None:
            return jsonify({'error': 'System is still initializing. Please try again in a few moments.'}), 503
        
        # Find matching building (with caching)
        cache_key = f"address:{address.lower().strip()}"
        building_match = address_cache.get(cache_key)
        
        if building_match is None:
            building_match = address_matcher.find_building(address)
            if building_match:
                address_cache.set(cache_key, building_match)
        
        # If still no match, use AC-based fallback
        if not building_match:
            logger.warning(f"Building not found for '{address}'. Using AC-based fallback estimation.")
            # Create a dummy building_data object for the estimator
            building_match = {'Address 1': address} 
            
            # Estimate bathrooms if not provided
            if num_bathrooms is None:
                num_bathrooms = bill_estimator.estimate_bathroom_count(num_rooms, apartment_type)
            
            # Use the original AC-based estimation
            monthly_estimates = bill_estimator.estimate_monthly_bills(
                building_data=building_match,
                num_rooms=num_rooms,
                num_bathrooms=num_bathrooms,
                apartment_type=apartment_type,
                sq_ft=sq_ft  # Pass square footage
            )
        else:
            # Estimate bathrooms if not provided
            if num_bathrooms is None:
                num_bathrooms = bill_estimator.estimate_bathroom_count(num_rooms, apartment_type)

            # Generate monthly estimates using new data-driven method (with caching)
            bill_cache_key = f"bill:v2:{building_match.get('Property ID', '')}:{num_rooms}:{num_bathrooms}:{sq_ft or 'none'}"
            monthly_estimates = bill_cache.get(bill_cache_key)
            
            if monthly_estimates is None:
                # Use the new data-driven estimation method
                monthly_estimates = bill_estimator.estimate_monthly_bills_data_driven(
                    building_data=building_match,
                    num_rooms=num_rooms,
                    num_bathrooms=num_bathrooms,
                    sq_ft=sq_ft  # Pass square footage
                )
                bill_cache.set(bill_cache_key, monthly_estimates)

        # Check if bill_estimator is initialized
        if bill_estimator is None:
            return jsonify({'error': 'System is still initializing. Please try again in a few moments.'}), 503
        
        # Calculate annual summary
        annual_bill = sum(est['estimated_bill'] for est in monthly_estimates)
        
        peak_month_data = max(monthly_estimates, key=lambda x: x['estimated_bill'])
        lowest_month_data = min(monthly_estimates, key=lambda x: x['estimated_bill'])
        
        # Get zip code for display
        zip_code = bill_estimator._extract_zip_code(building_match)
        
        # Extract estimation details from the first month (all months have same method/confidence)
        first_estimate = monthly_estimates[0] if monthly_estimates else {}
        estimation_method = first_estimate.get('estimation_method', 'unknown')
        confidence_score = first_estimate.get('confidence_score', 0)
        estimated_sqft = first_estimate.get('estimated_sqft', 0)
        intensity_kwh_sqft = first_estimate.get('intensity_kwh_sqft', 0)
        
        # Calculate total annual kWh
        annual_kwh = sum(est.get('kwh_estimate', 0) for est in monthly_estimates)
        
        # Get building's actual energy data for display
        building_intensity = building_match.get('Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)', 0)
        building_total_kwh = building_match.get('Electricity - Weather Normalized Site Electricity Use (Grid and Onsite Renewables) (kWh)', 0)
        
        # Helper function to safely convert values and handle NaN
        def safe_float_convert(value, default=None):
            if value is None:
                return default
            try:
                float_val = float(value)
                # Check if it's NaN
                if float_val != float_val:  # NaN check
                    return default
                return float_val
            except (ValueError, TypeError):
                return default
        
        # Prepare response
        response = {
            'building_info': {
                'property_name': building_match.get('Property Name', ''),
                'address': building_match.get('Address 1', ''),
                'city': building_match.get('City', ''),
                'borough': building_match.get('Borough', ''),
                'property_type': building_match.get('Primary Property Type - Self Selected', ''),
                'year_built': safe_float_convert(building_match.get('Year Built')),
                'total_gfa': safe_float_convert(building_match.get('Property GFA - Calculated (Buildings) (ft²)')),
                'occupancy_rate': safe_float_convert(building_match.get('Occupancy')),
                'building_efficiency': bill_estimator.get_building_efficiency_rating(building_match),
                'zip_code': zip_code,
                'building_intensity_kwh_sqft': round(safe_float_convert(building_intensity, 0), 2) if safe_float_convert(building_intensity) else None,
                'building_total_annual_kwh': round(safe_float_convert(building_total_kwh, 0), 0) if safe_float_convert(building_total_kwh) else None
            },
            'estimation_parameters': {
                'num_rooms': num_rooms,
                'num_bathrooms': num_bathrooms,
                'estimated_apartment_sqft': estimated_sqft,
                'intensity_kwh_per_sqft': round(intensity_kwh_sqft, 2),
                'estimation_method': estimation_method,
                'confidence_score': confidence_score,
                'confidence_level': 'High' if confidence_score >= 0.8 else 'Medium' if confidence_score >= 0.6 else 'Low',
                'annual_kwh_estimate': round(annual_kwh, 0)
            },
            'monthly_estimates': monthly_estimates,
            'annual_summary': {
                'total_kwh': round(annual_kwh, 0),
                'total_bill': round(annual_bill, 2),
                'average_monthly_kwh': round(annual_kwh / 12, 0),
                'average_monthly_bill': round(annual_bill / 12, 2),
                'peak_month': peak_month_data['month'],
                'peak_bill': peak_month_data['estimated_bill'],
                'peak_kwh': peak_month_data.get('kwh_estimate', 0),
                'lowest_month': lowest_month_data['month'],
                'lowest_bill': lowest_month_data['estimated_bill'],
                'lowest_kwh': lowest_month_data.get('kwh_estimate', 0)
            },
            'rate_structure': bill_estimator.get_rate_structure(building_match),
            'methodology': {
                'model': 'Data-driven estimation with graceful degradation',
                'estimation_hierarchy': [
                    'Tier 1: Building-specific intensity (95% confidence)',
                    'Tier 2: Calculated from building total consumption (85% confidence)',
                    'Tier 3: Property type & borough average (65% confidence)',
                    'Tier 4: AC-based fallback model (40% confidence)'
                ],
                'method_used': estimation_method,
                'formula': 'Annual kWh = Intensity (kWh/ft²) × Apartment size (ft²)',
                'data_source': 'San Francisco Building Energy Data (Weather Normalized)',
                'year': '2024',
                'seasonal_adjustment': True,
                'rates_used': {
                    'utility': 'PG&E',
                    'utility_rates': 'Actual PG&E tiered rates'
                }
            }
        }
        
        return jsonify(response)
        
    except ValueError as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400
    except Exception as e:
        logger.error(f"Estimation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/search', methods=['GET'])
def search_buildings():
    """
    Search for buildings by partial address
    
    Query parameters:
    - q: search query (address fragment)
    - limit: maximum results (default 10)
    """
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
        
        if not query:
            return jsonify({'error': 'Search query required'}), 400
        
        # Search for matching buildings (with caching)
        search_cache_key = f"search:{query.lower()}:{limit}"
        matches = address_cache.get(search_cache_key)
        
        if matches is None:
            matches = address_matcher.search_buildings(query, limit)
            address_cache.set(search_cache_key, matches)
        
        return jsonify({
            'query': query,
            'results': matches,
            'count': len(matches)
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({'error': 'Search failed'}), 500

@app.route('/api/building/<property_id>', methods=['GET'])
def get_building_details(property_id):
    """Get detailed information about a specific building"""
    try:
        building = data_processor.get_building_by_id(property_id)
        if not building:
            return jsonify({'error': 'Building not found'}), 404
        
        return jsonify(building)
        
    except Exception as e:
        logger.error(f"Building lookup error: {e}")
        return jsonify({'error': 'Building lookup failed'}), 500

@app.route('/api/safety', methods=['POST'])
def get_safety_rating():
    """
    Get safety rating for a specific area
    
    Expected JSON payload:
    {
        "address": "123 Main St, Queens, NY", // optional
        "zip_code": "10001", // optional
        "borough": "Manhattan", // optional
        "radius_miles": 0.1 // optional, default 0.1
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Extract parameters
        address = data.get('address')
        zip_code = data.get('zip_code')
        borough = data.get('borough')
        radius_miles = float(data.get('radius_miles', 0.1))
        
        # Validate that at least one location parameter is provided
        if not any([address, zip_code, borough]):
            return jsonify({'error': 'At least one location parameter (address, zip_code, or borough) is required'}), 400
        
        # Check if safety_analyzer is initialized
        if safety_analyzer is None:
            return jsonify({'error': 'System is still initializing. Please try again in a few moments.'}), 503
        
        # Get safety rating (with caching)
        safety_cache_key = f"safety:{zip_code or ''}:{borough or ''}:{address or ''}:{radius_miles}"
        safety_analysis = safety_cache.get(safety_cache_key)
        
        if safety_analysis is None:
            # Initialize SafetyAgent with Gemini API key from environment
            gemini_api_key = os.getenv('GEMINI_API_KEY')
            safety_agent = SafetyAgent(safety_analyzer, gemini_api_key)
            
            # Use agent for enhanced separated analysis
            agent_result = safety_agent.analyze_safety(
                address=address,
                borough=borough,
                zip_code=zip_code,
                radius_miles=radius_miles
            )
            
            if agent_result.get('success'):
                safety_analysis = agent_result.get('data')
            else:
                # Fallback to direct analyzer if agent fails
                safety_analysis = safety_analyzer.get_separated_area_analysis(
                zip_code=zip_code,
                borough=borough,
                address=address,
                radius_miles=radius_miles
            )
            
            safety_cache.set(safety_cache_key, safety_analysis)
        
        return jsonify(safety_analysis)
        
    except ValueError as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400
    except Exception as e:
        logger.error(f"Safety analysis error: {e}")
        return jsonify({'error': 'Safety analysis failed'}), 500

@app.route('/api/safety/borough-comparison', methods=['GET'])
def get_borough_safety_comparison():
    """Get safety comparison across all NYC boroughs"""
    try:
        comparison = safety_analyzer.get_borough_comparison()
        
        return jsonify({
            'borough_comparison': comparison,
            'data_source': 'NYC 311 Service Requests',
            'methodology': 'Complaints categorized by safety severity and weighted scoring'
        })
        
    except Exception as e:
        logger.error(f"Borough comparison error: {e}")
        return jsonify({'error': 'Borough comparison failed'}), 500

@app.route('/api/safety/refresh', methods=['POST'])
def refresh_safety_data():
    """Force refresh of safety data from NYC Open Data API"""
    try:
        data = request.get_json() or {}
        borough = data.get('borough')  # Optional borough filter
        
        success = safety_analyzer.refresh_data(borough=borough)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Safety data refreshed successfully{" for " + borough if borough else ""}',
                'borough': borough,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': 'Failed to refresh safety data'
            }), 500
            
    except Exception as e:
        logger.error(f"Safety data refresh error: {e}")
        return jsonify({'error': 'Safety data refresh failed'}), 500

@app.route('/api/debug/safety', methods=['GET'])
def debug_safety():
    """Debug endpoint to test safety analyzer with SF data"""
    try:
        # Test parameters
        test_address = request.args.get('address', '1234 Market St, San Francisco, CA')
        test_lat = float(request.args.get('lat', 37.7749))  # Default SF coordinates
        test_lon = float(request.args.get('lon', -122.4194))
        test_radius = float(request.args.get('radius', 0.1))
        
        # Get raw data info
        raw_data_info = {
            'total_records': len(safety_analyzer.crime_data) if safety_analyzer.crime_data is not None else 0,
            'columns': list(safety_analyzer.crime_data.columns) if safety_analyzer.crime_data is not None else [],
            'data_sources': safety_analyzer.crime_data['data_source'].unique().tolist() if safety_analyzer.crime_data is not None and 'data_source' in safety_analyzer.crime_data.columns else []
        }
        
        # Sample some data
        sample_data = None
        if safety_analyzer.crime_data is not None and not safety_analyzer.crime_data.empty:
            sample = safety_analyzer.crime_data.head(5)
            sample_data = sample[['complaint_type', 'latitude', 'longitude', 'borough', 'incident_address', 'data_source']].to_dict('records')
        
        # Test area filtering
        from safety_analyzer import _haversine_distance
        filtered_count = 0
        nearby_incidents = []
        
        if safety_analyzer.crime_data is not None and not safety_analyzer.crime_data.empty:
            # Calculate distances for all records
            distances = _haversine_distance(
                test_lat, test_lon,
                safety_analyzer.crime_data['latitude'],
                safety_analyzer.crime_data['longitude']
            )
            
            # Filter by radius
            within_radius = distances <= test_radius
            filtered_count = int(within_radius.sum())
            
            # Get some nearby incidents
            if filtered_count > 0:
                nearby_data = safety_analyzer.crime_data[within_radius].head(10)
                nearby_incidents = nearby_data[['complaint_type', 'latitude', 'longitude', 'borough', 'incident_address', 'data_source']].to_dict('records')
        
        # Test the full safety rating calculation
        safety_result = safety_analyzer.get_area_safety_rating(
            address=test_address,
            radius_miles=test_radius
        )
        
        return jsonify({
            'debug_info': {
                'test_location': {
                    'address': test_address,
                    'latitude': test_lat,
                    'longitude': test_lon,
                    'radius_miles': test_radius
                },
                'raw_data_info': raw_data_info,
                'sample_data': sample_data,
                'filtering_results': {
                    'total_records': len(safety_analyzer.crime_data) if safety_analyzer.crime_data is not None else 0,
                    'within_radius': filtered_count,
                    'nearby_incidents': nearby_incidents
                },
                'safety_rating_result': safety_result
            }
        })
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/safe-routes', methods=['POST'])
def analyze_safe_routes():
    """
    Analyze safe routes between two locations
    
    Expected JSON payload:
    {
        "origin": "123 Main St, Queens, NY",
        "destination": "456 Broadway, Manhattan, NY",
        "mode": "driving", // optional: driving, walking, transit
        "alternatives": true // optional: get multiple route options
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['origin', 'destination']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        origin = data['origin']
        destination = data['destination']
        mode = data.get('mode', 'driving')
        
        # Analyze safe routes
        route_analysis = route_analyzer.analyze_safe_routes(
            origin=origin,
            destination=destination,
            mode=mode
        )
        
        # Check for errors
        if 'error' in route_analysis:
            return jsonify(route_analysis), 500
        
        return jsonify(route_analysis)
        
    except Exception as e:
        logger.error(f"Safe route analysis error: {e}")
        return jsonify({'error': 'Route analysis failed'}), 500

@app.route('/api/reviews', methods=['POST'])
def get_building_reviews():
    """
    Analyze Google Reviews for an apartment building
    
    Expected JSON payload:
    {
        "address": "123 Main St, Queens, NY",
        "building_name": "Optional Building Name"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'address' not in data:
            return jsonify({'error': 'Address is required'}), 400
        
        address = data['address']
        building_name = data.get('building_name', None)
        
        # Analyze building reviews
        result = reviews_analyzer.analyze_building_reviews(address, building_name)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Reviews analysis error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # System already initialized at global level - no need to initialize again
    port = 9005
    logger.info(f"Starting Flask application on port {port}...")
    app.run(debug=True, host='0.0.0.0', port=port)
