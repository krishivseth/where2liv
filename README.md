# Where2Liv - SF Energy & Safety Route Planner

Frontend: A React + TypeScript + Tailwind CSS Chrome extension that calculates monthly energy costs for San Francisco listings and provides safe route planning.

Backend: A Flask-based backend API for estimating monthly electricity bills for SF residential apartments using building energy data and safety analysis.

## 🏗️ System Architecture

```
├── backend/
│   ├── app.py                    # Main Flask application
│   ├── data_processor.py         # CSV data loading and processing
│   ├── address_matcher.py        # Fuzzy address matching
│   ├── bill_estimator.py         # Core estimation algorithms
│   ├── seasonality_factors.py    # Monthly usage patterns
│   ├── rate_calculator.py        # PG&E utility rate calculations
│   ├── safety_analyzer.py        # SF crime and safety analysis
│   ├── route_analyzer.py         # Route planning and analysis
│   ├── reviews_analyzer.py       # AI-powered reviews analysis
│   └── SF_Building_Energy_Filtered_Clean.csv  # SF building energy data
├── frontend/                     # Chrome extension
├── safe-route/                   # Next.js route planner
└── env/                          # Python virtual environment
```

## 🚀 Quick Start

### Backend Installation

1. **Activate virtual environment:**
```bash
source env/bin/activate
```

2. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

3. **Ensure the SF data file is present:**
```bash
ls -la SF_Building_Energy_Filtered_Clean.csv
```

4. **Test the system:**
```bash
python test_system.py
```

5. **Start the Flask application:**
```bash
python app.py
```

The API will be available at `http://localhost:5000` (or dynamically assigned port)

### Frontend Installation

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Build the extension:**
```bash
npm run build:extension
```

### Safe-Route Installation

1. **Install dependencies:**
```bash
cd safe-route
npm install
```

2. **Start development server:**
```bash
npm run dev
```

## 🔧 Loading the Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `frontend/dist` folder (created after building)
5. The extension will appear in your Chrome toolbar

## 📡 API Endpoints

### Health Check
```bash
GET /health
```

### Estimate Electricity Bill
```bash
POST /api/estimate
Content-Type: application/json

{
  "address": "1015 Ashbury St, San Francisco",
  "num_rooms": 2,
  "apartment_type": "1br",
  "building_type": "residential",
  "include_demand_charges": false
}
```

### Safety Analysis
```bash
POST /api/safety
Content-Type: application/json

{
  "address": "1015 Ashbury St, San Francisco"
}
```

### Search Buildings
```bash
GET /api/search?q=Ashbury&limit=5
```

### Get Building Details
```bash
GET /api/building/<property_id>
```

## 🧮 Estimation Algorithm

### Core Components

1. **Base Consumption**: Uses building's weather-normalized electricity intensity (kWh/ft²)
2. **Apartment Sizing**: Estimates apartment size based on room count
3. **Building Efficiency**: Adjusts for building age and type
4. **Seasonality**: Applies SF-specific monthly usage patterns
5. **Rate Calculation**: Uses current PG&E rate structures

### Key Factors

```python
# Building efficiency by age
if year_built >= 2010: efficiency_factor = 0.85  # More efficient
elif year_built >= 1980: efficiency_factor = 1.00  # Average
else: efficiency_factor = 1.10  # Less efficient

# Apartment size estimates (SF adjusted)
apartment_sizes = {
    0: 400,   # Studio
    1: 650,   # 1BR  
    2: 850,   # 2BR
    3: 1100,  # 3BR
    4: 1400   # 4BR+
}

# Seasonal factors (SF climate)
monthly_factors = {
    1: 1.15,   # January (mild winter)
    7: 1.10,   # July (cool summer)
    5: 0.90    # May (pleasant weather)
}
```

## 💡 Example Usage

### cURL Examples

```bash
# Estimate bill for 2BR apartment
curl -X POST http://localhost:5000/api/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "address": "1015 Ashbury St, San Francisco",
    "num_rooms": 2,
    "apartment_type": "1br"
  }'

# Safety analysis
curl -X POST http://localhost:5000/api/safety \
  -H "Content-Type: application/json" \
  -d '{
    "address": "1015 Ashbury St, San Francisco"
  }'

# Search for buildings
curl "http://localhost:5000/api/search?q=Ashbury&limit=5"
```

### Python Example

```python
import requests

# Estimate electricity bill
response = requests.post('http://localhost:5000/api/estimate', json={
    'address': '1015 Ashbury St, San Francisco',
    'num_rooms': 2,
    'apartment_type': '1br',
    'building_type': 'residential'
})

if response.status_code == 200:
    data = response.json()
    print(f"Annual total: ${data['annual_summary']['total_bill']}")
    print(f"Average monthly: ${data['annual_summary']['average_monthly_bill']}")

# Safety analysis
safety_response = requests.post('http://localhost:5000/api/safety', json={
    'address': '1015 Ashbury St, San Francisco'
})

if safety_response.status_code == 200:
    safety_data = safety_response.json()
    print(f"Safety rating: {safety_data['safety_rating']}/100")
```

## 📊 Sample Response

```json
{
  "building_info": {
    "property_name": "1015 Ashbury St",
    "address": "1015 Ashbury St",
    "city": "San Francisco",
    "neighborhood": "Haight-Ashbury",
    "property_type": "Multifamily Housing",
    "year_built": "1920",
    "building_efficiency": "average"
  },
  "estimation_parameters": {
    "num_rooms": 2,
    "estimated_apartment_sqft": 850,
    "building_intensity_kwh_per_sqft": 12.5,
    "efficiency_factor": 1.10
  },
  "monthly_estimates": [
    {
      "month": "January",
      "kwh_estimate": 425,
      "estimated_bill": 85.50,
      "seasonal_factor": 1.15
    }
  ],
  "annual_summary": {
    "total_kwh": 4200,
    "total_bill": 945.00,
    "average_monthly_bill": 78.75,
    "peak_month": "August",
    "peak_bill": 95.20
  },
  "rate_structure": {
    "utility": "PG&E",
    "base_charge": 12.50,
    "first_tier_rate": 0.28,
    "tier_threshold": 300
  }
}
```

## 🔧 Configuration

### Utility Rates
Update rates in `rate_calculator.py`:

```python
self.pge_residential = {
    'base_charge': 12.50,
    'delivery_rate_tier1': 0.15,
    'supply_rate': 0.13,
    'tier_threshold': 300
}
```

### Seasonality Factors
Modify patterns in `seasonality_factors.py`:

```python
monthly_factors = {
    1: 1.15,  # January
    7: 1.10,  # July
    # ... other months
}
```

## 📈 Data Sources

### San Francisco
- **Building Data**: SF Building Energy Benchmark Data (Local Law 20)
- **Utility Rates**: PG&E 2024 rate schedules
- **Seasonality**: SF energy usage patterns and mild climate data
- **Safety Data**: SF Open Data APIs (311 service requests, SFPD crime data)
- **Crime Data**: SF Police Department Incident Reports (2018-Present)

### Route Planning
- **Routing**: OpenStreetMap routing via OSRM
- **Geocoding**: Nominatim geocoding service
- **Crime Heatmaps**: SF crime data visualization

## ⚠️ Limitations

1. **Annual Data Only**: Building data is annual; monthly breakdowns are estimated
2. **Rate Accuracy**: Utility rates change periodically and may not reflect current tariffs
3. **Building Match**: Address matching may not be perfect for all addresses
4. **Apartment Assumptions**: Size estimates are approximations based on room count
5. **Crime Data**: Limited to reported incidents; may not reflect all safety concerns

## 🧪 Testing

Run comprehensive tests:
```bash
cd backend
python test_system.py
```

Test individual components:
```python
from data_processor import DataProcessor
from bill_estimator import BillEstimator

# Test data loading
dp = DataProcessor('SF_Building_Energy_Filtered_Clean.csv')
dp.load_data()

# Test estimation
be = BillEstimator(dp)
# ... estimation tests
```

## 📝 Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (missing fields, invalid data)
- `404`: Building not found
- `500`: Internal server error

## 🔮 Future Enhancements

1. **Real-time Rates**: Integration with PG&E APIs for current rates
2. **Weather Data**: Historical weather data for better seasonality
3. **Machine Learning**: Improve estimates with ML models
4. **Time-of-Use**: Support for time-of-use rate plans
5. **Solar Integration**: Account for rooftop solar generation
6. **Enhanced Safety**: Real-time crime alerts and neighborhood insights

## 📞 Support

For issues or questions:
1. Check the test script output: `python test_system.py`
2. Review log files for error details
3. Verify CSV data integrity and column mappings

## 📄 License

This project uses SF open data and is intended for educational/research purposes.
