#!/usr/bin/env python3
"""
Local quick handoff fixture runner 회귀 테스트.

`scripts/run_quick_handoff_fixture.py`가 박사님이 명시한 11개 spec을
stdout에 정확히 출력하는지 확인한다.

확인 시나리오:
  --scenario active-symbol-signal

확인 패턴 (모두 stdout에 포함되어야 함):
  - "# Quick ChatGPT trading review"
  - "## Guardrail summary"
  - "## Review request"
  - "- Symbol: HPSP"
  - "## Trigger route"
  - "- Intent: signal_review"
  - "- Triggers: 신호"
  - "- Reply mode: short_review"
  - "- Used active symbol: true"
  - "## Intraday decision"
  - "## Required response format"

실행:
  python3 tests/test_run_quick_handoff_fixture.py
"""
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RUNNER = BASE / "scripts" / "run_quick_handoff_fixture.py"

REQUIRED_PATTERNS = [
    "# Quick ChatGPT trading review",
    "## Guardrail summary",
    "## Review request",
    "- Symbol: HPSP",
    "## Trigger route",
    "- Intent: signal_review",
    "- Triggers: 신호",
    "- Reply mode: short_review",
    "- Used active symbol: true",
    "## Intraday decision",
    "## Required response format",
]


def _run_runner(scenario: str) -> subprocess.CompletedProcess:
    """CLI 러너를 subprocess로 실행하고 결과를 반환한다."""
    return subprocess.run(
        [sys.executable, str(RUNNER), "--scenario", scenario],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )


def test_active_symbol_scenario_emits_required_sections():
    """--scenario active-symbol-signal이 박사님 11개 spec을 모두 stdout에 출력하는지 확인."""
    print("\n테스트 1: --scenario active-symbol-signal — 11개 spec 검증")
    result = _run_runner("active-symbol-signal")

    assert result.returncode == 0, (
        f"runner exit code {result.returncode} (expected 0); "
        f"stderr:\n{result.stderr}"
    )
    print(f"  ✓ exit code 0")

    out = result.stdout
    missing = [p for p in REQUIRED_PATTERNS if p not in out]
    assert not missing, (
        f"stdout에 누락된 spec ({len(missing)}개):\n"
        + "\n".join(f"  - {p}" for p in missing)
        + f"\n--- full stdout ---\n{out}"
    )
    print(f"  ✓ 11개 spec 모두 stdout에 포함: {len(REQUIRED_PATTERNS)}개 통과")

    return True


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


def test_explicit_symbol_entry_scenario_emits_packet():
    """--scenario explicit-symbol-entry가 HPSP/entry_check/used_active_symbol=false를 stdout에 출력하는지 확인."""
    print("\n테스트 3: --scenario explicit-symbol-entry — entry_check + 명시적 종목")
    result = _run_runner("explicit-symbol-entry")

    assert result.returncode == 0, (
        f"runner exit code {result.returncode} (expected 0); "
        f"stderr:\n{result.stderr}"
    )
    out = result.stdout

    for required in (
        "- Symbol: HPSP",
        "- Intent: entry_check",
        "- Used active symbol: false",  # 메시지에서 명시적으로 HPSP를 잡았으므로 active 아님
    ):
        assert required in out, (
            f"stdout에 누락: {required}\n--- full stdout ---\n{out}"
        )
    print("  ✓ explicit-symbol-entry: Symbol=HPSP, Intent=entry_check, Used active symbol=false")

    return True


def test_active_symbol_stop_scenario_emits_packet():
    """--scenario active-symbol-stop이 HPSP/stop_check/used_active_symbol=true를 stdout에 출력하는지 확인."""
    print("\n테스트 4: --scenario active-symbol-stop — stop_check + recent 해석 active")
    result = _run_runner("active-symbol-stop")

    assert result.returncode == 0, (
        f"runner exit code {result.returncode} (expected 0); "
        f"stderr:\n{result.stderr}"
    )
    out = result.stdout

    for required in (
        "- Symbol: HPSP",
        "- Intent: stop_check",
        "- Used active symbol: true",  # recent_messages에서 HPSP 해석
    ):
        assert required in out, (
            f"stdout에 누락: {required}\n--- full stdout ---\n{out}"
        )
    print("  ✓ active-symbol-stop: Symbol=HPSP, Intent=stop_check, Used active symbol=true")

    return True


def _run_list_scenarios() -> subprocess.CompletedProcess:
    """--list-scenarios 플래그로 runner를 subprocess 호출한다."""
    return subprocess.run(
        [sys.executable, str(RUNNER), "--list-scenarios"],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )


def test_list_scenarios_is_deterministic_and_sorted():
    """--list-scenarios는 3개 시나리오 이름을 알파벳 순으로 stdout에 출력한다."""
    print("\n테스트 5: --list-scenarios — deterministic sorted 목록")
    result = _run_list_scenarios()

    assert result.returncode == 0, (
        f"runner exit code {result.returncode} (expected 0); "
        f"stderr:\n{result.stderr}"
    )
    out = result.stdout

    for required_scenario in (
        "active-symbol-signal",
        "active-symbol-stop",
        "explicit-symbol-entry",
    ):
        assert required_scenario in out, (
            f"stdout에 시나리오 누락: {required_scenario}\n--- full stdout ---\n{out}"
        )
    print("  ✓ 3개 시나리오 이름 모두 stdout에 포함")

    # deterministic(sorted) 검증: 알파벳 순 위치 확인
    expected_order = sorted([
        "active-symbol-signal",
        "active-symbol-stop",
        "explicit-symbol-entry",
    ])
    # expected_order == ["active-symbol-signal", "active-symbol-stop", "explicit-symbol-entry"]
    positions = [out.index(name) for name in expected_order]
    assert positions == sorted(positions), (
        f"시나리오 이름이 알파벳 순이 아님: positions={positions} "
        f"(expected non-decreasing)"
    )
    print(f"  ✓ 알파벳 순 정렬 확인: {expected_order}")

    return True


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("run_quick_handoff_fixture.py 회귀 테스트")
    print("=" * 60)
    print(f"runner path: {RUNNER}")

    tests = [
        test_active_symbol_scenario_emits_required_sections,
        test_unknown_scenario_reports_error_and_exits_nonzero,
        test_explicit_symbol_entry_scenario_emits_packet,
        test_active_symbol_stop_scenario_emits_packet,
        test_list_scenarios_is_deterministic_and_sorted,
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
