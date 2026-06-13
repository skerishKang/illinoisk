#!/usr/bin/env python3
"""
Local full handoff fixture runner 회귀 테스트.

`scripts/run_full_handoff_fixture.py`가 full ChatGPT handoff packet contract의
주요 section order와 route-derived metadata를 deterministic하게 출력하는지 검증한다.

실행:
  python3 tests/test_run_full_handoff_fixture.py
"""
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RUNNER = BASE / "scripts" / "run_full_handoff_fixture.py"

EXPECTED_SCENARIOS = [
    {
        "name": "active-symbol-signal",
        "symbol": "HPSP",
        "user_question": "신호 왔어?",
        "intent": "signal_review",
        "trigger": "신호",
        "reply_mode": "short_review",
        "used_active_symbol": "true",
    },
    {
        "name": "explicit-symbol-entry",
        "symbol": "HPSP",
        "user_question": "HPSP 지금 진입해도 돼?",
        "intent": "entry_check",
        "trigger": "진입",
        "reply_mode": "short_review",
        "used_active_symbol": "false",
    },
    {
        "name": "active-symbol-stop",
        "symbol": "HPSP",
        "user_question": "손절 기준 알려줘",
        "intent": "stop_check",
        "trigger": "손절",
        "reply_mode": "short_review",
        "used_active_symbol": "true",
    },
]

FULL_PACKET_SECTIONS = [
    "# ChatGPT trading review handoff",
    "## 1. Review request",
    "## 2. Market/session context",
    "## 3. Active symbol context",
    "## 4. Local market snapshot",
    "## 5. Chart summary or attachments",
    "## 6. Recent Discord conversation excerpt",
    "## 7. Current model answer to review",
    "## 8. Applicable rules",
    "## 9. Known data gaps",
    "## 10. Questions for ChatGPT",
    "## 11. Expected output format",
]

REQUIRED_SNAPSHOT_FIELDS = [
    '"quote"',
    '"indicators"',
    '"flow"',
    '"data_gaps"',
    '"futures_foreign_institutional_flow": "unavailable"',
]


def _run_scenario(scenario: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--scenario", scenario],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )


def _run_list_scenarios() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--list-scenarios"],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )


def _section_positions(out: str) -> list[int]:
    positions = []
    for section in FULL_PACKET_SECTIONS:
        assert section in out, f"section 누락: {section}\n--- full stdout ---\n{out}"
        positions.append(out.index(section))
    return positions


def _route_patterns(row: dict) -> list[str]:
    return [
        f"- Symbol: {row['symbol']}",
        f"- User question: {row['user_question']}",
        f"- Scenario: {row['name']}",
        f"- Intent: {row['intent']}",
        f"- Triggers: {row['trigger']}",
        f"- Reply mode: {row['reply_mode']}",
        f"- Used active symbol: {row['used_active_symbol']}",
    ]


def test_full_handoff_scenarios_include_required_sections_and_route_metadata():
    """모든 scenario가 full packet sections와 route metadata를 포함하는지 검증."""
    print(f"\n테스트 1: full handoff packet section + route metadata ({len(EXPECTED_SCENARIOS)}개 scenario)")

    for row in EXPECTED_SCENARIOS:
        name = row["name"]
        result = _run_scenario(name)
        assert result.returncode == 0, (
            f"[{name}] runner exit code {result.returncode} (expected 0); "
            f"stderr:\n{result.stderr}"
        )
        assert not result.stderr, f"[{name}] stderr에 예기치 않은 출력: {result.stderr!r}"

        out = result.stdout
        positions = _section_positions(out)
        assert positions == sorted(positions), (
            f"[{name}] section 순서가 contract order와 다름: positions={positions}"
        )

        for pattern in _route_patterns(row):
            assert pattern in out, (
                f"[{name}] route-derived field 누락: {pattern}\n"
                f"--- full stdout ---\n{out}"
            )

        for field in REQUIRED_SNAPSHOT_FIELDS:
            assert field in out, (
                f"[{name}] snapshot field 누락: {field}\n"
                f"--- full stdout ---\n{out}"
            )

        assert "```json" in out and "```text" in out, (
            f"[{name}] json/text fenced block 누락\n--- full stdout ---\n{out}"
        )
        print(f"  ✓ {name}: sections, route metadata, snapshot fields 통과")

    return True


def test_list_scenarios_is_deterministic_and_sorted():
    """--list-scenarios 출력은 quick runner와 동일하게 deterministic sorted여야 한다."""
    print("\n테스트 2: --list-scenarios — deterministic sorted 목록")
    result = _run_list_scenarios()
    assert result.returncode == 0, (
        f"runner exit code {result.returncode} (expected 0); stderr:\n{result.stderr}"
    )
    assert not result.stderr, f"stderr에 예기치 않은 출력: {result.stderr!r}"

    out = result.stdout
    assert "Available scenarios:" in out, f"목록 title 누락\n--- full stdout ---\n{out}"
    scenario_names = [row["name"] for row in EXPECTED_SCENARIOS]
    expected_order = sorted(scenario_names)
    positions = [out.index(name) for name in expected_order]
    assert positions == sorted(positions), (
        f"시나리오 이름이 sorted 순서가 아님: positions={positions}, expected={expected_order}"
    )
    print(f"  ✓ sorted scenario 목록 확인: {expected_order}")

    return True


def test_unknown_scenario_reports_error_and_exits_nonzero():
    """알 수 없는 scenario는 stderr와 non-zero exit code로 거부되어야 한다."""
    print("\n테스트 3: --scenario unknown-* — 에러 처리")
    result = _run_scenario("unknown-this-scenario-does-not-exist")

    assert result.returncode != 0, (
        f"unknown scenario인데 exit code 0: stdout={result.stdout!r}, stderr={result.stderr!r}"
    )
    assert "unknown scenario" in result.stderr, (
        f"stderr에 'unknown scenario' 메시지 없음: {result.stderr!r}"
    )
    assert "active-symbol-signal" in result.stderr, (
        f"stderr에 사용 가능한 scenario 목록이 없음: {result.stderr!r}"
    )
    print(f"  ✓ unknown scenario 거부: exit code {result.returncode}")

    return True


def run_all_tests():
    """모든 테스트 실행."""
    print("=" * 60)
    print("run_full_handoff_fixture.py 회귀 테스트")
    print("=" * 60)
    print(f"runner path: {RUNNER}")

    tests = [
        test_full_handoff_scenarios_include_required_sections_and_route_metadata,
        test_list_scenarios_is_deterministic_and_sorted,
        test_unknown_scenario_reports_error_and_exits_nonzero,
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
