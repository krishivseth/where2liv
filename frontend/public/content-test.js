// MINIMAL TEST CONTENT SCRIPT
console.log('🟢 TEST: Content script loaded successfully!');
console.log('🟢 TEST: Current URL:', window.location.href);
console.log('🟢 TEST: Hostname:', window.location.hostname);

// Simple message listener
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('🟢 TEST: Message received:', request);
    
    if (request.action === 'extractAddress') {
        console.log('🟢 TEST: Extract address request received');
        sendResponse({
            address: 'TEST ADDRESS - Content script working!',
            numRooms: 1,
            buildingName: 'TEST BUILDING',
            rawAddress: 'TEST RAW ADDRESS',
            sqFt: 1000,
            borough: 'TEST CITY',
            source: 'test'
        });
    }
    return true; // Important for async responses
});

// Test on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('🟢 TEST: DOM loaded');
});

// Test immediately
setTimeout(() => {
    console.log('🟢 TEST: Content script still running after 2 seconds');
}, 2000); 