#!/usr/bin/env python3
"""14개 종목 문서 채우기 (levels.md, trades.md, overview.md 보강)
사용: python3 scripts/fill_stock_docs.py
"""
import os
import sys
import sqlite3
import json
from datetime import datetime

# ─── 트레이스 헬퍼 ───
sys.path.insert(0, os.path.dirname(__file__))
from trace_helper import new_trace, start_span, end_span, traced, span, inject_trace_env

BASE = "/mnt/g/Ddrive/BatangD/task/workdiary/illinoisK"
DB = os.path.join(BASE, "DB/illinoisK.db")
REALTIME = os.path.join(BASE, "realtime/latest.json")
NOW_KST = "2026-06-04 14:58"

# 종목 정의: code, name, folder_name, market
STOCKS = [
    # DB 데이터 있는 10종목
    ("005930", "삼성전자", "삼성전자", "KOSPI"),
    ("005935", "삼성전자우", "삼성전자우", "KOSPI"),
    ("000660", "SK하이닉스", "SK하이닉스", "KOSPI"),
    ("039030", "이오테크닉스", "이오테크닉스", "KOSDAQ"),
    ("058470", "리노공업", "리노공업", "KOSDAQ"),
    ("240810", "원익IPS", "원익IPS", "KOSDAQ"),
    ("005290", "동진쎄미켐", "동진쎄미켐", "KOSDAQ"),
    ("403870", "HPSP", "HPSP", "KOSDAQ"),
    ("042700", "한미반도체", "한미반도체", "KOSDAQ"),
    ("036930", "주성엔지니어링", "주성엔지니어링", "KOSDAQ"),
    # DB 데이터 없는 4종목 (추가 관심종목)
    ("007660", "이수페타시스", "이수페타시스", "KOSDAQ"),
    ("080220", "제주반도체", "제주반도체", "KOSDAQ"),
    ("067310", "하나마이크론", "하나마이크론", "KOSDAQ"),
    ("000000", "한화비전", "한화비전", "KOSPI"),  # 코드 미확인
]

# 이미 완료된 종목 (수동 생성)
SKIP = {"ISC", "두테"}

# 호가단위
def get_hoga(price):
    if price < 1000: return 1
    elif price < 5000: return 5
    elif price < 10000: return 10
    elif price < 50000: return 50
    elif price < 100000: return 100
    elif price < 500000: return 500
    elif price < 1000000: return 1000
    else: return 1000


@traced("db-load-stock-data", "종목별 DB 데이터 로드 (52주 범위, 최신가, 일별 데이터)")
def load_db_data(code):
    """DB에서 52주 범위, 최신가, 일별 데이터 조회"""
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # 52주 범위
    cur.execute("""
        SELECT MIN(price), MAX(price), MIN(captured_at), MAX(captured_at)
        FROM stock_prices WHERE code=? AND source='KRX'
    """, (code,))
    r = cur.fetchone()
    low_52w, high_52w, low_dt, high_dt = r if r else (None, None, None, None)
    
    # 최신 데이터
    cur.execute("""
        SELECT price, flu_rt, volume, captured_at
        FROM stock_prices WHERE code=? AND source='KRX'
        ORDER BY captured_at DESC LIMIT 1
    """, (code,))
    r = cur.fetchone()
    latest_price, flu_rt, volume, last_dt = r if r else (None, None, None, None)
    
    # 일별 고가/저가
    cur.execute("""
        SELECT date(captured_at) as dt,
               MIN(price) as day_low,
               MAX(price) as day_high,
               MAX(CASE WHEN captured_at = max_ts THEN price END) as close
        FROM stock_prices sp
        JOIN (SELECT date(captured_at) as d, MAX(captured_at) as max_ts
              FROM stock_prices WHERE code=? AND source='KRX' GROUP BY d) m
        ON date(sp.captured_at) = m.d
        WHERE sp.code=? AND sp.source='KRX'
        GROUP BY dt ORDER BY dt
    """, (code, code))
    daily_data = cur.fetchall()
    
    conn.close()
    return low_52w, high_52w, low_dt, high_dt, latest_price, flu_rt, volume, last_dt, daily_data

@traced("gen-levels", "levels.md 생성 (52주 고/저, 일봉 레벨, 호가단위)")
def gen_levels(code, name, folder, market):
    """levels.md 생성"""
    with span("db-load", f"{name} DB 데이터 조회"):
        low_52w, high_52w, low_dt, high_dt, lp, fr, vol, last_dt, dd = load_db_data(code)
    
    lines = [f"# {name} ({code}) — 가격 레벨",
             "",
             f"*최종 업데이트: {NOW_KST}*",
             "",
             "## 현재가",
             ]
    
    if lp:
        last_date = last_dt[:10] if last_dt else "?"
        lines += [f"- **{last_date} 현재:** {lp:,}원 ({fr:+.2f}%)"]
        if dd and len(dd) > 0:
            today = [d for d in dd if d[0] == last_date[:10]]
            if today:
                lines += [f"- **당일 고가:** {today[0][2]:,}  **당일 저가:** {today[0][1]:,}"]
        lines += [f"- **호가단위:** {get_hoga(lp):,}원",
                  f"- **거래량:** {vol:,}주" if vol else ""]
    else:
        lines += ["- DB 데이터 없음 (실시간 수집 대상 아님)"]
    
    lines += ["",
              "## 주요 레벨",
              "",
              "| 구분 | 가격 | 비고 |",
              "|:----|:---:|:-----|"]
    
    if high_52w:
        lines += [f"| **관측 최고가** | {high_52w:,} | {high_dt[:10] if high_dt else '?'} |"]
    if low_52w:
        lines += [f"| **관측 최저가** | {low_52w:,} | {low_dt[:10] if low_dt else '?'} |"]
    
    if dd and len(dd) >= 3:
        recent = dd[-3:]
        for d in recent:
            lines += [f"| {d[0]} 고가 | {d[2]:,} | |",
                      f"| {d[0]} 저가 | {d[1]:,} | |"]
    
    if lp:
        lines += ["",
                  "## 호가단위",
                  "| 가격대 | 호가단위 |",
                  "|:------|:--------|"]
        lines += [f"| {lp:,} 전후 | {get_hoga(lp):,}원 |"]
    
    lines += ["",
              "## 비고",
              "- 52주 범위는 DB 보유 기간(5/29~6/4) 기준 관측값",
              "- 실시간 지지/저항은 일봉 기준 추가 분석 필요",
              ""]
    
    return "\n".join(filter(None, lines))

@traced("gen-trades", "trades.md 생성 (매매 판단 기록 템플릿)")
def gen_trades(code, name, folder, market):
    """trades.md 생성 (기본 템플릿)"""
    lp = load_db_data(code)[4]
    
    lines = [f"# {name} ({code}) — 매매 판단 기록",
             f"",
             f"*최종 업데이트: {NOW_KST}*",
             f"",
             f"---",
             f"",
             f"## 매매 기록",
             f"",
             f"아직 매매 내역이 없습니다. 거래가 발생하면 이 파일에 기록합니다.",
             f""]
    
    if lp:
        lines += [f"**참고:** 마지막 관측가 = {lp:,}원 ({NOW_KST})",
                  f""]
    
    lines += ["---",
              "",
              "### 작성 양식",
              "",
              "```",
              "## YYYY-MM-DD (요일)",
              "",
              "| 구분 | 내용 |",
              "|:----|:------|",
              "| **매수가** | 000,000 |",
              "| **매도가** | 000,000 |",
              "| **수익률** | +0.0% |",
              "| **전략** | 전략명 |",
              "",
              "**판단 근거:** ...",
              "```",
              ""]
    
    return "\n".join(lines)

@traced("gen-overview", "overview.md 보강 (업종/특징 채움)")
def gen_overview_if_empty(code, name, folder, market):
    """overview.md가 비어있거나 최소한일 경우 보강"""
    path = os.path.join(BASE, "stock", folder, f"{folder}-overview.md")
    if not os.path.exists(path):
        return  # 없으면 스킵 (이미 Hermes가 생성했을 것)
    
    with open(path) as f:
        content = f.read()
    
    # 이미 내용이 충실하면 스킵
    if len(content.strip()) > 300:
        return
    
    # 업종 매핑
    sector_map = {
        "삼성전자": "반도체(종합)", "삼성전자우": "반도체(종합)", "SK하이닉스": "반도체(메모리)",
        "이오테크닉스": "반도체 장비", "리노공업": "반도체 소켓/테스트",
        "원익IPS": "반도체 장비(증착)", "동진쎄미켐": "반도체 소재(포토레지스트)",
        "HPSP": "반도체 장비(고압산화)", "한미반도체": "반도체 장비(패키징)",
        "주성엔지니어링": "반도체 장비(CVD/ALD)",
        "이수페타시스": "반도체 PCB/기판", "제주반도체": "반도체 유통/솔루션",
        "하나마이크론": "반도체 패키징/테스트", "한화비전": "보안/영상솔루션"
    }
    sector = sector_map.get(name, "일반")
    
    new_content = f"""# {name} ({code}) — 기업 개요

*최종 업데이트: {NOW_KST}*

## 기본 정보
- **업종:** {sector}
- **시장:** {market}
- **코드:** {code}

## 주요 사업
{sector} 분야 영위.

## 특징
- DB 실시간 수집 대상: {"✅ (1분 갱신)" if code != "000000" else "❌ (수집 대상 아님)"}
- 매매 판단 기록: [trades.md]({folder}-trades.md) 참조

---
*본 문서는 DB 관측 데이터 기반 자동 생성 템플릿입니다.*
"""
    with open(path, 'w') as f:
        f.write(new_content)
    print(f"  ✅ {name} overview.md 보강 완료")

def write_file_safe(path, content, label=""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    print(f"  ✅ {label or os.path.basename(path)}")

@traced("fill-stock-docs-main", "14개 종목 문서 일괄 생성 메인 플로우")
def main():
    # 트레이스 시작
    trace_id = new_trace("fill-stock-docs")
    os.environ.update(inject_trace_env())
    
    sep = "=" * 60
    print(sep)
    print(f"14개 종목 문서 채우기 시작 ({NOW_KST})")
    print(sep)
    
    for code, name, folder, market in STOCKS:
        if name in SKIP:
            print(f"\n⏭️  {name} — 수동 생성 완료, 스킵")
            continue
        
        stock_dir = os.path.join(BASE, "stock", folder)
        if not os.path.exists(stock_dir):
            print(f"\n⚠️  {name} 폴더 없음, 스킵")
            continue
        
        print(f"\n📄 {name} ({code}) [{market}]")
        
        # levels.md
        levels = gen_levels(code, name, folder, market)
        write_file_safe(os.path.join(stock_dir, f"{folder}-levels.md"), levels, f"{name} levels.md")
        
        # trades.md
        trades = gen_trades(code, name, folder, market)
        write_file_safe(os.path.join(stock_dir, f"{folder}-trades.md"), trades, f"{name} trades.md")
        
        # overview.md 보강 (필요시)
        gen_overview_if_empty(code, name, folder, market)
    
    # stock-index.md 업데이트
    print(sep)
    print("stock-index.md 업데이트")
    print(sep)
    
    # 최신가 조회
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # 실시간 JSON에서 가져오기
    latest_prices = {}
    try:
        with open(REALTIME) as f:
            rt = json.load(f)
        for s in rt['stocks']:
            if s['source'] == 'KRX':
                latest_prices[s['code']] = (s['price'], s['flu_rt'], s['volume'])
    except:
        pass
    
    # 부족하면 DB에서
    for code, name, folder, market in STOCKS:
        if code not in latest_prices and code != "000000":
            cur.execute("""
                SELECT price, flu_rt FROM stock_prices 
                WHERE code=? AND source='KRX' 
                ORDER BY captured_at DESC LIMIT 1
            """, (code,))
            r = cur.fetchone()
            if r:
                latest_prices[code] = (r[0], r[1], 0)
    
    conn.close()
    
    # stock-index.md 파일 읽고 테이블 부분 교체
    sipath = os.path.join(BASE, "stock/stock-index.md")
    with open(sipath) as f:
        sicontent = f.read()
    
    # 경고문 업데이트
    old_warn = "**⚠️ 현재가 정보는 스냅샷(6/4 12:30 기준). 실시간 시세는 `realtime/latest.json` 또는 DB 조회.**"
    new_warn = "**⚠️ 현재가 정보는 장종료 직전 데이터(6/4 14:58 기준). 실시간 시세는 `realtime/latest.json` 또는 DB 조회.**"
    sicontent = sicontent.replace(old_warn, new_warn)
    
    # 12종목 테이블 재작성
    table_lines = []
    for code, name, folder, market in [
        ("005930", "삼성전자", "삼성전자", "KOSPI"),
        ("000660", "SK하이닉스", "SK하이닉스", "KOSPI"),
        ("005935", "삼성전자우", "삼성전자우", "KOSPI"),
        ("095340", "ISC", "ISC", "KOSDAQ"),
        ("131970", "두테", "두테", "KOSDAQ"),
        ("039030", "이오테크닉스", "이오테크닉스", "KOSDAQ"),
        ("058470", "리노공업", "리노공업", "KOSDAQ"),
        ("240810", "원익IPS", "원익IPS", "KOSDAQ"),
        ("005290", "동진쎄미켐", "동진쎄미켐", "KOSDAQ"),
        ("403870", "HPSP", "HPSP", "KOSDAQ"),
        ("042700", "한미반도체", "한미반도체", "KOSDAQ"),
        ("036930", "주성엔지니어링", "주성엔지니어링", "KOSDAQ"),
    ]:
        short = name if len(name) <= 7 else name[:6]+"…"
        p, f, v = latest_prices.get(code, (None, None, None))
        if p:
            price_str = f"{p:,}"
            chg_str = f"{f:+.2f}%" if f else ""
        else:
            price_str = "?"
            chg_str = ""
        
        # 볼드 처리 (ISC/두테 강조)
        if name in ("ISC", "두테"):
            table_lines.append(f"|| **{short}** | {code} | {market} | **{price_str}** | {chg_str} | [바로가기]({folder}/{folder}-index.md) ✅ |")
        else:
            table_lines.append(f"|| {short} | {code} | {market} | {price_str} | {chg_str} | [바로가기]({folder}/{folder}-index.md) ✅ |")
    
    # 추가 관심종목
    extra_lines = []
    for code, name, folder in [
        ("080220", "제주반도체", "제주반도체"),
        ("067310", "하나마이크론", "하나마이크론"),
        ("007660", "이수페타시스", "이수페타시스"),
    ]:
        p, f, v = latest_prices.get(code, (None, None, None))
        if p:
            price_str = f"{p:,}"
            chg_str = f"{f:+.2f}%"
        else:
            price_str = "-"
            chg_str = "-"
        extra_lines.append(f"|| {name} | {code} | KOSDAQ | {price_str} | {chg_str} | [바로가기]({folder}/{folder}-index.md) ✅ |")
    
    # 한화비전
    extra_lines.append(f"|| 한화비전 | - | KOSPI | - | - | [바로가기](한화비전/한화비전-index.md) ✅ |")
    
    # 파일 다시 쓰기 (테이블 부분 교체는 복잡하니 전체 재생성)
    new_content = f"""# 📊 종목별 문서 인덱스

**⚠️ 현재가 정보는 장종료 직전 데이터(6/4 14:58 기준). 실시간 시세는 `realtime/latest.json` 또는 DB 조회.**

---

## 12종목

| 종목명 | 코드 | 시장 | 현재가 | 등락 | 문서 |
|:------|:---:|:---:|:-----:|:---:|:----|
{chr(10).join(table_lines)}

## 추가 관심종목

| 종목명 | 코드 | 시장 | 현재가 | 등락 | 문서 |
|:------|:---:|:----:|:-----:|:---:|:----|
{chr(10).join(extra_lines)}

---

*자동 업데이트: {NOW_KST}*
"""
    
    with open(sipath, 'w') as f:
        f.write(new_content)
    print(f"  ✅ stock-index.md 업데이트 완료")
    
    print(f"\n{sep}")
    print("✅ 전 종목 문서 채우기 완료!")
    print(sep)

if __name__ == "__main__":
    main()
