#!/usr/bin/env python3
"""
30분봉 실시간 데이터 수집기 - 단일 실행 테스트용
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional

# ========== 설정 ==========
DATA_DIR = os.path.expanduser("~/stock-trading/data")
TOKEN_FILE = "/tmp/kiwoom_token.txt"
APPKEY_FILE = "/mnt/g/Ddrive/BatangD/task/workdiary/65stock/keys/appkey.txt"
SECRETKEY_FILE = "/mnt/g/Ddrive/BatangD/task/workdiary/65stock/keys/secretkey.txt"
BASE_URL = "https://api.kiwoom.com"

STOCKS = [
    {"code": "039030", "name": "이오테크닉스"},
    {"code": "095340", "name": "ISC"},
    {"code": "403870", "name": "HPSP"},
    {"code": "005290", "name": "동진쎄미켐"},
    {"code": "058470", "name": "리노공업"},
    {"code": "036930", "name": "주성엔지니어링"},
    {"code": "042700", "name": "한미반도체"},
    {"code": "131970", "name": "두산테스나"},
    {"code": "240810", "name": "원익IPS"},
    {"code": "064760", "name": "티씨케이"},
    {"code": "214150", "name": "클래시스"},
    {"code": "319660", "name": "피에스케이"},
    {"code": "080220", "name": "제주반도체"},
    {"code": "067310", "name": "하나마이크론"},
    {"code": "357780", "name": "솔브레인"},
    {"code": "005930", "name": "삼성전자"},
    {"code": "000660", "name": "SK하이닉스"},
    {"code": "035720", "name": "카카오"},
    {"code": "005935", "name": "삼성전자우"},
]


def get_token() -> str:
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            cached = f.read().strip()
            if cached:
                return cached
    with open(APPKEY_FILE) as f:
        appkey = f.read().strip()
    with open(SECRETKEY_FILE) as f:
        secretkey = f.read().strip()
    r = requests.post(
        f"{BASE_URL}/oauth2/token",
        json={"grant_type": "client_credentials", "appkey": appkey, "secretkey": secretkey},
        timeout=10
    )
    token = r.json()["token"]
    with open(TOKEN_FILE, "w") as f:
        f.write(token)
    return token


def api_call(api_id: str, body: dict, token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json;charset=UTF-8",
        "api-id": api_id,
    }
    if api_id in ["ka10001", "ka90004"]:
        url = f"{BASE_URL}/api/dostk/stkinfo"
    elif api_id in ["ka10080", "ka10081", "ka10064"]:
        url = f"{BASE_URL}/api/dostk/chart"
    elif api_id == "ka10004":
        url = f"{BASE_URL}/api/dostk/mrkcond"
    elif api_id == "ka10040":
        url = f"{BASE_URL}/api/dostk/rkinfo"
    elif api_id == "ka10010":
        url = f"{BASE_URL}/api/dostk/sect"
    elif api_id == "kt00011":
        url = f"{BASE_URL}/api/dostk/acnt"
    else:
        url = f"{BASE_URL}/api/dostk/stkinfo"
    r = requests.post(url, headers=headers, json=body, timeout=10)
    return r.json()


def parse_int(val) -> int:
    if val is None:
        return 0
    s = str(val).replace(",", "").strip()
    if not s or s == "-":
        return 0
    try:
        return abs(int(s))
    except ValueError:
        return 0


def parse_float(val) -> float:
    if val is None:
        return 0.0
    s = str(val).replace(",", "").strip()
    if not s or s == "-":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def calc_wma(prices: List[float], period: int) -> Optional[float]:
    if len(prices) < period:
        return None
    recent = prices[-period:]
    weights = list(range(1, period + 1))
    weighted_sum = sum(p * w for p, w in zip(recent, weights))
    weight_sum = sum(weights)
    return weighted_sum / weight_sum


def calc_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    recent = closes[-(period + 1):]
    gains = []
    losses = []
    for i in range(1, len(recent)):
        diff = recent[i] - recent[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-diff)
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
def fetch_basic_info(code: str, token: str) -> dict:
    """ka10001: 주식기본정보"""
    res = api_call("ka10001", {"stk_cd": code}, token)
    # ka10001 응답은 직접 키에 데이터가 있음 (stk_min_pole_chart_qry 아님)
    return {
        "cur_prc": parse_int(res.get("cur_prc", 0)),
        "flu_rt": parse_float(res.get("flu_rt", 0)),
        "high": parse_int(res.get("high_pric", 0)),
        "low": parse_int(res.get("low_pric", 0)),
        "open": parse_int(res.get("open_pric", 0)),
        "volume": parse_int(res.get("trde_qty", 0)),
        "pred_pre": parse_int(res.get("pred_pre", 0)),
    }


def fetch_30min_chart(code: str, token: str) -> List[dict]:
    res = api_call("ka10080", {"stk_cd": code, "tic_scope": "30", "upd_stkpc_tp": "1"}, token)
    chart = res.get("stk_min_pole_chart_qry", [])
    chart = sorted(chart, key=lambda x: x.get("cntr_tm", ""))
    return chart


def fetch_investor_data(code: str, token: str) -> dict:
    res = api_call("ka10064", {"mrkt_tp": "000", "amt_qty_tp": "1", "trde_tp": "0", "stk_cd": code}, token)
    chart = res.get("opmr_invsr_trde_chart", [])
    if not chart:
        return {"frgn_net": 0, "orgn_net": 0}
    last = chart[-1]
    return {
        "frgn_net": parse_int(last.get("frgnr_invsr", 0)),
        "orgn_net": parse_int(last.get("orgn", 0)),
    }


def collect_stock_data(code: str, name: str, token: str) -> Optional[dict]:
    try:
        basic = fetch_basic_info(code, token)
        chart = fetch_30min_chart(code, token)
        closes = [parse_int(c.get("cur_prc", 0)) for c in chart if parse_int(c.get("cur_prc", 0)) > 0]
        wma20 = calc_wma(closes, 20)
        wma60 = calc_wma(closes, 60)
        rsi14 = calc_rsi(closes, 14)
        investor = fetch_investor_data(code, token)
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "code": code,
            "name": name,
            "cur_prc": basic["cur_prc"],
            "flu_rt": round(basic["flu_rt"], 2),
            "high": basic["high"],
            "low": basic["low"],
            "open": basic["open"],
            "volume": basic["volume"],
            "wma20": round(wma20, 1) if wma20 else None,
            "wma60": round(wma60, 1) if wma60 else None,
            "rsi14": round(rsi14, 1) if rsi14 else None,
            "frgn_net": investor["frgn_net"],
            "orgn_net": investor["orgn_net"],
        }
    except Exception as e:
        print(f"[{code} {name}] 수집 오류: {e}")
        return None


def save_jsonl(data: dict, date_str: str):
    filepath = os.path.join(DATA_DIR, f"realtime_30min_{date_str}.jsonl")
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def main():
    print("=" * 60)
    print(f"테스트 수집 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"대상 종목: {len(STOCKS)}개")
    print("=" * 60)

    token = get_token()
    print(f"토큰 발급 완료")

    date_str = datetime.now().strftime("%Y%m%d")

    for stock in STOCKS:
        data = collect_stock_data(stock["code"], stock["name"], token)
        if data:
            save_jsonl(data, date_str)
            print(f"  {data['code']} {data['name']}: {data['cur_prc']:,}원 ({data['flu_rt']:+.2f}%) "
                  f"WMA20:{data['wma20']} WMA60:{data['wma60']} RSI:{data['rsi14']} "
                  f"외인:{data['frgn_net']:,} 기관:{data['orgn_net']:,}")
        else:
            print(f"  {stock['code']} {stock['name']}: 수집 실패")

    print(f"\n저장 완료: {DATA_DIR}/realtime_30min_{date_str}.jsonl")
    print("=" * 60)


if __name__ == "__main__":
    main()