#!/usr/bin/env python3
"""
Test script for the electricity bill estimation system
"""

from data_processor import DataProcessor
from bill_estimator import BillEstimator
from address_matcher import AddressMatcher
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_system():
    """Test the complete system functionality"""
    try:
        logger.info("Starting system test...")
        
        # Initialize data processor
        csv_file = 'SF_Building_Energy_Filtered_Clean.csv'
        data_processor = DataProcessor(csv_file)
        
        if not data_processor.load_data():
            logger.error("Failed to load data")
            return False
        
        logger.info("✓ Data processor initialized successfully")
        
        # Initialize address matcher
        address_matcher = AddressMatcher(data_processor.get_building_data())
        logger.info("✓ Address matcher initialized successfully")
        
        # Initialize bill estimator
        bill_estimator = BillEstimator(data_processor)
        logger.info("✓ Bill estimator initialized successfully")
        
        # Test address search - use SF address
        test_address = "Market St"
        search_results = address_matcher.search_buildings(test_address, limit=3)
        logger.info(f"✓ Address search test: Found {len(search_results)} results for '{test_address}'")
        
        if search_results:
            # Test bill estimation with first result
            building = address_matcher.find_building(search_results[0]['address'])
            
            if building:
                logger.info(f"✓ Found building: {building.get('Property Name', 'Unknown')}")
                
                # Test bill estimation using new data-driven method
                monthly_estimates = bill_estimator.estimate_monthly_bills_data_driven(
                    building_data=building,
                    num_rooms=2,
                    num_bathrooms=1
                )
                
                if monthly_estimates:
                    logger.info(f"✓ Bill estimation successful: {len(monthly_estimates)} monthly estimates generated")
                    
                    # Show sample results
                    jan_estimate = monthly_estimates[0]
                    
                    # Handle both data-driven (with kwh_estimate) and AC-based methods
                    if 'kwh_estimate' in jan_estimate:
                        logger.info(f"✓ January estimate: {jan_estimate['kwh_estimate']} kWh, ${jan_estimate['estimated_bill']}")
                    else:
                        logger.info(f"✓ January estimate: ${jan_estimate['estimated_bill']} (AC-based method)")
                    
                    logger.info(f"✓ Estimation method: {jan_estimate.get('estimation_method', 'ac_based')}")
                    logger.info(f"✓ Confidence score: {jan_estimate.get('confidence_score', 0.4):.2f}")
                    
                    annual_total = sum(est['estimated_bill'] for est in monthly_estimates)
                    annual_kwh = sum(est.get('kwh_estimate', 0) for est in monthly_estimates)
                    
                    if annual_kwh > 0:
                        logger.info(f"✓ Annual total: ${annual_total:.2f} ({annual_kwh:.0f} kWh)")
                    else:
                        logger.info(f"✓ Annual total: ${annual_total:.2f} (AC-based estimation)")
                    
                else:
                    logger.error("Bill estimation failed")
                    return False
            else:
                logger.error("Building lookup failed")
                return False
        else:
            logger.error("No search results found")
            return False
        
        logger.info("🎉 All system tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"System test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_system()
    exit(0 if success else 1)
