import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def update_wati_webhook():
    """
    Automatically detects ngrok tunnel and registers it with WATI.
    Follows the pattern of unipile_webhook script for consistency.
    """
    api_token = os.getenv("WATI_API_TOKEN")
    api_endpoint = os.getenv("WATI_API_ENDPOINT")
    channel_number = os.getenv("WATI_CHANNEL_NUMBER")
    
    if not api_token or not api_endpoint:
        print("❌ Error: WATI_API_TOKEN or WATI_API_ENDPOINT not found in .env")
        return
        
    api_endpoint = api_endpoint.rstrip('/')

    # 1. Get current ngrok URL from local API
    try:
        print("🔍 Detecting ngrok tunnel...")
        ngrok_resp = requests.get("http://localhost:4040/api/tunnels")
        tunnels = ngrok_resp.json().get("tunnels", [])
        public_url = None
        for t in tunnels:
            if t['public_url'].startswith('https'):
                public_url = t['public_url']
                break
        
        if not public_url:
            print("❌ Error: No active ngrok tunnel found. Run 'ngrok http 8000' first!")
            return
            
        webhook_url = f"{public_url}/api/v1/whatsapp/webhook"
        print(f"🔗 Detected ngrok URL: {public_url}")
        print(f"📡 Target Webhook: {webhook_url}")
        
    except Exception as e:
        print(f"❌ Error talking to ngrok: {e}")
        print("💡 Make sure ngrok is running on your machine.")
        return

    # 2. Register Webhook with WATI
    # Prepare headers (handling Bearer prefix automatically)
    if api_token.startswith("Bearer "):
        auth_header = api_token
    else:
        auth_header = f"Bearer {api_token}"
        
    headers = {
        "Authorization": auth_header,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Try these event Type naming conventions
    # Convention 1: Dashed/Standard
    # Convention 2: V2 suffix (based on your logs)
    # Based on the OpenAPI doc provided by the user:
    # Example event types: "message", "newContactMessageReceived"
    candidate_events = [
        "message", 
        "newContactMessageReceived"
    ]
    
    # Payload as per OpenAPI: array of objects
    payload = [{
        "phoneNumber": channel_number,
        "status": 1,  # 1 = Enabled
        "url": webhook_url,
        "eventTypes": candidate_events
    }]
    
    print(f"\n⏳ Registering WATI webhook with events: {candidate_events}")
    try:
        response = requests.post(
            f"{api_endpoint}/api/v2/webhookEndpoints", 
            headers=headers, 
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                    "status": 1,
                    "url": webhook_url,
                    "eventTypes": valid_events
                }]
                requests.post(f"{api_endpoint}/api/v2/webhookEndpoints", headers=headers, json=final_payload)
                print("✅ Final Webhook registered with valid events.")
            else:
                print("❌ No valid events found among the candidates.")
            
    except Exception as e:
        print(f"❌ Error calling WATI API: {e}")

if __name__ == "__main__":
    print("="*50)
    print("📱 WATI AUTOMATIC WEBHOOK UPDATER (SMART)")
    print("="*50)
    update_wati_webhook()
    print("="*50)
