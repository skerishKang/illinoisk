#!/usr/bin/env python3
"""
일일 매매 복기 스크립트 - 15:40 실행용
11종목 장중 고가/저가/종가, 등락률, 거래원, WMA/RSI 분석
"""
import os
import requests
import json
import statistics
from datetime import datetime, timedelta

# 11종목 (관심종목)
STOCKS = {
    "403870": "HPSP",
    "039030": "이오테크닉스",
    "005290": "동진쎄미켐",
    "131970": "두산테스나",
    "042700": "한미반도체",
    "095340": "ISC",
    "058470": "리노공업",
    "319660": "피에스케이",
    "036930": "주성엔지니어링",
    "064760": "티씨케이",
    "240810": "원익IPS",
}

# 시장 구분
MARKET = {
    "403870": "KOSDAQ", "039030": "KOSDAQ", "005290": "KOSDAQ",
    "131970": "KOSDAQ", "042700": "KOSDAQ", "095340": "KOSDAQ",
    "058470": "KOSDAQ", "319660": "KOSDAQ", "036930": "KOSDAQ",
    "064760": "KOSDAQ", "240810": "KOSDAQ",
}

APP_KEY = "N248MlQKSoL6zY-dNF0jXEz09EE_nXrA77ev4XuscV8"
SECRET_KEY = "GXFAgPOeRKFOl94WRwhZWADwFlXhHSF6eOJtNBV2tZ4"
BASE_URL = "https://api.kiwoom.com"

def get_token():
    """액세스 토큰 발급"""
    r = requests.post(f"{BASE_URL}/oauth2/token", json={
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "secretkey": SECRET_KEY
    }, timeout=10)
    data = r.json()
    if "token" not in data:
        raise Exception(f"Token error: {data}")
    return data["token"]

def fix_price(val):
    """부호 있는 가격 문자열을 절대값 정수로 변환"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return abs(int(val))
    s = str(val).replace(",", "").strip()
    if s.startswith("-") or s.startswith("+"):
        s = s[1:]
    return int(s) if s else None

def call_kiwoom(token, api_id, body, url_suffix="stkinfo"):
    """키움 REST API 호출"""
    headers = {
        "api-id": api_id,
        "authorization": f"Bearer {token}",
        "cont-yn": "N",
        "next-key": "",
        "Content-Type": "application/json;charset=UTF-8",
    }
    url = f"{BASE_URL}/api/dostk/{url_suffix}"
    r = requests.post(url, headers=headers, json=body, timeout=10)
    return r.json()

def get_prices(token):
    """11종목 현재가/고가/저가/등락률/전일종가 조회 (ka10001)"""
    results = {}
    for code, name in STOCKS.items():
        data = call_kiwoom(token, "ka10001", {"stk_cd": code})
        if data.get("return_code") != 0:
            print(f"  {name}({code}): API error {data.get('return_code')}")
            continue
        cur = fix_price(data.get("cur_prc"))
        high = fix_price(data.get("high_pric"))
        low = fix_price(data.get("low_pric"))
        open_p = fix_price(data.get("open_pric"))
        base = fix_price(data.get("base_pric"))  # 전일종가
        flu_rt = data.get("flu_rt", "0")
        try:
            flu_pct = float(flu_rt.replace(",", "").replace("%", ""))
        except:
            flu_pct = 0.0
        vol = data.get("trde_qty", "0")
        try:
            volume = int(vol.replace(",", ""))
        except:
            volume = 0
        results[code] = {
            "name": name,
            "market": MARKET[code],
            "cur": cur,
            "high": high,
            "low": low,
            "open": open_p,
            "base": base,
            "flu_pct": flu_pct,
            "volume": volume,
        }
    return results

def get_trading_members(token):
    """11종목 거래원 TOP5 조회 (ka10002)"""
    results = {}
    for code, name in STOCKS.items():
        data = call_kiwoom(token, "ka10002", {"stk_cd": code})
        if data.get("return_code") != 0:
            print(f"  {name}({code}): 거래원 API error {data.get('return_code')}")
            continue
        buy_list = []
        sell_list = []
        for i in range(1, 6):
            bn = data.get(f"buy_trde_ori_nm_{i}")
            bq = data.get(f"buy_trde_qty_{i}")
            sn = data.get(f"sel_trde_ori_nm_{i}")
            sq = data.get(f"sel_trde_qty_{i}")
            if bn and bq:
                try:
                    buy_list.append((bn, int(str(bq).replace(",", "").replace("+", ""))))
                except:
                    pass
            if sn and sq:
                try:
                    sell_list.append((sn, int(str(sq).replace(",", "").replace("-", ""))))
                except:
                    pass
        results[code] = {"buy": buy_list, "sell": sell_list}
    return results

def get_daily_candles(token, code, count=30):
    """일봉 차트 조회 (ka10081) - WMA/RSI 계산용"""
    today = datetime.now().strftime("%Y%m%d")
    data = call_kiwoom(token, "ka10081", {
        "stk_cd": code,
        "base_dt": today,
        "qrycnt": str(count),
        "upd_stkpc_tp": "0"
    }, url_suffix="chart")
    if data.get("return_code") != 0:
        return []
    candles = data.get("stk_dt_pole_chart_qry", [])
    # oldest first
    candles = sorted(candles, key=lambda x: x.get("dt", ""))
    closes = []
    for c in candles:
        try:
            closes.append(int(c.get("cur_prc", "0").replace(",", "")))
        except:
            pass
    return closes

def calc_wma(values, period):
    """가중이동평균 (WMA) - 영웅문 방식"""
    if len(values) < period:
        return None
    recent = values[-period:]
    w = sum((i+1) * recent[i] for i in range(period))
    d = sum(i+1 for i in range(period))
    return w / d

def calc_rsi_wilder(closes, period=14):
    """Wilder RSI - 영웅문 HTS 기준"""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, period + 1):
        diff = closes[-i] - closes[-i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_g = sum(gains) / period
    avg_l = sum(losses) / period
    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return 100 - 100 / (1 + rs)

def calc_bb(closes, period=20, mult=2):
    """볼린저 밴드 (20, 2)"""
    if len(closes) < period:
        return None, None, None, None
    recent = closes[-period:]
    ma = statistics.mean(recent)
    std = statistics.stdev(recent) if len(recent) > 1 else 0
    upper = ma + mult * std
    lower = ma - mult * std
    band_pct = (closes[-1] - lower) / (upper - lower) * 100 if upper != lower else 50
    return upper, ma, lower, band_pct

def main():
    print(f"=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 일일 매매 복기 ===\n")
    
    token = get_token()
    print("토큰 발급 완료\n")
    
    # 1. 현재가/고가/저가/등락률
    print("📊 11종목 장중 데이터 수집 중...")
    prices = get_prices(token)
    print(f"  완료: {len(prices)}종목\n")
    
    # 2. 거래원 데이터
    print("📈 거래원 TOP5 수집 중...")
    trading = get_trading_members(token)
    print(f"  완료: {len(trading)}종목\n")
    
    # 3. 일봉 데이터로 WMA/RSI/BB 계산
    print("📉 기술적 지표 계산 중...")
    tech = {}
    for code, name in STOCKS.items():
        closes = get_daily_candles(token, code, 30)
        if len(closes) >= 20:
            wma20 = calc_wma(closes, 20)
            wma60 = calc_wma(closes, 60) if len(closes) >= 60 else None
            rsi = calc_rsi_wilder(closes, 14)
            bb_upper, bb_mid, bb_lower, bb_pct = calc_bb(closes, 20, 2)
            tech[code] = {
                "wma20": wma20,
                "wma60": wma60,
                "rsi": rsi,
                "bb_upper": bb_upper,
                "bb_mid": bb_mid,
                "bb_lower": bb_lower,
                "bb_pct": bb_pct,
                "close": closes[-1],
            }
    print(f"  완료: {len(tech)}종목\n")
    
    # 4. 결과 출력 및 분석
    print("=" * 60)
    print("📋 종목별 상세 분석")
    print("=" * 60)
    
    # 등락률 순으로 정렬
    sorted_stocks = sorted(prices.items(), key=lambda x: x[1]["flu_pct"], reverse=True)
    
    for code, p in sorted_stocks:
        name = p["name"]
        t = tech.get(code, {})
        tm = trading.get(code, {"buy": [], "sell": []})
        
        print(f"\n🔸 {name} ({code}) [{p['market']}]")
        print(f"   현재가: {p['cur']:,}원  전일대비: {p['flu_pct']:+.2f}%  고가: {p['high']:,}  저가: {p['low']:,}  시가: {p['open']:,}")
        print(f"   거래량: {p['volume']:,}주")
        
        # 기술적 지표
        if t:
            wma20 = t.get('wma20')
            wma60 = t.get('wma60')
            rsi = t.get('rsi')
            bb_pct = t.get('bb_pct')
            cur = t.get('close')
            if wma20:
                dev20 = (cur - wma20) / wma20 * 100
                print(f"   WMA20: {wma20:,.0f} (괴리 {dev20:+.1f}%)", end="")
            if wma60:
                dev60 = (cur - wma60) / wma60 * 100
                print(f"  WMA60: {wma60:,.0f} (괴리 {dev60:+.1f}%)", end="")
            print()
            if rsi is not None:
                rsi_signal = "과매도🔴" if rsi < 30 else "과매수🟢" if rsi > 70 else "중립"
                print(f"   RSI(14): {rsi:.1f} ({rsi_signal})", end="")
            if bb_pct is not None:
                bb_signal = "하단근접🔴" if bb_pct < 20 else "상단근접🟢" if bb_pct > 80 else "중간"
                print(f"  BB%B: {bb_pct:.1f}% ({bb_signal})", end="")
            print()
        
        # 거래원 요약
        if tm["buy"] or tm["sell"]:
            buy_str = " | ".join([f"{n} {q:+,}" for n, q in tm["buy"][:3]])
            sell_str = " | ".join([f"{n} {q:+,}" for n, q in tm["sell"][:3]])
            if buy_str:
                print(f"   매수거래원: {buy_str}")
            if sell_str:
                print(f"   매도거래원: {sell_str}")
            
            # 신한/외국계 체크
            shinhan_buy = sum(q for n, q in tm["buy"] if "신한" in n)
            shinhan_sell = sum(q for n, q in tm["sell"] if "신한" in n)
            foreign_buy = sum(q for n, q in tm["buy"] if any(f in n for f in ["메릴", "모건", "골드만", "씨티", "제이피", "CS", "UBS", "노무라", "다이와"]))
            foreign_sell = sum(q for n, q in tm["sell"] if any(f in n for f in ["메릴", "모건", "골드만", "씨티", "제이피", "CS", "UBS", "노무라", "다이와"]))
            if shinhan_buy or shinhan_sell:
                print(f"   신한 순매수: {shinhan_buy - shinhan_sell:+,}주")
            if foreign_buy or foreign_sell:
                print(f"   외국계 순매수: {foreign_buy - foreign_sell:+,}주")
    
    # 5. 2% 이상 움직임 종목 하이라이트
    print("\n" + "=" * 60)
    print("⚡ 2% 이상 변동 종목")
    print("=" * 60)
    for code, p in sorted_stocks:
        if abs(p["flu_pct"]) >= 2.0:
            direction = "상승" if p["flu_pct"] > 0 else "하락"
            print(f"  {p['name']}: {p['flu_pct']:+.2f}% ({direction})")
    
    # 6. WMA/RSI 신호 vs 실제 결과 비교
    print("\n" + "=" * 60)
    print("🎯 WMA/RSI 신호 vs 실제 결과 검증")
    print("=" * 60)
    for code, p in prices.items():
        t = tech.get(code, {})
        if not t:
            continue
        rsi = t.get('rsi')
        wma20 = t.get('wma20')
        cur = t.get('close')
        if rsi is not None and wma20:
            # RSI 30 이하에서 반등했나?
            if rsi < 30 and p["flu_pct"] > 0:
                print(f"  ✅ {p['name']}: RSI {rsi:.1f} 과매도 → +{p['flu_pct']:.2f}% 반등 성공")
            elif rsi < 30 and p["flu_pct"] < -2:
                print(f"  ❌ {p['name']}: RSI {rsi:.1f} 과매도 → {p['flu_pct']:.2f}% 추가 하락 (함정)")
            # WMA20 이탈 상태에서 반등했나?
            dev20 = (cur - wma20) / wma20 * 100
            if dev20 < -5 and p["flu_pct"] > 1:
                print(f"  📈 {p['name']}: WMA20 이탈({dev20:+.1f}%) → +{p['flu_pct']:.2f}% 반등")
            elif dev20 < -5 and p["flu_pct"] < -3:
                print(f"  📉 {p['name']}: WMA20 이탈({dev20:+.1f}%) → {p['flu_pct']:.2f}% 추가 하락")
    
    # 7. 놓친 진입 기회 분석
    print("\n" + "=" * 60)
    print("💡 오늘 놓친 진입 기회 / 진입했으면 좋았을 구간")
    print("=" * 60)
    for code, p in prices.items():
        t = tech.get(code, {})
        if not t:
            continue
        rsi = t.get('rsi')
        wma20 = t.get('wma20')
        cur = t.get('close')
        low = p['low']
        high = p['high']
        
        # 장중 저점이 매수 기회였는지 체크
        if rsi is not None and rsi < 35 and p["flu_pct"] > -1:
            # 저점에서 반등했으면 진입 기회였음
            bounce_from_low = (cur - low) / low * 100
            if bounce_from_low > 1:
                print(f"  🎯 {p['name']}: RSI {rsi:.1f} 저가권 + 저점대비 +{bounce_from_low:.1f}% 반등 → 진입 기회였음")
        
        # WMA20 지지 테스트 후 반등
        if wma20:
            dev20_low = (low - wma20) / wma20 * 100
            dev20_cur = (cur - wma20) / wma20 * 100
            if -3 < dev20_low < 1 and dev20_cur > 1:
                print(f"  🎯 {p['name']}: WMA20 지지 확인({dev20_low:+.1f}%→{dev20_cur:+.1f}%) → 눌림목 진입 구간")
    
    # 8. 내일 대비 전략
    print("\n" + "=" * 60)
    print("📅 내일(다음 거래일) 대비 전략")
    print("=" * 60)
    
    # 강세 종목
    strong = [(code, p) for code, p in prices.items() if p["flu_pct"] > 1.5]
    weak = [(code, p) for code, p in prices.items() if p["flu_pct"] < -1.5]
    
    if strong:
        print("  🟢 강세 지속 후보 (모멘텀 플레이):")
        for code, p in strong[:3]:
            t = tech.get(code, {})
            rsi = t.get('rsi', 50)
            if rsi < 70:
                print(f"    - {p['name']}: +{p['flu_pct']:.2f}%, RSI {rsi:.1f} (과매수 아닌 구간)")
    
    if weak:
        print("  🔴 반등 노릴 종목 (RSI 과매도 + WMA 지지):")
        for code, p in weak[:5]:
            t = tech.get(code, {})
            rsi = t.get('rsi', 50)
            wma20 = t.get('wma20')
            if rsi < 40 and wma20:
                dev = (p['cur'] - wma20) / wma20 * 100
                if dev > -5:
                    print(f"    - {p['name']}: {p['flu_pct']:.2f}%, RSI {rsi:.1f}, WMA20 괴리 {dev:+.1f}%")
    
    # 수급 기반
    print("  💰 수급 기반 관심 종목:")
    for code, p in prices.items():
        tm = trading.get(code, {"buy": [], "sell": []})
        shinhan_net = sum(q for n, q in tm["buy"] if "신한" in n) - sum(q for n, q in tm["sell"] if "신한" in n)
        foreign_net = sum(q for n, q in tm["buy"] if any(f in n for f in ["메릴", "모건", "골드만", "씨티", "제이피", "CS", "UBS", "노무라", "다이와"])) - \
                      sum(q for n, q in tm["sell"] if any(f in n for f in ["메릴", "모건", "골드만", "씨티", "제이피", "CS", "UBS", "노무라", "다이와"]))
        if shinhan_net > 5000 or foreign_net > 5000:
            print(f"    - {p['name']}: 신한 {shinhan_net:+,} / 외국계 {foreign_net:+,} (수급 양호)")

if __name__ == "__main__":
    main()