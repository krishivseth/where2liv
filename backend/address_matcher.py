import pandas as pd
import re
from typing import Dict, List, Optional, Tuple
from thefuzz import process, fuzz
import logging

logger = logging.getLogger(__name__)

class AddressMatcher:
    """Handles fuzzy address matching for building lookup"""
    
    def __init__(self, building_data: pd.DataFrame):
        self.building_data = building_data
        # Create dictionaries for both address and property name matching
        self.address_map, self.address_choices = self._create_address_map()
        self.property_map, self.property_choices = self._create_property_map()
        
    def _create_address_map(self):
        """Create a mapping from normalized addresses to original data index."""
        address_map = {}
        # Pre-cleaning addresses for thefuzz
        for idx, row in self.building_data.iterrows():
            address = str(row.get('Address 1', '')).strip().lower()
            # A simple normalization is enough for thefuzz
            cleaned = re.sub(r'[^\w\s]', '', address)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if cleaned:
                address_map[cleaned] = idx
        return address_map, list(address_map.keys())
    
    def _create_property_map(self):
        """Create a mapping from property names to original data index."""
        property_map = {}
        for idx, row in self.building_data.iterrows():
            property_name = str(row.get('Property Name', '')).strip().lower()
            if property_name and property_name != 'nan':
                # Normalize property name
                cleaned = re.sub(r'[^\w\s]', '', property_name)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if cleaned:
                    property_map[cleaned] = idx
        return property_map, list(property_map.keys())
    
    def _clean_and_normalize_address(self, address: str) -> str:
        """Strip apartment/unit numbers and normalize the address."""
        if not address:
            return ""
        
        # Corrected regex to only strip apartment/unit numbers at the end of the string
        base_address = re.sub(r'(\s+(#|apt|unit|suite|apartment|floor|fl)\.?\s*[\w\d-]+)\s*$', '', address, flags=re.IGNORECASE).strip()
        base_address = re.sub(r'\s+#[\w\d-]+$', '', base_address).strip() # Also handle addresses like "123 Main St #A-1"

        # Standard normalization (remove punctuation, extra spaces)
        cleaned = re.sub(r'[^\w\s]', '', base_address.lower())
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned
    
    def _extract_building_name_and_address(self, query: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract building name and address from a combined query string."""
        if not query:
            return None, None
        
        # Common patterns for building name + address
        # Pattern 1: "Building Name, 123 Main St, City, State"
        parts = query.split(',')
        if len(parts) >= 2:
            potential_building = parts[0].strip()
            potential_address = ', '.join(parts[1:]).strip()
            
            # Check if the first part looks like a building name (not starting with a number)
            # Actually, building names CAN start with numbers (e.g., "360 State Street")
            # So we'll just accept it as is
            return potential_building, potential_address
        
        # If no comma separation, return the whole thing as address
        return None, query
    
    def find_building(self, query: str) -> Optional[Dict]:
        """Find the best matching building using both property name and address."""
        if not query:
            return None
        
        # Extract building name and address from query
        building_name, address = self._extract_building_name_and_address(query)
        
        # Try exact matches first
        if building_name:
            # Try exact property name match
            for idx, row in self.building_data.iterrows():
                if str(row.get('Property Name', '')).strip().lower() == building_name.lower():
                    logger.info(f"Found exact property name match: {building_name}")
                    building_info = row.to_dict()
                    building_info['confidence_score'] = 100
                    building_info['match_type'] = 'exact_property_name'
                    return building_info
        
        if address:
            # Try exact address match (after normalization)
            cleaned_address = self._clean_and_normalize_address(address)
            for idx, row in self.building_data.iterrows():
                row_address = self._clean_and_normalize_address(str(row.get('Address 1', '')))
                if row_address == cleaned_address:
                    logger.info(f"Found exact address match: {address}")
                    building_info = row.to_dict()
                    building_info['confidence_score'] = 100
                    building_info['match_type'] = 'exact_address'
                    return building_info
        
        # If no exact match, try fuzzy matching
        best_match = None
        best_score = 0
        match_type = None
        
        # Try property name fuzzy match
        if building_name and self.property_choices:
            cleaned_name = re.sub(r'[^\w\s]', '', building_name.lower())
            cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
            
            if cleaned_name:
                name_match_result = process.extractOne(cleaned_name, self.property_choices, scorer=fuzz.WRatio)
                if name_match_result:
                    matched_name, score = name_match_result
                    if score > best_score:
                        best_score = score
                        best_match = self.property_map[matched_name]
                        match_type = 'fuzzy_property_name'
                        logger.info(f"Property name fuzzy match: '{building_name}' -> '{matched_name}' (score: {score})")
        
        # Try address fuzzy match
        if address:
            cleaned_query = self._clean_and_normalize_address(address)
            if cleaned_query:
                addr_match_result = process.extractOne(cleaned_query, self.address_choices, scorer=fuzz.WRatio)
                if addr_match_result:
                    matched_addr, score = addr_match_result
                    if score > best_score:
                        best_score = score
                        best_match = self.address_map[matched_addr]
                        match_type = 'fuzzy_address'
                        logger.info(f"Address fuzzy match: '{address}' -> '{matched_addr}' (score: {score})")
        
        # If still no match, try the full query as address
        if not best_match and not building_name:
            cleaned_query = self._clean_and_normalize_address(query)
            if cleaned_query:
                match_result = process.extractOne(cleaned_query, self.address_choices, scorer=fuzz.WRatio)
                if match_result:
                    matched_addr, score = match_result
                    best_match = self.address_map[matched_addr]
                    best_score = score
                    match_type = 'fuzzy_full_query'
                    logger.info(f"Full query fuzzy match: '{query}' -> '{matched_addr}' (score: {score})")
        
        # Return best match if above threshold
        if best_match is not None and best_score >= 85:  # Lowered threshold slightly for better matching
            logger.info(f"Found building match with score {best_score} using {match_type}")
            building_info = self.building_data.loc[best_match].to_dict()
            building_info['confidence_score'] = best_score
            building_info['match_type'] = match_type
            return building_info
        else:
            logger.warning(f"No good match found for '{query}'. Best score: {best_score}")
            return None
    
    def search_buildings(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for buildings with fuzzy matching using thefuzz."""
        if not query:
            return []
        
        cleaned_query = self._clean_and_normalize_address(query)
        
        # process.extract provides a list of matches
        matches = process.extract(cleaned_query, self.address_choices, scorer=fuzz.WRatio, limit=limit*2) # Get more to filter
        
        results = []
        for best_match, score in matches:
            if score >= 60: # Lower threshold for search
                original_idx = self.address_map[best_match]
                building_data = self.building_data.loc[original_idx].to_dict()
                match = {
                    'property_id': building_data.get('Property ID'),
                    'property_name': building_data.get('Property Name'),
                    'address': building_data.get('Address 1'),
                    'borough': building_data.get('Borough'),
                    'match_score': score,
                }
                results.append(match)
        
        return results[:limit]
    
    def find_by_partial_address(self, partial_address: str) -> List[Dict]:
        """Find buildings by partial address match"""
        if not partial_address:
            return []
        
        partial_lower = partial_address.lower()
        matches = []
        
        # Search in both address and property name
        for idx, row in self.building_data.iterrows():
            address = str(row.get('Address 1', '')).lower()
            property_name = str(row.get('Property Name', '')).lower()
            
            # Check if partial match in either field
            if partial_lower in address or partial_lower in property_name:
                match = {
                    'property_id': row.get('Property ID'),
                    'property_name': row.get('Property Name'),
                    'address': row.get('Address 1'),
                    'city': row.get('City'),
                    'borough': row.get('Borough'),
                    'property_type': row.get('Primary Property Type - Self Selected'),
                    'full_address': f"{row.get('Address 1', '')}, {row.get('City', '')}, {row.get('Borough', '')}"
                }
                matches.append(match)
        
        return matches[:20]  # Limit partial matches
    
    def find_by_borough(self, borough: str) -> List[Dict]:
        """Find buildings in a specific borough"""
        if not borough:
            return []
        
        borough_lower = borough.lower()
        matches = []
        
        for idx, row in self.building_data.iterrows():
            building_borough = str(row.get('Borough', '')).lower()
            
            if borough_lower in building_borough:
                match = {
                    'property_id': row.get('Property ID'),
                    'property_name': row.get('Property Name'),
                    'address': row.get('Address 1'),
                    'city': row.get('City'),
                    'borough': row.get('Borough'),
                    'property_type': row.get('Primary Property Type - Self Selected')
                }
                matches.append(match)
        
        return matches
