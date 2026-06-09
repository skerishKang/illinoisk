import requests, json, os
from datetime import datetime

# 19 종목 리스트 (사용자 지정)
STOCKS = [
    {"code": "005930", "name": "삼성전자"},
    {"code": "000660", "name": "SK하이닉스"},
    {"code": "005935", "name": "삼성전자우"},
    {"code": "009150", "name": "삼성전기"},
    {"code": "042700", "name": "한미반도체"},
    {"code": "403870", "name": "HPSP"},
    {"code": "319660", "name": "피에스케이"},
    {"code": "095610", "name": "테스"},
    {"code": "240810", "name": "원익IPS"},
    {"code": "036930", "name": "주성엔지니어링"},
    {"code": "039030", "name": "이오테크닉스"},
    {"code": "005290", "name": "동진쎄미켐"},
    {"code": "357780", "name": "솔브레인"},
    {"code": "064760", "name": "티씨케이"},
    {"code": "058470", "name": "리노공업"},
    {"code": "095340", "name": "ISC"},
    {"code": "131970", "name": "두산테스나"},
    {"code": "067310", "name": "하나마이크론"},
    {"code": "214150", "name": "클래시스"},
    {"code": "080220", "name": "제주반도체"},
]

# 토큰 캐싱
TOKEN_FILE = "/tmp/kiwoom_token.txt"

def get_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            t = f.read().strip()
            if t:
                return t
    with open("/mnt/g/Ddrive/BatangD/task/workdiary/65stock/keys/appkey.txt") as f:
        appkey = f.read().strip()
    with open("/mnt/g/Ddrive/BatangD/task/workdiary/65stock/keys/secretkey.txt") as f:
        secretkey = f.read().strip()
    r = requests.post("https://api.kiwoom.com/oauth2/token",
        json={"grant_type":"client_credentials","appkey":appkey,"secretkey":secretkey}, timeout=10)
    t = r.json()["token"]
    with open(TOKEN_FILE, "w") as f:
        f.write(t)
    return t

token = get_token()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json;charset=UTF-8"}

# 안전한 정수 변환
def safe_int(v):
    if v is None: return 0
    try:
        return int(str(v).replace(',','').replace('+',''))
    except:
        return 0

def safe_float(v):
    if v is None: return 0.0
    try:
        return float(str(v).replace(',','').replace('+',''))
    except:
        return 0.0

# WMA 계산 (가중이동평균) - 최신 데이터가 chart[0]이므로 최신 20개 사용
def calc_wma(closes, period):
    if len(closes) < period:
        return 0
    # closes[0] = 최신, closes[period-1] = period일 전
    weights = list(range(1, period+1))
    total = sum(w * c for w, c in zip(weights, closes[:period]))
    return total / sum(weights)

# RSI 계산 (14) - 최신 14개 사용
def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 0
    gains = []
    losses = []
    for i in range(period):
        diff = closes[i] - closes[i+1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-diff)
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

results = []
today = datetime.now().strftime("%Y%m%d")
output_file = f"/root/stock-trading/data/candles_30min_{today}.jsonl"

os.makedirs(os.path.dirname(output_file), exist_ok=True)

for stock in STOCKS:
    code = stock["code"]
    name = stock["name"]
    
    # 1. ka10001 - 현재가/시고저/등락률/거래량
    r1 = requests.post("https://api.kiwoom.com/api/dostk/stkinfo",
        headers={**headers, "api-id": "ka10001"},
        json={"stk_cd": code}, timeout=10)
    d1 = r1.json()
    
    # 2. ka10080 30분봉 - WMA/RSI 계산용 (차트[:20] 사용)
    r2 = requests.post("https://api.kiwoom.com/api/dostk/chart",
        headers={**headers, "api-id": "ka10080"},
        json={"stk_cd": code, "tic_scope": "30", "upd_stkpc_tp": "1"}, timeout=10)
    d2 = r2.json()
    
    # 3. ka10064 - 외인/기관 순매수
    r3 = requests.post("https://api.kiwoom.com/api/dostk/chart",
        headers={**headers, "api-id": "ka10064"},
        json={"mrkt_tp": "000", "amt_qty_tp": "1", "trde_tp": "0", "stk_cd": code}, timeout=10)
    d3 = r3.json()
    
    # 4. ka10080 1분봉 20틱
    r4 = requests.post("https://api.kiwoom.com/api/dostk/chart",
        headers={**headers, "api-id": "ka10080"},
        json={"stk_cd": code, "tic_scope": "1", "upd_stkpc_tp": "1"}, timeout=10)
    d4 = r4.json()
    
    # 데이터 파싱
    cur_prc = safe_int(d1.get('cur_prc'))
    flu_rt = safe_float(d1.get('flu_rt'))
    high = safe_int(d1.get('high_pric'))
    low = safe_int(d1.get('low_pric'))
    open_prc = safe_int(d1.get('open_prc'))
    vol = safe_int(d1.get('trde_qty'))
    
    # 30분봉 종가 리스트 (chart[0] = 최신)
    chart_30 = d2.get('stk_min_pole_chart_qry', [])
    closes_30 = [safe_int(row.get('cur_prc')) for row in chart_30 if safe_int(row.get('cur_prc')) > 0]
    
    wma20 = calc_wma(closes_30, 20) if len(closes_30) >= 20 else 0
    wma60 = calc_wma(closes_30, 60) if len(closes_30) >= 60 else 0
    wma120 = calc_wma(closes_30, 120) if len(closes_30) >= 120 else 0
    rsi14 = calc_rsi(closes_30, 14) if len(closes_30) >= 15 else 0
    
    # 외인/기관
    frgn_net = 0
    orgn_net = 0
    chart_inv = d3.get('opmr_invsr_trde_chart', [])
    if chart_inv:
        last = chart_inv[-1]
        frgn_net = safe_int(last.get('frgnr_invsr'))
        orgn_net = safe_int(last.get('orgn'))
    
    # 1분봉 20틱 저장용 (최신 20개)
    chart_1 = d4.get('stk_min_pole_chart_qry', [])
    min1_data = []
    for row in chart_1[:20]:
        c = safe_int(row.get('cur_prc'))
        if c > 0:
            min1_data.append({
                "tm": row.get('cntr_tm'),
                "cur": c,
                "vol": safe_int(row.get('trde_qty')),
                "high": safe_int(row.get('high_pric')),
                "low": safe_int(row.get('low_pric'))
            })
    
    record = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "code": code,
        "name": name,
        "cur_prc": cur_prc,
        "flu_rt": flu_rt,
        "high": high,
        "low": low,
        "open": open_prc,
        "vol": vol,
        "wma20": round(wma20, 2),
        "wma60": round(wma60, 2),
        "wma120": round(wma120, 2),
        "rsi14": round(rsi14, 2),
        "frgn_net": frgn_net,
        "orgn_net": orgn_net,
        "min1_20ticks": min1_data
    }
    
    results.append(record)
    print(f"{name}({code}): {cur_prc:,}원 ({flu_rt:+.2f}%) WMA20:{wma20:,.0f} WMA60:{wma60:,.0f} WMA120:{wma120:,.0f} RSI:{rsi14:.1f} 외인:{frgn_net:+,} 기관:{orgn_net:+,}")

# JSONL 저장
with open(output_file, "a") as f:
    for r in results:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"\n저장 완료: {output_file}")
print(f"총 {len(results)}종목 수집됨")