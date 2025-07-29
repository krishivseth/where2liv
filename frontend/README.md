# WattsUp - Energy Cost Calculator Chrome Extension

A React + TypeScript + Tailwind CSS Chrome extension that calculates monthly energy costs for StreetEasy listings.

## 🚀 Features

- 🔍 Automatically detects addresses from StreetEasy listing pages
- ⚡ Calculates estimated monthly energy costs
- 🎨 Modern UI built with React, TypeScript, and Tailwind CSS
- 🚀 Simple one-click energy cost calculation
- 📱 Responsive popup design optimized for Chrome extensions

## 🛠️ Tech Stack

- **React 19** - Modern React with hooks
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first CSS framework
- **Vite** - Fast build tool
- **Chrome Extension API** - Browser extension functionality

## 📦 Installation & Development

1. **Install dependencies:**

   ```bash
   npm install
   ```

2. **Start development server:**

   ```bash
   npm run dev
   ```

3. **Build the extension:**
   ```bash
   npm run build:extension
   ```

## 🔧 Loading the Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `dist` folder (created after building)
5. The extension will appear in your Chrome toolbar

## 🎯 Usage

1. Navigate to any StreetEasy listing page (e.g., `https://streeteasy.com/for-rent/...`)
2. Click the WattsUp extension icon in your Chrome toolbar
3. The extension will automatically detect the address
4. Click "Calculate Energy Cost" to get the monthly energy estimate

## 🔍 Address Extraction

The extension uses multiple methods to extract addresses:

1. **CSS Selectors** - Targets common StreetEasy DOM elements
2. **Regex Pattern Matching** - Fallback for address-like text
3. **Content Script Injection** - Executes on the page to extract data

## 🐛 Troubleshooting

- **Address not detected or Extension not working:** Ensure you're on a StreetEasy listing page
- **Build errors:** Run `npm install` and try `npm run build:extension`
