#!/usr/bin/env python3
"""Strategy Data Generator v2 — collects market data, generates strategy-data.js for Monday Strategy dashboard.

Usage:
  python3 scripts/strategy_generator.py
  (or via cronjob)

Output: report/js/strategy-data.js (read by monday-strategy.html)

Data sources (by priority): 
  1. DB/illinoisK.db → stock_prices (KRX source, daily snapshots)
  2. 분기보고서/*.txt → quarterly report summaries
"""
import sqlite3, json, os, sys
from datetime import datetime
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /mnt/g/.../illinoisK
DB = os.path.join(BASE, "DB/illinoisK.db")
REPORT_DIR = os.path.join(BASE, "report")
QUARTER_DIR = os.path.join(BASE, "분기보고서")

# Full watchlist + additional stocks (name → code mapping for DB lookup)
WATCH_STOCKS = {
    "삼성전자": "005930", "SK하이닉스": "000660", "삼성전자우": "005935",
    "리노공업": "058470", "원익IPS": "240810", "이오테크닉스": "039030",
    "동진쎄미켐": "005290", "ISC": "095340", "두산테스나": "131970",
    "HPSP": "403870", "한미반도체": "042700", "주성엔지니어링": "036930",
    "제주반도체": "080220", "하나마이크론": "067310", "이수페타시스": "007660",
    "피에스케이": "319660", "한화비전": "489790",
    "대덕전자": "353200", "케이씨텍": "281820",
    "이엔에프테크놀로지": "102710", "솔브레인": "357780",
    "와이씨": "232140", "에스티아이": "039440",
    "고영": "098460", "테스": "095610", "유진테크": "084370",
    "심텍": "222800", "에스에프에이": "056190",
    "에스앤에스텍": "101490", "GST": "083450", "코미코": "183490",
    "SFA반도체": "036540", "디아이": "003160", "DB하이텍": "000990"
}

CATEGORIES = {
    "005930": "대장주", "000660": "대장주", "005935": "대장주",
    "240810": "장비", "039030": "장비", "403870": "장비",
    "042700": "장비", "036930": "장비", "319660": "장비",
    "095610": "장비", "084370": "장비", "039440": "장비",
    "232140": "장비", "281820": "장비", "056190": "장비",
    "058470": "소켓", "095340": "소켓",
    "005290": "소재", "357780": "소재", "102710": "소재",
    "353200": "PCB", "222800": "반도체기판", "007660": "PCB",
    "131970": "테스트서비스", "067310": "패키징테스트",
    "036540": "조립검사", "080220": "유통", "489790": "보안/반도체장비",
    "101490": "마스크", "098460": "3D검사", "083450": "검사장비",
    "000990": "파운드리", "183490": "부품정비", "003160": "장비"
}

def calc_rsi_from_daily(daily_prices, period=14):
    """Calculate RSI from daily close prices (oldest first)."""
    if len(daily_prices) < period + 1: return 50.0
    p = daily_prices
    gains, losses = [], []
    for i in range(1, len(p)):
        diff = p[i] - p[i-1]
        if diff > 0: gains.append(diff); losses.append(0)
        else: gains.append(0); losses.append(abs(diff))
    if not gains: return 50.0
    recent_g = gains[-period:]
    recent_l = losses[-period:]
    avg_g = sum(recent_g) / period
    avg_l = sum(recent_l) / period
    if avg_l == 0: return 100.0
    if avg_g == 0: return 0.0
    rs = avg_g / avg_l
    return round(100.0 - (100.0 / (1.0 + rs)), 1)

def load_stock_data():
    """Load all stock data from DB. Returns dict by code."""
    if not os.path.exists(DB):
        print(f"❌ DB not found: {DB}", file=sys.stderr)
        return {}
    
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get all distinct codes in stock_prices
    cur.execute("SELECT DISTINCT code, name FROM stock_prices WHERE source='KRX'")
    db_codes = {r['code']: r['name'] for r in cur.fetchall()}
    
    print(f"📊 DB has {len(db_codes)} distinct codes (KRX source)")
    
    result = {}
    matched = 0
    
    for sname, scode in WATCH_STOCKS.items():
        # Try exact code match
        if scode in db_codes:
            code = scode
        else:
            # Try name match (exact match first, then startswith)
            matched_name = None
            for c, n in db_codes.items():
                if n and n.strip() == sname:
                    matched_name = c
                    break
            if not matched_name:
                for c, n in db_codes.items():
                    if n and n.strip().startswith(sname):
                        matched_name = c
                        break
            if matched_name:
                code = matched_name
            else:
                print(f"  ⚠️ {sname} ({scode}) not in DB, skipping")
                continue
        
        matched += 1
        
        # ── 1. Latest data ──
        cur.execute("""
            SELECT price, flu_rt, volume, open_pric, high_pric, low_pric, captured_at
            FROM stock_prices 
            WHERE code = ? AND source = 'KRX'
            ORDER BY captured_at DESC LIMIT 1
        """, (code,))
        latest = cur.fetchone()
        if not latest:
            continue
        
        # ── 2. Daily close prices (one per day, last 60 days) ──
        cur.execute("""
            SELECT DATE(captured_at) as d, price, volume
            FROM stock_prices 
            WHERE code = ? AND source = 'KRX'
            GROUP BY d ORDER BY d DESC LIMIT 60
        """, (code,))
        daily_rows = cur.fetchall()
        
        # Daily prices (oldest first for RSI)
        daily_prices = [r['price'] for r in reversed(daily_rows)]
        daily_volumes = [r['volume'] for r in reversed(daily_rows)]
        
        # ── 3. RSI ──
        rsi = calc_rsi_from_daily(daily_prices, 14)
        
        # ── 4. Volume ratio ──
        if len(daily_volumes) >= 10:
            avg_vol = sum(daily_volumes[-10:]) / 10
        else:
            avg_vol = latest['volume']
        vol_ratio = round(latest['volume'] / max(avg_vol, 1), 1) if avg_vol > 0 else 1.0
        
        # ── 5. Support / Resistance (last 10 daily closes) ──
        recent = daily_prices[-10:] if len(daily_prices) >= 10 else daily_prices
        support = min(recent) if recent else latest['price']
        resistance = max(recent) if recent else latest['price']
        
        # Round to nearest 100/500/1000 based on price level
        def round_price(val, tick=None):
            if tick: return round(val / tick) * tick
            if val >= 1000000: return round(val / 1000) * 1000
            if val >= 100000: return round(val / 500) * 500
            if val >= 10000: return round(val / 100) * 100
            return round(val / 10) * 10
        
        # ── 6. Moving Averages ──
        sma5 = round(sum(daily_prices[-5:]) / 5) if len(daily_prices) >= 5 else None
        sma10 = round(sum(daily_prices[-10:]) / 10) if len(daily_prices) >= 10 else None
        sma20 = round(sum(daily_prices[-20:]) / 20) if len(daily_prices) >= 20 else None
        
        # ── 7. Quarterly report summary ──
        quarterly_text = ""
        qpath = os.path.join(QUARTER_DIR, f"[{sname}]분기보고서(2026.05.15).txt")
        if os.path.exists(qpath):
            try:
                with open(qpath, 'r', encoding='utf-8') as f:
                    text = f.read(500)
                    # Strip leading whitespace/table of contents noise
                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                    quarterly_text = ' '.join(lines[:5])[:300]
            except:
                pass
        
        # ── 8. Build entry ──
        price = latest['price']
        change = round(latest['flu_rt'], 2) if latest['flu_rt'] else 0
        
        result[code] = {
            "name": sname,
            "ticker": code,
            "category": CATEGORIES.get(code, "기타"),
            "price": price,
            "change": change,
            "rsi": rsi,
            "volume_ratio": vol_ratio,
            "volume": int(latest['volume']) if latest['volume'] else 0,
            "support_1": round_price(support),
            "support_2": round_price(round(support * 0.95)),
            "resistance_1": round_price(resistance),
            "resistance_2": round_price(round(resistance * 1.05)),
            "sma_5": round_price(sma5) if sma5 else None,
            "sma_10": round_price(sma10) if sma10 else None,
            "sma_20": round_price(sma20) if sma20 else None,
            "quarterly_summary": quarterly_text,
            "data_days": len(daily_prices)
        }
        
        print(f"  ✅ {sname:>8} ({code}) | {price:>8,}원 | {'🟢' if change>=0 else '🔴'} {change:+.2f}% | RSI {rsi} | 지지 {support:,} → 저항 {resistance:,} | {len(daily_prices)}일 데이터")
    
    conn.close()
    print(f"\n📈 Total: {matched} stocks matched, {len(result)} with full data")
    return result

# Agent style round-robin based on WATCH_STOCKS order
AGENT_STYLES = {}
watch_order = list(WATCH_STOCKS.items())  # (name, code) pairs in definition order
for idx, (sname, scode) in enumerate(watch_order, start=1):
    if idx % 3 == 1:
        AGENT_STYLES[scode] = ("tech", "테크니컬")
    elif idx % 3 == 2:
        AGENT_STYLES[scode] = ("fund", "펀더멘탈")
    else:
        AGENT_STYLES[scode] = ("supply", "수급")

def generate_strategy_js(stocks):
    """Generate strategy-data.js — preserves existing Ultra/DeepSeek/ELO analysis from previous file."""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00")
    
    # Read existing data to preserve analysis content
    existing_analysis = {}  # ticker → {ultra: ..., hermes_deepseek: ...}
    existing_market = {}
    outpath = os.path.join(REPORT_DIR, "js/strategy-data.js")
    if os.path.exists(outpath):
        try:
            with open(outpath, 'r') as f:
                raw = f.read()
            # Extract JSON from const STRATEGY_DATA = { ... };
            import re
            m = re.search(r'const STRATEGY_DATA\s*=\s*({.*?});\s*$', raw, re.DOTALL)
            if m:
                old = json.loads(m.group(1))
                for s in old.get('stocks', []):
                    ticker = s.get('ticker')
                    if ticker and s.get('ultra', {}).get('analysis'):
                        existing_analysis[ticker] = {
                            'ultra': s['ultra'],
                            'hermes_deepseek': s['hermes_deepseek']
                        }
                        # Also preserve ELO fields (including agent_style, agent_label, judge_history)
                        if 'elo' in s.get('ultra', {}):
                            existing_analysis[ticker]['elo'] = s['ultra']['elo']
                if old.get('market', {}).get('ultra_analysis'):
                    existing_market = old['market']
        except:
            pass
    
    stock_list = []
    for code, s in stocks.items():
        # Assign agent_style based on round-robin
        agent_style, agent_label = AGENT_STYLES.get(code, ("tech", "테크니컬"))
        
        # Default elo with agent_style
        default_elo = {
            "score": 1200, "wins": 0, "losses": 0, "total": 0,
            "accuracy": "--", "last_result": "",
            "agent_style": agent_style,
            "agent_label": agent_label,
            "judge_history": []
        }
        
        # Carry over existing analysis if available
        ultra = {"analysis": "", "action": "", "entry": "", "target": "", "stop": "", "reasoning": "", "elo": default_elo}
        hermes = {"analysis": "", "risk": "", "supplement": "", "agreement": ""}
        if code in existing_analysis:
            ultra.update(existing_analysis[code].get('ultra', {}))
            hermes.update(existing_analysis[code].get('hermes_deepseek', {}))
            # Preserve ELO fields (agent_style, judge_history, score, etc.)
            if 'elo' in existing_analysis[code]:
                # Merge: keep agent_style/agent_label from round-robin, preserve score/wins/losses/judge_history
                saved_elo = existing_analysis[code]['elo']
                saved_elo['agent_style'] = agent_style
                saved_elo['agent_label'] = agent_label
                ultra['elo'] = saved_elo
        
        entry = {
            "name": s["name"],
            "ticker": s["ticker"],
            "category": s["category"],
            "price": s["price"],
            "change": s["change"],
            "rsi": s["rsi"],
            "support_1": s["support_1"],
            "support_2": s["support_2"],
            "resistance_1": s["resistance_1"],
            "resistance_2": s["resistance_2"],
            "volume_ratio": s["volume_ratio"],
            "volume": s["volume"],
            "sma_5": s["sma_5"],
            "sma_10": s["sma_10"],
            "sma_20": s["sma_20"],
            "quarterly_summary": s["quarterly_summary"],
            "ultra": ultra,
            "hermes_deepseek": hermes
        }
        stock_list.append(entry)
    
    # US market close: 6/5 Fri 16:00 EDT = 6/6 05:00 KST
    market = {
        "ultra_analysis": existing_market.get("ultra_analysis", ""),
        "ultra_action": existing_market.get("ultra_action", ""),
        "hermes_deepseek": existing_market.get("hermes_deepseek", "")
    }
    
    data = {
        "generated_at": now,
        "market_update": "US 06/05 16:00 EDT | KST 06/06 05:00",
        "market": market,
        "stocks": stock_list
    }
    
    # Sort by |change| descending (most volatile first)
    data["stocks"].sort(key=lambda x: abs(x["change"]), reverse=True)
    
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    js_content = f"const STRATEGY_DATA = {json_str};\n"
    
    outpath = os.path.join(REPORT_DIR, "js/strategy-data.js")
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    size = os.path.getsize(outpath)
    print(f"\n✅ strategy-data.js written: {size:,} bytes, {len(stock_list)} stocks")
    print(f"   Path: {outpath}")
    print(f"   Generated: {now}")
    print(f"   ⚠️  Ultra & DeepSeek analysis fields are empty — need sub-agent pipeline to fill")
    print(f"   📁 Open: http://localhost:8081/monday-strategy.html")
    return len(stock_list)

if __name__ == "__main__":
    print("=" * 60)
    print("📊 Strategy Data Generator v2")
    print(f"   DB: {DB}")
    print(f"   Target: {len(WATCH_STOCKS)} stocks")
    print("=" * 60)
    
    stocks = load_stock_data()
    
    if stocks:
        count = generate_strategy_js(stocks)
        print(f"\n🎯 {count} stocks ready for Monday Strategy page")
    else:
        print("❌ No stock data loaded!")
        sys.exit(1)
