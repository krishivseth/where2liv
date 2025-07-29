#!/usr/bin/env python3

from data_processor import DataProcessor
from bill_estimator import BillEstimator
from address_matcher import AddressMatcher

# Test the specific failing address
csv_file = 'SF_Building_Energy_Filtered_Clean.csv'
data_processor = DataProcessor(csv_file)
data_processor.load_data()

address_matcher = AddressMatcher(data_processor.get_building_data())
bill_estimator = BillEstimator(data_processor)

# Test the specific address that's failing
test_address = '2011 Powell St'
print(f'Testing: {test_address}')

# Search for the building
results = address_matcher.search_buildings(test_address, limit=5)
print(f'Search results: {len(results)}')
for i, result in enumerate(results):
    print(f'  {i+1}. {result["address"]}')
    print(f'      Keys: {list(result.keys())}')

if results:
    # Try to find the exact building
    building = address_matcher.find_building(results[0]['address'])
    if building:
        print(f'Found building: {building.get("Property Name", "Unknown")}')
        print(f'Property Type: {building.get("Primary Property Type - Self Selected", "Unknown")}')
        print(f'Energy intensity: {building.get("Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)", "N/A")}')
        
        # Test estimation with specific parameters
        try:
            estimates = bill_estimator.estimate_monthly_bills_data_driven(building, num_rooms=1, sq_ft=330)
            if estimates:
                jan = estimates[0]
                print(f'January estimate: ${jan["estimated_bill"]:.2f}')
                print(f'Method: {jan["estimation_method"]}')
                print(f'Confidence: {jan["confidence_score"]}')
                print(f'kWh: {jan.get("kwh_estimate", "N/A")}')
            else:
                print('No estimates generated!')
        except Exception as e:
            print(f'Error during estimation: {e}')
            import traceback
            traceback.print_exc()
    else:
        print('Building not found!')
else:
    print('No search results!')