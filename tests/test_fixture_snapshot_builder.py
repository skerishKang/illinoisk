#!/usr/bin/env python3
"""
Fixture-only snapshot builder regression tests.

Run:
  python3 tests/test_fixture_snapshot_builder.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from fixture_snapshot_builder import DEFAULT_AS_OF, DEFAULT_SYMBOL, build_fixture_snapshot
from snapshot_schema_validator import validate_snapshot_schema


def test_default_snapshot_is_valid():
    print("테스트 1: default snapshot is valid")
    snapshot = build_fixture_snapshot()
    result = validate_snapshot_schema(snapshot)
    assert result.ok is True, result
    assert snapshot["symbol"] == DEFAULT_SYMBOL, snapshot
    assert snapshot["as_of"] == DEFAULT_AS_OF, snapshot
    print("  ✓ default snapshot valid")
    return True


def test_symbol_and_time_overrides():
    print("\n테스트 2: symbol and time overrides")
    snapshot = build_fixture_snapshot(symbol="ISC", as_of="2026-06-11T11:00:00+09:00")
    assert snapshot["symbol"] == "ISC", snapshot
    assert snapshot["as_of"] == "2026-06-11T11:00:00+09:00", snapshot
    assert validate_snapshot_schema(snapshot).ok is True, snapshot
    print("  ✓ symbol and time overridden")
    return True


def test_nested_overrides_preserve_required_keys():
    print("\n테스트 3: nested overrides preserve required keys")
    snapshot = build_fixture_snapshot(
        quote_overrides={"current_price": 50000},
        indicator_overrides={"rsi_30m": 30.1},
        flow_overrides={"brokerage_net_quantity": 12000},
    )
    assert snapshot["quote"]["current_price"] == 50000, snapshot
    assert snapshot["indicators"]["rsi_30m"] == 30.1, snapshot
    assert snapshot["flow"]["brokerage_net_quantity"] == 12000, snapshot
    assert validate_snapshot_schema(snapshot).ok is True, snapshot
    print("  ✓ nested overrides valid")
    return True


def test_none_overrides_are_allowed():
    print("\n테스트 4: None overrides are allowed")
    snapshot = build_fixture_snapshot(
        quote_overrides={"current_price": None},
        indicator_overrides={"rsi_1m": None},
        flow_overrides={"brokerage_net_quantity": None},
    )
    assert snapshot["quote"]["current_price"] is None, snapshot
    assert snapshot["indicators"]["rsi_1m"] is None, snapshot
    assert snapshot["flow"]["brokerage_net_quantity"] is None, snapshot
    assert validate_snapshot_schema(snapshot).ok is True, snapshot
    print("  ✓ None values preserved")
    return True


def test_top_level_overrides_can_create_invalid_fixture_for_negative_tests():
    print("\n테스트 5: top-level override supports negative fixtures")
    snapshot = build_fixture_snapshot(top_level_overrides={"quote": []})
    result = validate_snapshot_schema(snapshot)
    assert result.ok is False, result
    assert "quote must be mapping" in result.errors, result.errors
    print("  ✓ invalid negative fixture can be built")
    return True


def run_all_tests():
    print("=" * 60)
    print("fixture_snapshot_builder.py fixture tests")
    print("=" * 60)

    tests = [
        test_default_snapshot_is_valid,
        test_symbol_and_time_overrides,
        test_nested_overrides_preserve_required_keys,
        test_none_overrides_are_allowed,
        test_top_level_overrides_can_create_invalid_fixture_for_negative_tests,
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
