#!/usr/bin/env python3
"""
Local full handoff fixture scenario runner.

사람이 직접 로컬에서 full ChatGPT handoff packet을 눈으로 확인할 수 있는
stdout-only 실행 흐름을 제공합니다.

이 스크립트는 side-effect free합니다. 서버 실행, 외부 서비스 연결,
실시간 시세 호출, 모델 호출, 파일 쓰기, 주문 실행 등을 하지 않습니다.

실행 예시:

    python3 scripts/run_full_handoff_fixture.py --list-scenarios
    python3 scripts/run_full_handoff_fixture.py --scenario active-symbol-signal
    python3 scripts/run_full_handoff_fixture.py --all-scenarios
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

# scripts/ 안의 sibling 모듈 import 지원
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_quick_handoff_fixture import SCENARIOS, list_scenarios, route_scenario


APPLICABLE_RULES = [
    "RSI 30 signal should not be overridden by vague market fear.",
    "Use ka10002 net quantity for brokerage net flow.",
    "Do not treat ka10040 ranking as net flow.",
    "Do not erase signed sell quantities with abs().",
    "Label price-change basis clearly.",
    "Keep KOSPI200 futures foreign/institutional flow unavailable unless a confirmed futures-specific source exists.",
    "User makes the trading decision; model provides checkpoints.",
    "The model must not act as a no-trade veto.",
    "제외 requires explicit invalidation data.",
    "Missing data should become 대기 with a missing trigger/data note, not generic 현금보유 or 내일 재검토.",
]

EXPECTED_OUTPUT_LINES = [
    "1. 판정: 진입 / 대기 / 제외",
    "2. 신호 상태",
    "3. 근거 데이터",
    "4. 진입 트리거",
    "5. 무효 조건 / 대기 조건",
    "6. 익절 기준",
    "7. 빠진 데이터",
    "8. 기존 모델 답변의 no-trade veto 여부",
    "9. 개선된 Discord 답변 예시",
]


def _format_value(value: Any) -> str:
    """full packet에서 bool/list/None 값을 deterministic 문자열로 바꾼다."""
    if value is None:
        return "unavailable"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        if not value:
            return "unavailable"
        return ", ".join(_format_value(item) for item in value)
    return str(value)


def _fixture_snapshot(symbol: str, time_kst: str) -> dict[str, Any]:
    """Full handoff contract에 맞춘 deterministic fixture snapshot을 반환한다."""
    return {
        "as_of": time_kst,
        "symbol": symbol,
        "quote": {
            "current_price": None,
            "previous_close_change_pct": None,
            "open_or_candle_change_pct": None,
            "high_to_current_pct": None,
            "low_to_current_pct": None,
            "volume": None,
            "source": "fixture_unavailable",
        },
        "indicators": {
            "rsi_1m": None,
            "rsi_5m": None,
            "rsi_30m": None,
            "bb_5m_pct": None,
            "bb_30m_pct": None,
            "moving_average_state": None,
        },
        "flow": {
            "brokerage_net_quantity_source": "ka10002_or_unavailable",
            "brokerage_net_quantity": None,
            "futures_foreign_institutional_flow": "unavailable",
        },
        "data_gaps": [
            "quote unavailable in fixture runner",
            "indicator values unavailable in fixture runner",
            "brokerage net quantity unavailable in fixture runner",
            "futures foreign/institutional flow unavailable from confirmed source",
        ],
    }


def _recent_excerpt(scenario: dict) -> list[str]:
    """scenario의 recent_messages와 현재 message를 Discord excerpt 문자열로 변환한다."""
    lines: list[str] = []
    for message in scenario.get("recent_messages") or []:
        lines.append(f"User: {message}")
        lines.append("Assistant: unavailable")
    lines.append(f"User: {scenario['message']}")
    lines.append("Assistant: unavailable")
    return lines


def build_full_handoff_packet(scenario_name: str, scenario: dict) -> str:
    """Fixture scenario 하나를 full ChatGPT handoff Markdown packet으로 렌더링한다."""
    route = route_scenario(scenario)
    route_dict = route.to_dict()
    symbol = route.symbol or "unavailable"
    time_kst = scenario.get("time_kst", "unavailable")
    snapshot = _fixture_snapshot(symbol, time_kst)
    triggers = _format_value(route_dict.get("triggers"))
    recent_excerpt = _recent_excerpt(scenario)

    lines = [
        "# ChatGPT trading review handoff",
        "",
        "## 1. Review request",
        "",
        "- Date: 2026-06-13",
        f"- Time KST: {time_kst}",
        f"- Symbol: {symbol}",
        "- Purpose: signal review",
        f"- User question: {scenario['message']}",
        "",
        "## 2. Market/session context",
        "",
        "- Market mode: fixture-only local review",
        "- Active strategy: unavailable",
        "- Watchlist: unavailable",
        "- Position status: unavailable",
        "- Trading session phase: regular fixture",
        "",
        "## 3. Active symbol context",
        "",
        f"- Active symbol: {symbol}",
        f"- Why this symbol is active: scenario={scenario_name}, used_active_symbol={_format_value(route.used_active_symbol)}",
        f"- Last trigger phrase: {triggers}",
        "- Last signal state: unavailable",
        "",
        "## 4. Local market snapshot",
        "",
        "```json",
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
        "## 5. Chart summary or attachments",
        "",
        "- 5-minute chart summary: unavailable",
        "- 30-minute chart summary: unavailable",
        "- Support/resistance: unavailable",
        "- Volume pattern: unavailable",
        "- Attached chart files: unavailable",
        "",
        "## 6. Recent Discord conversation excerpt",
        "",
        "```text",
        *recent_excerpt,
        "```",
        "",
        "## 7. Current model answer to review",
        "",
        "```text",
        "unavailable",
        "```",
        "",
        "## 8. Applicable rules",
        "",
        *[f"- {rule}" for rule in APPLICABLE_RULES],
        "",
        "## 9. Known data gaps",
        "",
        "- Missing data: quote, indicators, brokerage net quantity, chart summaries",
        "- Unverified estimates: unavailable",
        "- Source conflicts: unavailable",
        "",
        "## 10. Questions for ChatGPT",
        "",
        "1. Did the current model answer violate any rules?",
        "2. Is the signal valid, conflicted, near, invalid, or unavailable?",
        "3. What data supports the conclusion?",
        "4. What data is missing?",
        "5. What should the user check before deciding?",
        "6. How should the Discord model answer be improved?",
        "7. Did the model use unsupported no-trade veto language?",
        "8. If the answer says 제외, what exact invalidation condition supports it?",
        "9. If invalidation is not proven, what entry trigger or 대기 condition should be shown?",
        "",
        "## 11. Expected output format",
        "",
        "Please answer in Korean with:",
        "",
        *EXPECTED_OUTPUT_LINES,
        "",
        "## Fixture route metadata",
        "",
        f"- Scenario: {scenario_name}",
        f"- Intent: {_format_value(route.intent)}",
        f"- Triggers: {triggers}",
        f"- Reply mode: {_format_value(route.reply_mode)}",
        f"- Used active symbol: {_format_value(route.used_active_symbol)}",
    ]
    return "\n".join(lines) + "\n"


def run_all_scenarios() -> str:
    """모든 built-in scenario를 sorted 순서로 실행하고 full packet들을 header로 묶어 반환한다.

    출력 형식:
        ===== Scenario: <name> =====
        <full handoff packet>

        ===== Scenario: <name> =====
        <full handoff packet>
        ...
    """
    blocks: list[str] = []
    for name in sorted(SCENARIOS):
        blocks.append(f"===== Scenario: {name} =====")
        blocks.append(build_full_handoff_packet(name, SCENARIOS[name]).rstrip("\n"))
        blocks.append("")
    return "\n".join(blocks).rstrip("\n") + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a local full ChatGPT handoff packet from a fixture scenario and print it to stdout."
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
        "--all-scenarios",
        action="store_true",
        help=(
            "Run every built-in scenario in sorted order and print each full "
            "handoff packet with a header separator. Exits with 0 on success."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_scenarios:
        print(list_scenarios())
        return 0

    if args.all_scenarios:
        print(run_all_scenarios(), end="")
        return 0

    if not args.scenario:
        parser.error("either --scenario NAME, --all-scenarios, or --list-scenarios is required")

    if args.scenario not in SCENARIOS:
        print(f"unknown scenario: {args.scenario}", file=sys.stderr)
        print(
            f"available scenarios: {', '.join(sorted(SCENARIOS))}",
            file=sys.stderr,
        )
        return 2

    print(build_full_handoff_packet(args.scenario, SCENARIOS[args.scenario]), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
