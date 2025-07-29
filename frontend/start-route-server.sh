#!/bin/bash

# Get the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"

echo "🗺️ Starting WattsUp Route Planner Web Server..."
echo "📁 Script location: $SCRIPT_DIR"
echo "📁 Serving from: $DIST_DIR"

# Check if dist directory exists
if [ ! -d "$DIST_DIR" ]; then
    echo "❌ Error: dist directory not found at $DIST_DIR"
    echo "🔧 Please run: npm run build:extension"
    exit 1
fi

# Check if route-planner.html exists
if [ ! -f "$DIST_DIR/route-planner.html" ]; then
    echo "❌ Error: route-planner.html not found in $DIST_DIR"
    echo "🔧 Please run: npm run build:extension"
    exit 1
fi

echo "✅ Files found, starting server..."
echo "🌐 URL: http://localhost:8000"
echo "🔗 Route Planner: http://localhost:8000/route-planner.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo "----------------------------------------"

cd "$DIST_DIR" && python3 -m http.server 8000 