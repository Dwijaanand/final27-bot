import os, pytotp, time, requests, datetime
from SmartApi import SmartConnect
import pandas as pd
import numpy as np

API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

STOCKS_FINAL_15 = ["MANAPPURAM","CUMMINSIND","CHENNPETRO","DCXIND","IRFC","TORNTPOWER","GOPOWER","OIL","DEEPAKNTR","ABB","POWERGRID","SAIL","FEDERALBNK","PETRONET","NTPC"]

def login():
    obj = SmartConnect(api_key=API_KEY)
    obj.generateSession(CLIENT_ID, PASSWORD, pytotp.TOTP(TOTP_SECRET).now())
    return obj

def get_token_map():
    data = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=20).json()
    return {d['symbol'].replace('-EQ',''): d['token'] for d in data if d['exch_seg']=='NSE'}

def supertrend(df, p=10, m=3.0):
    hl2 = (df['h'] + df['l']) / 2
    df['tr'] = np.maximum(df['h']-df['l'], np.maximum(abs(df['h']-df['c'].shift()), abs(df['l']-df['c'].shift())))
    df['atr'] = df['tr'].ewm(alpha=1/p, min_periods=p).mean()
    df['up'] = hl2 + m * df['atr']
    df['lo'] = hl2 - m * df['atr']
    df['st_dir'] = 1
    for i in range(1, len(df)):
        if df['c'].iloc[i] < df['lo'].iloc[i-1]:
            df.loc[df.index[i], 'st_dir'] = -1
        elif df['c'].iloc[i] > df['up'].iloc[i-1]:
            df.loc[df.index[i], 'st_dir'] = 1
        else:
            df.loc[df.index[i], 'st_dir'] = df['st_dir'].iloc[i-1]
            if df['st_dir'].iloc[i]==1 and df['lo'].iloc[i] < df['lo'].iloc[i-1]:
                df.loc[df.index[i], 'lo'] = df['lo'].iloc[i-1]
            if df['st_dir'].iloc[i]==-1 and df['up'].iloc[i] > df['up'].iloc[i-1]:
                df.loc[df.index[i], 'up'] = df['up'].iloc[i-1]
    df['supertrend'] = np.where(df['st_dir']==1, df['lo'], df['up'])
    return df

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except:
        pass

def main():
    api = login()
    token_map = get_token_map()
    print(f"LOGIN OK | FINAL 15 SCANNER ONLY | {datetime.datetime.now().strftime('%d-%b %H:%M')}")

    buys = []
    for sym in STOCKS_FINAL_15:
        try:
            token = token_map.get(sym)
            if not token: continue
            to_date = datetime.date.today()
            from_date = to_date - datetime.timedelta(days=200)
            params = {"exchange": "NSE", "symboltoken": token, "interval": "ONE_DAY", "fromdate": from_date.strftime("%Y-%m-%d %H:%M"), "todate": to_date.strftime("%Y-%m-%d %H:%M")}
            hist = api.getCandleData(params)
            if not hist or 'data' not in hist: continue
            df = pd.DataFrame(hist['data'], columns=['dt','o','h','l','c','v'])
            df = supertrend(df)
            df['EMA20'] = df['c'].ewm(20).mean()
            df['EMA50'] = df['c'].ewm(50).mean()
            df['VOLAVG'] = df['v'].rolling(20).mean()
            delta = df['c'].diff()
            gain = (delta.where(delta>0,0)).ewm(alpha=1/14, min_periods=14).mean()
            loss = (-delta.where(delta<0,0)).ewm(alpha=1/14, min_periods=14).mean()
            rs = gain/loss
            df['RSI'] = 100 - (100/(1+rs))
            last = df.iloc[-1]
            if last['c'] > last['supertrend'] and last['c'] > last['EMA20'] and last['EMA20'] > last['EMA50'] and last['RSI'] > 55:
                buys.append(f"{sym} - PRICE {round(last['c'],2)}, RSI {round(last['RSI'],1)}")
            time.sleep(0.3)
        except:
            continue

    if buys:
        msg = f"🔥 *FINAL 15 - BUY SCAN* ({datetime.datetime.now().strftime('%d-%b %H:%M')})\n\n"
        for b in buys:
            msg += f"✅ {b}\n"
        msg += f"\nManual Entry Karo - No Auto Order"
    else:
        msg = f"FINAL 15 SCAN ({datetime.datetime.now().strftime('%d-%b %H:%M')}) - No BUY found today"

    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    main()
