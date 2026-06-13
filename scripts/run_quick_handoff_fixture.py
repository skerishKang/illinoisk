#!/usr/bin/env python3
"""
Local quick handoff fixture scenario catalog runner.

사람이 직접 로컬에서 handoff packet을 눈으로 확인할 수 있는 실행 흐름을 제공합니다.

    Discord식 메시지
      → route_message(...)
      → build_quick_handoff_packet(...)
      → Markdown packet을 stdout으로 출력

이 스크립트는 side-effect free합니다. 서버 실행, 외부 서비스 연결,
실시간 시세 호출, 모델 호출, 파일 쓰기, 주문 실행 등을 하지 않습니다.

실행 예시:

    python3 scripts/run_quick_handoff_fixture.py --list-scenarios
    python3 scripts/run_quick_handoff_fixture.py --summary-scenarios
    python3 scripts/run_quick_handoff_fixture.py --scenario active-symbol-signal
    python3 scripts/run_quick_handoff_fixture.py --scenario explicit-symbol-entry
    python3 scripts/run_quick_handoff_fixture.py --scenario active-symbol-stop
    python3 scripts/run_quick_handoff_fixture.py --all-scenarios
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
    "explicit-symbol-entry": {
        "recent_messages": None,
        "message": "HPSP 지금 진입해도 돼?",
        "active_symbol": None,
        "time_kst": "2026-06-13 10:35 KST",
    },
    "active-symbol-stop": {
        "recent_messages": ["HPSP 지금 어때?"],
        "message": "손절 기준 알려줘",
        "active_symbol": None,
        "time_kst": "2026-06-13 10:35 KST",
    },
}


def route_scenario(scenario: dict):
    """시나리오 dict를 받아 Discord-style message routing 결과를 반환한다."""
    return route_message(
        scenario["message"],
        active_symbol=scenario.get("active_symbol"),
        recent_messages=scenario.get("recent_messages"),
    )


def run_scenario(scenario: dict) -> str:
    """시나리오 dict를 받아 route → packet으로 변환한 Markdown 문자열을 반환한다."""
    route = route_scenario(scenario)
    payload = {
        "time_kst": scenario.get("time_kst", "unavailable"),
        "symbol": route.symbol or "unavailable",
        "user_question": scenario["message"],
        "route": route.to_dict(),
        "snapshot": {},
        "current_model_answer": None,
    }
    return build_quick_handoff_packet(payload)


def _format_summary_value(value) -> str:
    """summary table에서 bool/list/None 값을 사람이 읽기 좋은 deterministic 문자열로 바꾼다."""
    if value is None:
        return "unavailable"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        if not value:
            return "none"
        return ",".join(str(item) for item in value)
    return str(value)


def list_scenarios() -> str:
    """Available 시나리오 목록을 deterministic(sorted) 문자열로 반환한다."""
    lines = ["Available scenarios:"]
    for name in sorted(SCENARIOS):
        lines.append(f"  {name}")
    return "\n".join(lines)


def summarize_scenarios() -> str:
    """모든 built-in scenario의 route 결과를 sorted 순서의 compact table로 반환한다."""
    lines = [
        "Scenario summary:",
        "scenario | symbol | user_question | intent | triggers | reply_mode | used_active_symbol",
        "--- | --- | --- | --- | --- | --- | ---",
    ]
    for name in sorted(SCENARIOS):
        scenario = SCENARIOS[name]
        route = route_scenario(scenario)
        route_dict = route.to_dict()
        values = [
            name,
            route_dict.get("symbol", route.symbol or "unavailable"),
            scenario["message"],
            route_dict.get("intent"),
            route_dict.get("triggers", route_dict.get("trigger")),
            route_dict.get("reply_mode"),
            route_dict.get("used_active_symbol"),
        ]
        lines.append(" | ".join(_format_summary_value(value) for value in values))
    return "\n".join(lines)


def run_all_scenarios() -> str:
    """모든 built-in scenario를 sorted 순서로 실행하고 packet들을 header로 묶어 반환한다.

    출력 형식:
        ===== Scenario: <name> =====
        <packet>

        ===== Scenario: <name> =====
        <packet>
        ...
    """
    blocks: list[str] = []
    for name in sorted(SCENARIOS):
        blocks.append(f"===== Scenario: {name} =====")
        blocks.append(run_scenario(SCENARIOS[name]))
        blocks.append("")  # scenario 사이 빈 줄
    # 마지막 빈 줄은 strip하여 출력 끝의 불필요한 개행 1개로 마무리
    return "\n".join(blocks).rstrip("\n") + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a local quick handoff packet from a fixture scenario and print it to stdout."
        )
    )
    parser.add_argument(
        "--scenario",
        default=None,
        help=(
            "Fixture scenario name to run. "
            f"Available: {', '.join(sorted(SCENARIOS))}"
        ),
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="Print the deterministic list of available scenario names and exit.",
    )
    parser.add_argument(
        "--summary-scenarios",
        action="store_true",
        help=(
            "Route every built-in scenario in sorted order and print a compact "
            "summary table. Exits with 0 on success."
        ),
    )
    parser.add_argument(
        "--all-scenarios",
        action="store_true",
        help=(
            "Run every built-in scenario in sorted order and print each packet "
            "with a header separator. Exits with 0 on success."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_scenarios:
        print(list_scenarios())
        return 0

    if args.summary_scenarios:
        print(summarize_scenarios())
        return 0

    if args.all_scenarios:
        print(run_all_scenarios(), end="")
        return 0

    if not args.scenario:
        parser.error(
            "either --scenario NAME, --summary-scenarios, --all-scenarios, or --list-scenarios is required"
        )

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
