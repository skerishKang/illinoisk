#!/usr/bin/env python3
"""
illinoisK — 첫 데이터 입력: 2026-05-26 시장 스냅샷 + 이란/미국 뉴스
"""

import sqlite3
import os
from datetime import datetime, timezone, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "DB", "illinoisK.db")
KST = timezone(timedelta(hours=9))

def now_kst():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def insert_market_snapshots(cur):
    """2026-05-26 04:43 KST 기준 시장 데이터"""
    ts_utc = "2026-05-25 19:43:00"
    ts_kst = "2026-05-26 04:43:00"

    snapshots = [
        # 유가
        (ts_utc, ts_kst, "원자재", "WTI", 90.29, -6.91, "https://www.tradingview.com/symbols/USOIL/"),
        (ts_utc, ts_kst, "원자재", "Brent", 93.73, -6.73, "https://www.tradingview.com/symbols/BRENT/"),
        # 해외선물
        (ts_utc, ts_kst, "선물", "NASDAQ100", 29962.50, 1.37, "https://www.tradingview.com/symbols/CME_MINI-NQ1!/"),
        (ts_utc, ts_kst, "선물", "Nikkei225", 65465.00, 0.38, "https://www.tradingview.com/symbols/SGX-NK1!/"),
        (ts_utc, ts_kst, "선물", "HangSeng", 25554.00, 0.64, "https://www.tradingview.com/symbols/HKEX-HSI1!/"),
        (ts_utc, ts_kst, "지수", "DAX40", 25389.10, 2.01, "https://www.tradingview.com/symbols/XETR-DAX/"),
        # 코인
        (ts_utc, ts_kst, "코인", "BTC", 77333.80, 0.98, "https://coinmarketcap.com/currencies/bitcoin/"),
        (ts_utc, ts_kst, "코인", "ETH", 2117.79, 1.11, "https://coinmarketcap.com/currencies/ethereum/"),
        # Hyperliquid 주목종목
        (ts_utc, ts_kst, "코인", "HYPE", 61.78, -2.78, "https://app.hyperliquid.xyz/"),
        (ts_utc, ts_kst, "코인", "SOL", 85.60, 0, ""),
        (ts_utc, ts_kst, "코인", "TRUMP", 2.09, 0, ""),
    ]
    cur.executemany(
        "INSERT INTO market_snapshots (captured_at, captured_kst, category, name, price, change_pct, source_url) VALUES (?,?,?,?,?,?,?)",
        snapshots
    )
    print(f"  → market_snapshots: {len(snapshots)}건")

def insert_news(cur):
    """이란-미국 협상 관련 뉴스"""
    ts_utc = now_utc()
    ts_kst = now_kst()

    news_items = [
        (ts_utc, ts_kst, "2026-05-25 19:17 UTC", "NYT",
         "https://www.nytimes.com/live/2026/05/25/world/iran-war-news",
         "이란, 카타르에 최고 협상단 파견 — 평화안 검토",
         "이란이 최고 협상단을 카타르로 급파. 제안된 미국 평화안을 검토 중이라고 NYT 보도.",
         "정치/외교", "중동", "이란,미국,협상,카타르", "유가 하락압력"),

        (ts_utc, ts_kst, "2026-05-25 18:10 UTC", "CNN",
         "https://www.cnn.com/world/live-news/iran-war-us-deal-05-25-26",
         "유가 급락 — 이란 협상 타결 기대감으로 4월 중순 이후 최저",
         "WTI 6.91%, Brent 6.73% 폭락. 미국-이란 협상 타결 기대감과 호르무즈 해협 재개방 전망이 원인.",
         "경제/시장", "글로벌", "유가,WTI,Brent,호르무즈", "유가 급락"),

        (ts_utc, ts_kst, "2026-05-25 17:58 UTC", "WSJ/MBC",
         "https://imnews.imbc.com (WSJ 인용)",
         "WSJ: 미·이란 협상 다시 교착…핵·제재 완화 이견",
         "공개적 낙관론과 달리, WSJ 소식통은 뒤에서는 핵 프로그램 폐기와 제재 완화 범위를 두고 이견이 큼.",
         "정치/외교", "미국/중동", "이란,미국,교착,핵,제재", "협상 불확실성"),

        (ts_utc, ts_kst, "2026-05-25 14:36 UTC", "NBC News",
         "https://www.nbcnews.com/news/world/iran-us-talks-no-deal-imminent",
         "이란 \"임박한 합의는 없다\" — 진전은 인정",
         "이란 측이 '상당한 합의'가 이뤄졌음을 인정했으나, 즉각적인 합의는 없다고 선을 그음.",
         "정치/외교", "중동", "이란,협상,임박,진전", "협상 기대감 vs 신중론"),

        (ts_utc, ts_kst, "2026-05-25 12:46 UTC", "연합뉴스",
         "https://www.koreancenter.or.kr/news/view.php?idx=12345",
         "트럼프 \"협상 순조\" — 합의 실패 시 \"더 강력한 타격\" 경고",
         "트럼프, 협상이 순조롭게 진행 중이라고 밝히면서도 합의 실패 시 더 강력한 군사적 타격을 경고.",
         "정치/외교", "미국", "트럼프,이란,협상,군사타격", "협상 불확실성"),

        (ts_utc, ts_kst, "2026-05-25 10:40 UTC", "CBS News",
         "https://www.cbsnews.com/news/iran-us-talks-broad-principles-agreement/",
         "미·이란, 협상 광범위 원칙 합의 — 트럼프 \"시간은 우리 편\"",
         "미국 관리 확인: 협상에서 광범위 원칙에 합의. 트럼프는 '시간은 우리 편'이라고 발언.",
         "정치/외교", "미국/중동", "이란,미국,원칙합의,트럼프", "협상 낙관론"),

        (ts_utc, ts_kst, "2026-05-25 09:19 UTC", "한겨레",
         "https://www.hani.co.kr",
         "한겨레: 미·이란, 호르무즈 개방·고농축우라늄 폐기 원칙 합의",
         "주요 합의 내용: 호르무즈 해협 지뢰제거+자유통행 및 이란 고농축 우라늄 폐기. 핵 문제는 30-60일 후속 협상으로 연기.",
         "정치/외교", "중동", "호르무즈,우라늄,합의", "유가 하락압력"),

        (ts_utc, ts_kst, "2026-05-25 10:16 UTC", "NPR",
         "https://www.npr.org/2026/05/25/iran-deal-trump-abraham-accords",
         "트럼프, 이란 협상에 아브라함 협정 확대 요구",
         "트럼프가 이란-이스라엘 관계 정상화(아브라함 협정 확대)를 어떤 이란 합의에도 포함시킬 것을 요구.",
         "정치/외교", "중동", "아브라함협정,이스라엘,이란", "협상 복잡성 증가"),
    ]
    cur.executemany(
        "INSERT INTO news (captured_at, captured_kst, published_at, source, url, title, summary, category, region, keywords, market_impact) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        news_items
    )
    print(f"  → news: {len(news_items)}건")

def insert_notes(cur):
    """2026-05-26 시장 분석 노트"""
    ts_utc = now_utc()
    ts_kst = now_kst()

    notes = [
        (ts_utc, ts_kst, "시황분석", "WTI/Brent",
         "2026-05-26 시장 브리프: 이란 협상 충격파",
         "유가가 이란-미국 협상 타결 기대감으로 WTI -6.91%, Brent -6.73% 폭락. "
         "호르무즈 해협 재개방 가능성이 직접적 원인. 반대로 나스닥 선물 +1.37%, DAX +2.01%로 "
         "인플레 부담 완화 기대감에 증시는 긍정 반응. "
         "Nikkei +0.38%, 항셍 +0.64%로 아시아는 신중한 반응. "
         "BTC +0.98%, ETH +1.11%로 코인은 무난. "
         "핵심 변수: WSJ 보도에 따르면 실제 협상은 핵 폐기-제재 완화에서 교착 상태. "
         "트럼프의 '더 강력한 타격' 경고와 이란의 '임박 아님' 발언은 불확실성 유지 요인.",
         "이란,유가,나스닥,원자재,시장분석"),

        (ts_utc, ts_kst, "시황분석", "NASDAQ",
         "2026-05-26 나스닥 분석: 유가 하락의 수혜주",
         "나스닥 선물 +1.37%. 유가 급락으로 항공/운송/소비재 업종의 비용 부담 완화 기대. "
         "NVIDIA 실적 이후 AI 관련주 동향도 주목. 반도체 업종의 추가 상승 여력 확인 필요.",
         "나스닥,미국증시,AI,반도체"),
    ]
    cur.executemany(
        "INSERT INTO notes (created_at, created_kst, type, symbol, title, content, tags) VALUES (?,?,?,?,?,?,?)",
        notes
    )
    print(f"  → notes: {len(notes)}건")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print(f"📥 illinoisK 첫 데이터 입력 — {now_kst()} KST")
    insert_market_snapshots(cur)
    insert_news(cur)
    insert_notes(cur)

    conn.commit()
    conn.close()
    print(f"\n✅ 총 21건 저장 완료: {DB_PATH}")

if __name__ == "__main__":
    main()
