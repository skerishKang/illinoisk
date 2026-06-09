import requests
import json
import os
from datetime import datetime

# ============================================================
# 설정 및 헬퍼 함수
# ============================================================
TOKEN_FILE = "/tmp/kiwoom_token.txt"
APPKEY_FILE = "/mnt/g/Ddrive/BatangD/task/workdiary/65stock/keys/appkey.txt"
SECRETKEY_FILE = "/mnt/g/Ddrive/BatangD/task/workdiary/65stock/keys/secretkey.txt"
OUTPUT_DIR = "/mnt/g/Ddrive/BatangD/task/workdiary/illinoisK/realtime"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, f"candles_30min_{datetime.now().strftime('%Y%m%d')}.jsonl")

BASE_URL = "https://api.kiwoom.com"
CHART_URL = f"{BASE_URL}/api/dostk/chart"
STKINFO_URL = f"{BASE_URL}/api/dostk/stkinfo"

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

def get_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            t = f.read().strip()
            if t:
                return t
    with open(APPKEY_FILE) as f:
        appkey = f.read().strip()
    with open(SECRETKEY_FILE) as f:
        secretkey = f.read().strip()
    r = requests.post(f"{BASE_URL}/oauth2/token",
        json={"grant_type": "client_credentials", "appkey": appkey, "secretkey": secretkey}, timeout=10)
    t = r.json()["token"]
    with open(TOKEN_FILE, "w") as f:
        f.write(t)
    return t

def abs_int(val):
    """음수 가격도 절대값으로 변환, 빈 문자열은 0"""
    if not val or val == "":
        return 0
    return abs(int(str(val).replace(",", "").replace("+", "").replace("-", "")))

def parse_price(val):
    """가격 파싱 (음수/양수/빈값 처리)"""
    if not val or val == "":
        return 0
    s = str(val).replace(",", "")
    if s.startswith("-"):
        return abs(int(s))
    if s.startswith("+"):
        return int(s[1:])
    return int(s)

def parse_float(val):
    """부동소수점 파싱"""
    if not val or val == "":
        return 0.0
    return float(str(val).replace(",", ""))

def calculate_wma(prices, period):
    """가중이동평균 (WMA) 계산 - 최신 데이터에 더 큰 가중치"""
    if len(prices) < period:
        return None
    # prices[0]이 최신이므로 최근 period개를 사용
    recent = prices[:period]
    weights = list(range(1, period + 1))
    weighted_sum = sum(p * w for p, w in zip(recent, weights))
    weight_sum = sum(weights)
    return round(weighted_sum / weight_sum, 2)

def calculate_rsi(prices, period=14):
    """RSI(14) 계산 - Wilder's Smoothed 방식"""
    if len(prices) < period + 1:
        return None
    # 가격 변화 계산 (최신이 prices[0])
    changes = []
    for i in range(period):
        change = prices[i] - prices[i + 1]
        changes.append(change)
    
    gains = [max(c, 0) for c in changes]
    losses = [abs(min(c, 0)) for c in changes]
    
    # 초기 평균 (단순 평균)
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    # Wilder's smoothing
    for i in range(period, len(prices) - 1):
        change = prices[i] - prices[i + 1]
        gain = max(change, 0)
        loss = abs(min(change, 0))
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

# ============================================================
# 메인 실행
# ============================================================
if __name__ == "__main__":
    token = get_token()
    HEADERS_BASE = {
        "Content-Type": "application/json;charset=UTF-8",
        "Authorization": f"Bearer {token}"
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    saved_count = 0
    errors = []

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for stock in STOCKS:
            code = stock["code"]
            name = stock["name"]
            
            try:
                # 1) ka10001 - 현재가/시고저/등락률/거래량
                r1 = requests.post(STKINFO_URL,
                    headers={**HEADERS_BASE, "api-id": "ka10001"},
                    json={"stk_cd": code}, timeout=10)
                d1 = r1.json()
                
                if d1.get("return_code") != 0:
                    errors.append(f"{code} {name}: ka10001 return_code={d1.get('return_code')}")
                    continue
                
                cur_prc = parse_price(d1.get("cur_prc", "0"))
                flu_rt = parse_float(d1.get("flu_rt", "0"))
                high = parse_price(d1.get("high_pric", "0"))
                low = parse_price(d1.get("low_pric", "0"))
                open_prc = parse_price(d1.get("open_prc", "0"))
                vol = abs_int(d1.get("trde_qty", "0"))
                
                # 2) ka10080 30분봉 - WMA/RSI 계산용
                r2 = requests.post(CHART_URL,
                    headers={**HEADERS_BASE, "api-id": "ka10080"},
                    json={"stk_cd": code, "tic_scope": "30", "upd_stkpc_tp": "1"}, timeout=10)
                d2 = r2.json()
                
                wma20 = wma60 = wma120 = rsi14 = None
                
                if d2.get("return_code") == 0:
                    chart = d2.get("stk_min_pole_chart_qry", [])
                    if chart:
                        # chart[0]이 최신 - 차트에서 종가 추출
                        closes = [parse_price(row.get("cur_prc", "0")) for row in chart if row.get("cur_prc")]
                        if len(closes) >= 20:
                            wma20 = calculate_wma(closes, 20)
                        if len(closes) >= 60:
                            wma60 = calculate_wma(closes, 60)
                        if len(closes) >= 120:
                            wma120 = calculate_wma(closes, 120)
                        if len(closes) >= 15:
                            rsi14 = calculate_rsi(closes, 14)
                
                # 3) ka10064 - 외인/기관 순매수
                frgn_net = 0
                orgn_net = 0
                r3 = requests.post(CHART_URL,
                    headers={**HEADERS_BASE, "api-id": "ka10064"},
                    json={"mrkt_tp": "000", "amt_qty_tp": "1", "trde_tp": "0", "stk_cd": code}, timeout=10)
                d3 = r3.json()
                
                if d3.get("return_code") == 0:
                    chart3 = d3.get("opmr_invsr_trde_chart", [])
                    if chart3:
                        last = chart3[-1]
                        frgn_net = int(last.get("frgnr_invsr", "0") or "0")
                        orgn_net = int(last.get("orgn", "0") or "0")
                
                # 4) 결과 저장
                record = {
                    "ts": timestamp,
                    "code": code,
                    "name": name,
                    "cur_prc": cur_prc,
                    "flu_rt": flu_rt,
                    "high": high,
                    "low": low,
                    "open": open_prc,
                    "vol": vol,
                    "wma20": wma20,
                    "wma60": wma60,
                    "wma120": wma120,
                    "rsi14": rsi14,
                    "frgn_net": frgn_net,
                    "orgn_net": orgn_net
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                saved_count += 1
                
            except Exception as e:
                errors.append(f"{code} {name}: {str(e)}")

    # 결과 요약 출력
    result = {
        "timestamp": timestamp,
        "saved": saved_count,
        "total": len(STOCKS),
        "output_file": OUTPUT_FILE,
        "errors": errors
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))