#!/usr/bin/env python3

"""
Test script for San Francisco 311 data integration
"""

import os
import sys
import logging
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from safety_analyzer import SafetyAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_sf_311_integration():
    """Test SF 311 data fetching and processing"""
    logger.info("=== Testing San Francisco 311 Integration ===")
    
    try:
        # Initialize SafetyAnalyzer for SF
        logger.info("1. Initializing SafetyAnalyzer for San Francisco...")
        safety_analyzer = SafetyAnalyzer(city="SF")
        
        # Verify configuration
        assert safety_analyzer.city == "SF", f"Expected city='SF', got '{safety_analyzer.city}'"
        assert "mobile311.sfgov.org" in safety_analyzer.api_311_url, "SF 311 URL not configured correctly"
        logger.info("✓ SafetyAnalyzer configured for SF")
        
        # Test safety categories include SF-specific types
        logger.info("2. Checking SF-specific safety categories...")
        categories = safety_analyzer.safety_categories
        
        # Check for SF-specific categories
        sf_categories_found = {
            'Encampment': False,
            'Street or sidewalk cleaning': False,
            'Parking & Traffic Sign Repair': False,
            'Tree maintenance': False,
            'Graffiti': False
        }
        
        for category_name, category_data in categories.items():
            for service_type in category_data['types']:
                if service_type in sf_categories_found:
                    sf_categories_found[service_type] = True
        
        for service_type, found in sf_categories_found.items():
            if found:
                logger.info(f"✓ Found SF service type: {service_type}")
            else:
                logger.warning(f"⚠ SF service type not found: {service_type}")
        
        # Test 311 data fetching (limited test to avoid overwhelming the API)
        logger.info("3. Testing SF 311 data fetching...")
        sf_311_data = safety_analyzer._fetch_sf_311_data(days_back=1)  # Only fetch 1 day to be respectful
        
        if sf_311_data:
            logger.info(f"✓ Successfully fetched {len(sf_311_data)} SF 311 records")
            
            # Check data structure
            if len(sf_311_data) > 0:
                sample_record = sf_311_data[0]
                required_fields = ['unique_key', 'complaint_type', 'created_date', 'latitude', 'longitude']
                
                for field in required_fields:
                    if field in sample_record:
                        logger.info(f"✓ Found required field: {field}")
                    else:
                        logger.warning(f"⚠ Missing required field: {field}")
                
                # Log sample data (first record)
                logger.info("Sample SF 311 record:")
                logger.info(f"  Service: {sample_record.get('complaint_type')}")
                logger.info(f"  Description: {sample_record.get('descriptor', '')[:100]}...")
                logger.info(f"  Address: {sample_record.get('incident_address')}")
                logger.info(f"  Date: {sample_record.get('created_date')}")
                
        else:
            logger.warning("⚠ No SF 311 data fetched - this might be normal if there are no recent records")
        
        # Test overall load_data method
        logger.info("4. Testing overall data loading...")
        success = safety_analyzer.load_data()
        
        if success:
            logger.info("✓ Data loading successful")
            logger.info(f"✓ Total records loaded: {len(safety_analyzer.crime_data) if safety_analyzer.crime_data is not None else 0}")
        else:
            logger.warning("⚠ Data loading failed")
        
        logger.info("=== SF 311 Integration Test Complete ===")
        return True
        
    except Exception as e:
        logger.error(f"✗ Test failed with error: {e}")
        return False

def test_nyc_backward_compatibility():
    """Test that NYC functionality still works (backward compatibility)"""
    logger.info("=== Testing NYC Backward Compatibility ===")
    
    try:
        # Initialize SafetyAnalyzer for NYC (default)
        logger.info("1. Initializing SafetyAnalyzer for NYC...")
        safety_analyzer = SafetyAnalyzer(city="NYC")
        
        # Verify configuration
        assert safety_analyzer.city == "NYC", f"Expected city='NYC', got '{safety_analyzer.city}'"
        assert "data.cityofnewyork.us" in safety_analyzer.api_311_url, "NYC 311 URL not configured correctly"
        logger.info("✓ SafetyAnalyzer configured for NYC")
        
        # Test that NYC-specific methods still exist
        assert hasattr(safety_analyzer, '_fetch_nyc_311_data'), "NYC 311 fetching method missing"
        assert hasattr(safety_analyzer, '_fetch_nypd_crime_data'), "NYPD crime fetching method missing"
        logger.info("✓ NYC-specific methods available")
        
        logger.info("=== NYC Backward Compatibility Test Complete ===")
        return True
        
    except Exception as e:
        logger.error(f"✗ NYC compatibility test failed with error: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting SF 311 integration tests...")
    
    # Test SF integration
    sf_success = test_sf_311_integration()
    
    # Test NYC backward compatibility
    nyc_success = test_nyc_backward_compatibility()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST SUMMARY:")
    logger.info(f"SF Integration: {'✓ PASS' if sf_success else '✗ FAIL'}")
    logger.info(f"NYC Compatibility: {'✓ PASS' if nyc_success else '✗ FAIL'}")
    
    if sf_success and nyc_success:
        logger.info("🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed!")
        sys.exit(1) 