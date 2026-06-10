#!/usr/bin/env python3
"""
Fixture-only snapshot schema validator regression tests.

Run:
  python3 tests/test_snapshot_schema_validator.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from snapshot_schema_validator import require_valid_snapshot_schema, validate_snapshot_schema


def valid_snapshot():
    return {
        "as_of": "2026-06-11T10:35:00+09:00",
        "symbol": "HPSP",
        "quote": {
            "current_price": 41250,
            "previous_close_change_pct": -1.2,
            "open_or_candle_change_pct": 0.4,
            "high_to_current_pct": -2.1,
            "low_to_current_pct": 1.8,
            "volume": 1250000,
            "source": "fixture",
        },
        "indicators": {
            "rsi_1m": 29.8,
            "rsi_5m": 34.2,
            "rsi_30m": 41.0,
            "bb_5m_pct": 0.18,
            "bb_30m_pct": 0.42,
            "moving_average_state": "below_short_ma",
        },
        "flow": {
            "brokerage_net_quantity_source": "ka10002_or_unavailable",
            "brokerage_net_quantity": None,
            "futures_foreign_institutional_flow": "unavailable",
        },
    }


def test_valid_snapshot_passes():
    print("테스트 1: valid snapshot passes")
    result = validate_snapshot_schema(valid_snapshot())
    assert result.ok is True, result
    assert result.errors == [], result
    assert result.to_dict() == {"ok": True, "errors": []}, result.to_dict()
    print("  ✓ valid snapshot accepted")
    return True


def test_missing_top_level_key_fails():
    print("\n테스트 2: missing top-level key fails")
    snapshot = valid_snapshot()
    del snapshot["quote"]
    result = validate_snapshot_schema(snapshot)
    assert result.ok is False, result
    assert "missing snapshot.quote" in result.errors, result.errors
    print("  ✓ missing top-level key detected")
    return True


def test_non_mapping_sections_fail():
    print("\n테스트 3: non-mapping sections fail")
    snapshot = valid_snapshot()
    snapshot["indicators"] = []
    result = validate_snapshot_schema(snapshot)
    assert result.ok is False, result
    assert "indicators must be mapping" in result.errors, result.errors
    print("  ✓ non-mapping section detected")
    return True


def test_missing_nested_keys_fail():
    print("\n테스트 4: missing nested keys fail")
    snapshot = valid_snapshot()
    del snapshot["quote"]["current_price"]
    del snapshot["indicators"]["rsi_30m"]
    del snapshot["flow"]["brokerage_net_quantity"]
    result = validate_snapshot_schema(snapshot)
    assert result.ok is False, result
    assert "missing quote.current_price" in result.errors, result.errors
    assert "missing indicators.rsi_30m" in result.errors, result.errors
    assert "missing flow.brokerage_net_quantity" in result.errors, result.errors
    print("  ✓ missing nested keys detected")
    return True


def test_unavailable_values_are_allowed():
    print("\n테스트 5: unavailable values are allowed")
    snapshot = valid_snapshot()
    snapshot["quote"]["current_price"] = None
    snapshot["indicators"]["rsi_1m"] = None
    snapshot["flow"]["brokerage_net_quantity"] = None
    result = validate_snapshot_schema(snapshot)
    assert result.ok is True, result
    print("  ✓ unavailable values accepted")
    return True


def test_require_valid_snapshot_schema_reports_errors():
    print("\n테스트 6: require_valid_snapshot_schema reports errors")
    snapshot = valid_snapshot()
    del snapshot["symbol"]
    del snapshot["flow"]["futures_foreign_institutional_flow"]
    try:
        require_valid_snapshot_schema(snapshot)
    except ValueError as exc:
        message = str(exc)
        assert "missing snapshot.symbol" in message, message
        assert "missing flow.futures_foreign_institutional_flow" in message, message
        print("  ✓ error message includes expected entries")
        return True
    raise AssertionError("expected validation error")


def test_non_mapping_snapshot_fails():
    print("\n테스트 7: non-mapping snapshot fails")
    result = validate_snapshot_schema([])
    assert result.ok is False, result
    assert result.errors == ["snapshot must be mapping"], result.errors
    print("  ✓ non-mapping snapshot rejected")
    return True


def run_all_tests():
    print("=" * 60)
    print("snapshot_schema_validator.py fixture tests")
    print("=" * 60)

    tests = [
        test_valid_snapshot_passes,
        test_missing_top_level_key_fails,
        test_non_mapping_sections_fail,
        test_missing_nested_keys_fail,
        test_unavailable_values_are_allowed,
        test_require_valid_snapshot_schema_reports_errors,
        test_non_mapping_snapshot_fails,
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
