from typing import Dict

class SeasonalityFactors:
    """San Francisco-specific seasonality factors for electricity consumption"""
    
    def __init__(self):
        # Property-type specific seasonal factors
        self.seasonal_factors = {
            'multifamily housing': {
                1: 1.05, 2: 1.03, 3: 0.98, 4: 0.95, 5: 0.93, 6: 0.92,
                7: 0.90, 8: 0.91, 9: 0.94, 10: 0.96, 11: 1.00, 12: 1.06
            },
            'office': {
                1: 1.10, 2: 1.08, 3: 1.05, 4: 1.00, 5: 0.95, 6: 0.90,
                7: 0.85, 8: 0.88, 9: 0.95, 10: 1.02, 11: 1.08, 12: 1.12
            },
            'retail': {
                1: 1.15, 2: 1.12, 3: 1.05, 4: 0.98, 5: 0.92, 6: 0.88,
                7: 0.85, 8: 0.87, 9: 0.95, 10: 1.05, 11: 1.12, 12: 1.18
            }
        }
        
        # Monthly factors based on SF energy usage patterns
        # SF has mild weather year-round, so less seasonal variation than NYC
        self.monthly_factors = {
            1: 1.05,   # January - mild winter, some heating
            2: 1.03,   # February - mild winter
            3: 0.98,   # March - spring, minimal heating/cooling
            4: 0.95,   # April - mild spring
            5: 0.93,   # May - mild, fog season begins
            6: 0.92,   # June - cool summer, fog
            7: 0.90,   # July - cool summer, fog
            8: 0.91,   # August - slightly warmer
            9: 0.94,   # September - warm fall
            10: 0.96,  # October - mild fall
            11: 1.00,  # November - cooler, some heating
            12: 1.06   # December - mild winter, heating
        }
        
        # Default factors for unknown property types
        self.default_factors = {
            1: 1.25, 2: 1.20, 3: 1.05, 4: 0.90, 5: 0.80, 6: 1.10,
            7: 1.35, 8: 1.40, 9: 1.15, 10: 0.85, 11: 1.00, 12: 1.20
        }
        
        # Heating and cooling degree day correlations for NYC
        self.hdd_factors = {  # Heating Degree Days influence
            1: 1.25, 2: 1.20, 3: 1.10, 4: 0.95, 5: 0.85, 6: 0.90,
            7: 0.85, 8: 0.85, 9: 0.90, 10: 0.95, 11: 1.10, 12: 1.20
        }
        
        self.cdd_factors = {  # Cooling Degree Days influence
            1: 0.90, 2: 0.90, 3: 0.95, 4: 1.00, 5: 1.05, 6: 1.10,
            7: 1.20, 8: 1.25, 9: 1.15, 10: 1.05, 11: 0.95, 12: 0.90
        }
    
    def get_monthly_factor(self, month: int, property_type: str = None) -> float:
        """Get the seasonal factor for a specific month and property type"""
        if not property_type:
            return self.default_factors.get(month, 1.0)
        
        # Find matching property type
        for ptype, factors in self.seasonal_factors.items():
            if ptype.lower() in property_type.lower():
                return factors.get(month, 1.0)
        
        # Fallback to default if no match
        return self.default_factors.get(month, 1.0)
    
    def get_seasonal_pattern(self, property_type: str = None) -> Dict[int, float]:
        """Get the full year seasonal pattern for a property type"""
        if not property_type:
            return self.default_factors.copy()
        
        for ptype, factors in self.seasonal_factors.items():
            if ptype.lower() in property_type.lower():
                return factors.copy()
        
        return self.default_factors.copy()
    
    def get_peak_months(self, property_type: str = None) -> Dict[str, int]:
        """Get the peak consumption months for a property type"""
        pattern = self.get_seasonal_pattern(property_type)
        
        # Find highest and lowest consumption months
        max_month = max(pattern, key=pattern.get)
        min_month = min(pattern, key=pattern.get)
        
        return {
            'peak_month': max_month,
            'peak_factor': pattern[max_month],
            'low_month': min_month,
            'low_factor': pattern[min_month]
        }
    
    def adjust_for_climate_change(self, month: int, property_type: str = None, 
                                 year: int = 2024) -> float:
        """Adjust factors for climate change trends (hotter summers, milder winters)"""
        base_factor = self.get_monthly_factor(month, property_type)
        
        # Climate change adjustments (based on NYC climate trends)
        # Summers getting hotter (more cooling needed)
        if month in [6, 7, 8]:
            climate_adjustment = 1.05  # 5% increase for summer cooling
        # Winters getting milder (less heating needed)
        elif month in [12, 1, 2]:
            climate_adjustment = 0.98  # 2% decrease for winter heating
        else:
            climate_adjustment = 1.0
        
        return base_factor * climate_adjustment
    
    def get_weekday_weekend_factors(self) -> Dict[str, float]:
        """Get weekday vs weekend consumption factors"""
        return {
            'weekday': 1.05,    # Slightly higher weekday consumption
            'weekend': 0.95,    # Lower weekend consumption
            'holiday': 0.85     # Even lower on holidays
        }
    
    def get_time_of_day_factors(self) -> Dict[str, float]:
        """Get time-of-day consumption factors for residential"""
        return {
            'morning': 1.15,    # 6 AM - 10 AM
            'midday': 0.85,     # 10 AM - 4 PM
            'evening': 1.25,    # 4 PM - 10 PM
            'night': 0.75       # 10 PM - 6 AM
        }
    
    def calculate_annual_factor_check(self, property_type: str = None) -> float:
        """Verify that annual factors average to 1.0"""
        pattern = self.get_seasonal_pattern(property_type)
        annual_average = sum(pattern.values()) / len(pattern)
        return annual_average
    
    def get_extreme_weather_adjustments(self) -> Dict[str, float]:
        """Get adjustments for extreme weather events"""
        return {
            'heat_wave': 1.35,      # During heat waves (>95°F)
            'cold_snap': 1.30,      # During cold snaps (<20°F)
            'normal': 1.0,          # Normal weather
            'mild_summer': 0.90,    # Unusually mild summer
            'mild_winter': 0.85     # Unusually mild winter
        }
