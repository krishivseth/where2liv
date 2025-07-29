# Route Planning Setup Guide

## 🗺️ Google Maps API Setup

To enable the safe route planning feature, you need to configure a Google Maps API key.

### 1. Get Google Maps API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - **Directions API** (for route calculation)
   - **Maps JavaScript API** (for map display)
4. Go to "Credentials" → "Create credentials" → "API key"
5. Copy your API key

### 2. Configure API Key

**For the Frontend (Route Planner Page):**
```html
<!-- In frontend/public/route-planner.html, replace: -->
<script async defer 
    src="https://maps.googleapis.com/maps/api/js?key=YOUR_GOOGLE_MAPS_API_KEY&callback=initializeMap">
</script>

<!-- With your actual API key: -->
<script async defer 
    src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY_HERE&callback=initializeMap">
</script>
```

**For the Backend (Route Analysis):**
```python
# In route_analyzer.py, you can either:
# 1. Set environment variable
export GOOGLE_MAPS_API_KEY="your_api_key_here"

# 2. Or modify the RouteAnalyzer initialization in app.py:
route_analyzer = RouteAnalyzer(safety_analyzer, "your_api_key_here")
```

### 3. API Key Restrictions (Recommended)

For security, restrict your API key:

1. **Application restrictions:**
   - HTTP referrers: `http://localhost:*`, `chrome-extension://*`

2. **API restrictions:**
   - Directions API
   - Maps JavaScript API

## 🚀 Testing the Route Feature

### 1. Start Backend
```bash
cd /Users/sanchitbansal/Documents/WattsUp
python app.py
```

### 2. Build Extension
```bash
cd frontend
npm run build:extension
```

### 3. Test Route Planning

1. Load extension in Chrome
2. Visit a StreetEasy listing
3. Open WattsUp extension
4. Enter a destination in the "Safe Route Planning" section
5. Click "🗺️" to open the interactive map
6. View multiple route options with safety ratings

## 🛠️ How It Works

### User Flow
```
1. User enters destination in extension popup
2. Extension opens route-planner.html in new tab
3. Frontend calls backend API: POST /api/safe-routes
4. Backend calls Google Directions API for routes
5. Backend analyzes each route for safety using crime data
6. Frontend displays routes on interactive map with safety grades
```

### Route Categories
- **🛡️ Safest Route**: Highest safety score (may take longer)
- **⚖️ Balanced Route**: Best safety-to-time ratio
- **⚡ Fastest Route**: Shortest time (with safety warnings if needed)

### Safety Analysis
Routes are analyzed by:
- Breaking into segments by neighborhood
- Applying safety scores from NYC 311 crime data
- Weighting by distance through each area
- Generating overall route safety grade (A-F)

## 🔧 API Reference

### Backend Endpoint
```
POST http://127.0.0.1:5002/api/safe-routes

Body:
{
  "origin": "123 Main St, Queens, NY",
  "destination": "456 Broadway, Manhattan, NY", 
  "mode": "driving"
}

Response:
{
  "routes": [
    {
      "route_type": "safest",
      "overall_safety_score": 4.2,
      "overall_safety_grade": "B",
      "total_duration": {"text": "25 mins", "value": 1500},
      "safety_description": "Generally safe route with good ratings"
    }
  ],
  "recommendation": {
    "recommended_route_id": "route_0",
    "reason": "Best balance of safety and travel time"
  }
}
```

## 🐛 Troubleshooting

### Common Issues

**1. "Failed to load Google Maps"**
- Check your API key is valid
- Ensure Maps JavaScript API is enabled
- Verify API key restrictions allow chrome-extension://*

**2. "No routes found"**
- Check backend is running on port 5002
- Verify Google Directions API is enabled
- Ensure addresses are valid NYC locations

**3. "Route analysis failed"**
- Check backend logs for API errors
- Verify safety_analyzer.py is working
- Ensure crime_data.json is loaded

### Debug Tips

1. **Check browser console** for JavaScript errors
2. **Check backend logs** for API call failures
3. **Test API directly** with curl:
   ```bash
   curl -X POST http://127.0.0.1:5002/api/safe-routes \
     -H "Content-Type: application/json" \
     -d '{"origin":"Times Square","destination":"Brooklyn Bridge"}'
   ```

## 💰 Pricing Estimate

Google Maps API pricing (as of 2024):
- **Directions API**: $5 per 1,000 requests
- **Maps JavaScript API**: $7 per 1,000 loads

For moderate usage (50 routes/day), monthly cost ~$10-15.

## 🔐 Security Notes

- Never commit API keys to git
- Use environment variables in production
- Restrict API keys to specific domains/IPs
- Monitor usage in Google Cloud Console 