import pyotp, time, requests, datetime
from SmartApi import SmartConnect
import pandas as pd
import numpy as np

API_KEY = ''
CLIENT_ID = ''
PASSWORD = ''
TOTP_SECRET = ''

BOT_TOKEN = ''
CHAT_ID = ''

STOCKS_FINAL_15 = ['MANAPPURAM','CUMMINSIND','CHENNPETRO','DIXON','IRFC','TORNTPOWER','CGPOWER','OIL','DEEPAKNTR','ABB','MAZDOCK','TRENT','NATIONALUM','IRCTC','BOSCHLTD']

def login():
    obj = SmartConnect(api_key=API_KEY)
    obj.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
    return obj

def get_token_map():
    data = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
    return {d['symbol'].replace('-EQ',''): d['token'] for d in data if d['exch_seg']=='NSE'}

def supertrend(df, p=10, m=3.0):
    hl2 = (df['h'] + df['l']) / 2
    df['tr'] = np.maximum(df['h']-df['l'], np.maximum(abs(df['h']-df['c'].shift()), abs(df['l']-df['c'].shift())))
    df['atr'] = df['tr'].ewm(alpha=1/p, min_periods=p).mean()
    df['up'] = hl2 + m * df['atr']
    df['lo'] = hl2 - m * df['atr']
    df['st_dir'] = 1
    for i in range(1, len(df)):
        if df['c'].iloc[i] > df['up'].iloc[i-1]: df.loc[df.index[i], 'st_dir'] = 1
        elif df['c'].iloc[i] < df['lo'].iloc[i-1]: df.loc[df.index[i], 'st_dir'] = -1
        else:
            df.loc[df.index[i], 'st_dir'] = df['st_dir'].iloc[i-1]
            if df['st_dir'].iloc[i]==1 and df['lo'].iloc[i] < df['lo'].iloc[i-1]: df.loc[df.index[i], 'lo'] = df['lo'].iloc[i-1]
            if df['st_dir'].iloc[i]==-1 and df['up'].iloc[i] > df['up'].iloc[i-1]: df.loc[df.index[i], 'up'] = df['up'].iloc[i-1]
    df['supertrend'] = np.where(df['st_dir']==1, df['lo'], df['up'])
    return df

def send_telegram(msg):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={'chat_id':CHAT_ID,'text':msg,'parse_mode':'Markdown'}, timeout=10)
    except: pass

def main():
    api = login()
    token_map = get_token_map()
    print(f"Login OK | FINAL 15 SCANNER ONLY | {datetime.datetime.now().strftime('%d-%m %H:%M')}")

    buys = []
    for sym in STOCKS_FINAL_15:
        try:
            token = token_map.get(sym)
            if not token: continue
            to_date = datetime.datetime.now()
            from_date = to_date - datetime.timedelta(days=200)
            params = {"exchange":"NSE","symboltoken":str(token),"interval":"ONE_DAY","fromdate":from_date.strftime("%Y-%m-%d %H:%M"),"todate":to_date.strftime("%Y-%m-%d %H:%M")}
            hist = api.getCandleData(params)
            if not hist or 'data' not in hist: continue
            df = pd.DataFrame(hist['data'], columns=['dt','o','h','l','c','v'])
            df = supertrend(df)
            df['EMA20'] = df['c'].ewm(20).mean()
            df['EMA50'] = df['c'].ewm(50).mean()
            df['VolAvg'] = df['v'].rolling(20).mean()
            d = df['c'].diff(); g = d.clip(lower=0).ewm(alpha=1/14).mean(); l = -d.clip(upper=0).ewm(alpha=1/14).mean()
            df['RSI'] = 100 - (100/(1+g/l))
            last = df.iloc[-1]
            if last['c'] > last['supertrend'] and last['c'] > last['EMA50'] and last['l'] <= last['EMA20']*1.02 and 55 <= last['RSI'] <= 68 and last['v'] > last['VolAvg']*1.2:
                buys.append({'STOCK':sym,'PRICE':round(last['c'],2),'RSI':round(last['RSI'],1)})
            time.sleep(0.3)
        except: continue

    if buys:
        msg = f"📈 *FINAL 15 - BUY SCAN* ({datetime.datetime.now().strftime('%d-%m-%Y')})\n\n"
        for b in buys:
            msg += f"*{b['STOCK']}* @ {b['PRICE']} (RSI {b['RSI']})\n"
        msg += f"\nManual Entry Karo - No Auto Order"
        send_telegram(msg)
        print(msg)
    else:
        send_telegram(f"ℹ️ FINAL 15 Scan - No Setup Today - {datetime.datetime.now().strftime('%d-%m-%Y')}")
        print("No Setup Today")

main()
