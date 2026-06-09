#!/usr/bin/env python3
"""ISC (095340) 지지선 분석 — 키움 차트 데이터 조회"""
import json, subprocess, sys
sys.path.insert(0, '/mnt/g/Ddrive/BatangD/task/workdiary/illinoisK/scripts')
from kiwoom_api import get_token, load_keys

BASE_URL = "https://api.kiwoom.com"
token = get_token()

# 일봉 차트 조회 (tic_scope="1" = 일봉)
r = subprocess.run(
    ['curl', '-s', '-X', 'POST', f'{BASE_URL}/api/dostk/chart',
     '-H', f'Authorization: Bearer {token}',
     '-H', 'Content-Type: application/json;charset=UTF-8',
     '-H', 'api-id: ka10080',
     '-d', json.dumps({"stk_cd": "095340", "tic_scope": "1", "upd_stkpc_tp": "1"})],
    capture_output=True, text=True, timeout=15)

data = json.loads(r.stdout)

# Check response
if 'rt_cd' in data and data['rt_cd'] != '0':
    print(f"API ERROR: {data.get('rt_msg', 'unknown')}")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
    sys.exit(1)

# Parse chart data
chart_key = None
for key in ['stk_min_pole_chart_qry', 'output1', 'chart_data', 'data']:
    if key in data:
        chart_key = key
        break

if not chart_key:
    print("No chart data key found. Full response:")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])
    sys.exit(1)

rows = data[chart_key]
print(f"조회된 데이터: {len(rows)}개 봉")

if not rows:
    print("데이터 없음")
    sys.exit(0)

# Show column names
print(f"컬럼: {list(rows[0].keys())}")

# Extract price data
prices_data = []
for r in rows:
    try:
        date = r.get('pole_dt') or r.get('date') or r.get('stk_bsop_date', '')
        if not date:
            continue
        # Kiwoom prices have +/- prefix
        high_raw = str(r.get('high_pric', '0')).replace(',', '').lstrip('+-')
        low_raw = str(r.get('low_pric', '0')).replace(',', '').lstrip('+-')
        close_raw = str(r.get('cur_prc', '0')).replace(',', '').lstrip('+-')
        high = int(high_raw) if high_raw else 0
        low = int(low_raw) if low_raw else 0
        close = int(close_raw) if close_raw else 0
        if close > 0:
            prices_data.append({'date': date, 'high': high, 'low': low, 'close': close})
    except:
        continue

print(f"\n파싱된 일봉: {len(prices_data)}개")

# Sort by date
prices_data.sort(key=lambda x: x['date'])

# Show recent data
print(f"\n=== 최근 20일 ===")
for p in prices_data[-20:]:
    print(f"  {p['date']} | 고 {p['high']:>7,} | 저 {p['low']:>7,} | 종가 {p['close']:>7,}")

# Support analysis
if len(prices_data) >= 10:
    lows = sorted(set(p['low'] for p in prices_data))
    print(f"\n=== 저가 기준 지원 레벨 ===")
    for l in lows[:10]:
        print(f"  {l:,}")

    # Find recent lows (last 20 days)
    recent = prices_data[-20:] if len(prices_data) >= 20 else prices_data
    recent_lows = sorted(set(p['low'] for p in recent))
    print(f"\n=== 최근 {len(recent)}일 저가 기준 ===")
    for l in recent_lows:
        print(f"  {l:,}")

    # SMA calculations
    closes = [p['close'] for p in prices_data]
    def sma(data, period):
        if len(data) < period:
            return None
        return sum(data[-period:]) / period
    
    print(f"\n=== 이동평균선 ===")
    for period in [5, 10, 20, 60, 120]:
        val = sma(closes, period)
        if val:
            print(f"  {period}일선: {val:,.0f}")
