#!/usr/bin/env python3
"""5/28 대화 아카이브: Hermes state.db → conversations/2026-05-28/"""
import sqlite3, os, re, json
from datetime import datetime

BASE = "/mnt/g/Ddrive/BatangD/task/workdiary/illinoisK"
OUT_DIR = os.path.join(BASE, "conversations", "2026-05-28")
STATE_DB = "/root/.hermes/state.db"

os.makedirs(OUT_DIR, exist_ok=True)

conn = sqlite3.connect(STATE_DB)
cur = conn.cursor()

def extract_session(sid):
    """세션의 모든 메시지를 추출 (user/assistant 텍스트 + tool call 요약)"""
    cur.execute('''
        SELECT role, content, timestamp, tool_name, tool_calls
        FROM messages 
        WHERE session_id = ?
        ORDER BY timestamp ASC
    ''', (sid,))
    return cur.fetchall()

def format_transcript(msgs):
    """전문.md 형식으로 포맷"""
    lines = ["# 2026-05-28 (목) 대화 전문", "", "---", ""]
    for m in msgs:
        role, content, ts, tname, tcalls = m
        dt = datetime.fromtimestamp(ts).strftime('%H:%M:%S')
        
        if role == 'user':
            # 사용자 메시지 - 시스템 노트 제거
            text = content
            # Remove system notes
            text = re.sub(r'\[System note:.*?\]', '', text)
            text = re.sub(r'\[Note:.*?\]', '', text)
            text = re.sub(r'\[The user sent a text document.*?\]', '', text)
            text = re.sub(r'\[Content of message\.txt\]:', '', text)
            text = text.strip()
            if text:
                lines.append(f"### [{dt}] 🧑‍💻 사용자")
                lines.append(text)
                lines.append("")
        elif role == 'assistant':
            if content and len(content.strip()) > 10:
                # 실제 응답 내용
                lines.append(f"### [{dt}] 🤖 Hermes")
                lines.append(content.strip())
                lines.append("")
            elif tname:
                # Tool call
                tool_args = ""
                if tcalls:
                    try:
                        tc = json.loads(tcalls)
                        if isinstance(tc, list) and len(tc) > 0:
                            args = tc[0].get('function', {}).get('arguments', '')
                            tool_args = args[:100]
                    except:
                        pass
                lines.append(f"  _🔧 `{tname}` {tool_args}_")
                lines.append("")
    
    return "\n".join(lines)

def summarize_day(sessions_data):
    """5/28 전체 요약"""
    lines = [
        "# 2026-05-28 (목) 대화 요약",
        "",
        f"*생성일: 2026-06-04 (사후 아카이브)*",
        "",
        "## 📌 키워드",
        "`리노공업` `대주주매도` `NXT체크리스트` `차트생성` `OpenClaude`",
        "",
        "## 💬 세션별 요약",
        ""
    ]
    
    for title, sid, msgs in sessions_data:
        # 첫 user 메시지
        first_user = ""
        for m in msgs:
            if m[0] == 'user':
                first_user = m[1][:200]
                break
        
        # 마지막 assistant 메시지
        last_asst = ""
        for m in reversed(msgs):
            if m[0] == 'assistant' and m[1] and len(m[1]) > 20:
                last_asst = m[1][:300]
                break
        
        lines.append(f"### {title}")
        lines.append(f"- **세션:** `{sid}`")
        lines.append(f"- **메시지:** {len(msgs)}개")
        lines.append(f"- **요청:** {first_user}")
        lines.append(f"")
        if last_asst:
            lines.append(f"- **결과:** {last_asst}")
            lines.append("")
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)

# 5/28 주식 관련 세션들
session_list = [
    ("리노공업 대주주매도 조사", "20260528_094502_86423e"),
    ("NXT 체크리스트 문서 생성", "20260528_095639_d21bdf"),
    ("차트 생성 스크립트 개발", "20260528_101349_c958a0"),
]

all_sessions_data = []

for title, sid in session_list:
    print(f"처리 중: {title} ({sid})...")
    msgs = extract_session(sid)
    print(f"  → {len(msgs)}개 메시지")
    all_sessions_data.append((title, sid, msgs))

# 전문.md 생성
print("\n전문.md 생성 중...")
transcript = format_transcript([m for _, _, msgs in all_sessions_data for m in msgs])
with open(os.path.join(OUT_DIR, "전문.md"), 'w', encoding='utf-8') as f:
    f.write(transcript)
print(f"  ✅ {OUT_DIR}/전문.md ({len(transcript)}자)")

# 요약.md 생성
print("요약.md 생성 중...")
summary = summarize_day(all_sessions_data)
with open(os.path.join(OUT_DIR, "요약.md"), 'w', encoding='utf-8') as f:
    f.write(summary)
print(f"  ✅ {OUT_DIR}/요약.md ({len(summary)}자)")

# conversations-index.md 업데이트
print("\nconversations-index.md 업데이트 중...")
idx_path = os.path.join(BASE, "conversations", "conversations-index.md")
with open(idx_path, 'r', encoding='utf-8') as f:
    idx_content = f.read()

# 2026-05-28 항목 추가 (맨 앞에)
new_entry = """## 2026-05-28 (목) 📌 사전 작업
**리노공업 대주주매도 조사** | NXT 체크리스트 생성 | 차트 스크립트 개발
🔑 `리노공업` `대주주매도` `NXT체크리스트` `차트생성`
→ [전문](2026-05-28/전문.md) | [요약](2026-05-28/요약.md)

"""

# Insert after title line
if "2026-05-28" not in idx_content:
    # Find the position after the first ---
    idx_content = idx_content.replace(
        "---\n\n",
        "---\n\n" + new_entry
    )

with open(idx_path, 'w', encoding='utf-8') as f:
    f.write(idx_content)
print(f"  ✅ conversations-index.md 업데이트 완료")

conn.close()
print("\n✅ 5/28 대화 아카이브 완료!")
