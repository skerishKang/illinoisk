# 💬 대화 저장/검색 시스템

## 개요

Hermes와 독립된 illinoisK 자체 대화 저장소.  
어떤 AI 에이전트든 접근 가능.

## 저장소 구조

```
DB/conversations.db     ← SQLite (모든 대화)
  테이블: conversations (speaker, message, timestamp, topic, keywords)
  테이블: conversation_index (date, title, summary, message_count)

conversations/          ← 마크다운 (날짜별 전문)
├── conversations-index.md ← 인덱스
└── YYYY-MM-DD.md       ← 당일 대화 전문

daily-check/            ← 마크다운 (날짜별 요약/일지)
└── YYYY-MM-DD.md
```

## 스크립트 사용법

```bash
# 대화 저장 (새 메시지)
python3 scripts/save_conversation.py save \
    --speaker "박사님" --msg "내용" \
    --topic "주제" --keywords "키워드1,키워드2"

# 대화 검색
python3 scripts/save_conversation.py search --keyword "ISC"

# 오늘 대화 보기
python3 scripts/save_conversation.py today

# 인덱스 조회
python3 scripts/save_conversation.py index
```

## 문서화 의무

대화 중 **처음 듣는 정보**나 **수정사항**이 나오면:

1. 즉시 `save_conversation.py save`로 DB 저장
2. 해당 `docs/` 문서 업데이트
3. `daily-check/YYYY-MM-DD.md` 요약 업데이트
4. 에이전트 규칙(`agents/`)에 반영

## 검색 예

```python
# Python에서 직접 검색
import sqlite3
conn = sqlite3.connect("DB/conversations.db")
rows = conn.execute(
    "SELECT speaker, message FROM conversations WHERE message LIKE ? ORDER BY id DESC LIMIT 10",
    ("%ISC%",)
).fetchall()
```
