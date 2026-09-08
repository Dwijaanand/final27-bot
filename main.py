import os
import pyotp
import requests
import time
from SmartApi import SmartConnect

# --- Secrets from GitHub ---
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
    except Exception as e:
        print(f"Telegram Error: {e}")

def main():
    print("Starting FINAL 27 Bot...")
    try:
        if not all([API_KEY, CLIENT_ID, PASSWORD, TOTP_SECRET]):
            raise Exception("Secrets missing! GitHub Secrets check karo.")

        totp = pyotp.TOTP(TOTP_SECRET).now()
        print(f"TOTP: {totp}")

        smart = SmartConnect(api_key=API_KEY)
        session = smart.generateSession(CLIENT_ID, PASSWORD, totp)
        
        print(f"Session: {session}")
        
        if session and session.get('status') == True:
            telegram(f"✅ FINAL 27 Bot STARTED\nClient: {CLIENT_ID}\nLogin Success")
            
            # Yaha tumhara FINAL 27 ka logic aayega
            # Abhi ke liye sirf profile check kar raha hai
            profile = smart.getProfile(smart.getRefreshToken())
            print(profile)
            telegram(f"Profile OK: {CLIENT_ID} is Live")

        else:
            raise Exception
