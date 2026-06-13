#!/usr/bin/env python3
"""
Local quick handoff fixture runner 회귀 테스트.

`scripts/run_quick_handoff_fixture.py`의 scenario catalog(PR #127)가
future edit에도 의미를 잃지 않도록 table-driven으로 잠근다.

각 scenario에 대해 검증:
  1. scenario name
  2. expected symbol
  3. expected user question
  4. expected intent
  5. expected trigger
  6. expected reply mode
  7. expected used_active_symbol (bool 직렬화 형태: "true" / "false")
  8. 공통 packet section 6개

추가 검증:
  - unknown scenario는 명확한 stderr + non-zero exit code로 거부
  - --list-scenarios 출력은 deterministic(sorted) 3개 시나리오 이름

실행:
  python3 tests/test_run_quick_handoff_fixture.py
"""
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RUNNER = BASE / "scripts" / "run_quick_handoff_fixture.py"

# ---------------------------------------------------------------------------
# Scenario catalog table (Issue #128)
# ---------------------------------------------------------------------------
# 각 row는 scripts/run_quick_handoff_fixture.py의 한 scenario에 대응하며,
# packet이 stdout에 포함해야 할 7개 route 속성과 그 직렬화 값을 정의한다.
#
# used_active_symbol은 _format_value()가 bool을 직렬화한 결과("true"/"false")로
# 기록한다.
EXPECTED_SCENARIOS = [
    {
        "name": "active-symbol-signal",
        "symbol": "HPSP",
        "user_question": "신호 왔어?",
        "intent": "signal_review",
        "trigger": "신호",
        "reply_mode": "short_review",
        "used_active_symbol": "true",  # recent_messages에서 HPSP 해석
    },
    {
        "name": "explicit-symbol-entry",
        "symbol": "HPSP",
        "user_question": "HPSP 지금 진입해도 돼?",
        "intent": "entry_check",
        "trigger": "진입",
        "reply_mode": "short_review",
        "used_active_symbol": "false",  # 메시지에서 명시적으로 HPSP 사용
    },
    {
        "name": "active-symbol-stop",
        "symbol": "HPSP",
        "user_question": "손절 기준 알려줘",
        "intent": "stop_check",
        "trigger": "손절",
        "reply_mode": "short_review",
        "used_active_symbol": "true",  # recent_messages에서 HPSP 해석
    },
]

COMMON_PACKET_SECTIONS = [
    "# Quick ChatGPT trading review",
    "## Guardrail summary",
    "## Review request",
    "## Trigger route",
    "## Intraday decision",
    "## Required response format",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _run_runner(scenario: str) -> subprocess.CompletedProcess:
    """--scenario NAME으로 runner를 subprocess 호출한다."""
    return subprocess.run(
        [sys.executable, str(RUNNER), "--scenario", scenario],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )


def _run_list_scenarios() -> subprocess.CompletedProcess:
    """--list-scenarios 플래그로 runner를 subprocess 호출한다."""
    return subprocess.run(
        [sys.executable, str(RUNNER), "--list-scenarios"],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )


def _run_all_scenarios() -> subprocess.CompletedProcess:
    """--all-scenarios 플래그로 runner를 subprocess 호출한다."""
    return subprocess.run(
        [sys.executable, str(RUNNER), "--all-scenarios"],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )


def _build_route_patterns(row: dict) -> list[str]:
    """table row 하나를 packet에 있어야 할 7개 route pattern 리스트로 변환한다."""
    return [
        f"- Symbol: {row['symbol']}",
        f"- User question: {row['user_question']}",
        f"- Intent: {row['intent']}",
        f"- Triggers: {row['trigger']}",
        f"- Reply mode: {row['reply_mode']}",
        f"- Used active symbol: {row['used_active_symbol']}",
    ]


# ---------------------------------------------------------------------------
# Table-driven regression (Issue #128)
# ---------------------------------------------------------------------------
def test_scenario_catalog_table_driven_assertions():
    """3개 scenario의 7개 route 속성과 6개 공통 packet 섹션을 table-driven으로 검증."""
    print(f"\n테스트 1: scenario catalog table-driven 회귀 ({len(EXPECTED_SCENARIOS)}개 시나리오)")

    for row in EXPECTED_SCENARIOS:
        name = row["name"]
        result = _run_runner(name)

        assert result.returncode == 0, (
            f"[{name}] runner exit code {result.returncode} (expected 0); "
            f"stderr:\n{result.stderr}"
        )
        out = result.stdout

        # 7개 route 속성
        route_patterns = _build_route_patterns(row)
        missing_routes = [p for p in route_patterns if p not in out]
        assert not missing_routes, (
            f"[{name}] stdout에 누락된 route 속성 ({len(missing_routes)}개):\n"
            + "\n".join(f"  - {p}" for p in missing_routes)
            + f"\n--- full stdout ---\n{out}"
        )

        # 6개 공통 packet 섹션
        missing_sections = [s for s in COMMON_PACKET_SECTIONS if s not in out]
        assert not missing_sections, (
            f"[{name}] stdout에 누락된 공통 섹션 ({len(missing_sections)}개):\n"
            + "\n".join(f"  - {s}" for s in missing_sections)
            + f"\n--- full stdout ---\n{out}"
        )

        print(
            f"  ✓ {name}: 7개 route 속성 + {len(COMMON_PACKET_SECTIONS)}개 공통 섹션 모두 통과"
        )

    return True


# ---------------------------------------------------------------------------
# 유지되는 테스트
# ---------------------------------------------------------------------------
def test_unknown_scenario_reports_error_and_exits_nonzero():
    """알 수 없는 시나리오 이름은 명확한 에러와 non-zero exit code로 거부되어야 한다."""
    print("\n테스트 2: --scenario unknown-* — 에러 처리")
    result = _run_runner("unknown-this-scenario-does-not-exist")

    assert result.returncode != 0, (
        f"unknown scenario인데 exit code 0: stdout=\n{result.stdout!r}, "
        f"stderr=\n{result.stderr!r}"
    )
    assert "unknown scenario" in result.stderr, (
        f"stderr에 'unknown scenario' 메시지 없음: {result.stderr!r}"
    )
    assert "active-symbol-signal" in result.stderr, (
        f"stderr에 사용 가능한 시나리오 목록이 없음: {result.stderr!r}"
    )
    print(f"  ✓ unknown scenario 거부: exit code {result.returncode}")
    print(f"  ✓ stderr에 'unknown scenario' + 사용 가능 목록 포함")

    return True


def test_list_scenarios_is_deterministic_and_sorted():
    """--list-scenarios는 3개 시나리오 이름을 알파벳 순으로 stdout에 출력한다."""
    print("\n테스트 3: --list-scenarios — deterministic sorted 목록")
    result = _run_list_scenarios()

    assert result.returncode == 0, (
        f"runner exit code {result.returncode} (expected 0); "
        f"stderr:\n{result.stderr}"
    )
    out = result.stdout

    # table에서 시나리오 이름 추출
    scenario_names = [row["name"] for row in EXPECTED_SCENARIOS]
    missing = [n for n in scenario_names if n not in out]
    assert not missing, (
        f"stdout에 시나리오 누락: {missing}\n--- full stdout ---\n{out}"
    )
    print(f"  ✓ {len(scenario_names)}개 시나리오 이름 모두 stdout에 포함")

    # deterministic(sorted) 검증: 알파벳 순 위치 확인
    expected_order = sorted(scenario_names)
    positions = [out.index(name) for name in expected_order]
    assert positions == sorted(positions), (
        f"시나리오 이름이 알파벳 순이 아님: positions={positions} "
        f"(expected non-decreasing), expected_order={expected_order}"
    )
    print(f"  ✓ 알파벳 순 정렬 확인: {expected_order}")

    return True


def test_all_scenarios_runs_all_in_sorted_order():
    """--all-scenarios는 sorted 순서로 3개 scenario packet + header를 stdout에 출력한다."""
    print("\n테스트 4: --all-scenarios — sorted order, 모든 packet 검증")
    result = _run_all_scenarios()

    # 1) exit code 0
    assert result.returncode == 0, (
        f"runner exit code {result.returncode} (expected 0); "
        f"stderr:\n{result.stderr}"
    )

    # 6) stderr 비어있음 (또는 에러 없음)
    assert not result.stderr, (
        f"stderr에 예기치 않은 에러 출력: {result.stderr!r}"
    )

    out = result.stdout

    # 2) 3개 header 모두 stdout에 포함
    scenario_names = [row["name"] for row in EXPECTED_SCENARIOS]
    for name in scenario_names:
        header = f"===== Scenario: {name} ====="
        assert header in out, f"header 누락: {header}\n--- full stdout ---\n{out}"

    # 3) header 순서 = sorted 순서
    expected_order = sorted(scenario_names)
    positions = [out.index(f"===== Scenario: {n} =====") for n in expected_order]
    assert positions == sorted(positions), (
        f"header 순서가 sorted 아님: positions={positions} "
        f"(expected non-decreasing), expected_order={expected_order}"
    )

    # 4) 각 시나리오 packet 핵심 route 속성 stdout 포함
    #    _build_route_patterns 재사용 → table-driven과 정합성 유지
    for row in EXPECTED_SCENARIOS:
        for pattern in _build_route_patterns(row):
            assert pattern in out, (
                f"[{row['name']}] route 속성 누락: {pattern}\n"
                f"--- full stdout ---\n{out}"
            )

    # 5) 공통 packet section stdout 포함
    for section in COMMON_PACKET_SECTIONS:
        assert section in out, f"공통 섹션 누락: {section}\n--- full stdout ---\n{out}"

    print(f"  ✓ exit code 0, stderr 비어있음")
    print(f"  ✓ 3개 header 모두 stdout에 포함, sorted 순서 확인: {expected_order}")
    print(f"  ✓ 3개 시나리오 × 6개 route 속성 = 18개 검증 모두 통과")
    print(f"  ✓ 6개 공통 packet section 모두 stdout에 포함")

    return True


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("run_quick_handoff_fixture.py 회귀 테스트")
    print("=" * 60)
    print(f"runner path: {RUNNER}")

    tests = [
        test_scenario_catalog_table_driven_assertions,
        test_unknown_scenario_reports_error_and_exits_nonzero,
        test_list_scenarios_is_deterministic_and_sorted,
        test_all_scenarios_runs_all_in_sorted_order,
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
