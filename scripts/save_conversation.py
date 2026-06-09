#!/usr/bin/env python3
"""
illinoisK 대화 저장 및 검색 도구 (Hermes 독립)

사용법:
  python3 save_conversation.py save --speaker "박사님" --msg "내용"
  python3 save_conversation.py search --keyword "ISC"
  python3 save_conversation.py today
  python3 save_conversation.py index
"""
import sqlite3, os, sys, json
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(BASE, "DB", "conversations.db")
CONV_DIR = os.path.join(BASE, "conversations")

def get_conn():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
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
        for s, m, t in today_msgs():
            print(f"[{t[:19]}] {s}: {m[:80]}...")
        if not today_msgs():
            print("No messages today")
    elif cmd == "index":
        for d, title, cnt, kw in index():
            print(f"{d}: {title} ({cnt} msgs) [{kw}]")
