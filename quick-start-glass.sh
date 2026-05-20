#!/bin/bash
# Quick Start Script for Glass Design Frontend

echo "🚀 Glass Design Frontend - Quick Start"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Node.js
echo "${BLUE}📦 Checking Node.js installation...${NC}"
if ! command -v node &> /dev/null; then
    echo "${RED}❌ Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi
echo "${GREEN}✅ Node.js $(node --version) installed${NC}"
echo ""

# Navigate to frontend_glass
echo "${BLUE}📂 Navigating to frontend_glass directory...${NC}"
cd "$(dirname "$0")/frontend_glass" || exit 1
echo "${GREEN}✅ In $(pwd)${NC}"
echo ""

# Install dependencies
echo "${BLUE}📥 Installing dependencies...${NC}"
if npm install; then
    echo "${GREEN}✅ Dependencies installed${NC}"
else
    echo "${RED}❌ Failed to install dependencies${NC}"
    exit 1
fi
echo ""

# Start dev server
echo "${YELLOW}🎬 Starting development server...${NC}"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${GREEN}✅ Server running at: http://localhost:5173${NC}"
echo ""
echo "📝 Important:"
echo "   • Backend must be running on http://localhost:8000"
echo "   • Open browser to http://localhost:5173"
echo "   • Changes auto-reload"
echo "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

npm run dev
