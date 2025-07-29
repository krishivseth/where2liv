from address_matcher import AddressMatcher
from data_processor import DataProcessor
import logging

logging.basicConfig(level=logging.INFO)

def test_matcher():
    print("--- Testing AddressMatcher directly ---")
    
    # Initialize components
    csv_file = 'NYC_Building_Energy_Filtered_Clean.csv'
    data_processor = DataProcessor(csv_file)
    data_processor.load_data()
    
    address_matcher = AddressMatcher(data_processor.get_building_data())
    
    # Test address
    test_address = "401 East 34th Street #N16A"
    
    print(f"Testing address: '{test_address}'")
    
    # Find building
    building = address_matcher.find_building(test_address)
    
    if building:
        print("\n--- Match Found ---")
        print(f"Address: {building.get('Address 1')}")
        print(f"Borough: {building.get('Borough')}")
        print(f"Property Type: {building.get('Primary Property Type - Self Selected')}")
        print(f"Confidence Score: {building.get('confidence_score')}")
    else:
        print("\n--- No Match Found ---")

if __name__ == "__main__":
    test_matcher() 