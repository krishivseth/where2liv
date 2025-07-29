import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DataProcessor:
    """Handles loading and processing of the NYC building energy data"""
    
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.data = None
        self.building_index = {}
        
    def load_data(self) -> bool:
        """Load CSV data and create indexes for efficient lookup"""
        try:
            logger.info(f"Loading data from {self.csv_file}...")
            
            # Only load required columns to reduce memory usage
            required_columns = [
                'Property ID', 'Property Name', 'Address 1', 'City', 'Borough',
                'Primary Property Type - Self Selected', 'Year Built', 'Occupancy',
                'Property GFA - Calculated (Buildings) (ft²)',
                'Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)',
                'Electricity - Weather Normalized Site Electricity Use (Grid and Onsite Renewables) (kWh)'
            ]
            
            # Load CSV with only required columns
            self.data = pd.read_csv(self.csv_file, usecols=required_columns)
            
            # Clean and normalize data
            self._clean_data()
            
            # Create indexes for efficient lookup
            self._create_indexes()
            
            logger.info(f"Loaded {len(self.data)} building records (optimized columns)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def _clean_data(self):
        """Clean and normalize the data"""
        # Replace 'Not Available' with NaN
        self.data = self.data.replace('Not Available', np.nan)
        
        # Convert numeric columns
        numeric_columns = [
            'Year Built',
            'Occupancy',
            'Electricity - Weather Normalized Site Electricity Use (Grid and Onsite Renewables) (kWh)',
            'Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)',
            'Percent Electricity',
            'Electricity Use - Grid Purchase (kWh)',
            'Annual Maximum Demand (kW)',
            'Property GFA - Calculated (Buildings) (ft²)'
        ]
        
        for col in numeric_columns:
            if col in self.data.columns:
                self.data[col] = pd.to_numeric(self.data[col], errors='coerce')
        
        # Clean address data
        if 'Address 1' in self.data.columns:
            self.data['Address 1'] = self.data['Address 1'].str.strip().str.title()
        if 'City' in self.data.columns:
            self.data['City'] = self.data['City'].str.strip().str.title()
        if 'Borough' in self.data.columns:
            self.data['Borough'] = self.data['Borough'].str.strip().str.upper()
    
    def _create_indexes(self):
        """Create indexes for efficient data lookup"""
        # Index by Property ID
        self.building_index = {}
        
        for idx, row in self.data.iterrows():
            property_id = str(row.get('Property ID', ''))
            if property_id:
                self.building_index[property_id] = row.to_dict()
        
        logger.info(f"Created indexes for {len(self.building_index)} buildings")
    
    def get_building_data(self) -> pd.DataFrame:
        """Return the full building dataset"""
        return self.data
    
    def get_building_by_id(self, property_id: str) -> Optional[Dict]:
        """Get building data by Property ID"""
        return self.building_index.get(str(property_id))
    
    def search_by_address(self, address: str, limit: int = 10) -> List[Dict]:
        """Search buildings by address"""
        if self.data is None:
            return []
        
        address_lower = address.lower()
        matches = []
        
        for idx, row in self.data.iterrows():
            building_address = str(row.get('Address 1', '')).lower()
            building_city = str(row.get('City', '')).lower()
            building_name = str(row.get('Property Name', '')).lower()
            
            # Check if search terms match address, city, or property name
            if (address_lower in building_address or 
                address_lower in building_city or 
                address_lower in building_name):
                
                match = {
                    'property_id': row.get('Property ID'),
                    'property_name': row.get('Property Name'),
                    'address': row.get('Address 1'),
                    'city': row.get('City'),
                    'borough': row.get('Borough'),
                    'property_type': row.get('Primary Property Type - Self Selected'),
                    'year_built': row.get('Year Built'),
                    'gfa': row.get('Property GFA - Calculated (Buildings) (ft²)'),
                    'score': self._calculate_match_score(address_lower, building_address, building_city, building_name)
                }
                matches.append(match)
                
                if len(matches) >= limit * 2:  # Get more than needed for sorting
                    break
        
        # Sort by match score and return top results
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:limit]
    
    def _calculate_match_score(self, query: str, address: str, city: str, name: str) -> float:
        """Calculate match score for search results"""
        score = 0.0
        
        # Exact matches get highest score
        if query == address:
            score += 100
        elif query in address:
            score += 50
        
        if query == city:
            score += 30
        elif query in city:
            score += 15
        
        if query in name:
            score += 10
        
        return score
    
    def get_buildings_by_type(self, property_type: str) -> List[Dict]:
        """Get buildings by property type"""
        if self.data is None:
            return []
        
        filtered = self.data[
            self.data['Primary Property Type - Self Selected'].str.contains(
                property_type, case=False, na=False
            )
        ]
        
        return filtered.to_dict('records')
    
    def get_buildings_by_borough(self, borough: str) -> List[Dict]:
        """Get buildings by NYC borough"""
        if self.data is None:
            return []
        
        filtered = self.data[
            self.data['Borough'].str.contains(
                borough, case=False, na=False
            )
        ]
        
        return filtered.to_dict('records')
    
    def get_statistics(self) -> Dict:
        """Get dataset statistics"""
        if self.data is None:
            return {}
        
        stats = {
            'total_buildings': len(self.data),
            'property_types': self.data['Primary Property Type - Self Selected'].value_counts().to_dict(),
            'boroughs': self.data['Borough'].value_counts().to_dict(),
            'year_built_range': {
                'min': int(self.data['Year Built'].min()) if not pd.isna(self.data['Year Built'].min()) else None,
                'max': int(self.data['Year Built'].max()) if not pd.isna(self.data['Year Built'].max()) else None
            },
            'avg_electricity_intensity': float(self.data['Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)'].mean()) if 'Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)' in self.data.columns else None
        }
        
        return stats
    
    def validate_building_data(self, building_data: Dict) -> bool:
        """Validate that building has required data for estimation"""
        required_fields = [
            'Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)',
            'Property GFA - Calculated (Buildings) (ft²)'
        ]
        
        for field in required_fields:
            value = building_data.get(field)
            if pd.isna(value) or value is None or value == 0:
                logger.warning(f"Building missing required field: {field}")
                return False
        
        return True
