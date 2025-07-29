// Site detection helper
function isZillowSite() {
    return window.location.hostname.includes('zillow.com');
}

function isStreetEasySite() {
    return window.location.hostname.includes('streeteasy.com');
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('WattsUp: Message listener triggered', request);
    
    if (request.action === 'extractAddress') {
        if (isZillowSite()) {
            // Zillow extraction
            const address = extractAddressFromZillow();
            const numRooms = extractRoomCountFromZillow();
            const buildingName = extractBuildingNameFromZillow();
            const sqFt = extractSquareFootageFromZillow();
            const city = extractCityFromZillow();
            const price = extractPriceFromZillow();
            const propertyType = extractPropertyTypeFromZillow();

            console.log('WattsUp: Extracting from Zillow page');

            sendResponse({
                address: address,
                numRooms: numRooms,
                buildingName: buildingName,
                rawAddress: address,
                sqFt: sqFt,
                borough: city, // Use city instead of borough for non-NYC
                price: price,
                propertyType: propertyType,
                source: 'zillow'
            });
        } else if (isStreetEasySite()) {
            // StreetEasy extraction (existing logic)
            const address = extractAddressFromPage();
            const numRooms = extractRoomCountFromPage();
            const buildingName = extractBuildingNameFromPage();
            const sqFt = extractSquareFootageFromPage();
            const borough = extractBoroughFromPage();
            
            // Combine building name and address for better matching
            let finalQuery = address;
            if (buildingName && address) {
                finalQuery = `${buildingName}, ${address}`;
            } else if (buildingName && !address) {
                finalQuery = buildingName;
            }
            
            console.log('WattsUp: Extracting from StreetEasy page');
            
            sendResponse({ 
                address: finalQuery, 
                numRooms: numRooms,
                buildingName: buildingName,
                rawAddress: address,
                sqFt: sqFt,
                borough: borough,
                source: 'streeteasy'
            });
        } else {
            console.log('WattsUp: Unsupported site');
            sendResponse({ 
                address: null, 
                numRooms: null,
                buildingName: null,
                rawAddress: null,
                sqFt: null,
                borough: null,
                source: 'unsupported'
            });
        }
    }
    return true; // Important: Enable async response
});

// Zillow-specific extraction functions
function extractAddressFromZillow() {
    console.log('WattsUp: Extracting address from Zillow...');

    // Try multiple selectors for address based on current Zillow structure
    const addressSelectors = [
        // 2024/2025 Zillow selectors
        'h1[data-testid="bdp-building-address"]',
        '[data-testid="bdp-building-address"]',
        'h1[data-testid="address"]',
        '[data-testid="address"]',
        
        // Common header selectors
        'h1.notranslate',
        '.summary-container h1',
        '.hdp-summary-address h1',
        
        // Breadcrumb and navigation
        'nav[aria-label="Breadcrumb"] a:last-child',
        '.breadcrumbs a:last-child',
        
        // Property details sections
        '.property-details h1',
        '.listing-details h1',
        
        // Generic h1 tags (last resort)
        'h1'
    ];

    for (const selector of addressSelectors) {
        const element = document.querySelector(selector);
        if (element && element.textContent) {
            const address = element.textContent.trim();
            console.log(`WattsUp: Checking selector "${selector}": "${address}"`);
            
            // Check if it looks like an address (has numbers and letters, and is reasonable length)
            if (address.length > 10 && address.length < 200 && 
                (address.includes(',') || /\d+.*[A-Za-z]/.test(address)) &&
                !address.toLowerCase().includes('zillow') &&
                !address.toLowerCase().includes('for sale') &&
                !address.toLowerCase().includes('for rent')) {
                console.log('WattsUp: Found address using selector:', selector, address);
                return address;
            }
        }
    }

    // Enhanced fallback: look for address in page title
    const title = document.title;
    console.log('WattsUp: Page title:', title);
    
    if (title) {
        // Try to extract address from title patterns like "123 Main St, City, ST | Zillow"
        const titlePatterns = [
            /^([^|]+)\s*\|\s*Zillow/i,  // "Address | Zillow"
            /^([^-]+)\s*-\s*Zillow/i,   // "Address - Zillow"  
            /^([^,]+,[^,]+,[^|]+)/i     // "Street, City, State"
        ];
        
        for (const pattern of titlePatterns) {
            const match = title.match(pattern);
            if (match) {
                const addressMatch = match[1].trim();
                if (addressMatch.length > 10 && addressMatch.length < 200) {
                    console.log('WattsUp: Found address in title:', addressMatch);
                    return addressMatch;
                }
            }
        }
    }

    // Last resort: search for address-like text in all text content
    console.log('WattsUp: Searching page content for address patterns...');
    const pageText = document.body.textContent || '';
    
    // Look for street address patterns in page text
    const addressPatterns = [
        /\b\d+[A-Za-z]?\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl|Court|Ct)\b[^,]*,\s*[A-Za-z\s]+,\s*[A-Z]{2}\b/gi,
        /\b\d+[A-Za-z]?\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl|Court|Ct)\b/gi
    ];
    
    for (const pattern of addressPatterns) {
        const matches = pageText.match(pattern);
        if (matches) {
            for (const match of matches) {
                const address = match.trim();
                if (address.length > 10 && address.length < 150) {
                    console.log('WattsUp: Found address in page content:', address);
                    return address;
                }
            }
        }
    }

    console.log('WattsUp: No address found on Zillow page');
    return null;
}

function extractRoomCountFromZillow() {
    console.log('WattsUp: Extracting room count from Zillow...');

    // Try to find bedroom count in the bed/bath/sqft section
    const bedBathSelectors = [
        '[data-testid="bed-bath-sqft-facts"]',  // Updated selector for new Zillow structure
        '[data-testid="bed-bath-sqft-section"]',
        '.summary-table',
        '.hdp-fact-ataglance-list',
        '.fact-group-container'
    ];

    for (const selector of bedBathSelectors) {
        const element = document.querySelector(selector);
        if (element) {
            const text = element.textContent;
            console.log('WattsUp: Checking bed/bath section text:', text);

            // Look for "X beds" or "X bed" pattern
            const bedMatch = text.match(/(\d+)\s*beds?/i);
            if (bedMatch) {
                const count = parseInt(bedMatch[1]);
                console.log('WattsUp: Found bedroom count:', count);
                return count;
            }

            // Check for studio
            if (/studio/i.test(text)) {
                console.log('WattsUp: Found studio apartment');
                return 0;
            }
        }
    }

    // More specific targeting for the new Zillow structure
    // Look for the specific span that contains "beds" text
    const bedSpans = document.querySelectorAll('span');
    for (const span of bedSpans) {
        if (span.textContent.trim().toLowerCase() === 'beds') {
            // Find the previous sibling or parent that contains the number
            const container = span.closest('[data-testid="bed-bath-sqft-fact-container"]');
            if (container) {
                const valueSpan = container.querySelector('span.hCiIMl, span[class*="StyledValueText"]');
                if (valueSpan) {
                    const count = parseInt(valueSpan.textContent.trim());
                    if (!isNaN(count) && count >= 0 && count <= 10) {
                        console.log('WattsUp: Found bedroom count via specific targeting:', count);
                        return count;
                    }
                }
            }
        }
    }

    // Fallback: search entire page text
    const pageText = document.body.textContent;

    // Look for bedroom patterns in page text
    const bedPatterns = [
        /(\d+)\s*beds?/i,
        /(\d+)\s*bedrooms?/i,
        /(\d+)\s*br/i
    ];

    for (const pattern of bedPatterns) {
        const matches = pageText.match(pattern);
        if (matches) {
            const count = parseInt(matches[1]);
            if (count >= 0 && count <= 10) {
                console.log('WattsUp: Found bedroom count in page text:', count);
                return count;
            }
        }
    }

    // Check for studio in page text
    if (/studio/i.test(pageText)) {
        console.log('WattsUp: Found studio in page text');
        return 0;
    }

    console.log('WattsUp: No room count found, defaulting to 1');
    return 1;
}

function extractSquareFootageFromZillow() {
    console.log('WattsUp: Extracting square footage from Zillow...');

    // Try bed/bath/sqft section first
    const bedBathSelectors = [
        '[data-testid="bed-bath-sqft-facts"]',  // Updated selector for new Zillow structure
        '[data-testid="bed-bath-sqft-section"]',
        '.summary-table',
        '.hdp-fact-ataglance-list'
    ];

    for (const selector of bedBathSelectors) {
        const element = document.querySelector(selector);
        if (element) {
            const text = element.textContent;

            // Look for sqft patterns
            const sqftMatch = text.match(/([\d,]{1,6})\s*sqft/i);
            if (sqftMatch) {
                const sqft = parseInt(sqftMatch[1].replace(/,/g, ''));
                if (sqft >= 100 && sqft <= 10000) {
                    console.log('WattsUp: Found square footage:', sqft);
                    return sqft;
                }
            }
        }
    }

    // More specific targeting for the new Zillow structure
    // Look for the specific span that contains "sqft" text
    const sqftSpans = document.querySelectorAll('span');
    for (const span of sqftSpans) {
        if (span.textContent.trim().toLowerCase() === 'sqft') {
            // Find the container that contains the number
            const container = span.closest('[data-testid="bed-bath-sqft-fact-container"]');
            if (container) {
                const valueSpan = container.querySelector('span.hCiIMl, span[class*="StyledValueText"]');
                if (valueSpan) {
                    const sqft = parseInt(valueSpan.textContent.trim().replace(/,/g, ''));
                    if (!isNaN(sqft) && sqft >= 100 && sqft <= 10000) {
                        console.log('WattsUp: Found square footage via specific targeting:', sqft);
                        return sqft;
                    }
                }
            }
        }
    }

    // Search entire page for sqft
    const pageText = document.body.textContent;
    const sqftPatterns = [
        /([\d,]{1,6})\s*sqft/gi,
        /([\d,]{1,6})\s*sq\.?\s*ft\.?/gi,
        /([\d,]{1,6})\s*square\s*feet/gi
    ];

    for (const pattern of sqftPatterns) {
        const matches = pageText.match(pattern);
        if (matches) {
            for (const match of matches) {
                const numberMatch = match.match(/([\d,]{1,6})/);
                if (numberMatch) {
                    const sqft = parseInt(numberMatch[1].replace(/,/g, ''));
                    if (sqft >= 100 && sqft <= 10000) {
                        console.log('WattsUp: Found square footage in page text:', sqft);
                        return sqft;
                    }
                }
            }
        }
    }

    console.log('WattsUp: No square footage found');
    return null;
}

function extractBuildingNameFromZillow() {
    console.log('WattsUp: Extracting building name from Zillow...');

    // For Zillow, building name might not be as prominent as on StreetEasy
    // Try to find it in property details or description
    const buildingSelectors = [
        '[data-testid="building-name"]',
        '.building-name',
        '.property-name'
    ];

    for (const selector of buildingSelectors) {
        const element = document.querySelector(selector);
        if (element && element.textContent) {
            const buildingName = element.textContent.trim();
            console.log('WattsUp: Found building name:', buildingName);
            return buildingName;
        }
    }

    // For condos/apartments, the address might be the best building identifier
    console.log('WattsUp: No specific building name found');
    return null;
}

function extractCityFromZillow() {
    console.log('WattsUp: Extracting city from Zillow...');

    // Extract city from address
    const address = extractAddressFromZillow();
    if (address) {
        // Look for city in address (usually after last comma)
        const parts = address.split(',');
        if (parts.length >= 2) {
            const cityState = parts[parts.length - 1].trim();
            const city = cityState.split(' ')[0];
            console.log('WattsUp: Found city:', city);
            return city;
        }
    }

    // Fallback: check URL for city
    const url = window.location.href;
    const cities = ['san-francisco', 'new-york', 'los-angeles', 'chicago', 'boston', 'seattle'];
    for (const city of cities) {
        if (url.toLowerCase().includes(city)) {
            const formattedCity = city.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase());
            console.log('WattsUp: Found city in URL:', formattedCity);
            return formattedCity;
        }
    }

    console.log('WattsUp: No city found');
    return null;
}

function extractPriceFromZillow() {
    console.log('WattsUp: Extracting price from Zillow...');

    const priceSelectors = [
        '[data-testid="price"]',
        '.notranslate',
        '.summary-container .price',
        '.hdp-summary-price'
    ];

    for (const selector of priceSelectors) {
        const element = document.querySelector(selector);
        if (element) {
            const text = element.textContent.trim();
            // Look for price pattern
            if (/\$[\d,]+/.test(text)) {
                console.log('WattsUp: Found price:', text);
                return text;
            }
        }
    }

    // Search page text for price
    const pageText = document.body.textContent;
    const priceMatch = pageText.match(/\$[\d,]+/);
    if (priceMatch) {
        console.log('WattsUp: Found price in page text:', priceMatch[0]);
        return priceMatch[0];
    }

    console.log('WattsUp: No price found');
    return null;
}

function extractPropertyTypeFromZillow() {
    console.log('WattsUp: Extracting property type from Zillow...');

    const pageText = document.body.textContent.toLowerCase();

    const propertyTypes = [
        'condominium', 'condo', 'apartment', 'house', 'townhouse',
        'single family', 'multi family', 'duplex', 'studio'
    ];

    for (const type of propertyTypes) {
        if (pageText.includes(type)) {
            console.log('WattsUp: Found property type:', type);
            return type;
        }
    }

    console.log('WattsUp: No property type found');
    return null;
}

// StreetEasy-specific extraction functions (existing logic)
function extractRoomCountFromPage() {
    // First try the specific structure: data-testid="propertyDetails"
    const propertyDetails = document.querySelector('[data-testid="propertyDetails"]');
    if (propertyDetails) {
        const items = propertyDetails.querySelectorAll('p');
        for (const item of items) {
            const text = item.textContent?.trim() || '';
            // Look for "X rooms" pattern
            const roomMatch = text.match(/(\d+)\s*rooms?/i);
            if (roomMatch) {
                const count = parseInt(roomMatch[1]);
                console.log('WattsUp: Found room count in propertyDetails:', count);
                return count;
            }
        }
    }

    // Fallback to bedroom count if rooms not found
    if (propertyDetails) {
        const items = propertyDetails.querySelectorAll('p');
        for (const item of items) {
            const text = item.textContent?.trim() || '';
            // Look for "X bed" pattern
            const bedMatch = text.match(/(\d+)\s*beds?/i);
            if (bedMatch) {
                const count = parseInt(bedMatch[1]);
                console.log('WattsUp: Found bedroom count in propertyDetails:', count);
                return count;
            }
        }
    }

    // Original fallback logic for other page structures
    const bedroomPatterns = [
        /(\d+)\s*(?:bed|bedroom|br)(?:room)?s?/i,
        /studio/i
    ];

    const selectors = [
        '[data-testid="listing-details"]',
        '[class*="listing-details"]',
        '[class*="unit-info"]',
        '[class*="bedroom"]',
        '[class*="details"]',
        '.listing-title',
        'h1',
        'h2',
        '[class*="summary"]'
    ];

    for (const selector of selectors) {
        const elements = document.querySelectorAll(selector);
        for (const element of elements) {
            if (element && element.textContent) {
                const text = element.textContent.trim();
                
                if (/studio/i.test(text)) {
                    return 0;
                }
                
                const bedroomMatch = text.match(/(\d+)\s*(?:bed|bedroom|br)(?:room)?s?/i);
                if (bedroomMatch) {
                    const count = parseInt(bedroomMatch[1]);
                    if (count >= 1 && count <= 10) {
                        return count;
                    }
                }
            }
        }
    }

    const allText = document.body.innerText;
    
    if (/studio\s*apartment|studio\s*unit|studio\s*rental/i.test(allText)) {
        return 0;
    }
    
    const matches = allText.match(/(\d+)\s*(?:bed|bedroom|br)(?:room)?s?/gi);
    if (matches && matches.length > 0) {
        for (const match of matches) {
            const numberMatch = match.match(/(\d+)/);
            if (numberMatch) {
                const count = parseInt(numberMatch[1]);
                if (count >= 1 && count <= 10) {
                    return count;
                }
            }
        }
    }

    return 1;
}

function extractBuildingNameFromPage() {
    // First try the specific structure: data-testid="about-building-section"
    const aboutBuildingSection = document.querySelector('[data-testid="about-building-section"]');
    if (aboutBuildingSection) {
        // Look for h6 tag within this section
        const h6Element = aboutBuildingSection.querySelector('h6');
        if (h6Element && h6Element.textContent) {
            const buildingName = h6Element.textContent.trim();
            if (buildingName) {
                console.log('WattsUp: Found building name in about-building-section:', buildingName);
                return buildingName;
            }
        }
    }

    // Fallback to original logic
    const aboutBuildingHeading = Array.from(document.querySelectorAll('h2, h3')).find(
        (el) => el.textContent?.trim().toLowerCase() === 'about the building'
    );

    if (aboutBuildingHeading) {
        const nextElement = aboutBuildingHeading.nextElementSibling;
        if (nextElement && nextElement.tagName === 'H6' && nextElement.textContent) {
            const buildingName = nextElement.textContent.trim();
            if (buildingName) {
                return buildingName;
            }
        }
    }

    const buildingNameSelectors = [
        '[data-testid="building-name"]',
        '[class*="building-name"]',
        '.building-title',
        '[itemprop="name"]'
    ];

    for (const selector of buildingNameSelectors) {
        const element = document.querySelector(selector);
        if (element && element.textContent?.trim()) {
            return element.textContent.trim();
        }
    }

    return null;
}

function extractAddressFromPage() {
    // First try the specific structure: h1[data-testid="address"]
    const addressElement = document.querySelector('h1[data-testid="address"]');
    if (addressElement && addressElement.textContent) {
        const fullAddress = addressElement.textContent.trim();
        console.log('WattsUp: Found address in h1[data-testid="address"]:', fullAddress);
        return fullAddress;
    }

    // Fallback to original logic
    const aboutBuildingSection = Array.from(document.querySelectorAll('*')).find(el =>
        el.textContent?.includes('About the building')
    );

    if (aboutBuildingSection) {
        const parent = aboutBuildingSection.parentElement;
        if (parent) {
            const siblings = Array.from(parent.children);
            for (const sibling of siblings) {
                if (sibling !== aboutBuildingSection) {
                    const text = sibling.textContent?.trim();
                    if (text && text.length > 10 && text.length < 150) {
                        const fullAddressPattern = /\d+.*[A-Z]{2}\s+\d{5}/i;
                        if (fullAddressPattern.test(text)) {
                            return text;
                        }
                    }
                }
            }
        }
    }

    const selectors = [
        'h1[data-testid="listing-title"]',
        '.listing-title h1',
        '[data-testid="address"]',
        '.address',
        'h1',
        '.listing-details h1',
        '[class*="address"]',
        '[class*="title"]'
    ];

    for (const selector of selectors) {
        const element = document.querySelector(selector);
        if (element && element.textContent?.trim()) {
            const text = element.textContent.trim();
            const cleanText = text.replace(/\s+/g, ' ').trim();
            if (cleanText.length > 10 && cleanText.length < 150) {
                const fullAddressPattern = /\d+.*[A-Z]{2}\s+\d{5}/i;
                if (fullAddressPattern.test(cleanText)) {
                    return cleanText.slice(0, -5);
                }
            }
        }
    }

    const allText = document.body.innerText;
    const fullAddressPattern = /\d+.*[A-Z]{2}\s+\d{5}/i;
    const fullMatch = allText.match(fullAddressPattern);

    if (fullMatch) {
        return fullMatch[0].slice(0, -5);
    }

    return null;
}

function extractSquareFootageFromPage() {
    // First try the specific structure: data-testid="propertyDetails"
    const propertyDetails = document.querySelector('[data-testid="propertyDetails"]');
    if (propertyDetails) {
        const items = propertyDetails.querySelectorAll('p');
        for (const item of items) {
            const text = item.textContent?.trim() || '';
            // Look for text ending with "ft²"
            if (text.includes('ft²') && !text.includes('per ft²')) {
                // Extract just the number
                const match = text.match(/(\d+(?:,\d+)?)\s*ft²/);
                if (match) {
                    // Remove commas and parse
                    const sqft = parseInt(match[1].replace(/,/g, ''));
                    if (sqft >= 100 && sqft <= 10000) {
                        console.log('WattsUp: Found square footage in propertyDetails:', sqft);
                        return sqft;
                    }
                }
            }
        }
    }

    // Fallback to original logic
    const sqftPatterns = [
        /([\d,]{1,6})\s*(?:sq\.?\s*ft\.?|square\s*feet|ft²|ft2)/i,
        /([\d,]{1,6})\s*SF/i,
        /([\d,]{1,6})\s*sqft/i
    ];

    const selectors = [
        '[data-testid="listing-details"]',
        '[class*="listing-details"]',
        '[class*="unit-info"]',
        '[class*="details"]',
        '[class*="specs"]',
        '[class*="features"]',
        '.listing-title',
        '.vital-info',
        '.detail-cell',
        '[class*="size"]',
        '[class*="area"]',
        'li',
        'span',
        'div'
    ];

    for (const selector of selectors) {
        const elements = document.querySelectorAll(selector);
        for (const element of elements) {
            if (element && element.textContent) {
                const text = element.textContent.trim();
                
                for (const pattern of sqftPatterns) {
                    const match = text.match(pattern);
                    if (match) {
                        const sqft = parseInt(match[1].replace(/,/g, ''));
                        if (sqft >= 100 && sqft <= 10000) {
                            console.log('WattsUp: Found square footage:', sqft);
                            return sqft;
                        }
                    }
                }
            }
        }
    }

    const allText = document.body.innerText;
    
    for (const pattern of sqftPatterns) {
        const matches = allText.match(new RegExp(pattern.source, 'gi'));
        if (matches && matches.length > 0) {
            for (const match of matches) {
                const numberMatch = match.match(/([\d,]{1,6})/);
                if (numberMatch) {
                    const sqft = parseInt(numberMatch[1].replace(/,/g, ''));
                    if (sqft >= 100 && sqft <= 10000) {
                        console.log('WattsUp: Found square footage in page text:', sqft);
                        return sqft;
                    }
                }
            }
        }
    }

    console.log('WattsUp: No square footage found on page');
    return null;
}

function extractBoroughFromPage() {
    // First try: Look for borough in breadcrumb navigation
    const breadcrumbNav = document.querySelector('nav[aria-label="breadcrumb"]');
    if (breadcrumbNav) {
        const links = breadcrumbNav.querySelectorAll('a');
        for (const link of links) {
            const text = link.textContent?.trim();
            // Check if the link text is one of NYC's boroughs
            if (text && ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island'].includes(text)) {
                console.log('WattsUp: Found borough in breadcrumb:', text);
                return text;
            }
        }
    }

    // Second try: Parse from title tag
    const titleElement = document.querySelector('title');
    if (titleElement && titleElement.textContent) {
        const title = titleElement.textContent;
        // Look for pattern "in [Neighborhood], [Borough] | StreetEasy"
        const titleMatch = title.match(/in\s+[^,]+,\s+([^|]+)\s*\|/);
        if (titleMatch) {
            const potentialBorough = titleMatch[1].trim();
            // Verify it's a valid borough
            if (['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island'].includes(potentialBorough)) {
                console.log('WattsUp: Found borough in title:', potentialBorough);
                return potentialBorough;
            }
        }
    }

    // Third try: Look in the address itself
    const address = extractAddressFromPage();
    if (address) {
        const boroughPatterns = [
            { pattern: /\bManhattan\b/i, name: 'Manhattan' },
            { pattern: /\bBrooklyn\b/i, name: 'Brooklyn' },
            { pattern: /\bQueens\b/i, name: 'Queens' },
            { pattern: /\bBronx\b/i, name: 'Bronx' },
            { pattern: /\bStaten\s*Island\b/i, name: 'Staten Island' }
        ];
        
        for (const { pattern, name } of boroughPatterns) {
            if (pattern.test(address)) {
                console.log('WattsUp: Found borough in address:', name);
                return name;
            }
        }
    }

    console.log('WattsUp: No borough found on page');
    return null;
}

// Auto-extract on page load
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        if (isZillowSite()) {
            console.log('WattsUp: Auto-extracting from Zillow page...');
            const address = extractAddressFromZillow();
            const sqFt = extractSquareFootageFromZillow();
            const numRooms = extractRoomCountFromZillow();
            const price = extractPriceFromZillow();
            const city = extractCityFromZillow();

            if (address) {
                console.log('WattsUp: Successfully extracted Zillow data:');
                console.log('  Address:', address);
                console.log('  Rooms:', numRooms);
                console.log('  Square Feet:', sqFt);
                console.log('  Price:', price);
                console.log('  City:', city);
            } else {
                console.log('WattsUp: Could not extract data from this Zillow page');
            }
        } else if (isStreetEasySite()) {
            console.log('WattsUp: Auto-extracting from StreetEasy page...');
            const address = extractAddressFromPage();
            const buildingName = extractBuildingNameFromPage();
            const sqFt = extractSquareFootageFromPage();
            const numRooms = extractRoomCountFromPage();
            const borough = extractBoroughFromPage();

            if (address || buildingName) {
                console.log('WattsUp: Successfully extracted StreetEasy data:');
                console.log('  Address:', address);
                console.log('  Building name:', buildingName);
                console.log('  Square footage:', sqFt);
                console.log('  Room count:', numRooms);
                console.log('  Borough:', borough);
            } else {
                console.log('WattsUp: No address or building name found on this StreetEasy page');
            }
        }
    }, 2000); // Wait for page to fully load
}); 