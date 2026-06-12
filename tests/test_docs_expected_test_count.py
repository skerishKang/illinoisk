#!/usr/bin/env python3
"""
문서화된 expected test count가 `tests/run_all.py`의 실제 등록 테스트 개수와
일치하는지 동적으로 검증하는 회귀 테스트.

동작:
  1. `tests/run_all.py`를 AST로 정적 파싱해 `CHECKS = [...]` 리스트 길이를 센다.
     (이 테스트 자체도 CHECKS에 등록되므로 카운트에 포함된다.)
  2. entrypoint / support docs에서 "XX개 통과, 0개 실패" 패턴을 찾아 XX를 추출한다.
  3. 두 값이 다르면 명확한 메시지로 AssertionError를 발생시킨다.

이 테스트가 추가되면 run_all.py는 21 -> 22가 되고, 같은 PR에서 문서 기대값도
22로 올려야 한다. 미래에 다른 테스트가 추가/삭제되어도 이 테스트가 자동으로
문서 불일치를 잡는다.

확인 대상 문서 (4):
  - README.md
  - INDEX.md
  - AGENTS.md
  - docs/local-regression-checks.md

실행:
  python3 tests/test_docs_expected_test_count.py
"""
import ast
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RUN_ALL_PATH = BASE / "tests" / "run_all.py"

TARGET_DOCS = [
    "README.md",
    "INDEX.md",
    "AGENTS.md",
    "docs/local-regression-checks.md",
]

# "22개 통과, 0개 실패" 형식에서 22를 추출
COUNT_PATTERN = re.compile(r"(\d+)\s*개\s*통과\s*,\s*0\s*개\s*실패")


def _count_run_all_checks() -> int:
    """`tests/run_all.py`의 CHECKS = [...] 리스트 길이를 정적으로 센다."""
    tree = ast.parse(RUN_ALL_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "CHECKS"
                    and isinstance(node.value, (ast.List, ast.Tuple))
                ):
                    return len(node.value.elts)
    raise AssertionError(
        f"{RUN_ALL_PATH}에서 CHECKS = [...] 할당을 찾지 못함"
    )


def _extract_documented_count(rel_path: str):
    """문서에서 "XX개 통과, 0개 실패"의 XX를 정수로 추출. 없으면 None."""
    doc_path = BASE / rel_path
    if not doc_path.exists():
        raise AssertionError(f"문서 파일 없음: {rel_path}")
    try:
        content = doc_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = doc_path.read_text(encoding="utf-8", errors="replace")
    match = COUNT_PATTERN.search(content)
    if not match:
        return None
    return int(match.group(1))


def test_documented_test_count_matches_run_all():
    """문서 4개의 기대 test count가 run_all.py CHECKS 길이와 모두 일치하는지 확인."""
    print("\n테스트 1: 문서 expected test count == tests/run_all.py CHECKS length")

    actual = _count_run_all_checks()
    print(f"  tests/run_all.py CHECKS 등록 수: {actual}")

    for rel_path in TARGET_DOCS:
        documented = _extract_documented_count(rel_path)
        assert documented is not None, (
            f"{rel_path}: '{COUNT_PATTERN.pattern}' 패턴을 찾지 못함. "
            f"expected test count 문구가 누락되었거나 형식이 다름."
        )
        assert documented == actual, (
            f"{rel_path}: 문서 expected = {documented}, "
            f"실제 run_all.py CHECKS = {actual}. "
            f"expected count를 {actual}개로 정렬하세요."
        )
        print(f"  ✓ {rel_path}: {documented}개 통과 (실제와 일치)")

    return True


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("docs expected test count 동적 회귀 테스트 시작")
    print("=" * 60)
    print(f"확인 대상 문서 ({len(TARGET_DOCS)}개):")
    for doc in TARGET_DOCS:
        print(f"  - {doc}")

    tests = [
        test_documented_test_count_matches_run_all,
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
