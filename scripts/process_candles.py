import json
import os
from datetime import datetime
from collections import defaultdict

# Read the candles file (has pre-calculated WMA/RSI from historical data)
candles_file = "/mnt/g/Ddrive/BatangD/task/workdiary/illinoisK/realtime/candles_30min_20260609.jsonl"

data_by_stock = defaultdict(list)
with open(candles_file) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            code = d.get('code')
            if not code:
                continue
            # Parse timestamp to get HH:MM
            dt = datetime.strptime(d['ts'], "%Y-%m-%d %H:%M:%S")
            time_key = dt.strftime("%H:%M")
            data_by_stock[code].append({
                'ts': time_key,
                'full_ts': d['ts'],
                'cur_prc': d['cur_prc'],
                'flu_rt': d['flu_rt'],
                'frgn_net': d.get('frgn_net', 0),
                'orgn_net': d.get('orgn_net', 0),
                'name': d.get('name', ''),
                # Pre-calculated values
                'wma20': d.get('wma20'),
                'wma60': d.get('wma60'),
                'wma120': d.get('wma120'),
                'rsi14': d.get('rsi14'),
            })
        except Exception as e:
            continue

# Sort each stock's data by timestamp
for code in data_by_stock:
    data_by_stock[code].sort(key=lambda x: x['full_ts'])

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
    
    # For each timestamp, use the pre-calculated values
    for i, r in enumerate(records):
        wma20 = r['wma20']
        wma60 = r['wma60']
        wma120 = r['wma120']
        rsi14 = r['rsi14']
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
            "gap_pct_wma20": gap_pct_wma20,
            "frgn_net": r['frgn_net'],
            "orgn_net": r['orgn_net']
        }
        wma_rsi_output.append(out_record)
        
        # Check for golden/dead cross (WMA20 crossing WMA60)
        if i > 0 and wma20 and wma60:
            prev = records[i-1]
            prev_wma20 = prev['wma20']
            prev_wma60 = prev['wma60']
            if prev_wma20 and prev_wma60:
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

# Also write to ~/stock-trading/data/ as requested
home_data_dir = "/root/stock-trading/data"
os.makedirs(home_data_dir, exist_ok=True)

# Main output: illinoisK/realtime/
with open(os.path.join(output_dir, "wma_rsi_20260609.jsonl"), "w") as f:
    for r in wma_rsi_output:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

with open(os.path.join(output_dir, "golden_cross_20260609.jsonl"), "w") as f:
    for r in golden_cross_output:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

# Symlink/copy to ~/stock-trading/data/
for fname in ["wma_rsi_20260609.jsonl", "golden_cross_20260609.jsonl"]:
    src = os.path.join(output_dir, fname)
    dst = os.path.join(home_data_dir, fname)
    # Copy
    import shutil
    shutil.copy2(src, dst)

print(f"Generated {len(wma_rsi_output)} WMA/RSI records")
print(f"Generated {len(golden_cross_output)} golden/dead cross records")

# Show latest for each stock
print("\n=== Latest indicators per stock ===")
latest_by_stock = {}
for r in wma_rsi_output:
    code = r['code']
    if code not in latest_by_stock or r['ts'] > latest_by_stock[code]['ts']:
        latest_by_stock[code] = r

# Only show stocks with 10+ records (meaningful data)
for code in sorted(latest_by_stock.keys()):
    r = latest_by_stock[code]
    # Check if this stock has enough records
    if len(data_by_stock[code]) >= 10:
        print(f"{r['name']}({code}): {r['ts']} cur={r['cur_prc']:,} flu={r['flu_rt']}% wma20={r['wma20']} wma60={r['wma60']} wma120={r['wma120']} rsi={r['rsi14']} cross={r['ma_cross']} gap={r['gap_pct_wma20']}%")

print(f"\nGolden/Dead crosses found:")
for g in golden_cross_output:
    print(f"  {g['ts']} {g['name']}({g['code']}): {g['type']} wma20={g['wma20']} wma60={g['wma60']} rsi={g['rsi14']}")
