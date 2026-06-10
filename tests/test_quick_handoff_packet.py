#!/usr/bin/env python3
"""
Fixture-only quick handoff packet regression tests.

Run:
  python3 tests/test_quick_handoff_packet.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from quick_handoff_packet import FUTURES_UNAVAILABLE_NOTICE, build_quick_handoff_packet


def fixture_payload():
    return {
        "time_kst": "2026-06-11 10:35 KST",
        "symbol": "HPSP",
        "user_question": "신호 왔어?",
        "route": {
            "message": "신호 왔어?",
            "triggers": ["신호"],
            "intent": "signal_review",
            "symbol": "HPSP",
            "reply_mode": "short_review",
            "used_active_symbol": True,
        },
        "snapshot": {
            "as_of": "2026-06-11T10:35:00+09:00",
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
        },
        "signal_state": "valid_signal",
        "active_strategy": ["RSI_30"],
        "recent_discord_excerpt": [
            "HPSP 지금 어때?",
            "신호 왔어?",
        ],
        "current_model_answer": "신호는 보이지만 시장이 약해서 조심해야 합니다.",
    }


def test_packet_contains_required_sections():
    print("테스트 1: required packet sections")
    packet = build_quick_handoff_packet(fixture_payload())

    required = [
        "# Quick ChatGPT trading review",
        "## Review request",
        "## Trigger route",
        "## Local market snapshot",
        "## Indicators",
        "## Flow",
        "## Recent Discord conversation excerpt",
        "## Current model answer",
        "## Ask ChatGPT",
    ]
    for text in required:
        assert text in packet, f"missing section: {text}"

    print("  ✓ required sections present")
    return True


def test_packet_includes_route_and_snapshot_values():
    print("\n테스트 2: route and snapshot values")
    packet = build_quick_handoff_packet(fixture_payload())

    required = [
        "- Time KST: 2026-06-11 10:35 KST",
        "- Symbol: HPSP",
        "- User question: 신호 왔어?",
        "- Active strategy: RSI_30",
        "- Signal state: valid_signal",
        "- Intent: signal_review",
        "- Triggers: 신호",
        "- Reply mode: short_review",
        "- Used active symbol: true",
        "- Current price: 41250",
        "- RSI 1m: 29.8",
        "- BB 5m pct: 0.18",
    ]
    for text in required:
        assert text in packet, f"missing value: {text}"

    print("  ✓ route and snapshot values present")
    return True


def test_packet_preserves_unavailable_values():
    print("\n테스트 3: unavailable values are explicit")
    packet = build_quick_handoff_packet(fixture_payload())

    assert "- Brokerage net quantity: unavailable" in packet, packet
    assert "- Futures foreign/institutional flow: unavailable" in packet, packet
    assert FUTURES_UNAVAILABLE_NOTICE in packet, packet

    print("  ✓ unavailable values explicit")
    return True


def test_packet_includes_excerpt_model_answer_and_questions():
    print("\n테스트 4: excerpt, model answer, and questions")
    packet = build_quick_handoff_packet(fixture_payload())

    assert "- HPSP 지금 어때?" in packet, packet
    assert "- 신호 왔어?" in packet, packet
    assert "신호는 보이지만 시장이 약해서 조심해야 합니다." in packet, packet
    assert "Is the signal valid" in packet, packet
    assert "What should be checked before the user decides?" in packet, packet

    print("  ✓ excerpt, model answer, and questions present")
    return True


def test_empty_optional_fields_render_unavailable():
    print("\n테스트 5: empty optional fields render unavailable")
    payload = fixture_payload()
    payload["active_strategy"] = []
    payload["recent_discord_excerpt"] = []
    payload["current_model_answer"] = None
    payload["snapshot"]["quote"]["current_price"] = None

    packet = build_quick_handoff_packet(payload)

    assert "- Active strategy: unavailable" in packet, packet
    assert "- Current price: unavailable" in packet, packet
    assert "## Recent Discord conversation excerpt\n- unavailable" in packet, packet
    assert "## Current model answer\nunavailable" in packet, packet

    print("  ✓ empty values rendered unavailable")
    return True


def run_all_tests():
    print("=" * 60)
    print("quick_handoff_packet.py fixture tests")
    print("=" * 60)

    tests = [
        test_packet_contains_required_sections,
        test_packet_includes_route_and_snapshot_values,
        test_packet_preserves_unavailable_values,
        test_packet_includes_excerpt_model_answer_and_questions,
        test_empty_optional_fields_render_unavailable,
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
