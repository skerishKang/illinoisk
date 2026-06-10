#!/usr/bin/env python3
"""
illinoisK 대화 저장 및 검색 도구 (Hermes 독립)

사용법:
  python3 save_conversation.py save --speaker "박사님" --msg "내용"
  python3 save_conversation.py search --keyword "ISC"
  python3 save_conversation.py today
  python3 save_conversation.py index
  python3 save_conversation.py import-md --date 2026-06-10 [--keywords "키워드"]
  python3 save_conversation.py import-all-md
  python3 save_conversation.py sync [--keyword "키워드"]
"""
import sqlite3, os, sys, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))
BASE = Path(__file__).parent.parent
DB = BASE / "DB" / "conversations.db"
CONV_DIR = BASE / "conversations"

def get_conn():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT, speaker TEXT NOT NULL,
        message TEXT NOT NULL, timestamp TEXT NOT NULL,
        topic TEXT, keywords TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS conversation_index (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL UNIQUE,
        title TEXT, summary TEXT, keywords TEXT,
        message_count INTEGER DEFAULT 0, saved_at TEXT)""")
    conn.commit()
    return conn

def save(speaker, msg, topic="", keywords=""):
    conn = get_conn()
    now = datetime.now(KST).isoformat()
    today = datetime.now(KST).strftime("%Y-%m-%d")
    session = f"session_{today}"
    conn.execute("INSERT INTO conversations (session_id, speaker, message, timestamp, topic, keywords) VALUES (?,?,?,?,?,?)",
                 (session, speaker, msg, now, topic, keywords))
    # Update index
    existing = conn.execute("SELECT id FROM conversation_index WHERE date=?", (today,)).fetchone()
    cnt = conn.execute("SELECT COUNT(*) FROM conversations WHERE session_id=?", (session,)).fetchone()[0]
    if existing:
        conn.execute("UPDATE conversation_index SET message_count=?, saved_at=? WHERE date=?", (cnt, now, today))
    else:
        conn.execute("INSERT INTO conversation_index (date, title, summary, keywords, message_count, saved_at) VALUES (?,?,?,?,?,?)",
                     (today, f"{today} 대화", f"{cnt}개 메시지", keywords, cnt, now))
    conn.commit()
    conn.close()
    return True

def search(keyword, limit=20):
    conn = get_conn()
    rows = conn.execute(
        "SELECT speaker, message, timestamp, topic FROM conversations WHERE message LIKE ? ORDER BY id DESC LIMIT ?",
        (f"%{keyword}%", limit)).fetchall()
    conn.close()
    return rows

def today_msgs():
    conn = get_conn()
    today = datetime.now(KST).strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT speaker, message, timestamp FROM conversations WHERE timestamp LIKE ? ORDER BY id",
        (f"{today}%",)).fetchall()
    conn.close()
    return rows

def index():
    conn = get_conn()
    rows = conn.execute("SELECT date, title, message_count, keywords FROM conversation_index ORDER BY date DESC").fetchall()
    conn.close()
    return rows

def find_md_file(date_str):
    """YYYY-MM-DD 날짜에 해당하는 마크다운 파일 찾기"""
    # 우선순위 1: conversations/YYYY-MM-DD/전문.md
    dir_path = CONV_DIR / date_str / "전문.md"
    if dir_path.exists():
        return dir_path
    # 우선순위 2: conversations/YYYY-MM-DD.md
    file_path = CONV_DIR / f"{date_str}.md"
    if file_path.exists():
        return file_path
    return None

def parse_markdown_conversation(content, date_str):
    """
    마크다운 대화 전문 파싱
    
    표준 포맷:
    **박사님:** 내용
    **Agent:** 내용
    (마크다운 볼드에서 콜론이 안에 있음: **박사님:**)
    
    구형 Hermes 포맷 (Legacy):
    ### [09:47:23] 🧑‍💻 사용자
    내용
    
    ### [09:47:23] 🤖 Hermes
    내용
    
    정규화 규칙:
    - 사용자 / user / 🧑‍💻 사용자 → 박사님
    - Hermes / Agent / assistant / 🤖 Hermes → Agent
    """
    messages = []
    # 헤더(## ) 추출로 topic 결정
    topic = ""
    for line in content.split('\n'):
        if line.startswith('## '):
            topic = line[3:].strip()
            break
    
    # 표준 포맷 패턴: **박사님:** 또는 **Agent:** 마커
    standard_pattern = re.compile(r'^\*\*(박사님|Agent):\*\*\s*(.*)$')
    
    current_speaker = None
    current_message = []
    
    for line in content.split('\n'):
        # 표준 포맷 매칭 시도
        match = standard_pattern.match(line)
        if match:
            # 이전 발화 저장
            if current_speaker is not None and current_message:
                messages.append({
                    'speaker': current_speaker,
                    'message': '\n'.join(current_message).strip()
                })
            current_speaker = match.group(1)
            current_message = [match.group(2)]
            continue
        
        # 구형 Hermes 포맷 헤더 라인 감지
        # ### [09:47:23] 🧑‍💻 사용자
        # ### [09:47:23] 🤖 Hermes
        if line.startswith('### ['):
            # 이전 발화 저장
            if current_speaker is not None and current_message:
                messages.append({
                    'speaker': current_speaker,
                    'message': '\n'.join(current_message).strip()
                })
            
            # 발화자 정규화
            if '사용자' in line or 'user' in line.lower():
                current_speaker = '박사님'
            elif 'Hermes' in line or 'Agent' in line or 'assistant' in line.lower():
                current_speaker = 'Agent'
            else:
                # 알 수 없는 경우 건너뛰기
                current_speaker = None
            
            current_message = []
            continue
        
        # 같은 발화의 연속된 줄
        if current_speaker is not None:
            current_message.append(line)
    
    # 마지막 발화 저장
    if current_speaker is not None and current_message:
        messages.append({
            'speaker': current_speaker,
            'message': '\n'.join(current_message).strip()
        })
    
    return messages, topic

def import_md(date_str, keywords=""):
    """단일 날짜의 마크다운 파일을 DB로 가져오기"""
    md_file = find_md_file(date_str)
    if not md_file:
        print(f"에러: {date_str}에 해당하는 마크다운 파일을 찾을 수 없습니다.")
        print(f"  탐색 경로: {CONV_DIR / date_str / '전문.md'}")
        print(f"  탐색 경로: {CONV_DIR / f'{date_str}.md'}")
        sys.exit(1)
    
    print(f"가져오는 중: {md_file}")
    content = md_file.read_text(encoding='utf-8')
    messages, topic = parse_markdown_conversation(content, date_str)
    
    if not messages:
        print(f"경고: {md_file}에서 파싱된 메시지가 없습니다.")
        return 0
    
    conn = get_conn()
    session_id = f"session_{date_str}"
    
    # 기존 데이터 삭제 (중복 방지)
    conn.execute("DELETE FROM conversations WHERE session_id=?", (session_id,))
    conn.execute("DELETE FROM conversation_index WHERE date=?", (date_str,))
    
    # 타임스탬프 기준: 당일 00:00:00 KST부터 1초씩 증가
    base_time = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=KST)
    
    for i, msg in enumerate(messages):
        ts = (base_time + timedelta(seconds=i)).isoformat()
        conn.execute("""
            INSERT INTO conversations (session_id, speaker, message, timestamp, topic, keywords)
            VALUES (?,?,?,?,?,?)
        """, (session_id, msg['speaker'], msg['message'], ts, topic, keywords))
    
    # 인덱스 업데이트
    now = datetime.now(KST).isoformat()
    conn.execute("""
        INSERT INTO conversation_index (date, title, summary, keywords, message_count, saved_at)
        VALUES (?,?,?,?,?,?)
    """, (date_str, f"{date_str} 대화", f"Markdown import: {len(messages)} messages", keywords, len(messages), now))
    
    conn.commit()
    conn.close()
    
    print(f"  완료: {len(messages)}개 메시지 import됨 (topic: {topic or '없음'})")
    return len(messages)

def import_all_md():
    """모든 마크다운 대화 파일 일괄 가져오기"""
    # conversations/ 하위에서 YYYY-MM-DD/전문.md 또는 YYYY-MM-DD.md 찾기
    date_files = {}  # date_str -> Path (우선순위: 디렉터리 내 전문.md)
    
    for item in CONV_DIR.iterdir():
        if item.is_dir():
            # YYYY-MM-DD/전문.md
            match = re.match(r'^(\d{4}-\d{2}-\d{2})$', item.name)
            if match:
                date_str = match.group(1)
                md_file = item / "전문.md"
                if md_file.exists():
                    date_files[date_str] = md_file
        elif item.is_file():
            # YYYY-MM-DD.md
            match = re.match(r'^(\d{4}-\d{2}-\d{2})\.md$', item.name)
            if match:
                date_str = match.group(1)
                if date_str not in date_files:  # 디렉터리 버전이 우선
                    date_files[date_str] = item
    
    if not date_files:
        print("가져올 마크다운 대화 파일이 없습니다.")
        return
    
    # 날짜 오름차순 정렬
    sorted_dates = sorted(date_files.keys())
    
    print(f"발견된 날짜: {len(sorted_dates)}개")
    total = 0
    for date_str in sorted_dates:
        print(f"\n--- {date_str} ---")
        try:
            count = import_md(date_str, "")
            total += count
        except Exception as e:
            print(f"  에러: {e}")
    
    print(f"\n=== 총 {total}개 메시지 import 완료 ===")


def sync(keyword=""):
    """전체 동기화: import-all-md + index + 요약 + 선택적 검색"""
    print("=== 대화 동기화 시작 ===\n")
    
    # 1. import-all-md 실행
    import_all_md()
    
    print("\n=== 인덱스 현황 ===")
    
    # 2. index 출력 + 총계 계산
    rows = index()
    if not rows:
        print("데이터가 없습니다.")
        return
    
    total_dates = len(rows)
    total_messages = sum(row[2] for row in rows)
    
    for d, title, cnt, kw in rows:
        print(f"{d}: {title} ({cnt} msgs) [{kw}]")
    
    print(f"\n=== 요약 ===")
    print(f"총 날짜 수: {total_dates}개")
    print(f"총 메시지 수: {total_messages}개")
    
    # 3. 선택적 키워드 검색
    if keyword:
        print(f"\n=== 검색: '{keyword}' ===")
        results = search(keyword, limit=10)
        if not results:
            print("검색 결과 없음")
        else:
            for s, m, t, top in results:
                print(f"[{t[:19]}] {s}: {m[:100]}...")
    
    print("\n=== 동기화 완료 ===")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "save":
        speaker = sys.argv[sys.argv.index("--speaker") + 1] if "--speaker" in sys.argv else "unknown"
        msg = sys.argv[sys.argv.index("--msg") + 1] if "--msg" in sys.argv else ""
        topic = sys.argv[sys.argv.index("--topic") + 1] if "--topic" in sys.argv else ""
        kw = sys.argv[sys.argv.index("--keywords") + 1] if "--keywords" in sys.argv else ""
        save(speaker, msg, topic, kw)
        print("Saved")
    elif cmd == "search":
        kw = sys.argv[sys.argv.index("--keyword") + 1] if "--keyword" in sys.argv else ""
        for s, m, t, top in search(kw):
            print(f"[{t[:19]}] {s}: {m[:100]}...")
    elif cmd == "today":
        msgs = today_msgs()
        if not msgs:
            print("No messages today")
        for s, m, t in msgs:
            print(f"[{t[:19]}] {s}: {m[:80]}...")
    elif cmd == "index":
        for d, title, cnt, kw in index():
            print(f"{d}: {title} ({cnt} msgs) [{kw}]")
    elif cmd == "import-md":
        if "--date" not in sys.argv:
            print("에러: --date YYYY-MM-DD 필수")
            sys.exit(1)
        date_str = sys.argv[sys.argv.index("--date") + 1]
        kw = sys.argv[sys.argv.index("--keywords") + 1] if "--keywords" in sys.argv else ""
        import_md(date_str, kw)
    elif cmd == "import-all-md":
        import_all_md()
    elif cmd == "sync":
        kw = sys.argv[sys.argv.index("--keyword") + 1] if "--keyword" in sys.argv else ""
        sync(kw)
    else:
        print(f"알 수 없는 명령: {cmd}")
        print(__doc__)
        sys.exit(1)