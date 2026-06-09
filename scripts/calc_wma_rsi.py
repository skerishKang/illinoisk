import json
import os
from datetime import datetime
from collections import defaultdict

# Read the realtime data
data_by_stock = defaultdict(list)
with open("/mnt/g/Ddrive/BatangD/task/workdiary/illinoisK/realtime/realtime_30min_20260609.jsonl") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            # Normalize field names (ts vs timestamp, cur_prc, vol vs volume)
            ts = d.get('ts') or d.get('timestamp')
            code = d.get('code')
            if not ts or not code:
                continue
            # Parse timestamp to get just HH:MM
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            time_key = dt.strftime("%H:%M")
            price = d.get('cur_prc', 0)
            flu_rt = d.get('flu_rt', 0)
            frgn_net = d.get('frgn_net', 0)
            orgn_net = d.get('orgn_net', 0)
            name = d.get('name', '')
            data_by_stock[code].append({
                'ts': time_key,
                'full_ts': ts,
                'cur_prc': price,
                'flu_rt': flu_rt,
                'frgn_net': frgn_net,
                'orgn_net': orgn_net,
                'name': name
            })
        except Exception as e:
            continue

# Sort each stock's data by timestamp
for code in data_by_stock:
    data_by_stock[code].sort(key=lambda x: x['full_ts'])

# WMA calculation
def calc_wma(prices, period):
    if len(prices) < period:
        # Use available data
        period = len(prices)
    if period == 0:
        return None
    weights = list(range(1, period + 1))
    weighted_sum = sum(p * w for p, w in zip(prices[-period:], weights))
    return weighted_sum / sum(weights)

# RSI calculation (Wilder's smoothing)
def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [max(c, 0) for c in changes]
    losses = [max(-c, 0) for c in changes]
    
    # Initial SMA
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    # Wilder's smoothing
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# MA cross detection
def get_ma_cross(wma20, wma60, wma120):
    if wma20 is None or wma60 is None or wma120 is None:
        return "neutral"
    if wma20 > wma60 > wma120:
        return "bullish"
    elif wma20 < wma60 < wma120:
        return "bearish"
    else:
        return "neutral"

# Process each stock and generate output
wma_rsi_output = []
golden_cross_output = []

for code, records in data_by_stock.items():
    name = records[0]['name'] if records else ''
    closes = [r['cur_prc'] for r in records]
    
    # For each timestamp, calculate indicators using data up to that point
    for i, r in enumerate(records):
        available_closes = closes[:i+1]
        
        wma20 = calc_wma(available_closes, 20)
        wma60 = calc_wma(available_closes, 60)
        wma120 = calc_wma(available_closes, 120)
        rsi14 = calc_rsi(available_closes, 14)
        ma_cross = get_ma_cross(wma20, wma60, wma120)
        
        gap_pct_wma20 = None
        if wma20 and wma20 > 0:
            gap_pct_wma20 = round((r['cur_prc'] - wma20) / wma20 * 100, 2)
        
        out_record = {
            "ts": r['ts'],
            "code": code,
            "name": name,
            "cur_prc": r['cur_prc'],
            "flu_rt": round(r['flu_rt'], 2),
            "wma20": round(wma20, 2) if wma20 else None,
            "wma60": round(wma60, 2) if wma60 else None,
            "wma120": round(wma120, 2) if wma120 else None,
            "rsi14": round(rsi14, 2) if rsi14 else None,
            "ma_cross": ma_cross,
            "gap_pct_wma20": gap_pct_wma20
        }
        wma_rsi_output.append(out_record)
        
        # Check for golden/dead cross (WMA20 crossing WMA60)
        if i > 0:
            prev_closes = closes[:i]
            prev_wma20 = calc_wma(prev_closes, 20)
            prev_wma60 = calc_wma(prev_closes, 60)
            if prev_wma20 and prev_wma60 and wma20 and wma60:
                # Golden cross: WMA20 crosses above WMA60
                if prev_wma20 <= prev_wma60 and wma20 > wma60:
                    golden_cross_output.append({
                        "ts": r['ts'],
                        "code": code,
                        "name": name,
                        "type": "golden_cross",
                        "wma20": round(wma20, 2),
                        "wma60": round(wma60, 2),
                        "cur_prc": r['cur_prc'],
                        "rsi14": round(rsi14, 2) if rsi14 else None
                    })
                # Dead cross: WMA20 crosses below WMA60
                elif prev_wma20 >= prev_wma60 and wma20 < wma60:
                    golden_cross_output.append({
                        "ts": r['ts'],
                        "code": code,
                        "name": name,
                        "type": "dead_cross",
                        "wma20": round(wma20, 2),
                        "wma60": round(wma60, 2),
                        "cur_prc": r['cur_prc'],
                        "rsi14": round(rsi14, 2) if rsi14 else None
                    })

# Write outputs
output_dir = "/mnt/g/Ddrive/BatangD/task/workdiary/illinoisK/realtime"
os.makedirs(output_dir, exist_ok=True)

with open(os.path.join(output_dir, "wma_rsi_20260609.jsonl"), "w") as f:
    for r in wma_rsi_output:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

with open(os.path.join(output_dir, "golden_cross_20260609.jsonl"), "w") as f:
    for r in golden_cross_output:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"Generated {len(wma_rsi_output)} WMA/RSI records")
print(f"Generated {len(golden_cross_output)} golden/dead cross records")

# Show latest for each stock
print("\n=== Latest indicators per stock ===")
latest_by_stock = {}
for r in wma_rsi_output:
    code = r['code']
    if code not in latest_by_stock or r['ts'] > latest_by_stock[code]['ts']:
        latest_by_stock[code] = r

for code in sorted(latest_by_stock.keys()):
    r = latest_by_stock[code]
    print(f"{r['name']}({code}): {r['ts']} cur={r['cur_prc']:,} flu={r['flu_rt']}% wma20={r['wma20']} wma60={r['wma60']} wma120={r['wma120']} rsi={r['rsi14']} cross={r['ma_cross']} gap={r['gap_pct_wma20']}%")

print(f"\nGolden/Dead crosses found:")
for g in golden_cross_output:
    print(f"  {g['ts']} {g['name']}({g['code']}): {g['type']} wma20={g['wma20']} wma60={g['wma60']} rsi={g['rsi14']}")