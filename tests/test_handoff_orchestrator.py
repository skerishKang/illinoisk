#!/usr/bin/env python3
"""
Fixture-only handoff orchestrator regression tests.

Run:
  python3 tests/test_handoff_orchestrator.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from handoff_orchestrator import build_handoff_from_message
from quick_handoff_packet import FUTURES_UNAVAILABLE_NOTICE


def fixture_snapshot(symbol="HPSP"):
    return {
        "as_of": "2026-06-11T10:35:00+09:00",
        "symbol": symbol,
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


def test_orchestrator_routes_recent_symbol_followup():
    print("테스트 1: recent symbol follow-up routes into packet")
    result = build_handoff_from_message(
        {
            "message": "신호 왔어?",
            "recent_messages": ["HPSP 지금 어때?", "신호 왔어?"],
            "snapshot": fixture_snapshot(),
            "current_model_answer": "신호는 보이지만 시장이 약해서 조심해야 합니다.",
            "signal_state": "valid_signal",
            "active_strategy": ["RSI_30"],
            "time_kst": "2026-06-11 10:35 KST",
        }
    )

    assert result.symbol == "HPSP", result
    assert result.route["intent"] == "signal_review", result.route
    assert result.route["used_active_symbol"] is True, result.route
    assert "- Symbol: HPSP" in result.packet_markdown, result.packet_markdown
    assert "- Signal state: valid_signal" in result.packet_markdown, result.packet_markdown
    assert "- Active strategy: RSI_30" in result.packet_markdown, result.packet_markdown
    assert "- HPSP 지금 어때?" in result.packet_markdown, result.packet_markdown
    print("  ✓ follow-up routed and packet generated")
    return True


def test_orchestrator_prefers_explicit_symbol_over_snapshot_symbol():
    print("\n테스트 2: explicit symbol beats snapshot symbol fallback")
    result = build_handoff_from_message(
        {
            "message": "ISC 진입 가능?",
            "recent_messages": ["HPSP 지금 어때?"],
            "snapshot": fixture_snapshot(symbol="HPSP"),
            "current_model_answer": "진입은 아직 확인이 필요합니다.",
            "signal_state": "near_signal",
        }
    )

    assert result.symbol == "ISC", result
    assert result.route["intent"] == "entry_check", result.route
    assert "- Symbol: ISC" in result.packet_markdown, result.packet_markdown
    assert "- Signal state: near_signal" in result.packet_markdown, result.packet_markdown
    print("  ✓ explicit symbol used")
    return True


def test_orchestrator_uses_snapshot_symbol_when_route_has_no_symbol():
    print("\n테스트 3: snapshot symbol fallback")
    result = build_handoff_from_message(
        {
            "message": "오늘 시장이 애매하네",
            "snapshot": fixture_snapshot(symbol="두산테스나"),
            "current_model_answer": None,
        }
    )

    assert result.symbol == "두산테스나", result
    assert result.route["intent"] == "no_action", result.route
    assert "- Symbol: 두산테스나" in result.packet_markdown, result.packet_markdown
    assert "## Current model answer\nunavailable" in result.packet_markdown, result.packet_markdown
    print("  ✓ snapshot symbol fallback used")
    return True


def test_orchestrator_preserves_unavailable_flow_notice():
    print("\n테스트 4: unavailable flow notice preserved")
    result = build_handoff_from_message(
        {
            "message": "수급 봐줘",
            "active_symbol": "HPSP",
            "snapshot": fixture_snapshot(),
        }
    )

    assert "- Brokerage net quantity: unavailable" in result.packet_markdown, result.packet_markdown
    assert "- Futures foreign/institutional flow: unavailable" in result.packet_markdown, result.packet_markdown
    assert FUTURES_UNAVAILABLE_NOTICE in result.packet_markdown, result.packet_markdown
    print("  ✓ unavailable flow notice preserved")
    return True


def test_orchestrator_to_dict_shape():
    print("\n테스트 5: result to_dict shape")
    result = build_handoff_from_message(
        {
            "message": "손절은?",
            "active_symbol": "HPSP",
            "snapshot": fixture_snapshot(),
        }
    ).to_dict()

    assert sorted(result.keys()) == ["packet_markdown", "route", "symbol"], result
    assert result["symbol"] == "HPSP", result
    assert result["route"]["intent"] == "stop_check", result
    assert "# Quick ChatGPT trading review" in result["packet_markdown"], result
    print("  ✓ result dict shape stable")
    return True


def run_all_tests():
    print("=" * 60)
    print("handoff_orchestrator.py fixture tests")
    print("=" * 60)

    tests = [
        test_orchestrator_routes_recent_symbol_followup,
        test_orchestrator_prefers_explicit_symbol_over_snapshot_symbol,
        test_orchestrator_uses_snapshot_symbol_when_route_has_no_symbol,
        test_orchestrator_preserves_unavailable_flow_notice,
        test_orchestrator_to_dict_shape,
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
