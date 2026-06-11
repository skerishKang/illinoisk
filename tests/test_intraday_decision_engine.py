#!/usr/bin/env python3
"""
Fixture-only intraday decision engine regression tests.

Run:
  python3 tests/test_intraday_decision_engine.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from fixture_snapshot_builder import build_fixture_snapshot
from signal_state_engine import evaluate_signal_state
from intraday_decision_engine import (
    DECISION_TYPES,
    SIGNAL_TO_DECISION,
    IntradayDecisionResult,
    evaluate_intraday_decision,
)


def valid_signal_snapshot(quote_overrides=None):
    return build_fixture_snapshot(
        quote_overrides=quote_overrides,
        indicator_overrides={
            "rsi_1m": 29.5,
            "rsi_5m": 35.0,
            "rsi_30m": 28.0,
            "bb_5m_pct": 0.15,
            "bb_30m_pct": 0.35,
            "moving_average_state": "below_short_ma",
        },
        flow_overrides={
            "brokerage_net_quantity_source": "ka10002",
            "brokerage_net_quantity": 25000,
            "futures_foreign_institutional_flow": "unavailable",
        },
    )


def test_result_shape_and_allowed_decisions():
    print("테스트 1: result shape and allowed decisions")
    snapshot = build_fixture_snapshot()
    signal_result = evaluate_signal_state(snapshot)
    result = evaluate_intraday_decision(signal_result, snapshot=snapshot)

    assert isinstance(result, IntradayDecisionResult), result
    assert result.decision in DECISION_TYPES, result
    assert isinstance(result.strength, str), result
    assert isinstance(result.reasons, list), result
    assert isinstance(result.missing_data, list), result
    assert isinstance(result.entry_conditions, list), result
    assert isinstance(result.invalid_conditions, list), result
    assert result.stop_reference is None or isinstance(result.stop_reference, str), result
    assert result.take_profit_reference is None or isinstance(result.take_profit_reference, str), result

    data = result.to_dict()
    assert set(data.keys()) == {
        "decision",
        "strength",
        "reasons",
        "missing_data",
        "entry_conditions",
        "invalid_conditions",
        "stop_reference",
        "take_profit_reference",
    }, data
    print("  ✓ result shape stable")
    return True


def test_valid_signal_maps_to_진입_without_snapshot_risk_gate():
    print("\n테스트 2: valid_signal maps to 진입 without snapshot risk gate")
    snapshot = valid_signal_snapshot()

    signal_result = evaluate_signal_state(snapshot)
    assert signal_result.state == "valid_signal", signal_result

    result = evaluate_intraday_decision(signal_result)

    assert result.decision == "진입", result
    assert result.strength in ("강함", "보통", "약함"), result
    assert len(result.reasons) > 0, result
    assert "지원 요인" in " ".join(result.reasons), result
    assert len(result.entry_conditions) > 0, result
    assert result.stop_reference is not None, result
    assert "RSI 30m" in result.stop_reference, result
    assert result.take_profit_reference is None, result
    print(f"  ✓ decision={result.decision}, strength={result.strength}, stop_ref={result.stop_reference}")
    return True


def test_valid_signal_with_acceptable_risk_reward_stays_진입():
    print("\n테스트 3: valid_signal with acceptable risk/reward stays 진입")
    snapshot = valid_signal_snapshot(
        quote_overrides={
            "high_to_current_pct": -3.2,
            "low_to_current_pct": 1.4,
        }
    )
    signal_result = evaluate_signal_state(snapshot)
    result = evaluate_intraday_decision(signal_result, snapshot=snapshot)

    assert result.decision == "진입", result
    assert any("risk/reward gate passed" in c for c in result.entry_conditions), result
    assert result.stop_reference == "intraday low reference; estimated stop distance 1.40%", result
    assert result.take_profit_reference == "recent intraday high reference; estimated upside 3.20%", result
    print("  ✓ risk/reward gate passed and references rendered")
    return True


def test_late_chase_valid_signal_downgrades_to_대기():
    print("\n테스트 4: late-chase valid_signal downgrades to 대기")
    snapshot = valid_signal_snapshot(
        quote_overrides={
            "high_to_current_pct": -0.3,
            "low_to_current_pct": 1.8,
        }
    )
    signal_result = evaluate_signal_state(snapshot)
    result = evaluate_intraday_decision(signal_result, snapshot=snapshot)

    assert result.decision == "대기", result
    assert any("당일 고점 근처 추격" in reason for reason in result.reasons), result
    assert any("late-chase guard" in item for item in result.invalid_conditions), result
    assert result.stop_reference == "intraday low reference; estimated stop distance 1.80%", result
    assert result.take_profit_reference == "recent intraday high reference; estimated upside 0.30%", result
    print("  ✓ late-chase guard waits instead of entering")
    return True


def test_wide_stop_valid_signal_maps_to_제외():
    print("\n테스트 5: wide stop valid_signal maps to 제외")
    snapshot = valid_signal_snapshot(
        quote_overrides={
            "high_to_current_pct": -5.5,
            "low_to_current_pct": 3.4,
        }
    )
    signal_result = evaluate_signal_state(snapshot)
    result = evaluate_intraday_decision(signal_result, snapshot=snapshot)

    assert result.decision == "제외", result
    assert any("손절폭" in reason for reason in result.reasons), result
    assert any("stop distance too wide" in item for item in result.invalid_conditions), result
    assert result.stop_reference is None, result
    assert result.take_profit_reference is None, result
    print("  ✓ wide stop distance excludes entry")
    return True


def test_unfavorable_reward_risk_valid_signal_maps_to_제외():
    print("\n테스트 6: unfavorable reward/risk valid_signal maps to 제외")
    snapshot = valid_signal_snapshot(
        quote_overrides={
            "high_to_current_pct": -1.0,
            "low_to_current_pct": 2.0,
        }
    )
    signal_result = evaluate_signal_state(snapshot)
    result = evaluate_intraday_decision(signal_result, snapshot=snapshot)

    assert result.decision == "제외", result
    assert any("기대수익이 손실위험보다 크지 않음" in reason for reason in result.reasons), result
    assert any("expected upside must exceed downside risk" in item for item in result.invalid_conditions), result
    print("  ✓ unfavorable reward/risk excludes entry")
    return True


def test_near_signal_maps_to_대기():
    print("\n테스트 7: near_signal maps to 대기")
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

    signal_result = evaluate_signal_state(snapshot)
    assert signal_result.state == "near_signal", signal_result

    result = evaluate_intraday_decision(signal_result, snapshot=snapshot)

    assert result.decision == "대기", result
    assert result.strength in ("강함", "보통", "약함"), result
    assert len(result.reasons) > 0, result
    assert "접근 요인" in " ".join(result.reasons), result
    assert result.stop_reference is not None, result
    assert "estimated stop distance" in result.stop_reference, result
    assert result.take_profit_reference is not None, result
    print(f"  ✓ decision={result.decision}, strength={result.strength}")
    return True


def test_conflicted_signal_maps_to_보류():
    print("\n테스트 8: conflicted_signal maps to 보류")
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

    signal_result = evaluate_signal_state(snapshot)
    assert signal_result.state == "conflicted_signal", signal_result

    result = evaluate_intraday_decision(signal_result, snapshot=snapshot)

    assert result.decision == "보류", result
    assert len(result.reasons) > 0, result
    assert any("충돌" in r for r in result.reasons), result
    assert len(result.invalid_conditions) > 0, result
    assert result.stop_reference is None, result
    assert result.take_profit_reference is None, result
    print(f"  ✓ decision={result.decision}, strength={result.strength}")
    return True


def test_invalid_signal_maps_to_제외():
    print("\n테스트 9: invalid_signal maps to 제외")
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

    signal_result = evaluate_signal_state(snapshot)
    assert signal_result.state == "invalid_signal", signal_result

    result = evaluate_intraday_decision(signal_result, snapshot=snapshot)

    assert result.decision == "제외", result
    assert result.strength == "해당없음", result
    assert len(result.reasons) > 0, result
    assert "신호 불충분" in " ".join(result.reasons) or "지원" in " ".join(result.reasons), result
    assert len(result.invalid_conditions) > 0, result
    assert result.stop_reference is None, result
    assert result.take_profit_reference is None, result
    print(f"  ✓ decision={result.decision}, strength={result.strength}")
    return True


def test_unavailable_maps_to_제외():
    print("\n테스트 10: unavailable maps to 제외")
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

    signal_result = evaluate_signal_state(snapshot)
    assert signal_result.state == "unavailable", signal_result

    result = evaluate_intraday_decision(signal_result, snapshot=snapshot)

    assert result.decision == "제외", result
    assert result.strength == "해당없음", result
    assert len(result.reasons) > 0, result
    assert "데이터 불충분" in " ".join(result.reasons), result
    assert len(result.missing_data) > 0, result
    assert result.stop_reference is None, result
    assert result.take_profit_reference is None, result
    print(f"  ✓ decision={result.decision}, strength={result.strength}")
    return True


def test_all_signal_states_mapped():
    print("\n테스트 11: all SIGNAL_STATES have DECISION mapping")
    for state in ("valid_signal", "near_signal", "conflicted_signal", "invalid_signal", "unavailable"):
        assert state in SIGNAL_TO_DECISION, f"Missing mapping for {state}"
        assert SIGNAL_TO_DECISION[state] in DECISION_TYPES, f"Invalid decision for {state}"
    print("  ✓ all states mapped")
    return True


def test_dedupe_in_output_lists():
    print("\n테스트 12: output lists are deduplicated")
    # Create a snapshot that would produce duplicate factors
    snapshot = build_fixture_snapshot(
        indicator_overrides={
            "rsi_1m": 29.0,
            "rsi_5m": 29.0,
            "rsi_30m": 29.0,
            "bb_5m_pct": 0.10,
            "bb_30m_pct": 0.10,
            "moving_average_state": "above_short_ma",
        },
        flow_overrides={
            "brokerage_net_quantity_source": "ka10002",
            "brokerage_net_quantity": 25000,
            "futures_foreign_institutional_flow": "unavailable",
        },
    )

    signal_result = evaluate_signal_state(snapshot)
    result = evaluate_intraday_decision(signal_result, snapshot=snapshot)

    # Check no duplicates in lists
    for field_name in ["reasons", "missing_data", "entry_conditions", "invalid_conditions"]:
        field_value = getattr(result, field_name)
        assert len(field_value) == len(set(field_value)), f"Duplicates in {field_name}: {field_value}"
    print("  ✓ all lists deduplicated")
    return True


def run_all_tests():
    print("=" * 60)
    print("intraday_decision_engine.py fixture tests")
    print("=" * 60)

    tests = [
        test_result_shape_and_allowed_decisions,
        test_valid_signal_maps_to_진입_without_snapshot_risk_gate,
        test_valid_signal_with_acceptable_risk_reward_stays_진입,
        test_late_chase_valid_signal_downgrades_to_대기,
        test_wide_stop_valid_signal_maps_to_제외,
        test_unfavorable_reward_risk_valid_signal_maps_to_제외,
        test_near_signal_maps_to_대기,
        test_conflicted_signal_maps_to_보류,
        test_invalid_signal_maps_to_제외,
        test_unavailable_maps_to_제외,
        test_all_signal_states_mapped,
        test_dedupe_in_output_lists,
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
