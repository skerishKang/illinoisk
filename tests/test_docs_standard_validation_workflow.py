#!/usr/bin/env python3
"""
Standard 4-step local validation workflow 회귀 테스트.

entrypoint / support docs가 다음 4-step 표준 워크플로우를 모두 포함하는지
text-based로 확인한다. 미래에 문서가 부분 워크플로우(예: run_all 단독)로
회귀하는 것을 빨리 잡는 것이 목적.

확인 대상 명령 4개:
  1. python3 scripts/save_conversation.py sync
  2. python3 tests/run_all.py
  3. git diff --check
  4. git status --short

확인 대상 문서:
  - README.md
  - INDEX.md
  - AGENTS.md
  - docs/local-regression-checks.md
  - docs/repository-structure.md (선택 포함)

실행:
  python3 tests/test_docs_standard_validation_workflow.py
"""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

STANDARD_WORKFLOW_COMMANDS = [
    "python3 scripts/save_conversation.py sync",
    "python3 tests/run_all.py",
    "git diff --check",
    "git status --short",
]

TARGET_DOCS = [
    "README.md",
    "INDEX.md",
    "AGENTS.md",
    "docs/local-regression-checks.md",
    "docs/repository-structure.md",
]


def _check_doc_has_workflow(rel_path: str) -> bool:
    """문서 본문에 4-step 워크플로우 명령 4개가 모두 있는지 확인."""
    doc_path = BASE / rel_path
    if not doc_path.exists():
        print(f"  ✗ 파일 없음: {rel_path}")
        return False

    try:
        content = doc_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = doc_path.read_text(encoding="utf-8", errors="replace")

    missing = [cmd for cmd in STANDARD_WORKFLOW_COMMANDS if cmd not in content]
    if missing:
        print(f"  ✗ {rel_path}: 누락된 표준 워크플로우 명령")
        for cmd in missing:
            print(f"      - {cmd}")
        return False

    print(f"  ✓ {rel_path}: 4-step 표준 워크플로우 포함")
    return True


def test_README_has_standard_workflow():
    """README.md에 표준 4-step 워크플로우가 포함되어 있는지 확인."""
    print("\n테스트 1: README.md — 표준 4-step 워크플로우")
    assert _check_doc_has_workflow("README.md"), "README.md 표준 워크플로우 누락"
    return True


def test_INDEX_has_standard_workflow():
    """INDEX.md에 표준 4-step 워크플로우가 포함되어 있는지 확인."""
    print("\n테스트 2: INDEX.md — 표준 4-step 워크플로우")
    assert _check_doc_has_workflow("INDEX.md"), "INDEX.md 표준 워크플로우 누락"
    return True


def test_AGENTS_has_standard_workflow():
    """AGENTS.md에 표준 4-step 워크플로우가 포함되어 있는지 확인."""
    print("\n테스트 3: AGENTS.md — 표준 4-step 워크플로우")
    assert _check_doc_has_workflow("AGENTS.md"), "AGENTS.md 표준 워크플로우 누락"
    return True


def test_local_regression_checks_has_standard_workflow():
    """docs/local-regression-checks.md에 표준 4-step 워크플로우가 포함되어 있는지 확인."""
    print("\n테스트 4: docs/local-regression-checks.md — 표준 4-step 워크플로우")
    assert _check_doc_has_workflow("docs/local-regression-checks.md"), (
        "docs/local-regression-checks.md 표준 워크플로우 누락"
    )
    return True


def test_repository_structure_has_standard_workflow():
    """docs/repository-structure.md에 표준 4-step 워크플로우가 포함되어 있는지 확인."""
    print("\n테스트 5: docs/repository-structure.md — 표준 4-step 워크플로우")
    assert _check_doc_has_workflow("docs/repository-structure.md"), (
        "docs/repository-structure.md 표준 워크플로우 누락"
    )
    return True


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("docs 표준 4-step validation workflow 회귀 테스트 시작")
    print("=" * 60)
    print("표준 워크플로우 명령:")
    for cmd in STANDARD_WORKFLOW_COMMANDS:
        print(f"  - {cmd}")
    print(f"확인 대상 문서 ({len(TARGET_DOCS)}개):")
    for doc in TARGET_DOCS:
        print(f"  - {doc}")

    tests = [
        test_README_has_standard_workflow,
        test_INDEX_has_standard_workflow,
        test_AGENTS_has_standard_workflow,
        test_local_regression_checks_has_standard_workflow,
        test_repository_structure_has_standard_workflow,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            if t():
                passed += 1
            else:
                failed += 1
        except AssertionError as e:
            print(f"  ✗ AssertionError: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ 예외 발생: {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"결과: {passed}개 통과, {failed}개 실패")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
