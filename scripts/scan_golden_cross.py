#!/usr/bin/env python3
"""
illinoisK — 30분봉 골든크로스 + 거래원 + 프로그램매매 통합 스캔
사용: python3 scripts/scan_golden_cross.py [--full]
"""

import subprocess, json, sqlite3, time, sys, os
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DB", "illinoisK.db")

APPKEY_FILE = "/mnt/g/Ddrive/BatangD/task/workdiary/65stock/keys/appkey.txt"
SECRETKEY_FILE = "/mnt/g/Ddrive/BatangD/task/workdiary/65stock/keys/secretkey.txt"

def now_kst():
    return datetime.now(KST).strftime("%H:%M")

def get_token():
    with open(APPKEY_FILE) as f: appkey = f.read().strip()
    with open(SECRETKEY_FILE) as f: secretkey = f.read().strip()
    r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.kiwoom.com/oauth2/token',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({"grant_type":"client_credentials","appkey":appkey,"secretkey":secretkey})],
        capture_output=True, text=True, timeout=15)
    data = json.loads(r.stdout)
    if data.get("return_code") != 0:
        raise Exception(f"토큰 실패: {data.get('return_msg')}")
    return data["token"].strip()

def fetch_chart(token, code):
    """30분봉 차트 조회"""
    r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.kiwoom.com/api/dostk/chart',
        '-H', f'Authorization: Bearer {token}',
        '-H', 'Content-Type: application/json;charset=UTF-8',
        '-H', 'api-id: ka10080',
        '-d', json.dumps({"stk_cd": code, "tic_scope": "30", "upd_stkpc_tp": "1"})],
        capture_output=True, text=True, timeout=10)
    data = json.loads(r.stdout)
    rows = data.get("stk_min_pole_chart_qry", [])
    prices = []
    volumes = []
    for row in rows:
        try:
            p = abs(int(row.get("cur_prc", "0")))
            v = abs(int(row.get("trde_qty", "0")))
            if p > 0:
                prices.append(p)
                volumes.append(v)
        except:
            pass
    return list(reversed(prices)), list(reversed(volumes))

def fetch_brokerage(token, code):
    """거래원 조회 (ka10040) — 신한/키움 순위"""
    r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.kiwoom.com/api/dostk/rkinfo',
        '-H', f'Authorization: Bearer {token}',
        '-H', 'Content-Type: application/json;charset=UTF-8',
        '-H', 'api-id: ka10040',
        '-d', json.dumps({"stk_cd": code})],
        capture_output=True, text=True, timeout=10)
    data = json.loads(r.stdout)
    
    # Parse top 5 brokers
    buy_brokers = {}
    sell_brokers = {}
    for i in range(1, 6):
        bn = data.get(f"buy_trde_ori_{i}", "")
        bq = int(data.get(f"buy_trde_ori_qty_{i}", "0"))
        sn = data.get(f"sel_trde_ori_{i}", "")
        sq = int(data.get(f"sel_trde_ori_qty_{i}", "0"))
        if bn: buy_brokers[bn] = bq
        if sn: sell_brokers[sn] = sq
    
    # Shinhan = "신한", "신한투자" etc - check various names
    shinhan_buy_rank = 0
    shinhan_sell_rank = 0
    kiwoom_buy_rank = 0
    kiwoom_sell_rank = 0
    
    for i in range(1, 6):
        bn = data.get(f"buy_trde_ori_{i}", "")
        sn = data.get(f"sel_trde_ori_{i}", "")
        bq = int(data.get(f"buy_trde_ori_qty_{i}", "0"))
        sq = int(data.get(f"sel_trde_ori_qty_{i}", "0"))
        
        if "신한" in bn or "신한투자" in bn:
            shinhan_buy_rank = i
            shinhan_buy_qty = bq
        if "신한" in sn or "신한투자" in sn:
            shinhan_sell_rank = i
            shinhan_sell_qty = sq
        if "키움" in bn:
            kiwoom_buy_rank = i
            kiwoom_buy_qty = bq
        if "키움" in sn:
            kiwoom_sell_rank = i
            kiwoom_sell_qty = sq
    
    frgn_buy = int(data.get("frgn_buy_prsm_sum", "0"))
    frgn_sel = int(data.get("frgn_sel_prsm_sum", "0"))
    
    return {
        "shinhan_buy_rank": shinhan_buy_rank, "shinhan_sell_rank": shinhan_sell_rank,
        "kiwoom_buy_rank": kiwoom_buy_rank, "kiwoom_sell_rank": kiwoom_sell_rank,
        "frgn_net": frgn_buy - frgn_sel
    }

def fetch_program_batch(token):
    """종목별 프로그램 매수/매도 (ka90004) — 코스피/코스닥 각 1번 호출로 전 종목"""
    today = datetime.now(KST).strftime("%Y%m%d")
    result = {}
    
    for mrkt_code, mrkt_name in [("P00101", "코스피"), ("P10102", "코스닥")]:
        r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.kiwoom.com/api/dostk/stkinfo',
            '-H', f'Authorization: Bearer {token}',
            '-H', 'Content-Type: application/json;charset=UTF-8',
            '-H', 'api-id: ka90004',
            '-d', json.dumps({"dt": today, "mrkt_tp": mrkt_code, "stex_tp": "1"})],
            capture_output=True, text=True, timeout=15)
        try:
            data = json.loads(r.stdout)
            stocks_list = data.get("stk_prm_trde_prst", [])
            for s in stocks_list:
                code = s.get("stk_cd", "")
                if code:
                    result[code] = {
                        "prog_buy": int(s.get("buy_cntr_qty", "0") or "0"),
                        "prog_sell": int(s.get("sel_cntr_qty", "0") or "0"),
                        "prog_net": int(s.get("netprps_prica", "0") or "0"),
                        "prog_ratio": s.get("all_trde_rt", "0")
                    }
        except:
            pass
    
    return result

def fetch_futures_frgn_inst(token):
    """외인/기관 선물(KOSPI200) 순매수 조회 — ka10010 또는 전용 TR 필요"""
    # TODO: 키움 REST API에서 선물 외인/기관 수급 제공하는 TR 찾으면 구현
    # 현재 ka10010(프로그램매매동향)은 주식 기준, 선물 전용 TR 별도 필요
    # OpenAPI+라면: 
    #   - 선물/옵션 체결요청 (opt50001~)
    #   - 투자자별 매매동향 (opt10039/opt10040 등)
    return {"frgn_net": 0, "inst_net": 0, "source": "unavailable"}


def fetch_market_overview(token):
    """전체 시장 개요 — 코스피/코스닥 지수 + 선물 + 외인 매매 + 외인/기관 선물 수급"""
    overview = {}
    
    # 🔴 외인/기관 선물 수급 체크 (최우선)
    overview["futures_frgn_inst"] = fetch_futures_frgn_inst(token)
    
    # KOSPI200 선물 (106F200)
    r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.kiwoom.com/api/dostk/chart',
        '-H', f'Authorization: Bearer {token}',
        '-H', 'Content-Type: application/json;charset=UTF-8',
        '-H', 'api-id: ka10080',
        '-d', json.dumps({"stk_cd": "106F200", "tic_scope": "30", "upd_stkpc_tp": "1"})],
        capture_output=True, text=True, timeout=10)
    try:
        rows = json.loads(r.stdout).get("stk_min_pole_chart_qry", [])
        if rows:
            last = rows[0]
            overview["futures_price"] = abs(int(last.get("cur_prc","0")))
            overview["futures_time"] = last.get("cntr_tm","")
    except:
        pass
    
    # 프로그램 매매 동향 (ka10010 — 삼성전자로 시장 대표)
    r = subprocess.run(['curl', '-s', '-X', 'POST', 'https://api.kiwoom.com/api/dostk/sect',
        '-H', f'Authorization: Bearer {token}',
        '-H', 'Content-Type: application/json;charset=UTF-8',
        '-H', 'api-id: ka10010',
        '-d', json.dumps({"stk_cd": "005930"})],
        capture_output=True, text=True, timeout=10)
    try:
        d = json.loads(r.stdout)
        overview["프로그램_차익순매수"] = int(d.get("dfrt_trst_netprps_qty","0") or "0")
        overview["프로그램_비차익순매수"] = int(d.get("ndiffpro_trst_netprps_qty","0") or "0")
    except:
        pass
    
    return overview

def print_market_overview(ov):
    """시장 개요 출력"""
    print(f"\n🌍 전체 시장 현황 — {now_kst()} KST")
    print(f"  {'─'*40}")
    
    # 🔴 외인/기관 선물 수급 (최상단)
    ffi = ov.get("futures_frgn_inst", {})
    frgn_net = ffi.get("frgn_net", 0)
    inst_net = ffi.get("inst_net", 0)
    src = ffi.get("source", "unavailable")
    if frgn_net or inst_net:
        f_arrow = "🟢" if frgn_net > 0 else "🔴" if frgn_net < 0 else "⚪"
        i_arrow = "🟢" if inst_net > 0 else "🔴" if inst_net < 0 else "⚪"
        print(f"  📊 선물 외인: {f_arrow} {frgn_net:+,}주 | 기관: {i_arrow} {inst_net:+,}주 ({src})")
    else:
        print(f"  📊 선물 외인/기관: 데이터 없음 ({src})")
    
    # KOSPI200 선물
    fp = ov.get("futures_price", 0)
    if fp:
        print(f"  📈 코스피200선물: {fp:,}p")
    
    # 프로그램
    dfrt = ov.get("프로그램_차익순매수", 0)
    ndiff = ov.get("프로그램_비차익순매수", 0)
    if dfrt or ndiff:
        d_arrow = "🟢" if dfrt > 0 else "🔴" if dfrt < 0 else "⚪"
        n_arrow = "🟢" if ndiff > 0 else "🔴" if ndiff < 0 else "⚪"
        print(f"  🤖 프로그램 차익: {d_arrow} {dfrt:+,}주 | 비차익: {n_arrow} {ndiff:+,}주")

def main():
    print(f"\n{'='*60}")
    print(f"📊 30분봉 골든크로스 스캔 — {now_kst()} KST")
    print(f"{'='*60}")
    
    # 1. 토큰
    print("\n🔑 토큰 발급...", end=" ")
    token = get_token()
    print("OK")
    
    # 2. DB에서 미수 20~30% 종목 로드
    conn = sqlite3.connect(DB)
    stocks = conn.execute("""
        SELECT code, name, market, price, market_cap, margin_rate 
        FROM stock_list 
        WHERE margin_rate IN ('20%','30%')
        ORDER BY market_cap DESC
    """).fetchall()
    print(f"\n📋 스캔 대상: {len(stocks)}개 종목 (미수 20~30%)")
    
    # ───── 3. 30분봉 스캔 (ka10080) ─────
    print(f"\n📊 [1/4] 30분봉 차트 스캔...")
    gc_results = []
    total = len(stocks)
    
    for idx, (code, name, market, price, mcap, mr) in enumerate(stocks, 1):
        sys.stdout.write(f"\r  ⏳ [{idx}/{total}] {name:16s} ")
        sys.stdout.flush()
        
        prices, volumes = fetch_chart(token, code)
        
        if len(prices) < 20:
            continue
        
        current = prices[-1]
        ma20 = sum(prices[-20:]) / 20
        ma60 = sum(prices[-60:]) / 60 if len(prices) >= 60 else None
        
        if ma60 is None:
            continue
        
        is_gc = ma20 > ma60
        gap_pct = ((ma20 - ma60) / ma60) * 100
        trend_5 = ((prices[-1] - prices[-6]) / prices[-6]) * 100 if len(prices) >= 6 else 0
        
        if is_gc:
            gc_results.append({
                "code": code, "name": name, "market": market,
                "price": current, "mcap": mcap, "mr": mr,
                "gap_pct": gap_pct, "trend_5": trend_5,
                "ma20": round(ma20), "ma60": round(ma60)
            })
        
        time.sleep(0.15)
    
    sys.stdout.write("\r" + " " * 50 + "\r")
    gc_results.sort(key=lambda x: x["gap_pct"], reverse=True)
    print(f"\n✅ 골든크로스: {len(gc_results)}개 | 🔴 데드크로스: {total - len(gc_results)}개")
    
    # ───── 4. 거래원 스캔 (ka10040) — GC 종목만 ─────
    print(f"\n🏦 [2/4] 거래원 조회 (GC 종목)...")
    for idx, item in enumerate(gc_results, 1):
        sys.stdout.write(f"\r  🔍 [{idx}/{len(gc_results)}] {item['name']:16s} ")
        sys.stdout.flush()
        item["brokerage"] = fetch_brokerage(token, item["code"])
        time.sleep(0.12)
    
    sys.stdout.write("\r" + " " * 50 + "\r")
    print(f"✅ 거래원 완료")
    
    # ───── 5. 프로그램 매매 (ka90004) — 종목별, 2번 호출로 전 종목 ─────
    print(f"\n🤖 [3/4] 종목별 프로그램 매매 조회...")
    prog_data = fetch_program_batch(token)
    for item in gc_results:
        item["program"] = prog_data.get(item["code"], {"prog_buy":0,"prog_sell":0,"prog_net":0,"prog_ratio":"0"})
    print(f"✅ 프로그램 완료 ({len(prog_data)}개 종목)")
    
    # ───── 6. 시장 개요 ─────
    print(f"\n🌍 [4/4] 시장 개요 조회...")
    overview = fetch_market_overview(token)
    print(f"✅ 시장 개요 완료")
    
    # 리포트 상단에 시장 개요 추가
    print(f"\n{'='*60}")
    print_market_overview(overview)
    
    print(f"\n📊 GC 스캔 — {now_kst()} KST")
    print(f"✅ 골든크로스: {len(gc_results)}개 | 🔴 데드크로스: {total - len(gc_results)}개")
    
    # 상위 15개 — 1줄 1종목
    print(f"\n🔥 GC TOP15 (강도순)")
    for item in gc_results[:15]:
        # 거래원
        brk = item.get("brokerage", {})
        brk_parts = []
        if brk:
            sb_r = brk.get("shinhan_buy_rank", 0)
            ks_r = brk.get("kiwoom_sell_rank", 0)
            if sb_r: brk_parts.append(f"신↑{sb_r}")
            if ks_r: brk_parts.append(f"키↓{ks_r}")
        
        p = item.get("program", {})
        prog_str = ""
        if p:
            pb = p.get("prog_buy", 0)
            ps = p.get("prog_sell", 0)
            if pb or ps:
                prog_str = f"P{pb:,}/{ps:,}"
        
        arrow = "▲" if item["trend_5"] > 0 else "▼"
        sig = "🔥" if (brk and brk.get("shinhan_buy_rank",0) and brk.get("kiwoom_sell_rank",0)) else "  "
        mr_short = item["mr"].replace("%","")
        
        line = f"{sig}{item['name'][:4]} {item['price']:>7,} {mr_short:2s} {arrow}{abs(item['trend_5']):.1f}% g{abs(item['gap_pct']):.1f}%"
        if brk_parts: line += f" {' '.join(brk_parts)}"
        if prog_str: line += f" {prog_str}"
        print(line)
    
    # 6. DB 저장 — 시장 개요 + GC TOP 15 포함
    timestamp = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    content_lines = [f"## {timestamp} 30분봉 골든크로스 리포트"]
    
    # 시장 개요
    fp = overview.get("futures_price", 0)
    if fp: content_lines.append(f"코스피200선물: {fp:,}p")
    ffi = overview.get("futures_frgn_inst", {})
    frgn_net = ffi.get("frgn_net", 0)
    inst_net = ffi.get("inst_net", 0)
    if frgn_net or inst_net:
        content_lines.append(f"선물외인:{frgn_net:+,} 선물기관:{inst_net:+,}")
    dfrt = overview.get("프로그램_차익순매수", 0)
    ndiff = overview.get("프로그램_비차익순매수", 0)
    if dfrt or ndiff: content_lines.append(f"프로그램 차익{dfrt:+,} 비차익{ndiff:+,}")
    
    content_lines.append(f"GC:{len(gc_results)}개 DC:{total-len(gc_results)}개")
    for item in gc_results[:15]:
        b = item.get("brokerage", {})
        sign = "✅" 
        if b and b.get("shinhan_buy_rank",0) > 0 and b.get("kiwoom_sell_rank",0) > 0:
            sign = "🔥"
        content_lines.append(f"{sign} {item['name']} {item['price']:,} 격차+{item['gap_pct']:.1f}% 5봉{item['trend_5']:+.1f}% 증거금{item['mr']}")
    
    conn.execute("""INSERT INTO notes (created_at, created_kst, type, title, content, tags)
        VALUES (datetime('now'), datetime('now','+9 hours'), '전략분석', ?, ?, '30분봉,골든크로스,단타')""",
        (f"{timestamp} 30분봉 골든크로스 리포트", '\n'.join(content_lines)))
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"✅ 리포트 완료 — {now_kst()} KST")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()