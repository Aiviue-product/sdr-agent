#!/bin/bash

# ===========================================
#  SDR Backend Server Startup Script
# ===========================================

# Get the directory where this script is located
SCRIPT_DIR="$(dirname "$0")"

echo "=========================================="
echo "  🚀 SDR Backend Server"
echo "=========================================="
echo ""

# Navigate to backend directory
cd "$SCRIPT_DIR/backend"
echo "📂 Working directory: $(pwd)"
echo ""

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/Scripts/activate

echo "✅ Virtual environment activated!"
echo "📍 Python: $(which python)"
echo "🐍 Version: $(python --version)"
echo ""

# Check database connection
echo "🔌 Checking database connection..."
python -c "from app.db.session import engine; print('✅ Database connection OK!')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Database check skipped (will connect on first request)"
fi
echo ""

echo "🌐 Starting FastAPI server on http://127.0.0.1:8000"
echo "📋 API Docs: http://127.0.0.1:8000/docs"
echo "=========================================="
echo ""

# Run the FastAPI server
uvicorn app.main:app --reload 
 