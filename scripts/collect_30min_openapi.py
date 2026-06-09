#!/usr/bin/env python3
"""
illinoisK 실시간 수집기 - OpenAPI+ (PowerShell 브릿지) 버전
kiwoom_client.ps1을 통해 OpenAPI+ 조회
"""
import subprocess, json, os, time, re
from datetime import datetime

# 19 종목 리스트
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

PS_SCRIPT = r"C:/temp/kiwoom_client.ps1"

def run_ps(action, code=None):
    """PowerShell 스크립트 실행 후 JSON 파싱"""
    cmd = ['powershell.exe', '-File', PS_SCRIPT, '-Action', action]
    if code:
        cmd += ['-Code', code]
    
    for attempt in range(2):
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate(timeout=20)
            text = out.decode('utf-8', errors='ignore')
            
            m = re.search(r'\{.*"status".*\}', text, re.DOTALL)
            if m:
                return json.loads(m.group())
        except Exception as e:
            if attempt == 0:
                time.sleep(1)
            else:
                return {"status": "error", "message": str(e)}
    return {"status": "error", "message": "failed after retries"}

def parse_price(v):
    """+56900 → 56900, -49100 → ignore (previous day)"""
    s = str(v).replace(",", "")
    if s.startswith("+"): 
        return int(float(s[1:]))
    if s.startswith("-"):
        return None
    val = int(float(s))
    if val > 100 and val < 100000000:
        return val
    return None

def calc_wma(closes, period):
    if len(closes) < period: return 0
    weights = list(range(1, period+1))
    total = sum(w * c for w, c in zip(weights, closes[-period:]))
    return total / sum(weights)

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

# 안전한 정수/실수 변환
def safe_int(v):
    if v is None: return 0
    try: return int(str(v).replace(',','').replace('+',''))
    except: return 0
def safe_float(v):
    if v is None: return 0.0
    try: return float(str(v).replace(',','').replace('+',''))
    except: return 0.0

# ===== 실행 =====
today = datetime.now().strftime("%Y%m%d")
output_file = f"/root/stock-trading/data/candles_30min_{today}.jsonl"
os.makedirs(os.path.dirname(output_file), exist_ok=True)

results = []
print(f"[{datetime.now().strftime('%H:%M:%S')}] OpenAPI+ 수집 시작: {len(STOCKS)}종목")

for stock in STOCKS:
    code = stock["code"]
    name = stock["name"]
    
    # 1. 현재가/시고저/등락률/거래량 (OPT10001)
    r1 = run_ps('get_stock_price', code)
    if r1.get("status") != "ok":
        print(f"  {name}({code}): 현재가 조회 실패 - {r1.get('message','?')}")
        continue
    
    d1 = r1.get("data", {})
    # Handle both Korean and obscured keys
    def get_val(d, *keys):
        for k in keys:
            if k in d:
                return d[k]
        return 0
    
    cur_prc = safe_int(get_val(d1, "현재가", "cur_prc", "curprc"))
    flu_rt = safe_float(get_val(d1, "등락률", "flu_rt"))
    high = safe_int(get_val(d1, "고가", "high_pric", "high_prc"))
    low = safe_int(get_val(d1, "저가", "low_pric", "low_prc"))
    open_prc = safe_int(get_val(d1, "시가", "open_prc"))
    vol = safe_int(get_val(d1, "거래량", "trde_qty", "volume"))
    
    # 2. 30분봉 차트 (OPT10080) - WMA/RSI용
    r2 = run_ps('get_stock_minute', code)
    d2 = r2.get("data", [])
    if isinstance(d2, dict):
        d2 = d2.get("data", [])
    
    # 30분봉 종가 리스트 (최신순, 유효한 양수만)
    closes_30 = []
    for row in d2:
        p = parse_price(row.get("현재가", row.get("cur_prc", 0)))
        if p:
            closes_30.append(p)
    
    # 1분봉 20틱 (최신 20개 저장)
    min1_data = []
    for row in d2[:20]:
        c = parse_price(row.get("현재가", row.get("cur_prc", 0)))
        if c:
            min1_data.append({
                "tm": row.get("체결시간", row.get("cntr_tm", "")),
                "cur": c,
                "vol": safe_int(row.get("거래량", row.get("trde_qty", 0))),
                "high": safe_int(row.get("고가", row.get("high_pric", 0))),
                "low": safe_int(row.get("저가", row.get("low_pric", 0)))
            })
    
    # 지표 계산
    wma20 = calc_wma(closes_30, 20) if len(closes_30) >= 20 else 0
    wma60 = calc_wma(closes_30, 60) if len(closes_30) >= 60 else 0
    wma120 = calc_wma(closes_30, 120) if len(closes_30) >= 120 else 0
    rsi14 = calc_rsi(closes_30, 14) if len(closes_30) >= 15 else 0
    
    high_200 = max(closes_30[:200]) if closes_30 else 0
    cur_prc = closes_30[0] if closes_30 else 0
    
    record = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "code": code,
        "name": name,
        "cur_prc": cur_prc,
        "flu_rt": round(flu_rt, 2),
        "high": high,
        "low": low,
        "open": open_prc,
        "vol": vol,
        "wma20": round(wma20, 2),
        "wma60": round(wma60, 2),
        "wma120": round(wma120, 2),
        "rsi14": round(rsi14, 2),
        "frgn_net": 0,  # TODO: 외인/기관 수급은 별도 API 필요
        "orgn_net": 0,
        "min1_20ticks": min1_data
    }
    
    results.append(record)
    print(f"  {name}({code}): {cur_prc:,}원 ({flu_rt:+.2f}%) WMA20:{wma20:,.0f} WMA60:{wma60:,.0f} RSI:{rsi14:.1f}")

# JSONL 저장
with open(output_file, "a") as f:
    for r in results:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"\n저장 완료: {output_file}")
print(f"총 {len(results)}종목 수집됨")