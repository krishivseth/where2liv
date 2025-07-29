import pandas as pd
import numpy as np
from typing import Dict, List
import logging
from datetime import datetime

from seasonality_factors import SeasonalityFactors
from rate_calculator import RateCalculator

logger = logging.getLogger(__name__)

class BillEstimator:
    """AC-based electricity bill estimation logic"""
    
    def __init__(self, data_processor):
        self.data_processor = data_processor
        self.seasonality = SeasonalityFactors()
        self.rate_calculator = RateCalculator()
        
        # SF ZIP CODE BASED MONTHLY ENERGY COSTS (per room equivalent)
        # SF has mild climate with less AC usage - costs reflect heating/general electrical needs
        # Based on PG&E rates and neighborhood characteristics
        self.zip_energy_costs = {
            # SF Premium Areas (Pacific Heights, Nob Hill, Russian Hill)
            '94109': 45, '94115': 50, '94123': 48, '94133': 42,
            
            # High-End Residential (Marina, Cow Hollow, Presidio Heights)
            '94123': 48, '94118': 46, '94129': 44,
            
            # Central SF (Financial District, SOMA, Union Square)
            '94102': 42, '94103': 40, '94104': 44, '94105': 42, '94107': 38, '94108': 46,
            
            # Mission Bay, Potrero Hill, Castro
            '94158': 38, '94107': 38, '94114': 40, '94131': 36,
            
            # Mission, Bernal Heights, Noe Valley
            '94110': 35, '94131': 36, '94114': 40,
            
            # Richmond, Sunset Districts
            '94116': 32, '94117': 34, '94118': 36, '94121': 30, '94122': 28,
            
            # Outer Areas (Visitacion Valley, Bayview, Excelsior)
            '94124': 28, '94134': 30, '94112': 32,
            
            # Chinatown, North Beach
            '94108': 36, '94133': 38,
            
            # Haight, Fillmore, Western Addition
            '94117': 34, '94115': 40, '94102': 36,
            
            # Tenderloin, Civic Center
            '94102': 32, '94103': 34,
            
            # Glen Park, Diamond Heights
            '94131': 36, '94114': 38
        }
        
        # Default bathroom estimates by room count
        self.bathroom_estimates = {
            0: 1,    # Studio - 1 bathroom
            1: 1,    # 1BR - 1 bathroom
            2: 1,    # 2BR - 1 bathroom
            3: 2,    # 3BR - 2 bathrooms
            4: 2,    # 4BR - 2 bathrooms
            5: 3,    # 5BR - 3 bathrooms
            6: 3     # 6BR+ - 3 bathrooms
        }
        
        # Default energy cost per room if zip code not found (SF average)
        self.default_energy_cost = 35
        
        # Fixed costs
        self.base_extra_cost = 15  # $15 extra as specified
        self.energy_rating_multiplier = 10  # $10 * energy rating factor
        
        # Apartment size estimates by room count (in sq ft) - SF typical sizes
        self.apartment_sqft_estimates = {
            0: 550,   # Studio
            1: 750,   # 1 bedroom
            2: 1000,  # 2 bedroom  
            3: 1300,  # 3 bedroom
            4: 1600,  # 4 bedroom
            5: 1900   # 5+ bedroom
        }
        
        # Cache for average intensities by property type and neighborhood
        self._intensity_cache = {}
    
    def estimate_monthly_bills(self, building_data: Dict, num_rooms: int, 
                             apartment_type: str = None, building_type: str = 'residential',
                             include_demand_charges: bool = False, num_bathrooms: int = None,
                             sq_ft: int = None) -> List[Dict]:
        """
        Generate monthly electricity bills based on apartment configuration and location.
        This is the fallback method when building-specific data is not available.
        
        Now accepts optional sq_ft parameter for more accurate estimation.
        """
        
        # Get zip code from building data
        zip_code = self._extract_zip_code(building_data)
        
        # Estimate number of bathrooms if not provided
        if num_bathrooms is None:
            num_bathrooms = self.bathroom_estimates.get(min(num_rooms, 6), 1)
        
        # Calculate number of AC units: AC = (# of rooms - # of bath)
        num_ac_units = max(1, num_rooms - num_bathrooms)  # Minimum 1 AC unit
        
        # Get per-AC cost for this zip code (using the NYC logic structure)
        per_ac_cost = self.zip_energy_costs.get(zip_code, self.default_energy_cost)
        
        # Calculate energy rating factor
        energy_rating_factor = self._calculate_energy_rating_factor(building_data, zip_code)
        
        # Generate monthly estimates
        monthly_estimates = []
        
        for month in range(1, 13):
            # Get seasonal factor for AC usage (using NYC-style AC seasonal factors)
            seasonal_factor = self._get_ac_seasonal_factor(month)
            
            # Apply NYC-style formula: Total bill = Per AC bill * (# rooms + 1) + 15$ extra + 10 * (energy rating factor)
            # Note: Using num_rooms + 1 as specified in the NYC formula
            monthly_ac_cost = per_ac_cost * seasonal_factor
            total_bill = (monthly_ac_cost * (num_rooms + 1)) + self.base_extra_cost + (self.energy_rating_multiplier * energy_rating_factor)
            
            month_name = datetime(2024, month, 1).strftime('%B')
            
            estimate = {
                'month': month_name,
                'month_num': month,
                'estimated_bill': round(total_bill, 2),
                'ac_units': num_ac_units,
                'per_ac_cost': round(monthly_ac_cost, 2),
                'rooms_multiplier': num_rooms + 1,
                'base_extra_cost': self.base_extra_cost,
                'energy_rating_cost': round(self.energy_rating_multiplier * energy_rating_factor, 2),
                'seasonal_factor': round(seasonal_factor, 2),
                'zip_code': zip_code,
                'energy_rating_factor': round(energy_rating_factor, 2),
                'estimation_method': 'sf_ac_based_fallback',
                'confidence_score': 0.40  # AC-based fallback confidence
            }
            
            monthly_estimates.append(estimate)
        
        return monthly_estimates
    
    def estimate_monthly_bills_data_driven(self, building_data: Dict, num_rooms: int, 
                                         num_bathrooms: int = None, sq_ft: int = None) -> List[Dict]:
        """
        Generate monthly electricity bills using actual building energy data.
        This is the primary estimation method that uses real consumption data.
        
        Now accepts optional sq_ft parameter for more accurate estimation.
        Returns estimates with confidence scores based on data quality.
        """
        # Get building's energy intensity data
        intensity_kwh_sqft = building_data.get('Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)', 0)
        total_annual_kwh = building_data.get('Electricity - Weather Normalized Site Electricity Use (Grid and Onsite Renewables) (kWh)', 0)
        building_sqft = building_data.get('Property GFA - Calculated (Buildings) (ft²)', 0)
        
        # Convert to float and handle non-numeric values
        try:
            intensity_kwh_sqft = float(intensity_kwh_sqft) if intensity_kwh_sqft else 0
            total_annual_kwh = float(total_annual_kwh) if total_annual_kwh else 0
            building_sqft = float(building_sqft) if building_sqft else 0
        except (ValueError, TypeError):
            intensity_kwh_sqft = 0
            total_annual_kwh = 0
            building_sqft = 0
        
        # Use scraped square footage if available, otherwise estimate based on room count
        if sq_ft and sq_ft > 0:
            estimated_apt_sqft = sq_ft
            logger.info(f"Using scraped apartment size: {sq_ft} sq ft")
        else:
            estimated_apt_sqft = self.apartment_sqft_estimates.get(num_rooms, 900)  # Default to 2BR
            logger.info(f"Using estimated apartment size for {num_rooms} rooms: {estimated_apt_sqft} sq ft")
        
        # Determine estimation method and calculate annual kWh
        confidence_score = 0
        estimation_method = ""
        annual_apt_kwh = 0
        
        # Tier 1: Use building-specific intensity (Best)
        if intensity_kwh_sqft > 0:
            annual_apt_kwh = intensity_kwh_sqft * estimated_apt_sqft
            confidence_score = 0.95
            estimation_method = "building_specific_intensity"
            logger.info(f"Using Tier 1: Building-specific intensity ({intensity_kwh_sqft} kWh/ft²)")
        
        # Tier 2: Calculate intensity from total building consumption (Good)
        elif total_annual_kwh > 0 and building_sqft > 0:
            calculated_intensity = total_annual_kwh / building_sqft
            annual_apt_kwh = calculated_intensity * estimated_apt_sqft
            confidence_score = 0.85
            estimation_method = "calculated_building_intensity"
            logger.info(f"Using Tier 2: Calculated intensity ({calculated_intensity:.2f} kWh/ft²)")
        
        # Tier 3: Use average for property type and neighborhood (Fair)
        if not estimation_method:  # This ensures Tier 3 is attempted if Tiers 1 & 2 failed
            # Get average intensity for similar building types
            property_type = building_data.get('Primary Property Type - Self Selected', 'Commercial')
            neighborhood = building_data.get('Borough', 'Financial District')  # Borough column contains neighborhoods for SF
            
            avg_intensity = self._get_average_intensity_by_type_neighborhood(property_type, neighborhood)
            
            if avg_intensity > 0:
                annual_apt_kwh = avg_intensity * estimated_apt_sqft
                estimation_method = "property_type_neighborhood_average"
                confidence_score = 0.60  
                logger.info(f"Using Tier 3: Average for {property_type} in {neighborhood} ({avg_intensity:.2f} kWh/ft²)")
        
        # Tier 4: Fall back to AC-based method (Last resort)
        if not estimation_method:  # This ensures fallback only if previous tiers failed
            logger.info("Using Tier 4: Falling back to AC-based estimation")
            ac_estimates = self.estimate_monthly_bills(building_data, num_rooms, num_bathrooms=num_bathrooms)
            # Add confidence score and method to AC estimates
            for estimate in ac_estimates:
                estimate['confidence_score'] = 0.40
                estimate['estimation_method'] = 'ac_based_fallback'
                estimate['estimated_sqft'] = estimated_apt_sqft
            return ac_estimates
        
        # Get property type for seasonal factors
        property_type = building_data.get('Primary Property Type - Self Selected', 'Multifamily Housing')
        seasonal_factors = self.seasonality.get_seasonal_pattern(property_type)
        
        # Get zip code for utility determination
        zip_code = self._extract_zip_code(building_data)
        
        # Determine utility provider based on borough
        borough = building_data.get('Borough', 'MANHATTAN')
        utility = self._get_utility_by_neighborhood(borough)
        
        # Generate monthly estimates
        monthly_estimates = []
        
        for month in range(1, 13):
            # Apply seasonal factor to distribute annual consumption
            monthly_factor = seasonal_factors.get(month, 1.0)
            monthly_kwh = (annual_apt_kwh / 12) * monthly_factor
            
            # Use rate calculator to get actual bill
            bill_details = self.rate_calculator.calculate_monthly_bill(
                kwh_usage=monthly_kwh,
                utility=utility,
                include_demand_charges=False
            )
            
            month_name = datetime(2024, month, 1).strftime('%B')
            
            estimate = {
                'month': month_name,
                'month_num': month,
                'kwh_estimate': round(monthly_kwh, 2),
                'estimated_bill': bill_details['total_bill'],
                'base_charge': bill_details['base_charge'],
                'usage_charge': bill_details['usage_charge'],
                'demand_charge': bill_details['demand_charge'],
                'taxes_and_fees': bill_details['taxes_and_fees'],
                'effective_rate': bill_details['effective_rate'],
                'seasonal_factor': round(monthly_factor, 2),
                'confidence_score': confidence_score,
                'estimation_method': estimation_method,
                'estimated_sqft': estimated_apt_sqft,
                'intensity_kwh_sqft': round(intensity_kwh_sqft, 2) if intensity_kwh_sqft > 0 else round(annual_apt_kwh / estimated_apt_sqft, 2),
                'utility': bill_details['utility'],
                'rate_schedule': bill_details['rate_schedule']
            }
            
            monthly_estimates.append(estimate)
        
        return monthly_estimates
    
    def _extract_zip_code(self, building_data: Dict) -> str:
        """Extract zip code from building data"""
        zip_code = building_data.get('Postal Code', '')
        if not zip_code or pd.isna(zip_code):
            # Try to extract from address
            address = building_data.get('Address 1', '')
            if address:
                # Simple regex to find 5-digit zip code
                import re
                zip_match = re.search(r'\b\d{5}\b', str(address))
                if zip_match:
                    zip_code = zip_match.group()
        
        return str(zip_code) if zip_code else '94102'  # Default to SF Financial District
    
    def _calculate_energy_rating_factor(self, building_data: Dict, zip_code: str) -> float:
        """Calculate energy rating factor based on building efficiency and neighborhood"""
        
        # Building efficiency component (0-3 scale)
        year_built = building_data.get('Year Built', 0)
        if pd.isna(year_built) or year_built == 0:
            building_efficiency = 2.0  # Default
        elif year_built >= 2015:
            building_efficiency = 1.0  # Very efficient
        elif year_built >= 2005:
            building_efficiency = 1.5  # Efficient
        elif year_built >= 1995:
            building_efficiency = 2.0  # Average
        elif year_built >= 1980:
            building_efficiency = 2.5  # Below average
        else:
            building_efficiency = 3.0  # Inefficient
        
        # Neighborhood factor based on zip code (0-2 scale)
        neighborhood_factor = self._get_neighborhood_factor(zip_code)
        
        # Energy Star Score bonus (if available)
        energy_star_score = building_data.get('ENERGY STAR Score', 0)
        if energy_star_score and not pd.isna(energy_star_score) and energy_star_score > 0:
            # Higher scores = lower factor (more efficient)
            energy_star_bonus = -0.5 * (energy_star_score - 50) / 50  # Normalize around 50
            energy_star_bonus = max(-1.0, min(1.0, energy_star_bonus))  # Cap at +/-1
        else:
            energy_star_bonus = 0
        
        # Combined factor
        total_factor = building_efficiency + neighborhood_factor + energy_star_bonus
        
        # Ensure factor is reasonable (0.5 to 4.0)
        return max(0.5, min(4.0, total_factor))
    
    def _get_neighborhood_factor(self, zip_code: str) -> float:
        """Get neighborhood efficiency factor based on zip code"""
        # SF Premium neighborhoods (Pacific Heights, Nob Hill, Russian Hill)
        if zip_code in ['94109', '94115', '94123', '94133']:
            return 2.0
        # High-end residential areas (Marina, Presidio Heights)
        elif zip_code in ['94123', '94118', '94129']:
            return 1.8
        # Central/Downtown SF (Financial, SOMA, Union Square)
        elif zip_code in ['94102', '94103', '94104', '94105', '94107', '94108']:
            return 1.5
        # Popular neighborhoods (Mission Bay, Castro, Noe Valley)
        elif zip_code in ['94158', '94114', '94131']:
            return 1.3
        # Outer neighborhoods (Richmond, Sunset, Mission)
        elif zip_code in ['94116', '94117', '94121', '94122', '94110']:
            return 1.1
        # Outer areas (Bayview, Excelsior, Visitacion Valley)
        elif zip_code in ['94124', '94134', '94112']:
            return 1.0
        else:
            return 1.2  # Default for SF
    
    def _get_sf_seasonal_factor(self, month: int) -> float:
        """Get seasonal factor for SF energy usage (mild climate, heating focus)"""
        sf_seasonal_factors = {
            1: 1.2,   # January - heating season, higher usage
            2: 1.1,   # February - still cool, heating needed
            3: 1.0,   # March - mild, moderate usage
            4: 0.9,   # April - pleasant, lower usage
            5: 0.8,   # May - mild, minimal heating/cooling
            6: 0.8,   # June - foggy season, some heating
            7: 0.9,   # July - summer but often cool/foggy
            8: 1.0,   # August - warmer but still mild
            9: 1.0,   # September - warm days, cool nights
            10: 1.0,  # October - pleasant fall weather
            11: 1.1,  # November - cooling down, more heating
            12: 1.2   # December - winter, peak heating
        }
        
        return sf_seasonal_factors.get(month, 1.0)
    
    def _get_ac_seasonal_factor(self, month: int) -> float:
        """Get seasonal factor for AC usage (focused on cooling season) - NYC-style logic"""
        ac_seasonal_factors = {
            1: 0.3,   # January - minimal AC use
            2: 0.3,   # February - minimal AC use
            3: 0.4,   # March - some warming
            4: 0.6,   # April - moderate temperatures
            5: 0.8,   # May - AC starts being used
            6: 1.1,   # June - AC use increases
            7: 1.4,   # July - peak cooling
            8: 1.5,   # August - peak cooling
            9: 1.2,   # September - still warm
            10: 0.7,  # October - cooling down
            11: 0.4,  # November - minimal AC
            12: 0.3   # December - minimal AC
        }
        
        return ac_seasonal_factors.get(month, 1.0)
    
    def _get_average_intensity_by_type_neighborhood(self, property_type: str, neighborhood: str) -> float:
        """Calculate average electricity intensity for a property type and neighborhood combination"""
        cache_key = f"{property_type}:{neighborhood}"
        
        # Check cache first
        if cache_key in self._intensity_cache:
            return self._intensity_cache[cache_key]
        
        try:
            # Get building data
            building_data = self.data_processor.get_building_data()
            
            # Filter by property type and neighborhood
            filtered_buildings = building_data[
                (building_data['Primary Property Type - Self Selected'] == property_type) &
                (building_data['Borough'] == neighborhood)
            ]

            # If no exact matches, try just property type
            if filtered_buildings.empty:
                filtered_buildings = building_data[
                    building_data['Primary Property Type - Self Selected'] == property_type
                ]
            
            # If still no matches, use all multifamily housing
            if filtered_buildings.empty and property_type != 'Multifamily Housing':
                filtered_buildings = building_data[
                    building_data['Primary Property Type - Self Selected'] == 'Multifamily Housing'
                ]
            
            # Calculate average intensity
            if not filtered_buildings.empty:
                intensity_col = 'Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)'
                if intensity_col in filtered_buildings.columns:
                    # Remove zeros and NaN values
                    valid_intensities = filtered_buildings[intensity_col].dropna()
                    valid_intensities = valid_intensities[valid_intensities > 0]
                    
                    if not valid_intensities.empty:
                        avg_intensity = float(valid_intensities.mean())
                        self._intensity_cache[cache_key] = avg_intensity
                        return avg_intensity
            
        except Exception as e:
            logger.warning(f"Error calculating average intensity: {e}")
        
        # Default fallback intensity (SF average for commercial/multifamily)
        default_intensity = 7.5  # kWh/ft² - typical for SF multifamily buildings
        self._intensity_cache[cache_key] = default_intensity
        return default_intensity
    
    def _get_utility_by_neighborhood(self, neighborhood: str) -> str:
        """Determine utility provider based on neighborhood"""
        # San Francisco is entirely served by PG&E
        return 'pge'
    
    def get_building_efficiency_rating(self, building_data: Dict) -> str:
        """Get a building efficiency rating for display"""
        factor = self._calculate_energy_rating_factor(building_data, self._extract_zip_code(building_data))
        
        if factor <= 1.5:
            return 'very_efficient'
        elif factor <= 2.0:
            return 'efficient'
        elif factor <= 2.5:
            return 'average'
        elif factor <= 3.0:
            return 'below_average'
        else:
            return 'inefficient'
    
    def get_zip_energy_estimate(self, zip_code: str) -> Dict:
        """Get energy cost estimate for a specific SF zip code"""
        energy_cost = self.zip_energy_costs.get(zip_code, self.default_energy_cost)
        
        # Determine SF neighborhood from zip code
        neighborhood_map = {
            '94102': 'Financial District/Civic Center',
            '94103': 'SOMA',
            '94104': 'Financial District',
            '94105': 'Financial District',
            '94107': 'Mission Bay/Potrero Hill',
            '94108': 'Chinatown/Financial District',
            '94109': 'Nob Hill/Russian Hill',
            '94110': 'Mission',
            '94112': 'Excelsior',
            '94114': 'Castro/Noe Valley',
            '94115': 'Pacific Heights/Fillmore',
            '94116': 'Sunset',
            '94117': 'Haight/Cole Valley',
            '94118': 'Richmond/Presidio Heights',
            '94121': 'Richmond',
            '94122': 'Sunset',
            '94123': 'Marina/Cow Hollow',
            '94124': 'Bayview/Hunters Point',
            '94129': 'Presidio',
            '94131': 'Bernal Heights/Glen Park',
            '94133': 'North Beach',
            '94134': 'Visitacion Valley',
            '94158': 'Mission Bay'
        }
        
        neighborhood = neighborhood_map.get(zip_code, 'Unknown SF Area')
        
        return {
            'zip_code': zip_code,
            'neighborhood': neighborhood,
            'per_room_monthly_cost': energy_cost,
            'cost_tier': 'High' if energy_cost >= 45 else 'Medium' if energy_cost >= 35 else 'Low'
        }
    
    def estimate_bathroom_count(self, num_rooms: int, apartment_type: str = None) -> int:
        """Estimate number of bathrooms based on room count and apartment type"""
        if apartment_type:
            # Try to extract bathroom count from apartment type
            import re
            bath_match = re.search(r'(\d+)ba', apartment_type.lower())
            if bath_match:
                return int(bath_match.group(1))
        
        # Use default estimates
        return self.bathroom_estimates.get(min(num_rooms, 6), 1)
    
    def calculate_efficiency_factor(self, year_built) -> float:
        """Legacy method for compatibility - returns energy rating factor"""
        building_data = {'Year Built': year_built}
        return self._calculate_energy_rating_factor(building_data, '10001')
    
    def get_rate_structure(self, building_data: Dict) -> Dict:
        """Get rate structure information for SF buildings"""
        zip_code = self._extract_zip_code(building_data)
        energy_info = self.get_zip_energy_estimate(zip_code)
        
        return {
            'model': 'SF neighborhood-based estimation',
            'zip_code': zip_code,
            'neighborhood': energy_info['neighborhood'],
            'per_room_cost': energy_info['per_room_monthly_cost'],
            'cost_tier': energy_info['cost_tier'],
            'base_extra_cost': self.base_extra_cost,
            'energy_rating_multiplier': self.energy_rating_multiplier,
            'utility': 'PG&E',
            'climate_zone': 'San Francisco Bay Area'
        }
