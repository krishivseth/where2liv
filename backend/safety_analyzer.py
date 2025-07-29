import json
import pandas as pd
import numpy as np
import logging
import requests
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import time
import subprocess
from io import StringIO

logger = logging.getLogger(__name__)

def _haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on Earth in miles"""
    R = 3958.8  # Earth radius in miles
    
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c

class SafetyAnalyzer:
    """Analyzes crime and 311 data to provide safety ratings and summaries for specific areas"""
    
    def __init__(self, crime_data_file: str = None, google_api_key: str = None, city: str = "NYC"):
        self.city = city.upper()
        
        # Configure API endpoints based on city
        if self.city == "NYC":
            self.api_311_url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"  # 311 service requests
            self.api_crime_url = "https://data.cityofnewyork.us/resource/5uac-w243.json"  # NYPD crime data
        elif self.city == "SF":
            self.api_311_url = "https://mobile311.sfgov.org/open311/v2/requests.json"  # SF 311 service requests
            self.api_crime_url = None  # SF crime data - to be implemented if needed
        else:
            raise ValueError(f"Unsupported city: {city}. Supported cities: NYC, SF")
            
        self.crime_data = None
        self.data_cache = None
        self.cache_timestamp = None
        self.cache_duration = 3600  # Cache for 1 hour
        self.safety_categories = self._define_safety_categories()
        self.crime_categories = self._define_crime_categories()
        
        # Load Google API key from environment if not provided
        if google_api_key:
            self.google_api_key = google_api_key
        else:
            import os
            from dotenv import load_dotenv
            load_dotenv()
            self.google_api_key = os.getenv('GOOGLE_API_KEY')
            if self.google_api_key:
                logger.info("Loaded Google API key from environment variables")
            else:
                logger.warning("No Google API key found - location filtering will be limited")
        
    def _geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """Geocode an address to get latitude and longitude using Google Maps API or fallback"""
        # Try Google API first if available
        if self.google_api_key:
            return self._google_geocode(address)
        else:
            # Fallback to simple SF geocoding without API
            logger.info("Using fallback geocoding for SF (no Google API key)")
            return self._simple_sf_geocode(address)
    
    def _google_geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """Geocode using Google Maps API"""
        
        try:
            response = requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={'address': address, 'key': self.google_api_key}
            )
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'OK':
                location = data['results'][0]['geometry']['location']
                return location['lat'], location['lng']
            else:
                logger.warning(f"Geocoding failed for '{address}': {data['status']}")
                return None
        except requests.RequestException as e:
            logger.error(f"Geocoding request failed: {e}")
            return None
    
    def _simple_sf_geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """Simple fallback geocoding for common SF locations"""
        # Basic mapping for common SF areas (you could expand this)
        sf_locations = {
            'castro': (37.7609, -122.4350),
            'mission': (37.7599, -122.4148),
            'soma': (37.7749, -122.4194),
            'pacific heights': (37.7886, -122.4324),
            'marina': (37.8021, -122.4416),
            'fillmore': (37.7849, -122.4324),
            'union square': (37.7880, -122.4074),
            'financial district': (37.7946, -122.4194),
            'tenderloin': (37.7837, -122.4151),
            'nob hill': (37.7924, -122.4194)
        }
        
        address_lower = address.lower()
        for area, coords in sf_locations.items():
            if area in address_lower:
                logger.info(f"Using fallback coordinates for {area}: {coords}")
                return coords
                
        # Default SF center if no match
        logger.warning(f"No specific match for {address}, using SF center")
        return (37.7749, -122.4194)  # SF city center

    def _define_safety_categories(self) -> Dict[str, Dict]:
        """Define safety categories and their severity weights based on city"""
        base_categories = {
            'HIGH_CONCERN': {
                'weight': 2.2,
                'types': [
                    'Drug Activity',
                    'Non-Emergency Police Matter',
                    'Criminal Mischief',
                    'Harassment',
                    'Assault',
                    'Robbery',
                    'Burglary',
                    'Theft',
                    'Vandalism',
                    'Weapon'
                ],
                'description': 'Serious safety concerns requiring immediate attention'
            },
            'MEDIUM_CONCERN': {
                'weight': 1.5,
                'types': [
                    'Panhandling',
                    'Homeless Person Assistance',
                    'Abandoned Vehicle',
                    'Illegal Fireworks',
                    'Illegal Dumping',
                    'Public Urination',
                    'Disorderly Conduct'
                ],
                'description': 'Moderate safety and quality-of-life concerns'
            },
            'LOW_CONCERN': {
                'weight': 1.0,
                'types': [
                    'Noise - Residential',
                    'Noise - Street/Sidewalk',
                    'Noise - Commercial',
                    'Noise - Vehicle',
                    'Noise - Helicopter',
                    'Noise - Park',
                    'Noise',
                    'Illegal Parking',
                    'Blocked Driveway',
                    'Traffic',
                    'For Hire Vehicle Complaint',
                    'Taxi Complaint'
                ],
                'description': 'Minor quality-of-life issues with minimal safety impact'
            },
            'INFRASTRUCTURE': {
                'weight': 0.5,
                'types': [
                    'Street Condition',
                    'Sidewalk Condition',
                    'Traffic Signal Condition',
                    'Street Light Condition',
                    'Street Sign - Damaged',
                    'Damaged Tree',
                    'Water System',
                    'Sewer',
                    'Standing Water',
                    'Dirty Condition',
                    'Rodent',
                    'Maintenance or Facility',
                    'Residential Disposal Complaint'
                ],
                'description': 'Infrastructure and maintenance issues'
            }
        }
        
        # Add city-specific categories
        if self.city == "SF":
            # Add SF-specific 311 service types
            base_categories['HIGH_CONCERN']['types'].extend([
                'Encampment'  # Homeless encampments can be safety concerns
            ])
            
            base_categories['MEDIUM_CONCERN']['types'].extend([
                'Blocked driveway & illegal parking',
                'Blocked Pedestrian Walkway'
            ])
            
            base_categories['LOW_CONCERN']['types'].extend([
                'Graffiti'
            ])
            
            base_categories['INFRASTRUCTURE']['types'].extend([
                'Street or sidewalk cleaning',
                'Parking & Traffic Sign Repair',
                'Tree maintenance'
            ])
        
        return base_categories
    
    def _define_crime_categories(self) -> Dict[str, Dict]:
        """Define crime categories and their severity weights based on city"""
        if self.city == "SF":
            return self._define_sf_crime_categories()
        else:  # NYC and default
            return self._define_nyc_crime_categories()
    
    def _define_nyc_crime_categories(self) -> Dict[str, Dict]:
        """Define NYC crime categories and their severity weights"""
        return {
            'VIOLENT_CRIME': {
                'weight': 3.0,
                'types': [
                    'ASSAULT 3 & RELATED OFFENSES',
                    'FELONY ASSAULT',
                    'ROBBERY',
                    'RAPE',
                    'MURDER & NON-NEGL. MANSLAUGHTER',
                    'SEX CRIMES',
                    'KIDNAPPING',
                    'ARSON',
                    'HOMICIDE-NEGLIGENT,UNCLASSIFIED'
                ],
                'description': 'Serious violent crimes posing immediate danger'
            },
            'PROPERTY_CRIME': {
                'weight': 2.5,
                'types': [
                    'BURGLARY',
                    'GRAND LARCENY',
                    'PETIT LARCENY',
                    'GRAND LARCENY OF MOTOR VEHICLE',
                    'THEFT OF SERVICES',
                    'CRIMINAL MISCHIEF & RELATED OF',
                    'POSSESSION OF STOLEN PROPERTY',
                    'THEFT-FRAUD'
                ],
                'description': 'Property crimes affecting personal security'
            },
            'DRUG_CRIME': {
                'weight': 2.0,
                'types': [
                    'DANGEROUS DRUGS',
                    'CONTROLLED SUBSTANCE-RELATED',
                    'CANNABIS RELATED OFFENSES'
                ],
                'description': 'Drug-related offenses indicating area activity'
            },
            'PUBLIC_ORDER': {
                'weight': 1.5,
                'types': [
                    'HARRASSMENT 2',
                    'OFFENSES AGAINST PUBLIC ORDER',
                    'DISORDERLY CONDUCT',
                    'GAMBLING',
                    'PROSTITUTION & RELATED OFFENSES',
                    'WEAPONS POSSESSION',
                    'DANGEROUS WEAPONS',
                    'FIREARMS LICENSING',
                    'ALCOHOLIC BEVERAGE CONTROL LAW'
                ],
                'description': 'Public order violations affecting neighborhood safety'
            },
            'MINOR_OFFENSES': {
                'weight': 1.0,
                'types': [
                    'OFF. AGNST PUB ORD SENSBLTY &',
                    'MISCELLANEOUS PENAL LAW',
                    'VEHICLE AND TRAFFIC LAWS',
                    'ADMINISTRATIVE CODE',
                    'AGRICULTURE & MRKTS LAW-UNCLASSIFIED',
                    'NEW YORK CITY HEALTH CODE',
                    'ENDAN WELFARE INCOMP',
                    'OTHER OFFENSES RELATED TO THEF'
                ],
                'description': 'Minor violations with minimal safety impact'
            }
        }
    
    def _define_sf_crime_categories(self) -> Dict[str, Dict]:
        """Define SF police crime categories based on SFPD incident data"""
        return {
            'VIOLENT_CRIME': {
                'weight': 4.0,
                'types': [
                    'ASSAULT',
                    'ROBBERY',
                    'RAPE',
                    'HOMICIDE',
                    'SEX OFFENSES',
                    'WEAPONS',
                    'ARSON',
                    'KIDNAPPING',
                    'HUMAN TRAFFICKING'
                ],
                'description': 'Serious violent crimes posing immediate danger'
            },
            'PROPERTY_CRIME': {
                'weight': 2.5,
                'types': [
                    'BURGLARY',
                    'LARCENY THEFT',
                    'MOTOR VEHICLE THEFT',
                    'VANDALISM',
                    'MALICIOUS MISCHIEF',
                    'EMBEZZLEMENT',
                    'STOLEN PROPERTY',
                    'FRAUD',
                    'FORGERY AND COUNTERFEITING'
                ],
                'description': 'Property crimes affecting personal security'
            },
            'DRUG_CRIME': {
                'weight': 2.0,
                'types': [
                    'DRUG OFFENSE',
                    'DRUG VIOLATION',
                    'NARCOTICS'
                ],
                'description': 'Drug-related offenses indicating area activity'
            },
            'PUBLIC_ORDER': {
                'weight': 1.5,
                'types': [
                    'DISORDERLY CONDUCT',
                    'PROSTITUTION',
                    'WEAPON LAWS',
                    'LIQUOR LAWS',
                    'GAMBLING',
                    'SUSPICIOUS OCC',
                    'OFFENCES AGAINST THE FAMILY'
                ],
                'description': 'Public order violations affecting neighborhood safety'
            },
            'MINOR_OFFENSES': {
                'weight': 1.0,
                'types': [
                    'TRAFFIC VIOLATION ARREST',
                    'WARRANT',
                    'NON-CRIMINAL',
                    'MISCELLANEOUS INVESTIGATION',
                    'CIVIL SIDEWALKS',
                    'OTHER MISCELLANEOUS',
                    'CASE CLOSURE',
                    'LOST PROPERTY',
                    'MISSING PERSON',
                    'RECOVERED VEHICLE'
                ],
                'description': 'Minor violations with minimal safety impact'
            }
        }
    
    def load_data(self, borough: str = None) -> bool:
        """Load and process safety data from 311 and crime APIs based on configured city"""
        try:
            # Check if we have cached data that's still fresh and for the same borough
            if self._is_cache_valid(borough):
                logger.info(f"Using cached safety data{' for ' + borough if borough else ''}")
                self.crime_data = self.data_cache.copy()
                return True
            
            logger.info(f"Fetching fresh safety data for {self.city}{' for ' + borough if borough else ''}...")
            
            # Fetch data from available APIs based on city
            service_311_data = self._fetch_311_data(borough=borough)
            crime_data = None
            
            # Fetch crime data based on city
            if self.city == "NYC" and self.api_crime_url:
                crime_data = self._fetch_nypd_crime_data(borough=borough)
            elif self.city == "SF":
                crime_data = self._fetch_sf_police_data(borough=borough)
            
            if not service_311_data and not crime_data:
                logger.error(f"Failed to fetch data from {self.city} APIs")
                return False
            
            # Combine and process data
            combined_data = []
            
            # Add 311 service requests
            if service_311_data:
                logger.info(f"Loaded {len(service_311_data)} 311 service requests")
                combined_data.extend(service_311_data)
            
            # Add crime data (if available for the city)
            if crime_data:
                crime_source = "NYPD" if self.city == "NYC" else f"{self.city} Police"
                logger.info(f"Loaded {len(crime_data)} {crime_source} crime incidents")
                combined_data.extend(crime_data)
            
            # Convert to DataFrame for easier analysis
            self.crime_data = pd.DataFrame(combined_data)
            
            # Clean and process data
            self._clean_data()
            
            # Cache the processed data with borough info
            self.data_cache = self.crime_data.copy()
            self.cache_timestamp = time.time()
            self.cached_borough = borough
            
            logger.info(f"Loaded {len(self.crime_data)} total safety incidents from both APIs{' for ' + borough if borough else ''}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load safety data: {e}")
            # If API fails, create a minimal fallback dataset
            logger.info("Creating fallback safety data...")
            self._create_fallback_data()
            return True
    
    def _is_cache_valid(self, borough: str = None) -> bool:
        """Check if cached data is still valid for the requested borough"""
        if self.data_cache is None or self.cache_timestamp is None:
            return False
        
        # Check if time is still valid
        if (time.time() - self.cache_timestamp) >= self.cache_duration:
            return False
        
        # Check if borough matches (None means all boroughs)
        cached_borough = getattr(self, 'cached_borough', None)
        if borough != cached_borough:
            return False
        
        return True
    
    def _fetch_311_data(self, days_back: int = 30, borough: str = None) -> Optional[List[Dict]]:
        """Fetch 311 service requests based on configured city"""
        if self.city == "NYC":
            return self._fetch_nyc_311_data(days_back, borough)
        elif self.city == "SF":
            return self._fetch_sf_311_data(days_back, borough)
        else:
            logger.error(f"311 data fetching not implemented for city: {self.city}")
            return None
    
    def _fetch_nyc_311_data(self, days_back: int = 180, borough: str = None) -> Optional[List[Dict]]:
        """Fetch 311 service requests from NYC Open Data API"""
        try:
            # Calculate date range (last 180 days by default)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Format dates for the API
            start_date_str = start_date.strftime("%Y-%m-%dT00:00:00")
            end_date_str = end_date.strftime("%Y-%m-%dT23:59:59")
            
            # Build the WHERE clause
            where_clauses = [
                f'`created_date` BETWEEN "{start_date_str}" :: floating_timestamp AND "{end_date_str}" :: floating_timestamp'
            ]
            
            # Add borough filter if specified
            if borough:
                # Normalize borough name for API query
                borough_normalized = self._normalize_borough_name(borough)
                where_clauses.append(f"UPPER(`borough`) = '{borough_normalized}'")
            
            where_clause = ' AND '.join(where_clauses)
            
            # Build the SQL query for the API
            query = f"""SELECT
                `unique_key`,
                `created_date`,
                `closed_date`,
                `agency`,
                `agency_name`,
                `complaint_type`,
                `descriptor`,
                `location_type`,
                `incident_zip`,
                `incident_address`,
                `street_name`,
                `borough`,
                `latitude`,
                `longitude`,
                `status`,
                `resolution_description`
            WHERE
                {where_clause}
            ORDER BY `created_date` DESC"""
            
            # Make API request
            params = {
                '$query': query,
            }
            
            logger.info(f"Fetching NYC 311 data from {start_date_str} to {end_date_str}{' for ' + borough if borough else ''}")
            response = requests.get(self.api_311_url, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            # Add data source marker
            for record in data:
                record['data_source'] = '311'
            
            logger.info(f"Successfully fetched {len(data)} NYC 311 records{' for ' + borough if borough else ''}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"NYC 311 API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing NYC 311 API response: {e}")
            return None
    
    def _fetch_sf_311_data(self, days_back: int = 30, borough: str = None) -> Optional[List[Dict]]:
        """Load SF 311 service requests from CSV file with API supplement"""
        try:
            logger.info(f"Loading SF 311 data from CSV with recent API updates")
            
            # First, try to load historical data from CSV
            csv_data = self._load_sf_311_csv(days_back)
            
            # Then, supplement with recent API data
            api_data = self._fetch_sf_311_api_recent()
            
            # Combine both datasets
            all_data = []
            if csv_data:
                all_data.extend(csv_data)
                logger.info(f"Loaded {len(csv_data)} records from SF 311 CSV")
            
            if api_data:
                all_data.extend(api_data)
                logger.info(f"Added {len(api_data)} recent records from SF 311 API")
            
            # Remove duplicates based on service_request_id
            seen_ids = set()
            deduplicated_data = []
            for record in all_data:
                record_id = record.get('unique_key') or record.get('service_request_id')
                if record_id and record_id not in seen_ids:
                    seen_ids.add(record_id)
                    deduplicated_data.append(record)
                elif not record_id:
                    # Keep records without IDs (shouldn't happen but just in case)
                    deduplicated_data.append(record)
            
            logger.info(f"Final SF 311 dataset: {len(deduplicated_data)} unique records")
            return deduplicated_data
            
        except Exception as e:
            logger.error(f"Error loading SF 311 data: {e}")
            return None
    
    def _load_sf_311_csv(self, days_back: int = 30) -> Optional[List[Dict]]:
        """Load SF 311 data from local CSV file (fast approach - read from end where new data is)"""
        try:
            # Look for SF 311 CSV file (user needs to download this)
            csv_path = 'SF_311_Cases.csv'
            
            if not os.path.exists(csv_path):
                logger.warning(f"SF 311 CSV file not found at {csv_path}. Using API only.")
                logger.info("Download SF 311 data from: https://data.sfgov.org/City-Infrastructure/311-Cases/vw6y-z8j6")
                return None
            
            logger.info(f"Loading SF 311 data from {csv_path} (fast approach - reading from end)")
            
            # Calculate date filter
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # FAST APPROACH: Read only the last 50k rows where recent data is located
            # This avoids loading the entire 3.9GB file!
            logger.info("Reading last 50k rows from CSV (where newest data is)...")
            
            # First, get the header
            header_df = pd.read_csv(csv_path, nrows=0)  # Just read header
            
            # Then read the last 50k rows using tail command (much faster)
            try:
                # Use system tail command to get last 50k lines + header
                result = subprocess.run(['tail', '-n', '50000', csv_path], 
                                      capture_output=True, text=True, check=True)
                
                # Create a temporary file-like object with header + tail data
                from io import StringIO
                header_line = ','.join(header_df.columns) + '\n'
                csv_content = header_line + result.stdout
                
                # Read from the string buffer
                df = pd.read_csv(StringIO(csv_content), low_memory=False)
                
                logger.info(f"Successfully read {len(df):,} recent records from end of file")
                
            except subprocess.CalledProcessError:
                # Fallback: use pandas chunked reading from end
                logger.info("tail command failed, using pandas fallback...")
                total_lines = int(subprocess.run(['wc', '-l', csv_path], 
                                                capture_output=True, text=True).stdout.split()[0])
                skip_lines = max(1, total_lines - 50000)  # Skip all but last 50k lines
                df = pd.read_csv(csv_path, skiprows=range(1, skip_lines), low_memory=False)
                logger.info(f"Read {len(df):,} records using pandas skiprows")
            
            # Parse date column
            date_columns = ['Opened', 'opened', 'Created Date', 'created_date', 'requested_datetime']
            date_col = None
            for col in date_columns:
                if col in df.columns:
                    date_col = col
                    break
            
            if date_col:
                logger.info(f"Filtering by date column: {date_col}")
                # Use efficient date parsing
                try:
                    df[date_col] = pd.to_datetime(df[date_col], format='%m/%d/%Y %I:%M:%S %p', errors='coerce')
                    if df[date_col].isna().all():
                        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                except:
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                
                # Filter to recent data  
                recent_data = df[df[date_col] >= start_date]
                logger.info(f"Filtered to {len(recent_data):,} records from last {days_back} days")
            else:
                logger.warning("No date column found, using all data")
                recent_data = df
            
            # Filter out records without location data
            recent_data = recent_data.dropna(subset=['Latitude', 'Longitude'])
            logger.info(f"After location filter: {len(recent_data):,} records with coordinates")
            
            # Limit to 10k records for fast processing
            if len(recent_data) > 10000:
                recent_data = recent_data.head(10000)
                logger.info(f"Limiting to first 10,000 records for fast processing")
            
            # Convert to list of dicts (same as before)
            csv_records = []
            for _, row in recent_data.iterrows():
                normalized_record = {
                    'unique_key': row.get('CaseID') or row.get('Case ID'),
                    'created_date': row.get('Opened') or row.get('opened'),
                    'closed_date': row.get('Closed') or row.get('closed'),
                    'agency': 'SF311',
                    'agency_name': 'San Francisco 311',
                    'complaint_type': row.get('Category') or row.get('Request Type'),
                    'descriptor': row.get('Request Details') or row.get('Description'),
                    'location_type': None,
                    'incident_zip': None,
                    'incident_address': row.get('Address') or row.get('Location'),
                    'street_name': row.get('Address') or row.get('Location'),
                    'borough': 'SF',
                    'latitude': float(row.get('Latitude', 0)),
                    'longitude': float(row.get('Longitude', 0)),
                    'status': row.get('Status'),
                    'resolution_description': row.get('Resolution'),
                    'data_source': '311',
                    'media_url': row.get('Media URL'),
                    'service_code': None,
                    'token': None
                }
                csv_records.append(normalized_record)
            
            logger.info(f"Successfully processed {len(csv_records):,} SF 311 CSV records")
            return csv_records
            
        except Exception as e:
            logger.error(f"Error loading SF 311 CSV: {e}")
            return None
    
    def _fetch_sf_311_api_recent(self, days_recent: int = 7) -> Optional[List[Dict]]:
        """Fetch only recent SF 311 data from API (last 7 days)"""
        try:
            logger.info(f"Fetching recent SF 311 data from API (last {days_recent} days)")
            
            all_data = []
            max_pages = 3  # Only fetch recent data, so fewer pages needed
            
            # Fetch only recent data - both open and closed
            for status in ['open', 'closed']:
                for page in range(1, max_pages + 1):
                    params = {
                        'status': status,
                        'per_page': 50,  # Smaller requests for recent data
                        'page': page
                    }
                    
                    try:
                        response = requests.get(self.api_311_url, params=params, timeout=20)
                        
                        # Handle rate limiting gracefully
                        if response.status_code == 429:
                            logger.info(f"Rate limited - skipping recent API data (CSV should provide main data)")
                            return []
                            
                        response.raise_for_status()
                        data = response.json()
                        
                        if not isinstance(data, list) or len(data) == 0:
                            break
                            
                        # Filter to truly recent data (last week)
                        recent_cutoff = datetime.now() - timedelta(days=days_recent)
                        recent_records = []
                        
                        for record in data:
                            try:
                                record_date = datetime.fromisoformat(record.get('requested_datetime', '').replace('Z', '+00:00'))
                                if record_date >= recent_cutoff.replace(tzinfo=record_date.tzinfo):
                                    recent_records.append(record)
                            except:
                                # If date parsing fails, include the record
                                recent_records.append(record)
                        
                        all_data.extend(recent_records)
                        logger.info(f"API page {page} ({status}): {len(recent_records)} recent records")
                        
                        # If we got less than 50, this is the last page
                        if len(data) < 50:
                            break
                            
                        # Light rate limiting for recent data
                        time.sleep(1.0)
                        
                    except Exception as e:
                        logger.info(f"API fetch failed (page {page}, {status}), continuing with CSV data: {e}")
                        break
            
            logger.info(f"Total recent SF 311 API records: {len(all_data)}")
            
            # Normalize API data format
            normalized_data = []
            for record in all_data:
                # Skip records with no location data
                if not record.get('lat') or not record.get('long'):
                    continue
                
                # Normalize SF API format to match expected format
                normalized_record = {
                    'unique_key': record.get('service_request_id'),
                    'created_date': record.get('requested_datetime'),
                    'closed_date': record.get('updated_datetime'),
                    'agency': 'SF311',
                    'agency_name': 'San Francisco 311',
                    'complaint_type': record.get('service_name'),
                    'descriptor': record.get('description'),
                    'location_type': None,
                    'incident_zip': None,
                    'incident_address': record.get('address'),
                    'street_name': record.get('address'),
                    'borough': 'SF',
                    'latitude': float(record.get('lat', 0)),
                    'longitude': float(record.get('long', 0)),
                    'status': record.get('status'),
                    'resolution_description': None,
                    'data_source': '311',
                    'media_url': record.get('media_url'),
                    'service_code': record.get('service_code'),
                    'token': record.get('token')
                }
                normalized_data.append(normalized_record)
            
            logger.info(f"Successfully processed {len(normalized_data)} recent SF 311 API records")
            return normalized_data
            
        except requests.RequestException as e:
            logger.error(f"SF 311 API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing SF 311 API response: {e}")
            return None
    
    def _fetch_nypd_crime_data(self, days_back: int = 180, borough: str = None) -> Optional[List[Dict]]:
        """Fetch NYPD crime data from NYC Open Data API"""
        try:
            # Calculate date range (last 180 days by default)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Format dates for the API
            start_date_str = start_date.strftime("%Y-%m-%dT00:00:00")
            end_date_str = end_date.strftime("%Y-%m-%dT23:59:59")
            
            # Build the WHERE clause
            where_clauses = [
                f'`cmplnt_fr_dt` BETWEEN "{start_date_str}" :: floating_timestamp AND "{end_date_str}" :: floating_timestamp',
                '`latitude` IS NOT NULL',
                '`longitude` IS NOT NULL'
            ]
            
            # Add borough filter if specified
            if borough:
                # Normalize borough name for API query
                borough_normalized = self._normalize_borough_name(borough)
                where_clauses.append(f"UPPER(`boro_nm`) = '{borough_normalized}'")
            
            where_clause = ' AND '.join(where_clauses)
            
            # Build the SQL query for the API
            query = f"""SELECT
                `cmplnt_num` as unique_key,
                `cmplnt_fr_dt` as created_date,
                `rpt_dt` as closed_date,
                `pd_desc` as complaint_type,
                `crm_atpt_cptd_cd` as descriptor,
                `loc_of_occur_desc` as location_type,
                `addr_pct_cd` as incident_zip,
                `boro_nm` as borough,
                `latitude`,
                `longitude`,
                `law_cat_cd` as status,
                `ofns_desc` as resolution_description
            WHERE
                {where_clause}
            ORDER BY `cmplnt_fr_dt` DESC"""
            
            # Make API request
            params = {
                '$query': query,
            }
            
            logger.info(f"Fetching NYPD crime data from {start_date_str} to {end_date_str}{' for ' + borough if borough else ''}")
            response = requests.get(self.api_crime_url, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            # Add data source marker and normalize field names
            for record in data:
                record['data_source'] = 'NYPD'
                record['agency'] = 'NYPD'
                record['agency_name'] = 'New York Police Department'
                
                # Use ofns_desc as the primary complaint type for NYPD data
                if 'resolution_description' in record:
                    record['complaint_type'] = record['resolution_description']
            
            logger.info(f"Successfully fetched {len(data)} NYPD crime records{' for ' + borough if borough else ''}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"NYPD crime API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing NYPD crime API response: {e}")
            return None
    
    def _fetch_sf_police_data(self, days_back: int = 180, borough: str = None) -> Optional[List[Dict]]:
        """Load SF police data from local CSV file"""
        try:
            # Load the SF police data CSV
            csv_path = 'Police_Department_Incident_Reports__2018_to_Present_20250726.csv'
            logger.info(f"Loading SF police data from {csv_path}")
            
            # Read CSV with pandas for better performance
            df = pd.read_csv(csv_path, low_memory=False)
            
            # Calculate date range (last 180 days by default - six months)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Filter by date
            df['Incident Date'] = pd.to_datetime(df['Incident Date'], errors='coerce')
            recent_data = df[df['Incident Date'] >= start_date]
            
            # Filter out rows with missing coordinates
            recent_data = recent_data.dropna(subset=['Latitude', 'Longitude', 'Incident Category'])
            
            # Convert to list of dictionaries with normalized field names
            normalized_data = []
            for _, row in recent_data.iterrows():
                try:
                    # Normalize to match expected format
                    record = {
                        'unique_key': str(row.get('Incident ID', '')),
                        'created_date': row.get('Incident Datetime'),
                        'closed_date': None,  # SF data doesn't have closed dates
                        'agency': 'SFPD',
                        'agency_name': 'San Francisco Police Department',
                        'complaint_type': row.get('Incident Category'),
                        'descriptor': row.get('Incident Subcategory'),
                        'location_type': None,
                        'incident_zip': None,
                        'incident_address': row.get('Intersection'),
                        'street_name': row.get('Intersection'),
                        'borough': row.get('Analysis Neighborhood', 'SF'),
                        'latitude': float(row.get('Latitude', 0)),
                        'longitude': float(row.get('Longitude', 0)),
                        'status': row.get('Resolution'),
                        'resolution_description': row.get('Incident Description'),
                        'data_source': 'SFPD',
                        'police_district': row.get('Police District'),
                        'supervisor_district': row.get('Supervisor District'),
                        'incident_year': row.get('Incident Year'),
                        'incident_day_of_week': row.get('Incident Day of Week')
                    }
                    normalized_data.append(record)
                except Exception as e:
                    logger.warning(f"Error processing SF police record: {e}")
                    continue
            
            logger.info(f"Successfully loaded {len(normalized_data)} SF police records from the last {days_back} days")
            return normalized_data
            
        except FileNotFoundError:
            logger.error(f"SF police data file not found: {csv_path}")
            return None
        except Exception as e:
            logger.error(f"Error loading SF police data: {e}")
            return None
    
    def refresh_data(self, borough: str = None) -> bool:
        """Force refresh of safety data from APIs (ignores cache)"""
        logger.info(f"Force refreshing safety data from APIs{' for ' + borough if borough else ''}...")
        self.data_cache = None
        self.cache_timestamp = None
        if hasattr(self, 'cached_borough'):
            delattr(self, 'cached_borough')
        return self.load_data(borough=borough)
    
    def _normalize_borough_name(self, borough: str) -> str:
        """Normalize borough name for consistent API queries"""
        if not borough:
            return ""
        
        # Convert to uppercase and strip whitespace
        borough_upper = borough.upper().strip()
        
        # Handle various borough name formats
        borough_mapping = {
            'MANHATTAN': 'MANHATTAN',
            'NEW YORK': 'MANHATTAN',
            'NY': 'MANHATTAN',
            'BROOKLYN': 'BROOKLYN',
            'KINGS': 'BROOKLYN',
            'QUEENS': 'QUEENS',
            'BRONX': 'BRONX',
            'THE BRONX': 'BRONX',
            'STATEN ISLAND': 'STATEN ISLAND',
            'RICHMOND': 'STATEN ISLAND',
            'SI': 'STATEN ISLAND'
        }
        
        return borough_mapping.get(borough_upper, borough_upper)
    
    def _create_fallback_data(self):
        """Create minimal fallback data when API is unavailable"""
        # Create empty DataFrame with required columns
        columns = [
            'unique_key', 'created_date', 'complaint_type', 'borough', 
            'incident_zip', 'latitude', 'longitude', 'safety_category', 'safety_weight', 'data_source'
        ]
        self.crime_data = pd.DataFrame(columns=columns)
        logger.info("Created fallback safety data (empty dataset)")
    
    def _clean_data(self):
        """Clean and normalize the safety data from both sources"""
        # Convert date columns
        date_columns = ['created_date', 'closed_date', 'resolution_action_updated_date']
        for col in date_columns:
            if col in self.crime_data.columns:
                self.crime_data[col] = pd.to_datetime(self.crime_data[col], errors='coerce')
        
        # Clean string columns
        string_columns = ['complaint_type', 'borough', 'incident_zip', 'city', 'data_source']
        for col in string_columns:
            if col in self.crime_data.columns:
                self.crime_data[col] = self.crime_data[col].astype(str).str.strip()
        
        # Convert coordinates to numeric
        if 'latitude' in self.crime_data.columns:
            self.crime_data['latitude'] = pd.to_numeric(self.crime_data['latitude'], errors='coerce')
        if 'longitude' in self.crime_data.columns:
            self.crime_data['longitude'] = pd.to_numeric(self.crime_data['longitude'], errors='coerce')
        
        # Categorize complaints by safety level based on data source
        self.crime_data['safety_category'] = self.crime_data.apply(self._categorize_complaint, axis=1)
        self.crime_data['safety_weight'] = self.crime_data.apply(self._calculate_safety_weight, axis=1)
    
    def _categorize_complaint(self, row) -> str:
        """Categorize complaint by safety severity based on data source"""
        complaint_type = row.get('complaint_type', '')
        data_source = row.get('data_source', '311')
        
        if pd.isna(complaint_type):
            return 'INFRASTRUCTURE'
        
        complaint_type = str(complaint_type).strip().upper()
        
        # Handle police crime data with higher priority
        if data_source in ['NYPD', 'SFPD']:
            for category, info in self.crime_categories.items():
                # Check for exact matches first, then partial matches
                if any(crime_type.upper() == complaint_type for crime_type in info['types']):
                    return category
                if any(crime_type.upper() in complaint_type for crime_type in info['types']):
                    return category
            
            # Additional SF-specific mappings for common crime types
            if data_source == 'SFPD':
                if any(term in complaint_type for term in ['ASSAULT', 'BATTERY', 'ROBBERY', 'RAPE', 'HOMICIDE', 'MURDER']):
                    return 'VIOLENT_CRIME'
                elif any(term in complaint_type for term in ['LARCENY', 'THEFT', 'BURGLARY', 'FRAUD', 'VANDALISM']):
                    return 'PROPERTY_CRIME'
                elif any(term in complaint_type for term in ['DRUG', 'NARCOTIC']):
                    return 'DRUG_CRIME'
                elif any(term in complaint_type for term in ['WEAPON', 'DISORDERLY']):
                    return 'PUBLIC_ORDER'
            
            # Default for uncategorized police crimes
            return 'PUBLIC_ORDER'
        
        # Handle 311 service requests
        else:
            for category, info in self.safety_categories.items():
                if complaint_type.lower() in [t.lower() for t in info['types']]:
                    return category
            # Default category for uncategorized 311 complaints
            return 'INFRASTRUCTURE'
    
    def _calculate_safety_weight(self, row) -> float:
        """Calculate safety weight based on category and data source"""
        category = row.get('safety_category', 'INFRASTRUCTURE')
        data_source = row.get('data_source', '311')
        
        # Get base weight from appropriate category system
        if data_source in ['NYPD', 'SFPD'] and category in self.crime_categories:
            base_weight = self.crime_categories[category]['weight']
        elif data_source == '311' and category in self.safety_categories:
            base_weight = self.safety_categories[category]['weight']
        else:
            base_weight = 1.0  # Default weight
        
        # Apply slight boost to police crime data as it represents actual crimes
        if data_source in ['NYPD', 'SFPD']:
            base_weight *= 1.1  # Reduced from 1.2 to 1.1
        
        return base_weight
    
    def get_area_safety_rating(self, zip_code: str = None, borough: str = None, 
                              address: str = None, radius_miles: float = 0.1) -> Dict:
        """Get comprehensive safety rating for a specific area"""
        try:
            # Use pre-loaded data efficiently - only reload if truly missing
            if not hasattr(self, 'crime_data') or self.crime_data is None or self.crime_data.empty:
                logger.info("No pre-loaded data found, loading fresh data...")
                self.load_data(borough=borough)
            else:
                # Use pre-loaded data - much faster for extension
                logger.debug(f"Using pre-loaded safety data ({len(self.crime_data):,} records)")
            
            # Filter data based on area criteria
            area_data = self._filter_area_data(zip_code, borough, address, radius_miles)
            
            if area_data.empty:
                # If no data, try to provide a basic rating based on borough/zip
                if self.crime_data.empty:  # Fallback mode - API was unavailable
                    return self._create_fallback_rating(zip_code, borough, address)
                else:
                    return self._create_default_rating("No crime data available for this area")
            
            # Calculate safety metrics
            safety_metrics = self._calculate_safety_metrics(area_data)
            
            # Generate safety rating
            safety_rating = self._generate_safety_rating(safety_metrics)
            
            # Create safety summary
            safety_summary = self._create_safety_summary(area_data, safety_metrics, safety_rating)
            
            # Calculate data source breakdown
            data_source_breakdown = self._get_data_source_breakdown(area_data)
            
            return {
                'area_info': {
                    'zip_code': zip_code,
                    'borough': borough,
                    'address': address,
                    'radius_miles': radius_miles,
                    'data_points': len(area_data)
                },
                'safety_rating': safety_rating,
                'safety_metrics': safety_metrics,
                'safety_summary': safety_summary,
                'complaint_breakdown': self._get_complaint_breakdown(area_data),
                'recent_activity': self._get_recent_activity(area_data),
                'data_source_breakdown': data_source_breakdown,
                'recommendations': self._generate_recommendations(safety_rating, safety_metrics),
                'data_sources_used': self._get_active_data_sources(data_source_breakdown),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating safety rating: {e}")
            return self._create_default_rating("Error calculating safety rating")
    
    def _filter_area_data(self, zip_code: str, borough: str, address: str, radius_miles: float) -> pd.DataFrame:
        """Filter crime data for specific area"""
        filtered_data = self.crime_data.copy()
        
        # If an address is provided, use geocoding for precise filtering
        if address and self.google_api_key:
            coords = self._geocode_address(address)
            if coords:
                lat, lon = coords
                # Calculate distances and filter by radius
                distances = _haversine_distance(
                    lat, lon,
                    filtered_data['latitude'], filtered_data['longitude']
                )
                return filtered_data[distances <= radius_miles].copy()

        # Fallback to broader filters if geocoding fails or is not used
        if zip_code:
            filtered_data = filtered_data[filtered_data['incident_zip'] == str(zip_code)]
        
        if borough:
            borough_upper = borough.upper()
            filtered_data = filtered_data[filtered_data['borough'].str.upper() == borough_upper]
        
        return filtered_data
    
    def _calculate_safety_metrics(self, area_data: pd.DataFrame) -> Dict:
        """Calculate various safety metrics for the area"""
        total_complaints = len(area_data)
        
        if total_complaints == 0:
            return {
                'total_complaints': 0,
                'weighted_safety_score': 5.0,
                'complaints_per_day': 0,
                'high_concern_ratio': 0,
                'category_distribution': {}
            }
        
        # Calculate weighted safety score (lower is better)
        weighted_score = area_data['safety_weight'].sum() / total_complaints
        
        # Convert to 1-5 scale (5 being safest)
        # Adjusted formula to be less harsh - using 0.8 multiplier instead of 1.5
        # This means average weight of 2.0 gives score of 3.4 instead of 2.0
        safety_score = max(1.0, 5.0 - (weighted_score * 0.8))
        
        # Calculate time-based metrics
        if 'created_date' in area_data.columns:
            # Ensure created_date is datetime and handle timezone
            if not pd.api.types.is_datetime64_any_dtype(area_data['created_date']):
                area_data['created_date'] = pd.to_datetime(area_data['created_date'], errors='coerce')
            
            # Remove timezone info if present
            if area_data['created_date'].dt.tz is not None:
                area_data['created_date'] = area_data['created_date'].dt.tz_localize(None)
            
            valid_dates = area_data['created_date'].dropna()
            if len(valid_dates) > 0:
                date_range = (valid_dates.max() - valid_dates.min()).days or 1
                complaints_per_day = total_complaints / max(date_range, 1)
            else:
                complaints_per_day = 0
        else:
            complaints_per_day = 0
        
        # Calculate high concern ratio
        high_concern_count = len(area_data[area_data['safety_category'] == 'HIGH_CONCERN'])
        high_concern_ratio = high_concern_count / total_complaints if total_complaints > 0 else 0
        
        # Category distribution
        category_dist = area_data['safety_category'].value_counts(normalize=True).to_dict()
        
        return {
            'total_complaints': total_complaints,
            'weighted_safety_score': round(safety_score, 2),
            'complaints_per_day': round(complaints_per_day, 3),
            'high_concern_ratio': round(high_concern_ratio, 3),
            'category_distribution': category_dist
        }
    
    def _generate_safety_rating(self, metrics: Dict) -> Dict:
        """Generate overall safety rating and grade"""
        score = metrics['weighted_safety_score']
        high_concern_ratio = metrics['high_concern_ratio']
        complaints_per_day = metrics['complaints_per_day']
        
        # Adjust score based on high concern ratio
        if high_concern_ratio > 0.3:  # More than 30% high concern
            score -= 0.8
        elif high_concern_ratio > 0.2:  # More than 20% high concern
            score -= 0.4
        
        # Adjust score based on complaint frequency  
        if complaints_per_day > 5.0:  # Very high activity
            score -= 0.4
        elif complaints_per_day > 2.5:  # High activity
            score -= 0.2
        
        # Ensure score stays within bounds
        score = max(1.0, min(5.0, score))
        
        # Convert to letter grade
        if score >= 4.5:
            grade = 'A'
            description = 'Very Safe'
            color = 'green'
        elif score >= 3.5:
            grade = 'B'
            description = 'Generally Safe'
            color = 'lightgreen'
        elif score >= 2.5:
            grade = 'C'
            description = 'Moderately Safe'
            color = 'yellow'
        elif score >= 1.5:
            grade = 'D'
            description = 'Some Safety Concerns'
            color = 'orange'
        else:
            grade = 'F'
            description = 'Significant Safety Concerns'
            color = 'red'
        
        return {
            'score': round(score, 2),
            'grade': grade,
            'description': description,
            'color': color
        }
    
    def _create_safety_summary(self, area_data: pd.DataFrame, metrics: Dict, rating: Dict) -> str:
        """Create human-readable safety summary"""
        total = metrics['total_complaints']
        score = rating['score']
        description = rating['description']
        
        if total == 0:
            return "This area has no reported incidents in our database, suggesting it's a quiet, low-activity area."
        
        # Get top complaint types
        top_complaints = area_data['complaint_type'].value_counts().head(3)
        complaint_list = [f"{count} {complaint.lower()} complaints" for complaint, count in top_complaints.items()]
        
        summary = f"This area is rated as {description} (Grade {rating['grade']}) with a safety score of {score}/5.0. "
        
        if total == 1:
            summary += f"There has been 1 reported incident"
        else:
            summary += f"There have been {total} reported incidents"
        
        if len(complaint_list) > 0:
            if len(complaint_list) == 1:
                summary += f", primarily {complaint_list[0]}."
            elif len(complaint_list) == 2:
                summary += f", mainly {complaint_list[0]} and {complaint_list[1]}."
            else:
                summary += f", mainly {complaint_list[0]}, {complaint_list[1]}, and {complaint_list[2]}."
        
        # Add context about high concern incidents
        high_concern = metrics['high_concern_ratio']
        if high_concern > 0.1:
            summary += f" {high_concern:.1%} of incidents are high-concern safety issues."
        else:
            summary += " Most incidents are minor quality-of-life issues."
        
        return summary
    
    def _get_complaint_breakdown(self, area_data: pd.DataFrame) -> Dict:
        """Get detailed breakdown of complaint types"""
        if area_data.empty:
            logger.info("No area data for complaint breakdown")
            return {}
        
        logger.info(f"Creating complaint breakdown for {len(area_data)} incidents")
        
        # Debug: Check what safety categories are present
        category_counts = area_data['safety_category'].value_counts()
        logger.info(f"Safety categories in data: {category_counts.to_dict()}")
        
        # Breakdown by safety category (include both crime and 311 categories)
        category_breakdown = {}
        all_categories = {**self.safety_categories, **self.crime_categories}
        
        for category, info in all_categories.items():
            category_data = area_data[area_data['safety_category'] == category]
            if not category_data.empty:
                category_breakdown[category] = {
                    'count': len(category_data),
                    'percentage': len(category_data) / len(area_data) * 100,
                    'description': info['description'],
                    'top_complaints': category_data['complaint_type'].value_counts().head(3).to_dict()
                }
        
        logger.info(f"Created breakdown with {len(category_breakdown)} categories: {list(category_breakdown.keys())}")
        return category_breakdown
    
    def _get_data_source_breakdown(self, area_data: pd.DataFrame) -> Dict:
        """Get breakdown of incidents by data source"""
        if area_data.empty:
            return {}
        
        # Count by data source
        source_counts = area_data['data_source'].value_counts().to_dict()
        
        # Calculate percentages
        total = len(area_data)
        source_breakdown = {}
        
        for source, count in source_counts.items():
            percentage = (count / total) * 100
            
            # Get category breakdown for this source
            source_data = area_data[area_data['data_source'] == source]
            category_counts = source_data['safety_category'].value_counts().to_dict()
            
            # Proper data source descriptions
            descriptions = {
                'NYPD': 'NYPD Crime Data',
                'SFPD': 'SF Police Department Crime Data',
                '311': '311 Service Requests'
            }
            
            source_breakdown[source] = {
                'count': int(count),
                'percentage': round(percentage, 1),
                'categories': category_counts,
                'description': descriptions.get(source, f'{source} Data')
            }
        
        return source_breakdown
    
    def _get_active_data_sources(self, data_source_breakdown: Dict) -> List[str]:
        """Get list of active data sources based on what's actually in the data"""
        active_sources = []
        for source, data in data_source_breakdown.items():
            if data.get('count', 0) > 0:
                active_sources.append(data.get('description', f'{source} Data'))
        return active_sources if active_sources else ['No data sources available']
    
    def _separate_data_by_type(self, area_data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Separate area data into police and 311 data"""
        if area_data.empty:
            return {'police': pd.DataFrame(), 'neighborhood': pd.DataFrame()}
        
        # Police data (SFPD, NYPD)
        police_data = area_data[area_data['data_source'].isin(['SFPD', 'NYPD'])]
        
        # 311 data 
        neighborhood_data = area_data[area_data['data_source'] == '311']
        
        return {
            'police': police_data,
            'neighborhood': neighborhood_data
        }
    
    def _analyze_section_data(self, section_data: pd.DataFrame, section_type: str) -> Dict[str, Any]:
        """Analyze a specific section of data (police or neighborhood)"""
        if section_data.empty:
            return {
                'available': False,
                'message': f'No {section_type} data available for this area'
            }
        
        total_incidents = len(section_data)
        
        # Calculate sophisticated safety score based on crime severity and urban context
        if section_type == 'police':
            score = self._calculate_crime_safety_score(section_data)
        else:  # neighborhood quality
            score = self._calculate_quality_score(section_data)
        
        score = max(1.0, min(5.0, score))  # Bound between 1.0 and 5.0
        
        # Determine grade
        if score >= 4.5:
            grade = 'A'
        elif score >= 3.5:
            grade = 'B'
        elif score >= 2.5:
            grade = 'C'
        elif score >= 1.5:
            grade = 'D'
        else:
            grade = 'F'
        
        # Get complaint breakdown
        complaint_breakdown = self._get_complaint_breakdown(section_data)
        
        # Get recent activity (last 90 days) - use existing method
        recent_activity = self._get_recent_activity(section_data, days=90)
        recent_count = recent_activity.get('recent_complaints', 0)
        
        # Generate specific issue cards highlighting key problems
        issue_cards = self._generate_issue_cards(section_data, section_type)
        
        return {
            'available': True,
            'rating': {
                'grade': grade,
                'score': round(score, 2),
                'description': self._get_grade_description(grade, section_type)
            },
            'metrics': {
                'total_incidents': total_incidents,
                'recent_incidents': recent_count
            },
            'complaint_breakdown': complaint_breakdown,
            'issue_cards': issue_cards,  # NEW: Specific issue cards
            'recent_activity': {
                'recent_complaints': recent_count,
                'trend': 'stable'  # Could be enhanced with trend analysis
            }
        }
    
    def _get_grade_description(self, grade: str, section_type: str) -> str:
        """Get description for grade based on section type"""
        descriptions = {
            'police': {
                'A': 'Very Safe - Low crime activity',
                'B': 'Safe - Minimal safety concerns', 
                'C': 'Moderately Safe - Some safety concerns',
                'D': 'Caution Advised - Notable safety issues',
                'F': 'High Risk - Significant safety concerns'
            },
            'neighborhood': {
                'A': 'Excellent - Well-maintained neighborhood',
                'B': 'Good - Minor quality of life issues',
                'C': 'Fair - Some maintenance and service issues', 
                'D': 'Poor - Notable quality of life problems',
                'F': 'Very Poor - Significant neighborhood issues'
            }
        }
        return descriptions.get(section_type, {}).get(grade, f'Grade {grade}')
    
    def _calculate_crime_safety_score(self, crime_data: pd.DataFrame) -> float:
        """Calculate realistic crime safety score with proper weighting"""
        if crime_data.empty:
            return 4.5  # Default good score for no crime data
        
        # Weight different crime categories by severity
        crime_weights = {
            'violent_crime': 10.0,     # Assault, robbery, homicide - highest impact
            'property_crime': 3.0,     # Theft, burglary - moderate impact  
            'drug_crime': 2.0,         # Drug offenses - lower impact
            'public_order': 1.5,       # Disorderly conduct - minimal impact
            'minor_offenses': 0.5      # Minor violations - very low impact
        }
        
        # Calculate weighted crime score
        weighted_incidents = 0
        for _, row in crime_data.iterrows():
            category = row.get('safety_category', 'minor_offenses')
            weight = crime_weights.get(category, 1.0)
            weighted_incidents += weight
        
        # Urban-context scoring with logarithmic scale for high-density areas
        import math
        
        # For very dense urban areas, use more forgiving thresholds
        if weighted_incidents == 0:
            return 4.8
        elif weighted_incidents <= 100:     # Very safe for dense urban area
            return 4.5 - (weighted_incidents / 200)
        elif weighted_incidents <= 500:     # Safe for dense urban area  
            return 4.0 - (weighted_incidents - 100) / 800
        elif weighted_incidents <= 1500:    # Moderate - typical for busy districts
            return 3.5 - (weighted_incidents - 500) / 2000
        elif weighted_incidents <= 3000:    # Some concerns but manageable
            return 3.0 - (weighted_incidents - 1500) / 3000
        elif weighted_incidents <= 5000:    # Notable concerns
            return 2.5 - (weighted_incidents - 3000) / 4000
        elif weighted_incidents <= 8000:    # Significant concerns
            return 2.0 - (weighted_incidents - 5000) / 6000
        else:                                # High activity area
            # Use logarithmic dampening for extremely high incident areas
            base_score = 1.5
            excess = weighted_incidents - 8000
            log_penalty = math.log10(excess + 1) / 10  # Much gentler penalty
            return max(1.3, base_score - log_penalty)
    
    def _calculate_quality_score(self, quality_data: pd.DataFrame) -> float:
        """Calculate neighborhood quality score (more lenient - reports show engagement)"""
        if quality_data.empty:
            return 3.5  # Neutral score for no 311 data
        
        total_reports = len(quality_data)
        
        # 311 reports often indicate community engagement, not just problems
        if total_reports <= 20:           # Very few reports
            return 4.2  # Could mean well-maintained OR disengaged community
        elif total_reports <= 50:         # Low level of reports
            return 4.0  # Good maintenance with some engagement
        elif total_reports <= 100:        # Moderate reporting
            return 3.8  # Active community, minor issues
        elif total_reports <= 200:        # High reporting  
            return 3.5  # Very engaged community, some maintenance needs
        elif total_reports <= 400:        # Very high reporting
            return 3.0  # Highly engaged community, notable issues
        else:                             # Extremely high reporting
            return 2.5  # Community working hard on many issues
    
    def get_separated_area_analysis(self, zip_code: str = None, borough: str = None, 
                                   address: str = None, radius_miles: float = 0.1) -> Dict[str, Any]:
        """Get separated analysis for police safety and neighborhood quality"""
        try:
            # Use pre-loaded data efficiently - only reload if truly missing
            if not hasattr(self, 'crime_data') or self.crime_data is None or self.crime_data.empty:
                logger.info("No pre-loaded data found, loading fresh data...")
                self.load_data(borough=borough)
            else:
                # Use pre-loaded data - much faster for extension
                logger.debug(f"Using pre-loaded safety data ({len(self.crime_data):,} records)")

            # Get area data using the existing filter method
            area_data = self._filter_area_data(zip_code, borough, address, radius_miles)
            
            if area_data.empty:
                return {
                    'area_info': {
                        'zip_code': zip_code,
                        'borough': borough,
                        'address': address,
                        'radius_miles': radius_miles,
                        'data_points': 0
                    },
                    'personal_safety': {
                        'available': False,
                        'message': 'No crime data available for this area'
                    },
                    'neighborhood_quality': {
                        'available': False,
                        'message': 'No 311 data available for this area'
                    }
                }

            # Separate data by type
            separated_data = self._separate_data_by_type(area_data)
            
            # Analyze each section
            personal_safety = self._analyze_section_data(separated_data['police'], 'police')
            neighborhood_quality = self._analyze_section_data(separated_data['neighborhood'], 'neighborhood')
            
            return {
                'area_info': {
                    'zip_code': zip_code,
                    'borough': borough,
                    'address': address,
                    'latitude': None,
                    'longitude': None,
                    'radius_miles': radius_miles,
                    'data_points': len(area_data)
                },
                'personal_safety': personal_safety,
                'neighborhood_quality': neighborhood_quality,
                'data_source_breakdown': self._get_data_source_breakdown(area_data),
                'data_sources_used': self._get_active_data_sources(self._get_data_source_breakdown(area_data))
            }
            
        except Exception as e:
            logger.error(f"Error getting separated area analysis: {e}")
            return {
                'error': f'Failed to analyze area: {str(e)}',
                'area_info': {
                    'zip_code': zip_code,
                    'borough': borough,
                    'address': address,
                    'radius_miles': radius_miles,
                    'data_points': 0
                }
            }
    
    def _get_recent_activity(self, area_data: pd.DataFrame, days: int = 90) -> Dict:
        """Get recent activity summary"""
        if area_data.empty or 'created_date' not in area_data.columns:
            return {'recent_complaints': 0, 'trend': 'stable'}
        
        # Make a copy to avoid modifying original data
        area_data = area_data.copy()
        
        # Convert created_date to pandas datetime if not already
        if not pd.api.types.is_datetime64_any_dtype(area_data['created_date']):
            area_data['created_date'] = pd.to_datetime(area_data['created_date'], errors='coerce')
        
        # Remove timezone info if present to avoid comparison issues
        if area_data['created_date'].dt.tz is not None:
            area_data['created_date'] = area_data['created_date'].dt.tz_localize(None)
        
        # Filter recent data - make cutoff_date timezone-naive to match
        cutoff_date = pd.Timestamp.now().tz_localize(None) - pd.Timedelta(days=days)
        
        logger.info(f"Recent activity analysis: cutoff_date={cutoff_date}, total_records={len(area_data)}")
        
        # Debug: Check date range in data
        if not area_data['created_date'].empty:
            min_date = area_data['created_date'].min()
            max_date = area_data['created_date'].max()
            logger.info(f"Data date range: {min_date} to {max_date}")
        
        recent_data = area_data[area_data['created_date'] >= cutoff_date]
        logger.info(f"Found {len(recent_data)} recent incidents in last {days} days")
        
        # Compare with previous period
        prev_cutoff = cutoff_date - pd.Timedelta(days=days)
        prev_data = area_data[
            (area_data['created_date'] >= prev_cutoff) & 
            (area_data['created_date'] < cutoff_date)
        ]
        
        recent_count = len(recent_data)
        prev_count = len(prev_data)
        
        if prev_count == 0:
            trend = 'stable'
        elif recent_count > prev_count * 1.2:
            trend = 'increasing'
        elif recent_count < prev_count * 0.8:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'recent_complaints': recent_count,
            'previous_period_complaints': prev_count,
            'trend': trend,
            'days_analyzed': days
        }
    
    def _generate_recommendations(self, rating: Dict, metrics: Dict) -> List[str]:
        """Generate safety recommendations based on analysis"""
        recommendations = []
        
        score = rating['score']
        high_concern_ratio = metrics['high_concern_ratio']
        
        if score >= 4.0:
            recommendations.append("This is a safe area with minimal safety concerns.")
            recommendations.append("Continue normal safety precautions for urban living.")
        elif score >= 3.0:
            recommendations.append("This is generally a safe area with some minor issues.")
            recommendations.append("Be aware of your surroundings, especially at night.")
        elif score >= 2.0:
            recommendations.append("Exercise increased caution in this area.")
            recommendations.append("Consider avoiding late-night activities alone.")
        else:
            recommendations.append("This area has notable safety concerns.")
            recommendations.append("Take extra precautions and consider alternative locations.")
        
        if high_concern_ratio > 0.1:
            recommendations.append("There have been serious safety incidents reported recently.")
            recommendations.append("Stay alert and report any suspicious activity to authorities.")
        
        recommendations.append("Always trust your instincts and prioritize personal safety.")
        recommendations.append("Consider checking local community boards for recent updates.")
        
        return recommendations
    
    def _create_default_rating(self, message: str) -> Dict:
        """Create default rating response when no data is available"""
        return {
            'area_info': {'data_points': 0},
            'safety_rating': {
                'score': 3.0,
                'grade': 'C',
                'description': 'Insufficient Data',
                'color': 'gray'
            },
            'safety_metrics': {
                'total_complaints': 0,
                'weighted_safety_score': 3.0,
                'complaints_per_day': 0,
                'high_concern_ratio': 0,
                'category_distribution': {}
            },
            'safety_summary': message,
            'complaint_breakdown': {},
            'recent_activity': {'recent_complaints': 0, 'trend': 'stable'},
            'recommendations': [
                "No recent data available for safety analysis.",
                "Consider checking with local authorities or community resources.",
                "Use general urban safety precautions."
            ]
        }
    
    def get_borough_comparison(self) -> Dict:
        """Get safety comparison across NYC boroughs"""
        if self.crime_data is None or self.crime_data.empty:
            return {}
        
        borough_stats = {}
        
        for borough in self.crime_data['borough'].unique():
            if pd.isna(borough) or borough == 'nan':
                continue
                
            borough_data = self.crime_data[self.crime_data['borough'] == borough]
            metrics = self._calculate_safety_metrics(borough_data)
            rating = self._generate_safety_rating(metrics)
            
            borough_stats[borough] = {
                'safety_score': rating['score'],
                'grade': rating['grade'],
                'total_complaints': metrics['total_complaints'],
                'high_concern_ratio': metrics['high_concern_ratio']
            }
        
        return borough_stats
    
    def _create_fallback_rating(self, zip_code: str = None, borough: str = None, address: str = None) -> Dict:
        """Create basic safety rating when API data is unavailable"""
        
        # Basic borough safety ratings (general NYC knowledge)
        borough_ratings = {
            'Manhattan': {'score': 3.8, 'grade': 'B+', 'description': 'Generally safe with heavy foot traffic and police presence'},
            'Brooklyn': {'score': 3.5, 'grade': 'B', 'description': 'Safety varies by neighborhood, generally improving'},
            'Queens': {'score': 3.6, 'grade': 'B', 'description': 'Diverse borough with generally good safety record'},
            'Bronx': {'score': 3.2, 'grade': 'B-', 'description': 'Improving safety conditions, varies by area'},
            'Staten Island': {'score': 4.0, 'grade': 'A-', 'description': 'Generally the safest NYC borough'}
        }
        
        # Try to get borough-specific rating
        if borough and borough in borough_ratings:
            rating_info = borough_ratings[borough]
        else:
            # Default rating
            rating_info = {'score': 3.5, 'grade': 'B', 'description': 'General NYC area safety rating'}
        
        return {
            'safety_rating': {
                'score': rating_info['score'],
                'grade': rating_info['grade'],
                'description': rating_info['description']
            },
            'safety_metrics': {
                'total_complaints': 0,
                'high_concern_count': 0,
                'medium_concern_count': 0,
                'low_concern_count': 0,
                'avg_complaints_per_month': 0
            },
            'complaint_breakdown': {},
            'recent_activity': {
                'trend': 'stable',
                'recent_incidents': 0,
                'comparison_text': 'No recent data available'
            },
            'area_info': {
                'zip_code': zip_code,
                'borough': borough,
                'address': address,
                'radius_miles': 0.1,
                'data_points': 0
            },
            'safety_summary': f"Basic safety information for {borough or 'this area'}. {rating_info['description']} Live crime data temporarily unavailable - showing general area assessment.",
            'recommendations': [
                "Stay aware of your surroundings",
                "Use well-lit streets when walking at night",
                "Keep valuables secure",
                "Trust your instincts about situations"
            ],
            'llm_summary': f"Safety assessment for {borough or 'this area'}: {rating_info['description']} Please note that live crime data is temporarily unavailable, so this is a general assessment.",
            'llm_recommendations': [
                "Follow general urban safety practices",
                "Check local news for recent developments",
                "Consider using ride-sharing for late night travel",
                "Stay connected with friends when out"
            ],
            'data_source': 'Fallback rating (API unavailable)',
            'analysis_timestamp': datetime.now().isoformat()
        }

    def validate_system(self) -> bool:
        """Validate that the safety analysis system is working correctly"""
        if self.crime_data is None:
            logger.error("Crime data not loaded")
            return False
        
        if self.crime_data.empty:
            logger.error("Crime data is empty")
            return False
        
        required_columns = ['complaint_type', 'incident_zip', 'borough']
        missing_columns = [col for col in required_columns if col not in self.crime_data.columns]
        
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return False
        
        logger.info("Safety analysis system validation passed")
        return True 

    def _generate_issue_cards(self, section_data: pd.DataFrame, section_type: str) -> List[Dict]:
        """Generate specific issue cards highlighting key problems"""
        if section_data.empty:
            return []
        
        issue_cards = []
        
        if section_type == 'neighborhood':
            # Get the most frequent complaint types
            top_complaints = section_data['complaint_type'].value_counts().head(5)
            
            # Get category breakdown for context
            category_counts = section_data['safety_category'].value_counts()
            
            # Generate cards for major issues
            for complaint_type, count in top_complaints.items():
                if count >= 3:  # Only show issues with 3+ incidents
                    
                    # Determine severity and icon based on category
                    complaint_data = section_data[section_data['complaint_type'] == complaint_type]
                    categories = complaint_data['safety_category'].value_counts()
                    main_category = categories.index[0] if len(categories) > 0 else 'INFRASTRUCTURE'
                    
                    # Create issue-specific cards
                    if 'cleaning' in complaint_type.lower() or 'dirty' in complaint_type.lower():
                        issue_cards.append({
                            'type': 'cleanliness',
                            'title': '🧹 Street Cleanliness Issues',
                            'count': count,
                            'severity': 'medium' if count > 10 else 'low',
                            'description': f'{count} reports of cleanliness issues in the area',
                            'tip': 'Use 311 app to report issues quickly. Peak cleaning days are usually weekdays.',
                            'action': 'Report via SF311 app or call 311'
                        })
                    
                    elif 'parking' in complaint_type.lower() or 'vehicle' in complaint_type.lower():
                        issue_cards.append({
                            'type': 'parking',
                            'title': '🚗 Parking & Vehicle Issues', 
                            'count': count,
                            'severity': 'medium' if count > 8 else 'low',
                            'description': f'{count} parking-related complaints reported',
                            'tip': 'Check parking signs carefully. Avoid peak enforcement hours (7-9 AM, 4-6 PM).',
                            'action': 'Use SpotHero or similar apps for guaranteed parking'
                        })
                    
                    elif 'noise' in complaint_type.lower():
                        issue_cards.append({
                            'type': 'noise',
                            'title': '🔊 Noise Concerns',
                            'count': count,
                            'severity': 'medium' if count > 6 else 'low', 
                            'description': f'{count} noise complaints in the neighborhood',
                            'tip': 'Peak noise issues are typically evenings/weekends. Consider soundproofing.',
                            'action': 'Report persistent issues to 311 or local police non-emergency'
                        })
                    
                    elif 'homeless' in complaint_type.lower() or 'encampment' in complaint_type.lower():
                        issue_cards.append({
                            'type': 'homelessness',
                            'title': '🏕️ Homeless Services Needed',
                            'count': count,
                            'severity': 'high' if count > 5 else 'medium',
                            'description': f'{count} reports related to homeless services needed', 
                            'tip': 'These reports often indicate community engagement with helping unhoused individuals.',
                            'action': 'Use HOT Team (311) for non-emergency homeless outreach'
                        })
                    
                    elif 'graffiti' in complaint_type.lower() or 'vandalism' in complaint_type.lower():
                        issue_cards.append({
                            'type': 'vandalism',
                            'title': '🎨 Graffiti & Vandalism',
                            'count': count,
                            'severity': 'medium' if count > 4 else 'low',
                            'description': f'{count} graffiti/vandalism reports',
                            'tip': 'Quick reporting leads to faster cleanup. Take photos when reporting.',
                            'action': 'Report immediately via 311 for fastest response'
                        })
                    
                    elif any(word in complaint_type.lower() for word in ['street', 'sidewalk', 'pothole', 'sign']):
                        issue_cards.append({
                            'type': 'infrastructure',
                            'title': '🚧 Infrastructure Maintenance',
                            'count': count,
                            'severity': 'medium' if count > 7 else 'low',
                            'description': f'{count} infrastructure maintenance issues reported',
                            'tip': 'City is generally responsive to infrastructure reports with photos.',
                            'action': 'Report with photos via 311 for priority handling'
                        })
                        
                    # Generic card for other issues
                    elif count >= 5:  # Only show generic card for significant issues
                        severity = 'high' if count > 15 else 'medium' if count > 8 else 'low'
                        issue_cards.append({
                            'type': 'general',
                            'title': f'⚠️ {complaint_type}',
                            'count': count,
                            'severity': severity,
                            'description': f'{count} reports of {complaint_type.lower()}',
                            'tip': 'Active community reporting indicates engaged residents.',
                            'action': 'Contact 311 for city services or local representatives'
                        })
            
            # Add summary card if multiple issues
            if len(issue_cards) > 2:
                total_reports = len(section_data)
                issue_cards.insert(0, {
                    'type': 'summary',
                    'title': '📊 Neighborhood Activity Summary',
                    'count': total_reports,
                    'severity': 'info',
                    'description': f'Total of {total_reports} community reports show active civic engagement',
                    'tip': 'Higher 311 reporting often indicates involved, caring residents.',
                    'action': 'Join neighborhood groups to stay informed about local issues'
                })
        
        elif section_type == 'police':
            # Generate cards for crime data
            top_crimes = section_data['complaint_type'].value_counts().head(4)
            
            for crime_type, count in top_crimes.items():
                if count >= 2:  # Show crimes with 2+ incidents
                    
                    if any(word in crime_type.lower() for word in ['theft', 'larceny', 'burglary']):
                        issue_cards.append({
                            'type': 'property_crime',
                            'title': '🔓 Property Crime Concern',
                            'count': count,
                            'severity': 'high' if count > 8 else 'medium',
                            'description': f'{count} property crime incidents reported',
                            'tip': 'Secure valuables, use good lighting, consider security systems.',
                            'action': 'Report suspicious activity to SFPD. Consider neighborhood watch.'
                        })
                    
                    elif any(word in crime_type.lower() for word in ['assault', 'battery', 'violence']):
                        issue_cards.append({
                            'type': 'violent_crime',
                            'title': '⚡ Violent Crime Alert',
                            'count': count,
                            'severity': 'high',
                            'description': f'{count} violent incidents in the area',
                            'tip': 'Stay aware of surroundings, avoid isolated areas at night.',
                            'action': 'Report immediately to 911. Consider personal safety tools.'
                        })
                    
                    elif 'drug' in crime_type.lower() or 'narcotic' in crime_type.lower():
                        issue_cards.append({
                            'type': 'drug_activity',
                            'title': '💊 Drug Activity Reported',
                            'count': count,
                            'severity': 'medium',
                            'description': f'{count} drug-related incidents reported',
                            'tip': 'Avoid loitering in affected areas. Report suspicious activity.',
                            'action': 'Report to SFPD non-emergency or anonymous tip line'
                        })
        
        # Limit to top 4 most important cards
        return issue_cards[:4]