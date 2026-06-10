#!/usr/bin/env python3
"""
save_conversation.py import-md 기능 테스트

실행:
  python3 tests/test_save_conversation_import.py
"""
import os, sys, tempfile, shutil, sqlite3
from datetime import datetime, timezone, timedelta

# 프로젝트 루트 기준 경로 설정
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from save_conversation import (
    get_conn, parse_markdown_conversation, import_md, 
    find_md_file, KST
)

def setup_test_env():
    """테스트용 임시 디렉토리 및 DB 설정"""
    from pathlib import Path
    test_dir = tempfile.mkdtemp(prefix="test_illinoisk_")
    test_conv_dir = Path(test_dir) / "conversations"
    test_db_dir = Path(test_dir) / "DB"
    test_conv_dir.mkdir(parents=True, exist_ok=True)
    test_db_dir.mkdir(parents=True, exist_ok=True)
    
    # 전역 변수 임시 변경
    import save_conversation as sc
    orig_base = sc.BASE
    orig_db = sc.DB
    orig_conv_dir = sc.CONV_DIR
    sc.BASE = Path(test_dir)
    sc.DB = test_db_dir / "conversations.db"
    sc.CONV_DIR = test_conv_dir
    
    return test_dir, test_conv_dir, test_db_dir, orig_base, orig_db, orig_conv_dir

def teardown_test_env(test_dir, orig_base, orig_db, orig_conv_dir):
    """원복 및 정리"""
    import save_conversation as sc
    sc.BASE = orig_base
    sc.DB = orig_db
    sc.CONV_DIR = orig_conv_dir
    shutil.rmtree(test_dir, ignore_errors=True)

def test_parse_markdown_conversation():
    """마크다운 파싱 테스트"""
    print("테스트 1: parse_markdown_conversation")
    
    content = """# 2026-06-10 대화

## 대화 개요

## 1. 첫 번째 섹션
**박사님:** 안녕하세요
**Agent:** 네 안녕하세요

**박사님:** ISC 어떻게 생각해요?
오늘 흐름이 좋네요
**Agent:** ISC는 신한 순매수 들어오고 있습니다
저가 지지 확인됐습니다

## 2. 두 번째 섹션
**Agent:** 추가 분석 결과
거래량도 증가세입니다
**박사님:** 그럼 매수 고려해볼게요
"""
    
    messages, topic = parse_markdown_conversation(content, "2026-06-10")
    
    assert topic == "대화 개요", f"topic 불일치: {topic}"
    assert len(messages) == 6, f"메시지 수 불일치: {len(messages)}"
    
    # 발화 순서 및 화자 확인
    expected_speakers = ["박사님", "Agent", "박사님", "Agent", "Agent", "박사님"]
    for i, (msg, exp) in enumerate(zip(messages, expected_speakers)):
        assert msg['speaker'] == exp, f"메시지 {i} 화자 불일치: {msg['speaker']} != {exp}"
    
    # 여러 줄 합쳐지는지 확인 (3번째 메시지)
    assert "오늘 흐름이 좋네요" in messages[2]['message'], "여러 줄 합치기 실패"
    
    print("  ✓ topic 파싱 정상")
    print("  ✓ 메시지 6개 파싱 정상")
    print("  ✓ 화자 순서 정상")
    print("  ✓ 여러 줄 합치기 정상")
    return True

def test_import_md_basic():
    """import-md 기본 동작 테스트"""
    print("\n테스트 2: import_md 기본 동작")
    
    test_dir, test_conv_dir, test_db_dir, orig_base, orig_db, orig_conv_dir = setup_test_env()
    
    try:
        import save_conversation as sc
        
        # 테스트용 마크다운 파일 생성
        date_str = "2026-06-10"
        conv_date_dir = test_conv_dir / date_str
        conv_date_dir.mkdir(exist_ok=True)
        md_file = conv_date_dir / "전문.md"
        
        md_content = """# 2026-06-10 (수) 전체 대화

## 대화 개요
- 참여: 박사님, Agent

## 1. 장전 체크
**박사님:** 오늘 장 어때?
**Agent:** 코스피 상승, 코스닥 하락 디커플링

## 2. ISC 분석
**박사님:** ISC 신한 순매수 들어왔어?
**Agent:** 네, 신한 +26,268주 순매수 확인됨
저가 202,000 지지
"""
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # import 실행
        count = sc.import_md(date_str, "테스트키워드")
        
        assert count == 4, f"import된 메시지 수 불일치: {count}"
        
        # DB 확인
        conn = sc.get_conn()
        rows = conn.execute(
            "SELECT speaker, message, topic, keywords FROM conversations WHERE session_id=? ORDER BY id",
            (f"session_{date_str}",)
        ).fetchall()
        conn.close()
        
        assert len(rows) == 4, f"DB 행 수 불일치: {len(rows)}"
        
        speakers = [r[0] for r in rows]
        assert speakers == ["박사님", "Agent", "박사님", "Agent"], f"화자 순서 불일치: {speakers}"
        
        for r in rows:
            assert r[2] == "대화 개요", f"topic 불일치: {r[2]}"
            assert r[3] == "테스트키워드", f"keywords 불일치: {r[3]}"
        
        # conversation_index 확인
        conn = sc.get_conn()
        idx = conn.execute(
            "SELECT date, title, summary, keywords, message_count FROM conversation_index WHERE date=?",
            (date_str,)
        ).fetchone()
        conn.close()
        
        assert idx is not None, "인덱스 없음"
        assert idx[0] == date_str
        assert idx[1] == f"{date_str} 대화"
        assert idx[2] == "Markdown import: 4 messages"
        assert idx[3] == "테스트키워드"
        assert idx[4] == 4
        
        print("  ✓ 4개 메시지 import 정상")
        print("  ✓ 화자/메시지/토픽/키워드 저장 정상")
        print("  ✓ conversation_index 업데이트 정상")
        return True
        
    finally:
        teardown_test_env(test_dir, orig_base, orig_db, orig_conv_dir)

def test_import_md_duplicate_prevention():
    """동일 날짜 두 번 import 시 중복 방지 테스트"""
    print("\n테스트 3: import_md 중복 방지 (같은 날짜 두 번 import)")
    
    test_dir, test_conv_dir, test_db_dir, orig_base, orig_db, orig_conv_dir = setup_test_env()
    
    try:
        import save_conversation as sc
        
        date_str = "2026-06-11"
        conv_date_dir = test_conv_dir / date_str
        conv_date_dir.mkdir(exist_ok=True)
        md_file = conv_date_dir / "전문.md"
        
        md_content = """# 2026-06-11 대화

## 주제
**박사님:** 첫 번째
**Agent:** 응답1
"""
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        # 첫 번째 import
        count1 = sc.import_md(date_str, "첫번째")
        assert count1 == 2, f"첫 번째 import 수 불일치: {count1}"
        
        # 두 번째 import (같은 파일)
        count2 = sc.import_md(date_str, "두번째")
        assert count2 == 2, f"두 번째 import 수 불일치: {count2}"
        
        # DB에 총 2개만 있어야 함 (중복 없음)
        conn = sc.get_conn()
        total = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE session_id=?",
            (f"session_{date_str}",)
        ).fetchone()[0]
        conn.close()
        
        assert total == 2, f"중복 방지 실패: 총 {total}개 (예상 2개)"
        
        # keywords는 두 번째 값으로 업데이트돼야 함
        conn = sc.get_conn()
        idx = conn.execute(
            "SELECT keywords FROM conversation_index WHERE date=?", (date_str,)
        ).fetchone()
        conn.close()
        
        assert idx[0] == "두번째", f"keywords 미업데이트: {idx[0]}"
        
        print("  ✓ 첫 번째 import: 2개")
        print("  ✓ 두 번째 import: 2개 (덮어쓰기)")
        print("  ✓ DB 총 2개 유지 (중복 없음)")
        print("  ✓ keywords 최신값으로 업데이트")
        return True
        
    finally:
        teardown_test_env(test_dir, orig_base, orig_db, orig_conv_dir)

def test_import_md_file_priority():
    """파일 우선순위 테스트: 디렉터리/전문.md > 파일.md"""
    print("\n테스트 4: 파일 우선순위 (디렉터리/전문.md 우선)")
    
    test_dir, test_conv_dir, test_db_dir, orig_base, orig_db, orig_conv_dir = setup_test_env()
    
    try:
        import save_conversation as sc
        
        date_str = "2026-06-12"
        conv_date_dir = test_conv_dir / date_str
        conv_date_dir.mkdir(parents=True, exist_ok=True)
        
        # 둘 다 생성: 디렉터리 버전과 파일 버전
        md_dir_file = conv_date_dir / "전문.md"
        md_file = test_conv_dir / f"{date_str}.md"
        
        with open(md_dir_file, 'w', encoding='utf-8') as f:
            f.write("# 디렉터리 버전\n**박사님:** 디렉터리\n**Agent:** 응답D")
        
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# 파일 버전\n**박사님:** 파일\n**Agent:** 응답F")
        
        # import 실행 - 디렉터리 버전이 우선되어야 함
        count = sc.import_md(date_str)
        
        conn = sc.get_conn()
        rows = conn.execute(
            "SELECT speaker, message FROM conversations WHERE session_id=? ORDER BY id",
            (f"session_{date_str}",)
        ).fetchall()
        conn.close()
        
        assert len(rows) == 2, f"메시지 수 불일치: {len(rows)}"
        assert rows[0][1] == "디렉터리", f"우선순위 실패: {rows[0][1]}"
        assert rows[1][1] == "응답D", f"우선순위 실패: {rows[1][1]}"
        
        print("  ✓ 디렉터리/전문.md가 파일.md보다 우선됨")
        return True
        
    finally:
        teardown_test_env(test_dir, orig_base, orig_db, orig_conv_dir)

def test_import_md_error_handling():
    """파일 없을 때 에러 처리 테스트"""
    print("\n테스트 5: import_md 에러 처리 (파일 없음)")
    
    test_dir, test_conv_dir, test_db_dir, orig_base, orig_db, orig_conv_dir = setup_test_env()
    
    try:
        import save_conversation as sc
        
        # 존재하지 않는 날짜
        try:
            sc.import_md("2026-09-99", "")
            assert False, "에러가 발생해야 함"
        except SystemExit as e:
            assert e.code == 1, "종료 코드 1이어야 함"
        
        print("  ✓ 파일 없을 때 SystemExit(1) 발생")
        return True
        
    finally:
        teardown_test_env(test_dir, orig_base, orig_db, orig_conv_dir)

def test_find_md_file():
    """find_md_file 함수 테스트"""
    print("\n테스트 6: find_md_file")

    test_dir, test_conv_dir, test_db_dir, orig_base, orig_db, orig_conv_dir = setup_test_env()

    try:
        import save_conversation as sc

        date_str = "2026-06-13"
        conv_date_dir = test_conv_dir / date_str
        conv_date_dir.mkdir(parents=True, exist_ok=True)

        # 케이스 1: 디렉터리/전문.md만 있음
        dir_file = conv_date_dir / "전문.md"
        with open(dir_file, 'w') as f:
            f.write("test")

        found = sc.find_md_file(date_str)
        assert found == dir_file, f"디렉터리 파일 못 찾음: {found}"

        # 케이스 2: 파일.md만 있음 (디렉터리 삭제)
        dir_file.unlink()
        conv_date_dir.rmdir()

        file_md = test_conv_dir / f"{date_str}.md"
        with open(file_md, 'w') as f:
            f.write("test")

        found = sc.find_md_file(date_str)
        assert found == file_md, f"파일.md 못 찾음: {found}"

        # 케이스 3: 둘 다 없음
        file_md.unlink()
        found = sc.find_md_file("2026-01-01")
        assert found is None, f"없는 파일인데 찾음: {found}"

        print("  ✓ 디렉터리/전문.md 우선 찾기")
        print("  ✓ 파일.md 대체 찾기")
        print("  ✓ 없으면 None 반환")
        return True

    finally:
        teardown_test_env(test_dir, orig_base, orig_db, orig_conv_dir)


def test_parse_legacy_hermes_format():
    """구형 Hermes 포맷 파싱 테스트"""
    print("\n테스트 7: parse_markdown_conversation 구형 Hermes 포맷")

    content = """# 2026-05-28 대화

### [09:47:23] 🧑‍💻 사용자
리노공업 대주주 매도 찾아봐

### [09:47:24] 🤖 Hermes
확인해보겠습니다.

### [09:47:25] 🤖 Hermes
추가 정보입니다.
여러 줄도 가능합니다.

### [09:47:26] 🧑‍💻 사용자
고마워요
"""

    messages, topic = parse_markdown_conversation(content, "2026-05-28")

    assert len(messages) == 4, f"메시지 수 불일치: {len(messages)}"

    # 발화자 정규화 확인
    assert messages[0]['speaker'] == "박사님", f"1번째 화자 불일치: {messages[0]['speaker']}"
    assert messages[1]['speaker'] == "Agent", f"2번째 화자 불일치: {messages[1]['speaker']}"
    assert messages[2]['speaker'] == "Agent", f"3번째 화자 불일치: {messages[2]['speaker']}"
    assert messages[3]['speaker'] == "박사님", f"4번째 화자 불일치: {messages[3]['speaker']}"

    # 메시지 내용 확인
    assert "리노공업 대주주 매도 찾아봐" in messages[0]['message']
    assert "확인해보겠습니다." in messages[1]['message']
    assert "추가 정보입니다." in messages[2]['message']
    assert "여러 줄도 가능합니다." in messages[2]['message']
    assert "고마워요" in messages[3]['message']

    print("  ✓ 구형 Hermes 포맷 4개 메시지 파싱 정상")
    print("  ✓ 화자 정규화: 사용자 → 박사님, Hermes → Agent")
    print("  ✓ 여러 줄 메시지 합치기 정상")
    return True


def test_parse_mixed_format():
    """표준 포맷과 구형 포맷이 섞여 있을 때 테스트"""
    print("\n테스트 8: 표준 포맷 + 구형 포맷 혼합 파싱")

    content = """# 2026-06-10 대화

## 대화 개요

**박사님:** 표준 포맷 시작
**Agent:** 표준 응답

### [09:47:23] 🧑‍💻 사용자
구형 포맷 사용자

### [09:47:24] 🤖 Hermes
구형 포맷 에이전트

**박사님:** 다시 표준 포맷
**Agent:** 다시 표준 응답
"""

    messages, topic = parse_markdown_conversation(content, "2026-06-10")

    assert len(messages) == 6, f"메시지 수 불일치: {len(messages)}"
    assert topic == "대화 개요", f"topic 불일치: {topic}"

    # 순서 확인
    expected_speakers = ["박사님", "Agent", "박사님", "Agent", "박사님", "Agent"]
    for i, (msg, exp) in enumerate(zip(messages, expected_speakers)):
        assert msg['speaker'] == exp, f"메시지 {i} 화자 불일치: {msg['speaker']} != {exp}"

    print("  ✓ 혼합 포맷 6개 메시지 파싱 정상")
    print("  ✓ 화자 순서 정상 유지")
    print("  ✓ topic 추출 정상")
    return True


def test_legacy_variants():
    """구형 포맷 변형 테스트 (user, assistant, Agent 등)"""
    print("\n테스트 9: 구형 포맷 변형 (user, assistant, Agent)")

    content = """### [10:00:00] 🧑‍💻 user
user 키워드

### [10:00:01] 🤖 assistant
assistant 키워드

### [10:00:02] Agent as text
Agent 텍스트 포함

### [10:00:03] 🧑‍💻 사용자
한국어 사용자
"""

    messages, _ = parse_markdown_conversation(content, "2026-06-10")

    assert len(messages) == 4, f"메시지 수 불일치: {len(messages)}"
    assert messages[0]['speaker'] == "박사님", f"user → 박사님 실패: {messages[0]['speaker']}"
    assert messages[1]['speaker'] == "Agent", f"assistant → Agent 실패: {messages[1]['speaker']}"
    assert messages[2]['speaker'] == "Agent", f"Agent 텍스트 → Agent 실패: {messages[2]['speaker']}"
    assert messages[3]['speaker'] == "박사님", f"한국어 사용자 → 박사님 실패: {messages[3]['speaker']}"

    print("  ✓ user → 박사님 정규화")
    print("  ✓ assistant → Agent 정규화")
    print("  ✓ Agent 텍스트 포함 → Agent 정규화")
    print("  ✓ 한국어 사용자 → 박사님 정규화")
    return True

def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 50)
    print("save_conversation.py import-md 테스트 시작")
    print("=" * 50)

    tests = [
        test_parse_markdown_conversation,
        test_import_md_basic,
        test_import_md_duplicate_prevention,
        test_import_md_file_priority,
        test_import_md_error_handling,
        test_find_md_file,
        test_parse_legacy_hermes_format,
        test_parse_mixed_format,
        test_legacy_variants,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            result = test()
            if result:
                passed += 1
        except Exception as e:
            failed += 1
            print(f"  ✗ 실패: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 50)
    print(f"결과: {passed}개 통과, {failed}개 실패")
    print("=" * 50)

    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)