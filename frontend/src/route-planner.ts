import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Map setup
const map = L.map('map').setView([40.7128, -74.0060], 13); // Default to NYC
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

const routeColors: { [key: string]: string } = {
    safest: '#28a745',
    balanced: '#ffc107',
    fastest: '#dc3545',
    default: '#007bff'
};

function getRouteColor(routeType: string): string {
    return routeColors[routeType] || routeColors.default;
}

async function fetchAndDisplayRoutes(origin: string, destination: string) {
    const API_ENDPOINT = "http://127.0.0.1:61188/api/safe-routes";
    const loadingElement = document.getElementById('loading');
    const routesElement = document.getElementById('routes');

    if (!loadingElement || !routesElement) return;

    loadingElement.style.display = 'block';

    try {
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ origin, destination, mode: 'driving' })
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }

        displayRoutes(data.routes);

    } catch (error) {
        if (error instanceof Error) {
            routesElement.innerHTML = `<div class="error">Failed to fetch routes: ${error.message}</div>`;
        } else {
            routesElement.innerHTML = `<div class="error">An unknown error occurred.</div>`;
        }
    } finally {
        loadingElement.style.display = 'none';
    }
}

function displayRoutes(routes: any[]) {
    const routesElement = document.getElementById('routes');
    if (!routesElement) return;

    routesElement.innerHTML = ''; // Clear previous routes

    if (!routes || routes.length === 0) {
        routesElement.innerHTML = '<div>No routes found.</div>';
        return;
    }

    routes.forEach(route => {
        // Draw route on map
        const polyline = L.polyline(decodePolyline(route.polyline), { 
            color: getRouteColor(route.route_type),
            weight: 6,
            opacity: 0.8
        }).addTo(map);

        map.fitBounds(polyline.getBounds());

        // Display route details
        const routeDiv = document.createElement('div');
        routeDiv.className = 'route-option';
        routeDiv.innerHTML = `
            <h3>${route.summary} (${route.route_type})</h3>
            <p><strong>Duration:</strong> ${route.total_duration.text}</p>
            <p><strong>Distance:</strong> ${route.total_distance.text}</p>
            <p><strong>Safety Score:</strong> ${route.overall_safety_score.toFixed(2)}/5.0 (Grade ${route.overall_safety_grade})</p>
            <p>${route.safety_description}</p>
        `;
        routesElement.appendChild(routeDiv);
    });
}

function decodePolyline(encoded: string): L.LatLngExpression[] {
    let lat = 0, lng = 0;
    const path: L.LatLngExpression[] = [];
    let index = 0;

    while (index < encoded.length) {
        let b, shift = 0, result = 0;
        do {
            b = encoded.charCodeAt(index++) - 63;
            result |= (b & 0x1f) << shift;
            shift += 5;
        } while (b >= 0x20);
        const dlat = ((result & 1) ? ~(result >> 1) : (result >> 1));
        lat += dlat;

        shift = 0;
        result = 0;
        do {
            b = encoded.charCodeAt(index++) - 63;
            result |= (b & 0x1f) << shift;
            shift += 5;
        } while (b >= 0x20);
        const dlng = ((result & 1) ? ~(result >> 1) : (result >> 1));
        lng += dlng;

        path.push([lat / 1e5, lng / 1e5]);
    }
    return path;
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const origin = params.get('origin');
    const destination = params.get('destination');

    if (origin && destination) {
        document.getElementById('origin')!.textContent = origin;
        document.getElementById('destination')!.textContent = destination;
        fetchAndDisplayRoutes(origin, destination);
    } else {
        document.getElementById('loading')!.textContent = 'Missing origin or destination.';
    }
}); 