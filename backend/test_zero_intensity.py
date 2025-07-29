#!/usr/bin/env python3

from data_processor import DataProcessor
from bill_estimator import BillEstimator
from address_matcher import AddressMatcher

# Test what happens with zero intensity building
csv_file = 'SF_Building_Energy_Filtered_Clean.csv'
data_processor = DataProcessor(csv_file)
data_processor.load_data()

bill_estimator = BillEstimator(data_processor)

# Create a building with zero intensity (like the 111 Powell St case)
test_building = {
    'Property ID': 'test',
    'Property Name': 'Test Building',
    'Address 1': '111 Powell St',
    'Primary Property Type - Self Selected': 'Commercial',
    'Year Built': 1910.0,
    'Electricity - Weather Normalized Site Electricity Use (Grid and Onsite Renewables) (kWh)': 0,  # Also 0
    'Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)': 0.0,  # This is the problem
    'Property GFA - Calculated (Buildings) (ft²)': 29081,
    'Borough': 'TENDERLOIN'
}

print("Testing building with 0.0 intensity...")
print(f"Intensity: {test_building.get('Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)', 'N/A')}")
print(f"Total kWh: {test_building.get('Electricity - Weather Normalized Site Electricity Use (Grid and Onsite Renewables) (kWh)', 'N/A')}")

try:
    estimates = bill_estimator.estimate_monthly_bills_data_driven(
        building_data=test_building,
        num_rooms=1,
        sq_ft=330
    )
    
    if estimates:
        jan = estimates[0]
        print(f'January estimate: ${jan["estimated_bill"]:.2f}')
        print(f'Method: {jan["estimation_method"]}')
        print(f'Confidence: {jan["confidence_score"]}')
        print(f'kWh: {jan.get("kwh_estimate", "N/A")}')
    else:
        print('No estimates generated!')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()