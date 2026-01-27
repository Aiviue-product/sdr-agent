"""
WATI Webhook Updater Script
==========================
Automatically detects ngrok tunnel and updates WATI webhook configuration.
Similar to the Unipile webhook script pattern.

Usage:
    Development (ngrok): python scripts/update_wati_webhook.py
    Production:          python scripts/update_wati_webhook.py --url https://your-domain.com
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================
# CONFIGURATION
# ============================================

# Events we want to receive (all essential ones for SDR outreach)
WEBHOOK_EVENTS = [
    "message",                    # All inbound messages from leads
    "templateMessageSent_v2",     # When our template is sent
    "sentMessageDELIVERED_v2",    # When message is delivered (✓✓)
    "sentMessageREAD_v2",         # When message is read (blue ✓✓)
    "templateMessageFAILED_v2",   # When message fails to send
    "sentMessageREPLIED_v2",      # When message is replied
]

# Webhook endpoint path on our backend
WEBHOOK_PATH = "/api/v1/whatsapp/webhook"


def get_ngrok_url():
    """Detect current ngrok tunnel URL."""
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        tunnels = response.json().get("tunnels", [])
        for tunnel in tunnels:
            if tunnel['public_url'].startswith('https'):
                return tunnel['public_url']
    except Exception as e:
        print(f"⚠️ Could not detect ngrok: {e}")
    return None


def update_webhook(base_url: str = None):
    """
    Update WATI webhook configuration.
    
    Args:
        base_url: Override URL (for production). If None, uses ngrok.
    """
    # Load WATI credentials
    api_token = os.getenv("WATI_API_TOKEN")
    api_endpoint = os.getenv("WATI_API_ENDPOINT", "").rstrip('/')
    channel_number = os.getenv("WATI_CHANNEL_NUMBER")
    
    if not all([api_token, api_endpoint, channel_number]):
        print("❌ Missing WATI configuration in .env")
        print("   Required: WATI_API_TOKEN, WATI_API_ENDPOINT, WATI_CHANNEL_NUMBER")
        return False
    
    # Determine webhook URL
    if base_url:
        webhook_url = f"{base_url.rstrip('/')}{WEBHOOK_PATH}"
        print(f"🌐 Using production URL: {base_url}") 
    else:
        ngrok_url = get_ngrok_url()
        if not ngrok_url:
            print("❌ No ngrok tunnel found. Start ngrok first: ngrok http 8000")
            return False
        webhook_url = f"{ngrok_url}{WEBHOOK_PATH}"
        print(f"🔗 Using ngrok URL: {ngrok_url}")
    
    print(f"📡 Webhook endpoint: {webhook_url}")
    print(f"📋 Events: {', '.join(WEBHOOK_EVENTS)}")
    
    # Prepare request
    headers = {
        "Authorization": api_token if api_token.startswith("Bearer ") else f"Bearer {api_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # WATI expects an array of webhook configurations
    payload = [{
        "phoneNumber": channel_number,
        "status": 1,  # 1 = Enabled
        "url": webhook_url,
        "eventTypes": WEBHOOK_EVENTS
    }]
    
    print(f"\n⏳ Updating WATI webhook...")
    
    try:
        response = requests.post(
            f"{api_endpoint}/api/v2/webhookEndpoints",
            headers=headers,
            json=payload
        )
        
        data = response.json() if response.status_code == 200 else {}
        
        if response.status_code == 200 and data.get("ok"):
            print("\n✅ SUCCESS! Webhook updated.")
            print(f"   📡 URL: {webhook_url}")
            print(f"   📋 Events: {len(WEBHOOK_EVENTS)} registered")
            
            # Show registered webhooks if available
            if data.get("result"):
                print("\n   Registered webhooks:")
                for wh in data["result"]:
                    print(f"   - {wh.get('url', 'N/A')} ({len(wh.get('eventTypes', []))} events)")
            return True
            
        elif "exceed" in str(data.get("error", "")).lower():
            print("\n❌ WEBHOOK LIMIT REACHED!")
            print("   Your WATI plan allows maximum 4 webhooks.")
            print("\n   TO FIX:")
            print("   1. Go to WATI Dashboard → Automation → Webhooks")
            print("   2. Delete old/unused webhook URLs")
            print("   3. Run this script again")
            return False
            
        else:
            print(f"\n❌ Failed: {data.get('error', response.text)}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def main():
    print("=" * 50)
    print("📱 WATI WEBHOOK UPDATER")
    print("=" * 50)
    
    # Check for production URL argument
    production_url = None
    if len(sys.argv) > 1:
        if sys.argv[1] == "--url" and len(sys.argv) > 2:
            production_url = sys.argv[2]
        elif sys.argv[1].startswith("http"):
            production_url = sys.argv[1]
    
    success = update_webhook(production_url)
    
    print("=" * 50)
    
    if success:
        print("\n💡 Your webhook is now listening for:")
        for event in WEBHOOK_EVENTS:
            print(f"   • {event}")
        print("\n� Send a test message to verify!")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())