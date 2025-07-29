#!/usr/bin/env python3

from data_processor import DataProcessor
from bill_estimator import BillEstimator
from address_matcher import AddressMatcher

# Test what happens when address is not found
csv_file = 'SF_Building_Energy_Filtered_Clean.csv'
data_processor = DataProcessor(csv_file)
data_processor.load_data()

address_matcher = AddressMatcher(data_processor.get_building_data())
bill_estimator = BillEstimator(data_processor)

# Test the exact failing address
test_address = '2011 Powell St, San Francisco, CA 94133'
print(f'Testing exact address: {test_address}')

# Test find_building (what the API uses)
building_match = address_matcher.find_building(test_address)
print(f'find_building result: {building_match}')

if not building_match:
    print('No building match found - testing AC fallback...')
    
    # This is what the API does when no building is found
    building_match = {'Address 1': test_address}
    
    # Test AC-based estimation (fallback method)
    try:
        monthly_estimates = bill_estimator.estimate_monthly_bills(
            building_data=building_match,
            num_rooms=1,
            num_bathrooms=1,
            apartment_type=None,
            sq_ft=330
        )
        
        if monthly_estimates:
            jan = monthly_estimates[0]
            print(f'AC Fallback January estimate: ${jan["estimated_bill"]:.2f}')
            print(f'Method: {jan.get("estimation_method", "ac_based")}')
            print(f'Confidence: {jan.get("confidence_score", "N/A")}')
            print(f'AC units: {jan.get("ac_units", "N/A")}')
            print(f'Seasonal factor: {jan.get("seasonal_factor", "N/A")}')
        else:
            print('No AC estimates generated!')
            
    except Exception as e:
        print(f'Error in AC estimation: {e}')
        import traceback
        traceback.print_exc()

else:
    print('Building found, testing data-driven estimation...')
    estimates = bill_estimator.estimate_monthly_bills_data_driven(
        building_data=building_match,
        num_rooms=1,
        sq_ft=330
    )
    if estimates:
        jan = estimates[0]
        print(f'Data-driven January estimate: ${jan["estimated_bill"]:.2f}')