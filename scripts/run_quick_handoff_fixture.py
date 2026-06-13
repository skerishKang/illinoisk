#!/usr/bin/env python3
"""
Local quick handoff fixture runner.

사람이 직접 로컬에서 handoff packet을 눈으로 확인할 수 있는 실행 흐름을 제공합니다.

    Discord식 메시지
      → route_message(...)
      → build_quick_handoff_packet(...)
      → Markdown packet을 stdout으로 출력

이 스크립트는 side-effect free합니다. 서버 실행, 외부 서비스 연결,
실시간 시세 호출, 모델 호출, 파일 쓰기, 주문 실행 등을 하지 않습니다.

실행 예시:

    python3 scripts/run_quick_handoff_fixture.py --scenario active-symbol-signal
"""
from __future__ import annotations

import argparse
import os
import sys

# scripts/ 안의 sibling 모듈 (discord_trigger_router, quick_handoff_packet) import 지원
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from discord_trigger_router import route_message
from quick_handoff_packet import build_quick_handoff_packet


SCENARIOS: dict[str, dict] = {
    "active-symbol-signal": {
        "recent_messages": ["HPSP 지금 어때?"],
        "message": "신호 왔어?",
        "active_symbol": None,
        "time_kst": "2026-06-13 10:35 KST",
    },
}


def run_scenario(scenario: dict) -> str:
    """시나리오 dict를 받아 route → packet으로 변환한 Markdown 문자열을 반환한다."""
    route = route_message(
        scenario["message"],
        active_symbol=scenario.get("active_symbol"),
        recent_messages=scenario.get("recent_messages"),
    )
    payload = {
        "time_kst": scenario.get("time_kst", "unavailable"),
        "symbol": route.symbol or "unavailable",
        "user_question": scenario["message"],
        "route": route.to_dict(),
        "snapshot": {},
        "current_model_answer": None,
    }
    return build_quick_handoff_packet(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a local quick handoff packet from a fixture scenario and print it to stdout."
        )
    )
    parser.add_argument(
        "--scenario",
        required=True,
        help=(
            "Fixture scenario name. "
            f"Available: {', '.join(sorted(SCENARIOS))}"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.scenario not in SCENARIOS:
        print(
            f"unknown scenario: {args.scenario}",
            file=sys.stderr,
        )
        print(
            f"available scenarios: {', '.join(sorted(SCENARIOS))}",
            file=sys.stderr,
        )
        return 2

    print(run_scenario(SCENARIOS[args.scenario]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
