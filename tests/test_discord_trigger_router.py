#!/usr/bin/env python3
"""
Fixture-only Discord trigger router regression tests.

Run:
  python3 tests/test_discord_trigger_router.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from discord_trigger_router import resolve_active_symbol, route_message


def assert_route(
    message,
    *,
    intent,
    symbol,
    reply_mode,
    active_symbol=None,
    recent_messages=None,
    used_active_symbol=False,
):
    result = route_message(
        message,
        active_symbol=active_symbol,
        recent_messages=recent_messages,
    ).to_dict()
    assert result["intent"] == intent, f"intent mismatch for {message!r}: {result}"
    assert result["symbol"] == symbol, f"symbol mismatch for {message!r}: {result}"
    assert result["reply_mode"] == reply_mode, f"reply_mode mismatch for {message!r}: {result}"
    assert result["used_active_symbol"] is used_active_symbol, (
        f"used_active_symbol mismatch for {message!r}: {result}"
    )
    return result


def test_symbol_signal_short_review():
    print("테스트 1: symbol + 신호 -> signal_review")
    result = assert_route(
        "HPSP 신호 왔어?",
        intent="signal_review",
        symbol="HPSP",
        reply_mode="short_review",
    )
    assert result["triggers"] == ["신호"], f"unexpected triggers: {result}"
    print("  ✓ HPSP signal routed")
    return True


def test_korean_symbol_entry_check():
    print("\n테스트 2: Korean symbol + 진입 -> entry_check")
    result = assert_route(
        "두산테스나 진입",
        intent="entry_check",
        symbol="두산테스나",
        reply_mode="short_review",
    )
    assert result["triggers"] == ["진입"], f"unexpected triggers: {result}"
    print("  ✓ Korean symbol entry routed")
    return True


def test_followup_uses_active_symbol():
    print("\n테스트 3: no-symbol follow-up uses active symbol")
    result = assert_route(
        "신호 왔어?",
        active_symbol="HPSP",
        intent="signal_review",
        symbol="HPSP",
        reply_mode="short_review",
        used_active_symbol=True,
    )
    assert result["triggers"] == ["신호"], f"unexpected triggers: {result}"
    print("  ✓ active symbol used")
    return True


def test_broad_market_without_symbol_offers_market_review():
    print("\n테스트 4: broad market trigger without symbol avoids stock-specific review")
    result = assert_route(
        "코스피 위험해?",
        intent="risk_review",
        symbol=None,
        reply_mode="offer_market_review",
    )
    assert result["triggers"] == ["위험"], f"unexpected triggers: {result}"
    print("  ✓ broad market routed as market review")
    return True


def test_no_trigger_stays_quiet():
    print("\n테스트 5: no trigger stays quiet")
    result = assert_route(
        "오늘 시장이 애매하네",
        intent="no_action",
        symbol=None,
        reply_mode="stay_quiet",
    )
    assert result["triggers"] == [], f"unexpected triggers: {result}"
    print("  ✓ no trigger stays quiet")
    return True


def test_chatgpt_handoff_priority():
    print("\n테스트 6: GPT trigger has handoff priority")
    result = assert_route(
        "HPSP GPT 검토해줘",
        intent="chatgpt_handoff",
        symbol="HPSP",
        reply_mode="build_handoff_packet",
    )
    assert "GPT" in result["triggers"], f"missing GPT trigger: {result}"
    assert "검토" in result["triggers"], f"missing 검토 trigger: {result}"
    print("  ✓ GPT handoff priority locked")
    return True


def test_resolve_active_symbol_from_recent_messages():
    print("\n테스트 7: recent messages resolve active symbol")
    resolution = resolve_active_symbol([
        "HPSP 지금 어때?",
        "모델 답변은 대기",
    ])
    assert resolution.active_symbol == "HPSP", f"unexpected resolution: {resolution}"
    assert resolution.source == "explicit_symbol", f"unexpected source: {resolution}"

    routed = assert_route(
        "손절은?",
        recent_messages=["HPSP 지금 어때?"],
        intent="stop_check",
        symbol="HPSP",
        reply_mode="short_review",
        used_active_symbol=True,
    )
    assert routed["triggers"] == ["손절"], f"unexpected triggers: {routed}"
    print("  ✓ recent message active symbol used")
    return True


def test_broad_market_does_not_switch_active_symbol():
    print("\n테스트 8: broad market-only message does not switch active symbol")
    resolution = resolve_active_symbol(
        ["코스피랑 선물 위험해?"],
        current_active_symbol="HPSP",
    )
    assert resolution.active_symbol == "HPSP", f"broad market switched symbol: {resolution}"
    assert resolution.source == "provided", f"unexpected source: {resolution}"

    routed = assert_route(
        "신호 왔어?",
        active_symbol="HPSP",
        recent_messages=["코스피랑 선물 위험해?"],
        intent="signal_review",
        symbol="HPSP",
        reply_mode="short_review",
        used_active_symbol=True,
    )
    assert routed["triggers"] == ["신호"], f"unexpected triggers: {routed}"
    print("  ✓ broad market message preserved active symbol")
    return True


def test_model_comparison_does_not_switch_active_symbol():
    print("\n테스트 9: model comparison text does not switch active symbol")
    resolution = resolve_active_symbol(
        ["GPT 답변이랑 HPSP 모델 비교해봐"],
        current_active_symbol="두산테스나",
    )
    assert resolution.active_symbol == "두산테스나", f"model comparison switched symbol: {resolution}"
    assert resolution.source == "provided", f"unexpected source: {resolution}"
    print("  ✓ model comparison did not switch active symbol")
    return True


def test_focus_switch_updates_active_symbol():
    print("\n테스트 10: focus-switch message updates active symbol")
    resolution = resolve_active_symbol(
        ["다음은 ISC 봐줘"],
        current_active_symbol="HPSP",
    )
    assert resolution.active_symbol == "ISC", f"focus switch failed: {resolution}"
    assert resolution.source == "focus_switch", f"unexpected source: {resolution}"

    routed = assert_route(
        "진입 가능?",
        active_symbol="HPSP",
        recent_messages=["다음은 ISC 봐줘"],
        intent="entry_check",
        symbol="ISC",
        reply_mode="short_review",
        used_active_symbol=True,
    )
    assert routed["triggers"] == ["진입"], f"unexpected triggers: {routed}"
    print("  ✓ focus switch updated active symbol")
    return True


def run_all_tests():
    print("=" * 60)
    print("discord_trigger_router.py fixture tests")
    print("=" * 60)

    tests = [
        test_symbol_signal_short_review,
        test_korean_symbol_entry_check,
        test_followup_uses_active_symbol,
        test_broad_market_without_symbol_offers_market_review,
        test_no_trigger_stays_quiet,
        test_chatgpt_handoff_priority,
        test_resolve_active_symbol_from_recent_messages,
        test_broad_market_does_not_switch_active_symbol,
        test_model_comparison_does_not_switch_active_symbol,
        test_focus_switch_updates_active_symbol,
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
