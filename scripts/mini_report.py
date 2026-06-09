#!/usr/bin/env python3
"""
5분 간격 미니 리포트 — 거래원 + 프로그램 + 시장 개요
사용: python3 scripts/mini_report.py
"""
import subprocess, json, sqlite3, sys, os
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kiwoom_api import get_token

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DB", "illinoisK.db")

def now_kst():
    return datetime.now(KST).strftime("%H:%M")

def fetch_brokerage_top5(token, codes):
    """거래원 — 상위 5개 종목만 빠르게"""
    results = []
    for code in codes[:5]:
        r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.kiwoom.com/api/dostk/rkinfo',
            '-H', f'Authorization: Bearer {token}',
            '-H', 'Content-Type: application/json;charset=UTF-8',
            '-H', 'api-id: ka10040',
            '-d', json.dumps({"stk_cd": code})],
            capture_output=True, text=True, timeout=10)
        try:
            d = json.loads(r.stdout)
            results.append({"code": code, "data": d})
        except:
            pass
    return results

def get_gc_codes():
    """DB에서 골든크로스 종목코드 top 5 조회"""
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT code, name FROM stock_list 
        WHERE margin_rate IN ('20%','30%')
        ORDER BY market_cap DESC LIMIT 5
    """).fetchall()
    conn.close()
    return rows

def fetch_market_fast(token):
    """시장 개요 빠르게 — 선물 (ka10080)"""
    r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.kiwoom.com/api/dostk/chart',
        '-H', f'Authorization: Bearer {token}', '-H', 'Content-Type: application/json;charset=UTF-8',
        '-H', 'api-id: ka10080',
        '-d', json.dumps({"stk_cd": "106F200", "tic_scope": "30", "upd_stkpc_tp": "1"})],
        capture_output=True, text=True, timeout=10)
    fp = 0
    try:
        rows = json.loads(r.stdout).get("stk_min_pole_chart_qry", [])
        if rows: fp = abs(int(rows[0].get("cur_prc","0")))
    except: pass
    return fp

def fetch_program_batch_light(token):
    """종목별 프로그램 (ka90004) — 2번 호출, 캐시"""
    today = datetime.now(KST).strftime("%Y%m%d")
    result = {}
    for mrkt in ["P00101", "P10102"]:
        r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.kiwoom.com/api/dostk/stkinfo',
            '-H', f'Authorization: Bearer {token}',
            '-H', 'Content-Type: application/json;charset=UTF-8',
            '-H', 'api-id: ka90004',
            '-d', json.dumps({"dt": today, "mrkt_tp": mrkt, "stex_tp": "1"})],
            capture_output=True, text=True, timeout=15)
        try:
            for s in json.loads(r.stdout).get("stk_prm_trde_prst", []):
                if s.get("stk_cd"):
                    result[s["stk_cd"]] = {
                        "prog_buy": int(s.get("buy_cntr_qty","0") or "0"),
                        "prog_sell": int(s.get("sel_cntr_qty","0") or "0"),
                    }
        except: pass
    return result

def fetch_nxt_data(token):
    """NXT 프리장 데이터 (8:00~9:00 전용)"""
    today = datetime.now(KST).strftime("%Y%m%d")
    
    # NXT 프로그램 (ka90004, stex_tp=2)
    r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.kiwoom.com/api/dostk/stkinfo',
        '-H', f'Authorization: Bearer {token}', '-H', 'Content-Type: application/json;charset=UTF-8',
        '-H', 'api-id: ka90004',
        '-d', json.dumps({"dt": today, "mrkt_tp": "P00101", "stex_tp": "2"})],
        capture_output=True, text=True, timeout=15)
    prog = {}
    name_map = {}
    try:
        for s in json.loads(r.stdout).get("stk_prm_trde_prst", []):
            if s.get("stk_cd"):
                code = s["stk_cd"]
                prog[code] = {
                    "prog_buy": int(s.get("buy_cntr_qty","0") or "0"),
                    "prog_sell": int(s.get("sel_cntr_qty","0") or "0"),
                }
                name_map[code] = s.get("stk_nm", code.replace("_NX",""))
    except: pass
    
    # NXT TOP5 거래원
    nxt_codes = list(prog.keys())[:5]
    brk = {}
    nxt_names = []
    for code in nxt_codes:
        r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.kiwoom.com/api/dostk/rkinfo',
            '-H', f'Authorization: Bearer {token}', '-H', 'Content-Type: application/json;charset=UTF-8',
            '-H', 'api-id: ka10040',
            '-d', json.dumps({"stk_cd": code})],
            capture_output=True, text=True, timeout=10)
        try:
            brk[code] = json.loads(r.stdout)
            nm = name_map.get(code, code.replace("_NX",""))
            nxt_names.append((code, nm))
        except: pass
    
    return prog, brk, nxt_names

def main():
    token = get_token()
    now = datetime.now(KST)
    hour = now.hour
    minute = now.minute
    is_nxt = (hour < 9 or hour >= 15)  # 8시~9시 NXT프리장, 15시 이후 NXT애프터장
    # 15:30 KOSPI 종료, NXT는 20시까지 계속
    nxt_after = (hour >= 15 and not (hour == 15 and minute < 30))
    is_nxt = (hour < 9 or nxt_after)
    is_half = (minute == 0 or minute == 30)
    
    if is_nxt:
        # ───── NXT 프리장 (8:00~9:00) ─────
        prog, brk_data, top5 = fetch_nxt_data(token)
        fp = 0
        
        lines = [f"\n🌙 **NXT {now_kst()}** ", ""]
        
        # 프로그램 요약
        total_buy = sum(v["prog_buy"] for v in prog.values()) if prog else 0
        total_sell = sum(v["prog_sell"] for v in prog.values()) if prog else 0
        net = total_buy - total_sell
        lines.append(f"NXT {len(prog)}개 프로그램 {'🟢' if net>=0 else '🔴'} {net:+,}")
        lines.append("")
        
        for code, name in top5[:5]:
            d = brk_data.get(code, {})
            items = []
            sk_buy = kw_sell = False
            for j in range(1, 6):
                bn = d.get(f"buy_trde_ori_{j}","")
                sn = d.get(f"sel_trde_ori_{j}","")
                bq = d.get(f"buy_trde_ori_qty_{j}","0")
                sq = d.get(f"sel_trde_ori_qty_{j}","0")
                if "신한" in bn: items.append(f"신↑{bq.replace('+','')}"); sk_buy = True
                if "키움" in sn: items.append(f"키↓{sq.replace('-','').replace('+','')}"); kw_sell = True
            p = prog.get(code, {})
            ps = f" P{p['prog_buy']}/{p['prog_sell']}" if p and (p['prog_buy'] or p['prog_sell']) else ""
            sig = "🔥" if sk_buy and kw_sell else "  "
            lines.append(f"{sig}{name[:4]} {' '.join(items)}{ps}")
        
        print("\n".join(lines))
        
        # JSON 저장 (대시보드용)
        dash_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard_data.json")
        stocks_dash = []
        for code, name in top5[:5]:
            d = brk_data.get(code, {})
            sb = int(d.get("buy_trde_ori_qty_1","0")) if any("신한" in d.get(f"buy_trde_ori_{j}","") for j in range(1,6)) else 0
            ks = int(d.get("sel_trde_ori_qty_1","0")) if any("키움" in d.get(f"sel_trde_ori_{j}","") for j in range(1,6)) else 0
            p = prog.get(code, {})
            stocks_dash.append({"name":name,"price":0,"mr":"20","signal":sb>0 and ks>0,"shinhan_buy":sb,"kiwoom_sell":ks,"prog":p.get("prog_buy",0)-p.get("prog_sell",0) if p else 0,"change":0})
        total_net = sum(v["prog_buy"]-v["prog_sell"] for v in prog.values()) if prog else 0
        checks = []
        try:
            with open(dash_path) as f: checks = json.load(f).get("checks",[])
        except: pass
        checks.append({"time":now_kst(),"futures":"NXT","prog":f"{total_net:+,}","shinhan":str(stocks_dash[0].get("shinhan_buy",0)) if stocks_dash else "-","kiwoom":str(stocks_dash[0].get("kiwoom_sell",0)) if stocks_dash else "-"})
        checks = checks[-100:]
        with open(dash_path,"w") as f:
            json.dump({"time":now_kst(),"futures":0,"prog_net":total_net,"gc_count":0,"stocks":stocks_dash,"checks":checks}, f)
        
        conn = sqlite3.connect(DB)
        conn.execute("INSERT INTO notes (created_at, created_kst, type, title, content, tags) VALUES (datetime('now'), datetime('now','+9 hours'), '전략분석', ?, ?, 'NXT,5분체크')",
            (f"NXT {now_kst()}", f"NXT {len(prog)}개 프로그램 {total_net:+,}"))
        conn.commit()
        conn.close()
        return
    
    # ───── 본장 (9:00~15:30) ─────
    fp = fetch_market_fast(token)
    prog = fetch_program_batch_light(token)
    
    conn = sqlite3.connect(DB)
    top5 = conn.execute("SELECT code, name FROM stock_list WHERE margin_rate IN ('20%','30%') ORDER BY market_cap DESC LIMIT 5").fetchall()
    conn.close()
    
    brk_data = {}
    for code, name in top5:
        r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.kiwoom.com/api/dostk/rkinfo',
            '-H', f'Authorization: Bearer {token}', '-H', 'Content-Type: application/json;charset=UTF-8',
            '-H', 'api-id: ka10040',
            '-d', json.dumps({"stk_cd": code})],
            capture_output=True, text=True, timeout=10)
        try: brk_data[code] = json.loads(r.stdout)
        except: pass
    
    tag = "🔬" if is_half else ""
    lines = [f"\n{tag}**{now_kst()}** ", ""]
    
    # 1줄: 시장 개요
    parts = [f"선물 {fp:,}p"] if fp else []
    if prog:
        total_buy = sum(v["prog_buy"] for v in prog.values())
        total_sell = sum(v["prog_sell"] for v in prog.values())
        net = total_buy - total_sell
        ic = "🟢" if net > 0 else "🔴"
        parts.append(f"프로그램 {ic} {net:+,}")
    lines.append(" ".join(parts))
    lines.append("")
    
    # 주요 종목 — 1줄 1종목
    for code, name in top5[:3]:
        d = brk_data.get(code, {})
        items = []
        sk_buy = sk_sell = kw_buy = kw_sell = False
        for j in range(1, 6):
            bn = d.get(f"buy_trde_ori_{j}","")
            sn = d.get(f"sel_trde_ori_{j}","")
            bq = int(d.get(f"buy_trde_ori_qty_{j}","0"))
            sq = int(d.get(f"sel_trde_ori_qty_{j}","0"))
            if "신한" in bn: items.append(f"신↑{bq:,}"); sk_buy = True
            if "신한" in sn: items.append(f"신↓{sq:,}"); sk_sell = True
            if "키움" in bn: items.append(f"키↑{bq:,}"); kw_buy = True
            if "키움" in sn: items.append(f"키↓{sq:,}"); kw_sell = True
        
        p = prog.get(code, {})
        prog_str = f" P{p.get('prog_buy',0):,}/{p.get('prog_sell',0):,}" if p and (p.get('prog_buy') or p.get('prog_sell')) else ""
        
        sig = "🔥" if sk_buy and kw_sell else "  "
        
        name_short = name[:4]
        line = f"{sig}{name_short} {' '.join(items)}{prog_str}"
        lines.append(line)
    
    print("\n".join(lines))
    
    # 30분마다: FULL 리포트 참고
    if is_half:
        print(f"  ➡ 30분봉 GC 스캔 실행: scan_golden_cross.py")
    
    # ===== JSON 저장 (대시보드용) =====
    dash_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard_data.json")
    
    stocks_dash = []
    for code, name in top5[:5]:
        d = brk_data.get(code, {})
        sb = 0; ks = 0
        for j in range(1, 6):
            bn = d.get(f"buy_trde_ori_{j}","")
            sn = d.get(f"sel_trde_ori_{j}","")
            if "신한" in bn: sb = int(d.get(f"buy_trde_ori_qty_{j}","0"))
            if "키움" in sn: ks = int(d.get(f"sel_trde_ori_qty_{j}","0"))
        p = prog.get(code, {})
        stocks_dash.append({
            "name": name, "price": 0, "mr": "20",
            "signal": sb > 0 and abs(ks) > 0,
            "shinhan_buy": sb, "kiwoom_sell": ks,
            "prog": p.get("prog_buy", 0) - p.get("prog_sell", 0) if p else 0,
            "change": 0
        })
    
    checks = []
    try:
        with open(dash_path) as f: existing = json.load(f)
        checks = existing.get("checks", [])
    except: pass
    
    total_prog_net = sum(v["prog_buy"] - v["prog_sell"] for v in prog.values()) if prog else 0
    checks.append({
        "time": now_kst(), "futures": f"{fp:,}p" if fp else "-",
        "prog": f"{total_prog_net:+,}",
        "shinhan": str(stocks_dash[0].get("shinhan_buy",0)) if stocks_dash else "-",
        "kiwoom": str(stocks_dash[0].get("kiwoom_sell",0)) if stocks_dash else "-"
    })
    checks = checks[-100:]
    
    with open(dash_path, "w") as f:
        json.dump({"time": now_kst(), "futures": fp, "prog_net": total_prog_net,
                    "gc_count": 0, "stocks": stocks_dash, "checks": checks}, f)
    
    # DB 저장
    conn2 = sqlite3.connect(DB)
    conn2.execute("INSERT INTO notes (created_at, created_kst, type, title, content, tags) VALUES (datetime('now'), datetime('now','+9 hours'), '전략분석', ?, ?, '5분체크,거래원,프로그램')",
        (f"{now_kst()} 체크", f"선물{fp:,}p 프로그램{total_prog_net:+,}"))
    conn2.commit()
    conn2.close()

if __name__ == "__main__":
    main()

