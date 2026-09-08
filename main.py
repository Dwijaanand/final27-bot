import os
import pyotp
import requests
from SmartApi import SmartConnect

API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except:
        pass

def main():
    try:
        totp = pyotp.TOTP(TOTP_SECRET).now()
        smart = SmartConnect(api_key=API_KEY)
        data = smart.generateSession(CLIENT_ID, PASSWORD, totp)
        
        if data.get('status'):
            refresh = data['data']['refreshToken']
            profile = smart.getProfile(refresh)
            telegram(f"✅ FINAL 27 Bot LIVE\nClient: {CLIENT_ID}\nProfile: {profile['data']['name']}")
            print("SUCCESS")
        else:
            raise Exception(data.get('message'))

    except Exception as e:
        print(e)
        telegram(f"❌ Bot Failed\nError: {e}")

if __name__ == "__main__":
    main()
