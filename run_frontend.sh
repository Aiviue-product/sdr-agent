#!/bin/bash

# ===========================================
#  SDR Frontend Server Startup Script
# ===========================================

# Get the directory where this script is located
SCRIPT_DIR="$(dirname "$0")"

echo "==========================================" 
echo "  🎨 SDR Frontend Server"
echo "=========================================="
echo ""

# Navigate to client directory
cd "$SCRIPT_DIR/client/client"
echo "📂 Working directory: $(pwd)"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

echo "🌐 Starting Next.js dev server..."
echo "🔗 Frontend: http://localhost:3000"
echo "=========================================="
echo ""

# Run the Next.js dev server
npm run dev
