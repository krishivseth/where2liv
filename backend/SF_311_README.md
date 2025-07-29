# SF 311 Data Setup

## Overview
The system now uses a **hybrid approach** for SF 311 data:
- **Primary**: Historical CSV file (6+ months of data)
- **Supplement**: Recent API calls (last 7 days)

This provides much more robust neighborhood quality analysis with thousands of historical records instead of just ~100 recent ones.

## Setup Instructions

### 1. Download SF 311 Historical Data

Visit the SF Open Data Portal:
**https://data.sfgov.org/City-Infrastructure/311-Cases/vw6y-z8j6**

1. Click the **"Export"** button (top right)
2. Select **"CSV"** format
3. Download the file
4. Rename it to: `SF_311_Cases.csv`
5. Place it in the `backend/` directory (same folder as this README)

### 2. File Structure
```
backend/
├── SF_311_Cases.csv                    # ← Historical 311 data (you download)
├── Police_Department_Incident_...csv   # ← Police data (already exists)
├── safety_analyzer.py                  # ← Updated code
└── SF_311_README.md                    # ← This file
```

### 3. Expected Results

**Before (API-only):**
- ~100-1000 recent 311 records
- Many neighborhoods show 0-1 reports
- Inconsistent due to rate limiting

**After (CSV + API hybrid):**
- 10,000+ historical 311 records
- Rich neighborhood data (10-50+ reports per area)
- Consistent, reliable analysis
- Recent updates from API

### 4. Data Processing

The system will:
1. **Load CSV first** (filtered to last 6 months)
2. **Supplement with API** (last 7 days only)
3. **Remove duplicates** (based on Case ID)
4. **Normalize formats** (both sources → common format)

### 5. CSV Column Mapping

The code expects these columns in the CSV:
- `CaseID` or `Case ID` → unique identifier
- `Opened` → creation date
- `Closed` → closure date  
- `Category` → service type
- `Request Details` → description
- `Address` → location
- `Latitude` → coordinates
- `Longitude` → coordinates
- `Status` → current status

### 6. Fallback Behavior

If CSV is missing:
- ⚠️ Warning logged: "SF 311 CSV file not found"
- 🔄 Falls back to API-only mode
- 📊 Provides download URL in logs
- ✅ System continues to work (just with less data)

## Benefits

- **📈 10x more data**: Thousands vs hundreds of records
- **🎯 Better accuracy**: Rich historical context
- **⚡ Faster**: No API rate limiting issues
- **🔄 Always current**: API provides recent updates
- **💪 Robust**: Works even if API fails

## File Size Note

The SF 311 CSV file is typically 100-500MB depending on how much historical data you download. This is normal and provides much richer analysis than the API alone. 