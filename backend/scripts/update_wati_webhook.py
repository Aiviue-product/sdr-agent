import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_wati_webhook():
    """
    Automatically detects ngrok tunnel and registers it with WATI.
    Uses precise event names derived from WATI dashboard v2 definitions.
    """
    api_token = os.getenv("WATI_API_TOKEN")
    api_endpoint = os.getenv("WATI_API_ENDPOINT")
    channel_number = os.getenv("WATI_CHANNEL_NUMBER")
    
    if not api_token or not api_endpoint:
        print("❌ Error: WATI_API_TOKEN or WATI_API_ENDPOINT not found in .env")
        return
        
    # Ensure endpoint is clean and doesn't end with a slash
    api_endpoint = api_endpoint.rstrip('/')

    # 1. Detect Ngrok
    try:
        print("🔍 Detecting ngrok tunnel...")
        ngrok_resp = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        tunnels = ngrok_resp.json().get("tunnels", [])
        public_url = next((t['public_url'] for t in tunnels if t['public_url'].startswith('https')), None)
        
        if not public_url:
            print("❌ Error: No active HTTPS ngrok tunnel found.")
            return
            
        webhook_url = f"{public_url}/api/v1/whatsapp/webhook"
        print(f"🔗 Ngrok URL: {public_url}")
        
    except Exception as e:
        print(f"❌ Error connecting to ngrok: {e}")
        return

    # 2. Setup Authentication
    auth_header = api_token if api_token.startswith("Bearer ") else f"Bearer {api_token}"
    headers = {
        "Authorization": auth_header,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # 3. Define Events (Updated based on your images)
    # These strings are the exact technical identifiers for the UI labels you shared
    events = [
        "message",                    # Message Received
        "newContactMessageReceived",  # New Contact Message
        "sessionMessageSent_v2",      # Session Message Sent v2
        "templateMessageSent_v2",     # Template Message Sent v2
        "sentMessageDELIVERED_v2",    # Sent Message is DELIVERED v2
        "sentMessageREAD_v2",         # Sent Message is READ v2
        "sentMessageREPLIED_v2",      # Sent Message is REPLIED v2
        "templateMessageFAILED_v2"    # Template message FAILED
    ]
    
    # The API expects an array of objects
    payload = [{
        "phoneNumber": channel_number,
        "status": 1, 
        "url": webhook_url,
        "eventTypes": events
    }]
    
    print(f"⏳ Syncing {len(events)} events to WATI...")
    
    try:
        # Note: Using /api/v2/webhookEndpoints as required by WATI v2
        response = requests.post(
            f"{api_endpoint}/api/v2/webhookEndpoints", 
            headers=headers, 
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                print("✅ Success! Webhook active.")
                print(f"📡 Endpoint: {webhook_url}")
            else:
                print(f"⚠️ API rejected request: {data.get('info', 'No details provided')}")
                print(f"🔍 Response Detail: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ HTTP Error {response.status_code}")
            # This will show if specific event names were invalid
            print(f"🔍 Server Message: {response.text}")
            
    except Exception as e:
        print(f"❌ Script Error: {e}")

if __name__ == "__main__":
    print("="*50)
    print("📱 WATI V2 WEBHOOK SYNC")
    print("="*50)
    update_wati_webhook()
    print("="*50) 