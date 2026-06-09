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
└── YYYY-MM-DD/
    ├── 전문.md         ← 전체 대화 전문 (원본 보관)
    └── 요약.md         ← 핵심 요약

daily-check/            ← 마크다운 (날짜별 요약/일지)
└── YYYY-MM-DD.md
```

## Hermes/Discord 주식 쓰레드 대화 저장 워크플로우

Discord `#illinoisk / 주식관련` 쓰레드에서 주식 관련 대화만 복사해 `conversations/YYYY-MM-DD/전문.md`에 저장한다.

**Markdown 형식:**
```markdown
**박사님:** 내용
**Agent:** 내용
```

같은 발화의 다음 줄들은 다음 speaker 마커가 나오기 전까지 같은 message에 붙인다.

**절차:**
1. Discord 쓰레드에서 오늘 대화 복사
2. `conversations/YYYY-MM-DD/전문.md` 생성 (위 형식으로)
3. `python3 scripts/save_conversation.py import-md --date YYYY-MM-DD` 실행
4. `python3 scripts/save_conversation.py index` 로 확인
5. `daily-check/YYYY-MM-DD.md`에도 주식 매매 요약 기록

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

# 마크다운 전문 → DB 가져오기 (단일 날짜)
python3 scripts/save_conversation.py import-md --date 2026-06-10 [--keywords "키워드"]

# 전체 마크다운 전문 일괄 가져오기
python3 scripts/save_conversation.py import-all-md
```

## import-md / import-all-md 상세

### import-md
- `conversations/YYYY-MM-DD/전문.md` 우선 탐색
- 없으면 `conversations/YYYY-MM-DD.md` 탐색
- 파일이 없으면 명확한 에러 출력 후 종료
- 기존 `session_id = session_YYYY-MM-DD` 데이터는 먼저 삭제 (중복 방지)
- Markdown에서 `**박사님:**` / `**Agent:**` 형식 파싱
- DB `conversations` 테이블에 삽입:
  - `session_id = session_YYYY-MM-DD`
  - `speaker = 박사님` 또는 `Agent`
  - `message = 파싱된 본문`
  - `timestamp = YYYY-MM-DDT00:00:00+09:00`부터 메시지 순서대로 1초씩 증가
  - `topic = 파일 내 가장 가까운 ## 제목` 또는 빈 문자열
  - `keywords = --keywords 인자` 또는 빈 문자열
- `conversation_index` 업데이트:
  - `date = YYYY-MM-DD`
  - `title = YYYY-MM-DD 대화`
  - `summary = Markdown import: N messages`
  - `keywords = --keywords 값` 또는 빈 문자열
  - `message_count = N`
  - `saved_at = 현재 KST 시각`

### import-all-md
- `conversations/` 하위에서 날짜 디렉터리 `YYYY-MM-DD/전문.md` 전부 찾기
- `conversations/YYYY-MM-DD.md` 파일도 찾기
- 날짜 오름차순으로 `import-md` 실행
- 각 날짜별 imported count 출력
- 중복 날짜가 있으면 `YYYY-MM-DD/전문.md`를 우선함

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

## 원칙: Markdown이 원본, DB는 검색 인덱스

- `conversations/YYYY-MM-DD/전문.md` = **원본 보관** (사람이 읽기 좋은 형태)
- `DB/conversations.db` = **검색 인덱스** (프로그램/에이전트가 빠르게 찾기 위한 용도)
- 두 곳이 동기화돼야 함 → 대화 저장 후 `import-md` 실행 습관화
- Markdown 포맷이 변경되면 `import-md` 파서도 함께 수정