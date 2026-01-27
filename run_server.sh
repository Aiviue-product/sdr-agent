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
cd "$SCRIPT_DIR/backend" || exit
echo "📂 Working directory: $(pwd)"
echo ""

# Activate virtual environment
echo "🔄 Activating virtual environment..."
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "✅ Virtual environment activated!"
echo ""

# Check for ngrok public URL
echo "🔍 Checking for ngrok tunnel..."
# Better regex and error handling for curl
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o "https://[a-zA-Z0-9.-]*\.ngrok-free\.app" | head -n 1)

echo "------------------------------------------"
if [ -n "$NGROK_URL" ]; then
    echo "🔗 ngrok is ACTIVE!"
    echo "🌎 Public URL: $NGROK_URL"
    echo "📡 Webhook URL: $NGROK_URL/api/v1/linkedin/dm/webhook"
    echo ""
    echo "✅ TIP: Run 'python scripts/update_unipile_webhook.py' to update Unipile!"
else
    echo "⚠️  ngrok not detected. Start it manually if needed: ngrok http 8000"
fi
echo "------------------------------------------"
echo ""

echo "🌐 Starting FastAPI server on http://127.0.0.1:8000"
echo "📋 API Docs: http://127.0.0.1:8000/docs"
echo "=========================================="
echo ""

# Run the FastAPI server
uvicorn app.main:app --reload