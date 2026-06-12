#!/usr/bin/env python3
"""
Deterministic snapshot age guard regression tests.

Run:
  python3 tests/test_handoff_snapshot_age_guard.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from fixture_snapshot_builder import build_fixture_snapshot
from handoff_orchestrator import build_handoff_from_message


def valid_signal_snapshot():
    snapshot = build_fixture_snapshot(
        indicator_overrides={
            "rsi_1m": 42.0,
            "rsi_5m": 38.0,
            "rsi_30m": 29.7,
            "bb_5m_pct": 0.18,
            "bb_30m_pct": 0.40,
            "moving_average_state": "below_short_ma",
        }
    )
    snapshot["as_of"] = "2026-06-11T10:35:00+09:00"
    return snapshot


def test_fresh_snapshot_age_preserves_valid_signal():
    print("테스트 1: fresh snapshot age preserves valid signal")
    result = build_handoff_from_message(
        {
            "message": "HPSP status check",
            "active_symbol": "HPSP",
            "snapshot": valid_signal_snapshot(),
            "snapshot_reference_time": "2026-06-11T10:37:30+09:00",
        }
    )

    assert "- Signal state: valid_signal" in result.packet_markdown, result.packet_markdown
    assert "- Decision: 진입" in result.packet_markdown, result.packet_markdown
    assert "snapshot stale" not in result.packet_markdown, result.packet_markdown
    print("  ✓ fresh snapshot remains actionable")
    return True


def test_stale_snapshot_age_forces_unavailable_decision():
    print("\n테스트 2: stale snapshot age forces unavailable decision")
    snapshot = valid_signal_snapshot()
    snapshot["as_of"] = "2026-06-11T10:30:00+09:00"

    result = build_handoff_from_message(
        {
            "message": "HPSP status check",
            "active_symbol": "HPSP",
            "snapshot": snapshot,
            "signal_state": "valid_signal",
            "snapshot_reference_time": "2026-06-11T10:35:01+09:00",
        }
    )

    assert "- Signal state: unavailable" in result.packet_markdown, result.packet_markdown
    assert "- Decision: 대기" in result.packet_markdown, result.packet_markdown
    assert "snapshot stale: 301s old" in result.packet_markdown, result.packet_markdown
    print("  ✓ stale snapshot is blocked")
    return True


def test_unparsable_snapshot_time_forces_unavailable_decision():
    print("\n테스트 3: unparsable snapshot time forces unavailable decision")
    snapshot = valid_signal_snapshot()
    snapshot["as_of"] = "not-a-time"

    result = build_handoff_from_message(
        {
            "message": "HPSP status check",
            "active_symbol": "HPSP",
            "snapshot": snapshot,
            "snapshot_reference_time": "2026-06-11T10:35:01+09:00",
        }
    )

    assert "- Signal state: unavailable" in result.packet_markdown, result.packet_markdown
    assert "- Decision: 대기" in result.packet_markdown, result.packet_markdown
    assert "snapshot as_of unparsable" in result.packet_markdown, result.packet_markdown
    print("  ✓ unparsable snapshot time is blocked")
    return True


def run_all_tests():
    print("=" * 60)
    print("snapshot age guard fixture tests")
    print("=" * 60)

    tests = [
        test_fresh_snapshot_age_preserves_valid_signal,
        test_stale_snapshot_age_forces_unavailable_decision,
        test_unparsable_snapshot_time_forces_unavailable_decision,
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
