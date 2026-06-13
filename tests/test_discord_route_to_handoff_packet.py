#!/usr/bin/env python3
"""
Discord route → quick handoff packet end-to-end fixture flow.

사용자 흐름 단위 회귀 보호:

    Discord식 메시지
      → route_message(...)
        → active symbol / intent / reply_mode 결정
      → build_quick_handoff_packet(...)
        → ChatGPT 검토용 Markdown packet

라우터와 packet builder는 모두 fixture-only, deterministic, side-effect free.
Discord / Kiwoom / OpenAI / network / live market API 연결 없음.

확인 시나리오:
    recent_messages = ["HPSP 지금 어때?"]
    current message = "신호 왔어?"

    route_message(...)
      → symbol: HPSP (최근 메시지에서 active symbol 해석)
      → intent: signal_review ("신호" trigger)
      → reply_mode: short_review
      → used_active_symbol: True
      → triggers: ["신호"]

    build_quick_handoff_packet(...)
      → packet 안에 Symbol / Intent / Triggers / Reply mode / Used active symbol 렌더링
      → Trigger route, Intraday decision, Required response format, Guardrail summary 섹션 포함

실행:
  python3 tests/test_discord_route_to_handoff_packet.py
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

from discord_trigger_router import route_message
from quick_handoff_packet import build_quick_handoff_packet


def test_discord_route_to_handoff_packet_end_to_end():
    """Discord route → quick handoff packet end-to-end 흐름 보호."""
    print("\n테스트 1: Discord route → quick handoff packet end-to-end")

    # 1) 입력: 사용자 메시지 흐름
    recent = ["HPSP 지금 어때?"]
    current = "신호 왔어?"

    # 2) route 단계
    route = route_message(current, recent_messages=recent)

    # 3) route 결과 검증 (Issue #122 핵심 spec)
    assert route.symbol == "HPSP", (
        f"symbol이 'HPSP'가 아님 (recent_messages에서 active symbol 해석 실패?): "
        f"{route.symbol!r}"
    )
    assert route.intent == "signal_review", (
        f"intent가 'signal_review'가 아님: {route.intent!r}"
    )
    assert route.reply_mode == "short_review", (
        f"reply_mode가 'short_review'가 아님: {route.reply_mode!r}"
    )
    assert route.used_active_symbol is True, (
        f"used_active_symbol이 True가 아님: {route.used_active_symbol!r}"
    )
    assert "신호" in route.triggers, (
        f"triggers에 '신호'가 없음: {route.triggers!r}"
    )
    print(
        f"  ✓ route 단계 통과: symbol={route.symbol}, intent={route.intent}, "
        f"reply_mode={route.reply_mode}, used_active_symbol={route.used_active_symbol}, "
        f"triggers={route.triggers}"
    )

    # 4) packet 단계: route 결과를 packet payload에 전달
    payload = {
        "time_kst": "2026-06-13 10:35 KST",
        "symbol": route.symbol,
        "user_question": current,
        "route": route.to_dict(),
        "snapshot": {},
        "current_model_answer": None,
    }
    packet = build_quick_handoff_packet(payload)

    # 5) packet 안에 route 필드들이 렌더링됐는지 확인
    assert "Symbol: HPSP" in packet, "packet에 'Symbol: HPSP' 누락"
    assert "Intent: signal_review" in packet, "packet에 'Intent: signal_review' 누락"
    assert "Reply mode: short_review" in packet, "packet에 'Reply mode: short_review' 누락"
    assert "Used active symbol: true" in packet, (
        "packet에 'Used active symbol: true' 누락 (bool은 소문자로 직렬화됨)"
    )
    assert "Triggers: 신호" in packet, "packet에 'Triggers: 신호' 누락"
    print("  ✓ packet 렌더링 통과: Symbol / Intent / Reply mode / Used active symbol / Triggers")

    # 6) packet 주요 섹션 포함 확인
    for required_section in (
        "## Trigger route",
        "## Intraday decision",
        "## Required response format",
        "## Guardrail summary",
    ):
        assert required_section in packet, (
            f"packet에 필수 섹션 누락: {required_section}"
        )
    print("  ✓ packet 섹션 통과: Trigger route / Intraday decision / Required response format / Guardrail summary")

    return True


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("Discord route → quick handoff packet end-to-end fixture flow")
    print("=" * 60)

    tests = [
        test_discord_route_to_handoff_packet_end_to_end,
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
