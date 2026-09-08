import os, pyotp, pandas as pd, ta, time, requests
from datetime import datetime
from SmartApi import SmartConnect

API_KEY = os.getenv("API_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
PASSWORD = os.getenv("PASSWORD")
TOTP_SECRET = os.getenv("TOTP_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

STOCKS_FINAL_27 = [
"AEROENTER", "RPGLIFE", "BECTORFOOD", "SIRCA", "IITL", "NITIRAJ", "KERNEX",
"GODREJIND", "TORNTPOWER", "KAPSTON", "ALOKINDS", "MOTILALOFS", "SEMAC",
"GEEKAYWIRE", "TRENT", "HAL", "RADAAN", "KOKUYOCMLN", "PARAGMILK", "VOLTAMP",
"SYMPHONY", "RAMRAT", "MANORAMA", "TEJASNET", "SPAL", "LUMAXIND", "ARTEMISMED"
]

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=20)
    except: pass

try:
    obj = SmartConnect(api_key=API_KEY)
    obj.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
    print("LOGIN OK - FINAL 27 V2 PRO")

    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    data = requests.get(url, timeout=30).json()
    token_map = {x['name']: x['token'] for x in data if x['exch_seg']=='NSE'}

    def supertrend(df, period=10, multiplier=3):
        hl2 = (df['high'] + df['low']) / 2
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], period).average_true_range()
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        direction = pd.Series(1, index=df.index)
        for i in range(1, len(df)):
            if df['close'].iloc[i] > upper_band.iloc[i-1]:
                direction.iloc[i] = 1
            elif df['close'].iloc[i] < lower_band.iloc[i-1]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = direction.iloc[i-1]
        return direction

    def get_signal_final(symbol):
        try:
            token = token_map.get(symbol)
            if not token: return None
            params={"exchange":"NSE","symboltoken":token,"interval":"ONE_DAY",
                    "fromdate":"2021-01-01 09:15","todate": datetime.now().strftime("%Y-%m-%d 15:30")}
            res = obj.getCandleData(params)
            if not res.get('data') or len(res['data'])<200: return None
            df=pd.DataFrame(res['data'], columns=['time','open','high','low','close','volume'])
            for c in ['open','high','low','close','volume']: df[c]=df[c].astype(float)
            df['20EMA']=ta.trend.EMAIndicator(df['close'],20).ema_indicator()
            df['50EMA']=ta.trend.EMAIndicator(df['close'],50).ema_indicator()
            df['200EMA']=ta.trend.EMAIndicator(df['close'],200).ema_indicator()
            df['RSI']=ta.momentum.RSIIndicator(df['close'],14).rsi()
            df['ATR']=ta.volatility.AverageTrueRange(df['high'],df['low'],df['close'],14).average_true_range()
            df['VolAvg']=df['volume'].rolling(20).mean()
            df['ST_dir']=supertrend(df,10,3)
            df['52W_High']=df['high'].rolling(252).max()
            last = df.iloc[-1]
            prev = df.iloc[-2]
            cond1 = last['close'] > last['20EMA'] > last['50EMA'] > last['200EMA']
            cond2 = 55 < last['RSI'] < 70 and last['RSI'] > prev['RSI']
            cond3 = last['volume'] > last['VolAvg'] * 1.2
            cond4 = last['close'] > prev['close']
            cond5 = last['ST_dir'] == 1
            cond6 = last['close'] >= last['52W_High'] * 0.90
            if cond1 and cond2 and cond3 and cond4 and cond5 and cond6:
                entry=last['close']
                atr=last['ATR']
                return {"symbol":symbol,"entry":round(entry,2),"sl":round(entry - atr*2.0,2),
                        "tgt1":round(entry + atr*2.0,2),"tgt2":round(entry + atr*4.0,2),
                        "rsi":round(last['RSI'],1),"dist_52w":round((last['52W_High']-entry)/entry*100,1)}
        except: return None
        return None

    signals=[]
    for sym in STOCKS_FINAL_27:
        s=get_signal_final(sym)
        if s: signals.append(s)
        time.sleep(0.35)

    if signals:
        msg = f"🚀 *FINAL 27 V2 PRO - {datetime.now().strftime('%d-%m-%Y %I:%M %p')}* 🚀\n\n"
        for x in signals:
            msg += f"📈 *{x['symbol']}*\nEntry: {x['entry']} | SL: {x['sl']}\nTGT1: {x['tgt1']} (50%) | TGT2: {x['tgt2']} (Trail)\n52W Dist: {x['dist_52w']}% | RSI {x['rsi']}\n\n"
        msg += "⚠️ Rule: TGT1 pe 50% book, SL to Cost, TGT2 trail"
        send_telegram(msg)
    else:
        send_telegram(f"📭 No signal - FINAL 27 - {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")
    print("DONE")

except Exception as e:
    send_telegram(f"❌ FINAL 27 Error\n{str(e)}")
    print(e)
