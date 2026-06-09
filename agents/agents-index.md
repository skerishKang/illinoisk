# 🤖 에이전트 매뉴얼

이 폴더는 illinoisK에 진입하는 모든 AI 에이전트(나, Hermes, OpenClaude, Codex 등)를 위한 지침서.

## 규칙

- [행동 규칙](rules.md) — illinoisK 진입 시 따라야 할 규칙
- [Discipline Partner](discipline.md) — 원칙 리마인드
- [대화 저장/검색](conversation.md) — 대화 DB 사용법

## 데이터 출처

- [실시간 시세](../realtime/latest.json) — 1분 갱신 12종목
- [DB 조회](../DB/illinoisK.db) — SQLite (stock_prices 테이블)
- [위키](../docs/) — 매매규칙, 시장패턴, 신호분석 등
- [일일 체크](../daily-check/) — 날짜별 거래 요약/체크리스트
- [대화 기록](../conversations/) — 날짜별 대화 전문

## 퀵스타트

```bash
# 1. 현재 시세 확인
cat realtime/latest.json | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'{s["name"]}: {s["price"]:,} ({s["flu_rt"]:+.2f}%)') for s in d['stocks'] if s['source']=='KRX']"

# 2. 대화 검색
python3 scripts/save_conversation.py search --keyword "키워드"

# 3. 오늘 대화 보기
python3 scripts/save_conversation.py today

# 4. DB 최신 데이터
sqlite3 DB/illinoisK.db "SELECT * FROM stock_prices ORDER BY captured_at DESC LIMIT 12"

# 5. 오늘의 일지
cat daily-check/$(date +%Y-%m-%d).md 2>/dev/null || echo "오늘 일지 없음"
```
