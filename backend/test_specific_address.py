import requests
import json

def test_specific_address():
    # Test the specific address
    address = '401 East 34th Street #N16A'
    num_rooms = 2
    num_bathrooms = 2

    data = {
        'address': address,
        'num_rooms': num_rooms,
        'num_bathrooms': num_bathrooms
    }

    try:
        response = requests.post('http://127.0.0.1:62031/api/estimate', json=data)
        result = response.json()

        print('=== ESTIMATION RESULTS FOR 401 East 34th Street #N16A ===')
        print(f'Address: {address}')
        print(f'Rooms: {num_rooms}, Bathrooms: {num_bathrooms}')
        print(f'Square Footage: 1,343 ft² (from listing)')
        print()

        print('=== ANNUAL SUMMARY ===')
        annual_summary = result.get('annual_summary', {})
        print(f'Total Annual Cost: ${annual_summary.get("total_annual_cost", 0):.2f}')
        print(f'Average Monthly Cost: ${annual_summary.get("average_monthly_cost", 0):.2f}')
        print(f'Peak Month: {annual_summary.get("peak_month", "N/A")} (${annual_summary.get("peak_month_cost", 0):.2f})')
        print(f'Lowest Month: {annual_summary.get("lowest_month", "N/A")} (${annual_summary.get("lowest_month_cost", 0):.2f})')
        print(f'Confidence Score: {annual_summary.get("confidence_score", 0):.2f}')
        print(f'Estimation Method: {annual_summary.get("estimation_method", "N/A")}')
        print()

        print('=== MONTHLY BREAKDOWN ===')
        monthly_estimates = result.get('monthly_estimates', [])
        for month_data in monthly_estimates:
            month = month_data.get('month', 'N/A')
            bill = month_data.get('estimated_bill', 0)
            kwh = month_data.get('kwh_estimate', 0)
            seasonal_factor = month_data.get('seasonal_factor', 0)
            print(f'{month}: ${bill:.2f} ({kwh:.1f} kWh, factor: {seasonal_factor})')

        print()
        print('=== BUILDING DATA USED ===')
        building_data = result.get('building_data', {})
        print(f'Building Found: {building_data.get("Address 1", "N/A")}')
        print(f'Property Type: {building_data.get("Primary Property Type - Self Selected", "N/A")}')
        print(f'Borough: {building_data.get("Borough", "N/A")}')
        print(f'Year Built: {building_data.get("Year Built", "N/A")}')
        print(f'Energy Intensity: {building_data.get("Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)", "N/A")} kWh/ft²')
        print(f'Building Size: {building_data.get("Property GFA - Calculated (Buildings) (ft²)", "N/A")} ft²')
        
        # Check if we're using AC-based method
        print()
        print('=== ESTIMATION METHOD ANALYSIS ===')
        if annual_summary.get("estimation_method") == "ac_based_fallback":
            print("Using AC-based fallback method because building not found in database")
            print()
            print("AC-BASED CALCULATION LOGIC:")
            print("1. Number of AC units = Rooms - Bathrooms = 2 - 2 = 0 → Default to 1 AC unit")
            print("2. Per AC cost for zip code (likely 10016 for East 34th St) ≈ $60/month")
            print("3. Seasonal factors applied (peak in July/August)")
            print("4. Base extra cost: $15")
            print("5. Energy rating factor: ~2.0 (based on building age/neighborhood)")
            print("6. Formula: (Per AC cost × AC units × seasonal factor) + $15 + ($10 × energy rating)")
            print()
            print("For this apartment:")
            print(f"- AC units: 1 (default)")
            print(f"- Per AC cost: ~$60 (Manhattan premium area)")
            print(f"- Base extra: $15")
            print(f"- Energy rating cost: ~$20")
            print(f"- Monthly range: $70-95 (depending on seasonal factor)")
        
        # Calculate our logic breakdown
        print()
        print('=== OUR CALCULATION LOGIC ===')
        if annual_summary.get("estimation_method") == "building_specific_intensity":
            intensity = building_data.get("Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)", 0)
            apt_sqft = 1343  # From listing
            annual_kwh = float(intensity) * apt_sqft
            print(f"1. Building Energy Intensity: {intensity} kWh/ft²")
            print(f"2. Apartment Size: {apt_sqft} ft²")
            print(f"3. Annual kWh = {intensity} × {apt_sqft} = {annual_kwh:.0f} kWh")
            print(f"4. Monthly kWh = {annual_kwh:.0f} ÷ 12 = {annual_kwh/12:.0f} kWh")
            print(f"5. Seasonal factors applied to distribute across months")
            print(f"6. Utility rates applied to calculate final bills")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_specific_address() 