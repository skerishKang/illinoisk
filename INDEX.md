# Stock Trading Index

## 파일 구조
- **관심종목** → `~/stock-trading/watchlist/` (섹터별 분리)
- **일별 로그** → `~/stock-trading/daily-logs/YYYY-MM-DD.md`
- **전략 노트** → `~/stock-trading/strategies/`
- **과거 대화 검색** → `session_search(query="...")` (FTS5 인덱싱)

## 빠른 참조
- **User**: Chulwon Kang, 존댓말, 직설적
- **매매**: RSI 기반 시스템 + 수급 분석, 3~5K 손절
- **규모**: 일 손익 천만원대, 하루 2~3회 이상 거래
- **핵심 원칙**: 데이터 기반, 추측 금지 (근거 없는 해석 X), KOSPI/KOSDAQ 구분
- **가장 좋아하는 종목**: 이오테크닉스 (039030)

## 사용 방법
1. 에이전트가 INDEX.md 먼저 로드
2. 필요시 watchlist/ 내 파일 추가 로드
3. 과거 대화는 session_search()로 검색
4. 일별 로그는 daily-logs/에서 확인
