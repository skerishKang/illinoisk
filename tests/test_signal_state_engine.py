#!/usr/bin/env python3
"""
Fixture-only signal state engine regression tests.

Run:
  python3 tests/test_signal_state_engine.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from fixture_snapshot_builder import build_fixture_snapshot
from signal_state_engine import (
    FUTURES_FLOW_UNAVAILABLE_NOTICE,
    KA10040_RANKING_NOTICE,
    SIGNAL_STATES,
    SignalStateResult,
    evaluate_signal_state,
)


def test_result_shape_and_allowed_states():
    print("테스트 1: result shape and allowed states")
    result = evaluate_signal_state(build_fixture_snapshot())
    data = result.to_dict()

    assert isinstance(result, SignalStateResult), result
    assert result.state in SIGNAL_STATES, result
    assert sorted(data.keys()) == [
        "active_strategy",
        "conflicting_factors",
        "missing_data",
        "near_factors",
        "state",
        "supporting_factors",
    ], data
    print("  ✓ result shape stable")
    return True


def test_rsi_30_and_lower_band_can_be_valid_without_futures_flow():
    print("\n테스트 2: RSI 30 with lower band stays valid without futures flow")
    snapshot = build_fixture_snapshot(
        indicator_overrides={
            "rsi_1m": 42.0,
            "rsi_5m": 38.0,
            "rsi_30m": 29.7,
            "bb_5m_pct": 0.18,
            "bb_30m_pct": 0.40,
            "moving_average_state": "below_short_ma",
        },
        flow_overrides={
            "brokerage_net_quantity_source": "ka10002_or_unavailable",
            "brokerage_net_quantity": None,
            "futures_foreign_institutional_flow": "unavailable",
        },
    )

    result = evaluate_signal_state(snapshot)

    assert result.state == "valid_signal", result
    assert "RSI 30m is at or below 30" in result.supporting_factors, result
    assert "BB 5m pct is near the lower band" in result.supporting_factors, result
    assert FUTURES_FLOW_UNAVAILABLE_NOTICE in result.missing_data, result
    assert "RSI_30" in result.active_strategy, result
    print("  ✓ valid signal preserved")
    return True


def test_near_signal_from_near_rsi_and_near_band():
    print("\n테스트 3: near signal from near RSI and near band")
    snapshot = build_fixture_snapshot(
        indicator_overrides={
            "rsi_1m": 48.0,
            "rsi_5m": 34.5,
            "rsi_30m": 45.0,
            "bb_5m_pct": 0.30,
            "bb_30m_pct": 0.50,
            "moving_average_state": "below_short_ma",
        }
    )

    result = evaluate_signal_state(snapshot)

    assert result.state == "near_signal", result
    assert "RSI 5m is near the oversold threshold" in result.near_factors, result
    assert "BB 5m pct is approaching the lower band" in result.near_factors, result
    print("  ✓ near signal detected")
    return True


def test_negative_brokerage_net_quantity_conflicts_without_abs():
    print("\n테스트 4: negative brokerage net quantity remains negative")
    snapshot = build_fixture_snapshot(
        indicator_overrides={
            "rsi_1m": 44.0,
            "rsi_5m": 38.0,
            "rsi_30m": 29.5,
            "bb_5m_pct": 0.18,
            "bb_30m_pct": 0.38,
            "moving_average_state": "below_short_ma",
        },
        flow_overrides={
            "brokerage_net_quantity_source": "ka10002",
            "brokerage_net_quantity": -15000,
            "futures_foreign_institutional_flow": "unavailable",
        },
    )

    result = evaluate_signal_state(snapshot)

    assert result.state == "conflicted_signal", result
    assert "brokerage net quantity is negative" in result.conflicting_factors, result
    assert "BROKERAGE_NET_BUY" not in result.active_strategy, result
    print("  ✓ signed negative quantity not converted with abs()")
    return True


def test_positive_ka10002_brokerage_net_quantity_supports_signal():
    print("\n테스트 5: positive ka10002 net quantity supports signal")
    snapshot = build_fixture_snapshot(
        indicator_overrides={
            "rsi_1m": 50.0,
            "rsi_5m": 50.0,
            "rsi_30m": 50.0,
            "bb_5m_pct": 0.50,
            "bb_30m_pct": 0.50,
            "moving_average_state": "above_short_ma",
        },
        flow_overrides={
            "brokerage_net_quantity_source": "ka10002",
            "brokerage_net_quantity": 25000,
            "futures_foreign_institutional_flow": "unavailable",
        },
    )

    result = evaluate_signal_state(snapshot)

    assert result.state == "valid_signal", result
    assert "brokerage net quantity is positive" in result.supporting_factors, result
    assert "moving average state supports: above_short_ma" in result.supporting_factors, result
    assert "BROKERAGE_NET_BUY" in result.active_strategy, result
    print("  ✓ positive signed net quantity used")
    return True


def test_ka10040_ranking_is_not_treated_as_net_flow():
    print("\n테스트 6: ka10040 ranking is not net flow")
    snapshot = build_fixture_snapshot(
        indicator_overrides={
            "rsi_1m": 50.0,
            "rsi_5m": 50.0,
            "rsi_30m": 50.0,
            "bb_5m_pct": 0.50,
            "bb_30m_pct": 0.50,
            "moving_average_state": "below_short_ma",
        },
        flow_overrides={
            "brokerage_net_quantity_source": "ka10040_ranking",
            "brokerage_net_quantity": 999999,
            "futures_foreign_institutional_flow": "unavailable",
        },
    )

    result = evaluate_signal_state(snapshot)

    assert result.state == "invalid_signal", result
    assert KA10040_RANKING_NOTICE in result.missing_data, result
    assert "brokerage net quantity is positive" not in result.supporting_factors, result
    assert "BROKERAGE_NET_BUY" not in result.active_strategy, result
    print("  ✓ ranking data ignored as net flow")
    return True


def test_stock_or_program_flow_does_not_substitute_futures_flow():
    print("\n테스트 7: stock/program flow does not replace futures flow")
    snapshot = build_fixture_snapshot(
        indicator_overrides={
            "rsi_1m": 55.0,
            "rsi_5m": 55.0,
            "rsi_30m": 55.0,
            "bb_5m_pct": 0.55,
            "bb_30m_pct": 0.55,
            "moving_average_state": "below_short_ma",
        },
        flow_overrides={
            "brokerage_net_quantity_source": "unavailable",
            "brokerage_net_quantity": None,
            "futures_foreign_institutional_flow": "unavailable",
            "stock_foreign_flow": 999999,
            "program_trading_net": 888888,
        },
    )

    result = evaluate_signal_state(snapshot)

    assert result.state == "invalid_signal", result
    assert FUTURES_FLOW_UNAVAILABLE_NOTICE in result.missing_data, result
    assert not any("stock" in factor.lower() for factor in result.supporting_factors), result
    assert not any("program" in factor.lower() for factor in result.supporting_factors), result
    print("  ✓ unrelated flow fields not substituted")
    return True


def test_invalid_signal_when_data_is_available_but_no_signal_support():
    print("\n테스트 8: invalid when available data has no support")
    snapshot = build_fixture_snapshot(
        indicator_overrides={
            "rsi_1m": 58.0,
            "rsi_5m": 58.0,
            "rsi_30m": 58.0,
            "bb_5m_pct": 0.55,
            "bb_30m_pct": 0.55,
            "moving_average_state": "flat",
        },
        flow_overrides={
            "brokerage_net_quantity_source": "ka10002",
            "brokerage_net_quantity": 0,
            "futures_foreign_institutional_flow": "unavailable",
        },
    )

    result = evaluate_signal_state(snapshot)

    assert result.state == "invalid_signal", result
    assert "moving average state is neutral: flat" in result.missing_data, result
    assert "brokerage net quantity is zero" in result.missing_data, result
    print("  ✓ neutral signal handled deterministically")
    return True


def test_unavailable_when_core_indicator_values_are_missing():
    print("\n테스트 9: unavailable when core indicator values are missing")
    snapshot = build_fixture_snapshot(
        indicator_overrides={
            "rsi_1m": None,
            "rsi_5m": None,
            "rsi_30m": None,
            "bb_5m_pct": None,
            "bb_30m_pct": None,
            "moving_average_state": None,
        },
        flow_overrides={
            "brokerage_net_quantity_source": "ka10002_or_unavailable",
            "brokerage_net_quantity": None,
            "futures_foreign_institutional_flow": "unavailable",
        },
    )

    result = evaluate_signal_state(snapshot)

    assert result.state == "unavailable", result
    assert "RSI 30m unavailable" in result.missing_data, result
    assert "BB 5m pct unavailable" in result.missing_data, result
    assert result.active_strategy == [], result
    print("  ✓ unavailable state returned")
    return True


def run_all_tests():
    print("=" * 60)
    print("signal_state_engine.py fixture tests")
    print("=" * 60)

    tests = [
        test_result_shape_and_allowed_states,
        test_rsi_30_and_lower_band_can_be_valid_without_futures_flow,
        test_near_signal_from_near_rsi_and_near_band,
        test_negative_brokerage_net_quantity_conflicts_without_abs,
        test_positive_ka10002_brokerage_net_quantity_supports_signal,
        test_ka10040_ranking_is_not_treated_as_net_flow,
        test_stock_or_program_flow_does_not_substitute_futures_flow,
        test_invalid_signal_when_data_is_available_but_no_signal_support,
        test_unavailable_when_core_indicator_values_are_missing,
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
