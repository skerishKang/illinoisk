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
import tempfile
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


def _run_runner(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUNNER), *args],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )


def _run_scenario(scenario: str) -> subprocess.CompletedProcess:
    return _run_runner(["--scenario", scenario])


def _run_list_scenarios() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--list-scenarios"],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )


def _run_all_scenarios() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--all-scenarios"],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )


def _run_write_output(
    scenario: str,
    root_dir: Path,
    *extra_args: str,
) -> subprocess.CompletedProcess:
    return _run_runner(
        [
            "--scenario",
            scenario,
            "--write-output",
            str(root_dir),
            *extra_args,
        ]
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


def _expected_packet_path(root_dir: Path, scenario_name: str) -> Path:
    return root_dir / "2026-06-13" / f"1035-HPSP-full_handoff_{scenario_name}.md"


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


def test_all_scenarios_runs_every_full_packet_in_sorted_order():
    """--all-scenarios는 sorted 순서로 모든 full packet을 출력해야 한다."""
    print("\n테스트 3: --all-scenarios — sorted full packet 묶음")
    result = _run_all_scenarios()
    assert result.returncode == 0, (
        f"runner exit code {result.returncode} (expected 0); stderr:\n{result.stderr}"
    )
    assert not result.stderr, f"stderr에 예기치 않은 출력: {result.stderr!r}"

    out = result.stdout
    scenario_names = [row["name"] for row in EXPECTED_SCENARIOS]
    expected_order = sorted(scenario_names)

    header_positions = []
    for name in expected_order:
        header = f"===== Scenario: {name} ====="
        assert header in out, f"scenario header 누락: {header}\n--- full stdout ---\n{out}"
        header_positions.append(out.index(header))

    assert header_positions == sorted(header_positions), (
        f"scenario header가 sorted 순서가 아님: "
        f"positions={header_positions}, expected={expected_order}"
    )

    for section in FULL_PACKET_SECTIONS:
        actual_count = out.count(section)
        assert actual_count == len(EXPECTED_SCENARIOS), (
            f"section 출력 개수 불일치: {section!r}, "
            f"actual={actual_count}, expected={len(EXPECTED_SCENARIOS)}"
        )

    for row in EXPECTED_SCENARIOS:
        for pattern in _route_patterns(row):
            assert pattern in out, (
                f"[{row['name']}] all-scenarios route-derived field 누락: {pattern}\n"
                f"--- full stdout ---\n{out}"
            )

    print(f"  ✓ sorted full packet 출력 확인: {expected_order}")
    return True


def test_write_output_writes_single_scenario_to_deterministic_path():
    """--write-output은 한 scenario packet만 deterministic path에 저장한다."""
    print("\n테스트 4: --write-output — deterministic single packet write")

    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        (root_dir / "2026-06-13").mkdir()
        expected_path = _expected_packet_path(root_dir, "active-symbol-signal")

        result = _run_write_output("active-symbol-signal", root_dir)
        assert result.returncode == 0, (
            f"runner exit code {result.returncode} (expected 0); stderr:\n{result.stderr}"
        )
        assert not result.stderr, f"stderr에 예기치 않은 출력: {result.stderr!r}"
        assert result.stdout.strip() == f"wrote handoff packet: {expected_path}", (
            f"write stdout 불일치: {result.stdout!r}"
        )
        assert expected_path.is_file(), f"packet 파일이 생성되지 않음: {expected_path}"

        packet = expected_path.read_text(encoding="utf-8")
        required_patterns = [
            "# ChatGPT trading review handoff",
            "- Date: 2026-06-13",
            "- Time KST: 2026-06-13 10:35 KST",
            "- Symbol: HPSP",
            "- User question: 신호 왔어?",
            "- Scenario: active-symbol-signal",
        ]
        for pattern in required_patterns:
            assert pattern in packet, f"written packet 누락: {pattern}\n--- packet ---\n{packet}"

    print("  ✓ deterministic path + UTF-8 full packet write 확인")
    return True


def test_write_output_refuses_existing_file_unless_overwrite():
    """--write-output은 기존 파일을 overwrite 없이 덮어쓰지 않는다."""
    print("\n테스트 5: --write-output — existing file guard + --overwrite")

    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        (root_dir / "2026-06-13").mkdir()
        expected_path = _expected_packet_path(root_dir, "active-symbol-signal")

        first = _run_write_output("active-symbol-signal", root_dir)
        assert first.returncode == 0, f"first write 실패: stderr={first.stderr!r}"
        original = expected_path.read_text(encoding="utf-8")

        second = _run_write_output("active-symbol-signal", root_dir)
        assert second.returncode == 2, (
            f"기존 파일인데 exit code가 2가 아님: rc={second.returncode}, stderr={second.stderr!r}"
        )
        assert "reason=exists" in second.stderr, (
            f"existing file reason 누락: stderr={second.stderr!r}"
        )
        assert expected_path.read_text(encoding="utf-8") == original, (
            "overwrite=False 거부 후 파일 내용이 바뀜"
        )

        third = _run_write_output("active-symbol-signal", root_dir, "--overwrite")
        assert third.returncode == 0, f"--overwrite write 실패: stderr={third.stderr!r}"
        assert not third.stderr, f"--overwrite stderr 출력: {third.stderr!r}"
        replaced = expected_path.read_text(encoding="utf-8")
        assert replaced == original, "deterministic fixture overwrite 결과가 원본과 달라짐"
        assert "- Scenario: active-symbol-signal" in replaced, "overwrite 후 packet 내용 누락"

    print("  ✓ existing guard + explicit --overwrite 확인")
    return True


def test_write_output_overwrite_false_blocks_second_write():
    """overwrite 기본값은 기존 packet을 보존하고 두 번째 쓰기를 거부한다."""
    print("\n테스트 6: --write-output — second write blocked by default")

    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        (root_dir / "2026-06-13").mkdir()
        expected_path = _expected_packet_path(root_dir, "active-symbol-signal")

        first = _run_write_output("active-symbol-signal", root_dir)
        assert first.returncode == 0, f"first write 실패: stderr={first.stderr!r}"
        original = expected_path.read_text(encoding="utf-8")

        second = _run_write_output("active-symbol-signal", root_dir)
        assert second.returncode == 2, (
            f"overwrite=False second write가 거부되지 않음: rc={second.returncode}"
        )
        assert not second.stdout, f"거부된 write가 stdout을 출력함: {second.stdout!r}"
        assert "reason=exists" in second.stderr, (
            f"existing file reason 누락: stderr={second.stderr!r}"
        )
        assert str(expected_path) in second.stderr, (
            f"stderr에 기존 packet path가 없음: stderr={second.stderr!r}"
        )
        assert expected_path.read_text(encoding="utf-8") == original, (
            "overwrite=False 거부 후 packet 내용이 변경됨"
        )

    print("  ✓ overwrite=False second write guard + unchanged file 확인")
    return True


def test_write_output_overwrite_true_replaces_existing_packet():
    """--overwrite는 기존 packet 파일을 canonical packet으로 교체한다."""
    print("\n테스트 7: --write-output --overwrite — replace stale packet")

    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        (root_dir / "2026-06-13").mkdir()
        expected_path = _expected_packet_path(root_dir, "active-symbol-signal")
        expected_path.write_text("stale local packet\n", encoding="utf-8")

        result = _run_write_output("active-symbol-signal", root_dir, "--overwrite")
        assert result.returncode == 0, (
            f"--overwrite write 실패: rc={result.returncode}, stderr={result.stderr!r}"
        )
        assert not result.stderr, f"--overwrite stderr 출력: {result.stderr!r}"
        assert result.stdout.strip() == f"wrote handoff packet: {expected_path}", (
            f"write stdout 불일치: {result.stdout!r}"
        )

        packet = expected_path.read_text(encoding="utf-8")
        assert packet != "stale local packet\n", "stale packet이 교체되지 않음"
        assert "# ChatGPT trading review handoff" in packet, "교체된 packet header 누락"
        assert "- Scenario: active-symbol-signal" in packet, "교체된 packet scenario 누락"

    print("  ✓ explicit --overwrite stale packet replacement 확인")
    return True


def test_write_output_rejects_overwrite_without_write_output():
    """--overwrite 단독 사용은 write-output 없이 거부되어야 한다."""
    print("\n테스트 8: --overwrite without --write-output — rejected")

    result = _run_runner(["--scenario", "active-symbol-signal", "--overwrite"])
    assert result.returncode == 2, (
        f"--overwrite 단독인데 exit code가 2가 아님: rc={result.returncode}"
    )
    assert not result.stdout, f"거부된 CLI가 stdout을 출력함: {result.stdout!r}"
    assert "--overwrite requires --write-output ROOT_DIR" in result.stderr, (
        f"stderr에 overwrite guard 메시지가 없음: {result.stderr!r}"
    )

    print("  ✓ --overwrite 단독 거부 확인")
    return True


def test_write_output_requires_scenario_when_used():
    """--write-output은 대상 scenario 없이 실행될 수 없다."""
    print("\n테스트 9: --write-output without --scenario — rejected")

    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        result = _run_runner(["--write-output", str(root_dir)])
        assert result.returncode == 2, (
            f"--write-output 단독인데 exit code가 2가 아님: rc={result.returncode}"
        )
        assert not result.stdout, f"거부된 CLI가 stdout을 출력함: {result.stdout!r}"
        assert "--write-output requires --scenario NAME" in result.stderr, (
            f"stderr에 scenario guard 메시지가 없음: {result.stderr!r}"
        )
        assert not any(root_dir.iterdir()), "scenario 없이 write-output이 파일/디렉터리를 생성함"

    print("  ✓ --write-output requires --scenario guard 확인")
    return True


def test_write_output_requires_existing_date_directory():
    """--write-output은 parent directory를 자동 생성하지 않는다."""
    print("\n테스트 10: --write-output — parent_missing guard")

    with tempfile.TemporaryDirectory() as tmp:
        root_dir = Path(tmp)
        expected_path = _expected_packet_path(root_dir, "active-symbol-signal")

        result = _run_write_output("active-symbol-signal", root_dir)
        assert result.returncode == 2, (
            f"parent_missing인데 exit code가 2가 아님: rc={result.returncode}, stderr={result.stderr!r}"
        )
        assert "reason=parent_missing" in result.stderr, (
            f"parent_missing reason 누락: stderr={result.stderr!r}"
        )
        assert not expected_path.exists(), "parent_missing인데 packet 파일이 생성됨"
        assert not (root_dir / "2026-06-13").exists(), (
            "parent_missing인데 date directory가 자동 생성됨"
        )

    print("  ✓ parent directory 자동 생성 없음 + guard 확인")
    return True


def test_unknown_scenario_reports_error_and_exits_nonzero():
    """알 수 없는 scenario는 stderr와 non-zero exit code로 거부되어야 한다."""
    print("\n테스트 11: --scenario unknown-* — 에러 처리")
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
        test_all_scenarios_runs_every_full_packet_in_sorted_order,
        test_write_output_writes_single_scenario_to_deterministic_path,
        test_write_output_refuses_existing_file_unless_overwrite,
        test_write_output_overwrite_false_blocks_second_write,
        test_write_output_overwrite_true_replaces_existing_packet,
        test_write_output_rejects_overwrite_without_write_output,
        test_write_output_requires_scenario_when_used,
        test_write_output_requires_existing_date_directory,
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
