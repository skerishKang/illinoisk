# 📡 데이터 소스별 사용법

## 데이터 소스 순위 (박사님 확정 2026-06-05)

> **🥇 키움 API = 절대 기준.** 당일 등락률/현재가는 반드시 키움 ka10001 실시간 데이터 기준. (agents/rules.md 참조)

| 순위 | 소스 | 용도 | 비고 |
|:---:|:----|:-----|:-----|
| **1** | **키움 ka10001 REST API** | **국내 현재가/등락률/저고가** | **절대 기준** |
| **2** | **키움 ka10002 REST API** | **거래원 (순매수/순매도)** | |
| **3** | **DB (illinoisK.db)** | **전종목 통합조회/분봉/히스토리** | **장중 source='KRX' 필터 필수** |
| **4** | **Naver Mobile API (curl)** | **KOSPI/KOSDAQ 지수** | 지수만 참고, 등락률은 키움 우선 |
| **5** | **Yahoo Finance / TradingView** | 해외지수/환율/유가/미국개별종목 | |
| **6** | **네이버 증권 browser** | 테마/상승률TOP/NXT | |

## ⚠️ DB 조회 시 source 필터 필수

DB(`illinoisK.db`)의 `stock_prices` 테이블에는 **KRX(정규장)**와 **NXT(프리장/시간외)** 데이터가 `source` 컬럼으로 구분되어 함께 저장됨.

- NXT는 본장 이외시간(08:00~09:00, 15:30~)에만 거래
- **장중(09:00~15:30)에는 반드시 `source='KRX'` 필터를 추가할 것**
- 필터 없이 조회하면 NXT 데이터가 섞여서 거래량/가격이 왜곡됨
- 실제 사례: ISC 63%→19%, 이오 74%→11%로 잘못 표시됨

## 키움 API 엔드포인트

| API ID | 메서드 | 용도 |
|:------|:------|:-----|
| ka10001 | `POST /api/dostk/stkinfo` | 현재가 (`_NX`=넥장) |
| ka10002 | `POST /api/dostk/stkinfo` | 거래원 |
| ka10004 | `POST /api/dostk/mrkcond` | 호가 (cur_prc=0, 타임스탬프 용도) |
| ka10080 | `POST /api/dostk/stkcnf` | 분봉/일봉 차트 |
| ka10081 | `POST /api/dostk/stkcnf` | 일봉 (base_dt 필수) |
