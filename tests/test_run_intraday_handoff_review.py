#!/usr/bin/env python3
"""
Local handoff review CLI regression tests.

Run:
  python3 tests/test_run_intraday_handoff_review.py
"""
import json
import os
import subprocess
import sys
import tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from fixture_snapshot_builder import build_fixture_snapshot


SCRIPT = os.path.join(BASE, "scripts", "run_intraday_handoff_review.py")


def write_snapshot(snapshot):
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
    try:
        json.dump(snapshot, handle, ensure_ascii=False)
        handle.flush()
        return handle.name
    finally:
        handle.close()


def run_cli(args):
    return subprocess.run(
        [sys.executable, SCRIPT] + args,
        cwd=BASE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_cli_prints_packet_from_local_snapshot_file():
    print("테스트 1: CLI prints packet from local snapshot JSON")
    snapshot_path = write_snapshot(
        build_fixture_snapshot(
            symbol="HPSP",
            indicator_overrides={
                "rsi_1m": 42.0,
                "rsi_5m": 38.0,
                "rsi_30m": 29.7,
                "bb_5m_pct": 0.18,
                "bb_30m_pct": 0.40,
                "moving_average_state": "below_short_ma",
            },
        )
    )
    try:
        result = run_cli(
            [
                "--snapshot",
                snapshot_path,
                "--message",
                "HPSP 신호 왔어?",
                "--snapshot-reference-time",
                "2026-06-11T10:36:00+09:00",
            ]
        )
    finally:
        os.unlink(snapshot_path)

    assert result.returncode == 0, result.stderr
    assert "# Quick ChatGPT trading review" in result.stdout, result.stdout
    assert "- Symbol: HPSP" in result.stdout, result.stdout
    assert "## Intraday decision" in result.stdout, result.stdout
    assert "- Decision: 진입" in result.stdout, result.stdout
    assert "## Guardrail summary" in result.stdout, result.stdout
    print("  ✓ local packet printed")
    return True


def test_cli_uses_active_symbol_fallback():
    print("\n테스트 2: CLI supports active symbol fallback")
    snapshot_path = write_snapshot(build_fixture_snapshot(symbol="HPSP"))
    try:
        result = run_cli(
            [
                "--snapshot",
                snapshot_path,
                "--message",
                "신호 왔어?",
                "--active-symbol",
                "HPSP",
            ]
        )
    finally:
        os.unlink(snapshot_path)

    assert result.returncode == 0, result.stderr
    assert "- Symbol: HPSP" in result.stdout, result.stdout
    assert "signal_review" in result.stdout, result.stdout
    print("  ✓ active symbol fallback used")
    return True


def test_cli_rejects_missing_snapshot_file():
    print("\n테스트 3: CLI rejects missing snapshot file")
    result = run_cli(
        [
            "--snapshot",
            os.path.join(BASE, "missing-snapshot.json"),
            "--message",
            "HPSP 신호 왔어?",
        ]
    )

    assert result.returncode != 0, result
    assert "snapshot file not found" in result.stderr, result.stderr
    print("  ✓ missing snapshot rejected")
    return True


def test_cli_rejects_non_object_json_root():
    print("\n테스트 4: CLI rejects non-object JSON root")
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False)
    try:
        handle.write("[]")
        handle.close()
        result = run_cli(
            [
                "--snapshot",
                handle.name,
                "--message",
                "HPSP 신호 왔어?",
            ]
        )
    finally:
        os.unlink(handle.name)

    assert result.returncode != 0, result
    assert "snapshot JSON root must be an object" in result.stderr, result.stderr
    print("  ✓ non-object root rejected")
    return True


def run_all_tests():
    print("=" * 60)
    print("run_intraday_handoff_review.py CLI tests")
    print("=" * 60)

    tests = [
        test_cli_prints_packet_from_local_snapshot_file,
        test_cli_uses_active_symbol_fallback,
        test_cli_rejects_missing_snapshot_file,
        test_cli_rejects_non_object_json_root,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as exc:
            failed += 1
            print(f"  ✗ 실패: {exc}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"결과: {passed}개 통과, {failed}개 실패")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
