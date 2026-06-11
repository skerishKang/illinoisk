#!/usr/bin/env python3
"""
Fixture-only quick handoff packet generator.

This module renders a Markdown string for ChatGPT review handoff. It does not
write files, connect to external services, fetch market data, or call models.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


FUTURES_UNAVAILABLE_NOTICE = (
    "KOSPI200 futures foreign/institutional net flow is unavailable from the "
    "current confirmed source. This handoff does not substitute stock foreign "
    "flow or program trading data for it."
)
EXPECTED_DECISION_PREFIXES = (
    "Decision: 진입",
    "Decision: 대기",
    "Decision: 보류",
    "Decision: 제외",
)
LIVE_EXECUTION_TERMS = (
    "buy now",
    "sell now",
    "place an order",
    "execute the trade",
    "market order",
    "지금 매수",
    "지금 매도",
    "바로 매수",
    "바로 매도",
    "주문 넣",
    "시장가",
)
EXPECTED_DECISION_BY_SIGNAL_STATE = {
    "valid_signal": "진입",
    "near_signal": "대기",
    "conflicted_signal": "보류",
    "invalid_signal": "제외",
    "unavailable": "제외",
}


@dataclass(frozen=True)
class QuickHandoffInput:
    time_kst: str
    symbol: str
    user_question: str
    route: Mapping[str, Any]
    snapshot: Mapping[str, Any]
    signal_state: str = "unavailable"
    active_strategy: Sequence[str] = field(default_factory=list)
    signal_supporting_factors: Sequence[str] = field(default_factory=list)
    signal_conflicting_factors: Sequence[str] = field(default_factory=list)
    signal_near_factors: Sequence[str] = field(default_factory=list)
    signal_missing_data: Sequence[str] = field(default_factory=list)
    intraday_decision: str = "unavailable"
    intraday_decision_strength: str = "unavailable"
    intraday_decision_reasons: Sequence[str] = field(default_factory=list)
    intraday_entry_conditions: Sequence[str] = field(default_factory=list)
    intraday_invalid_conditions: Sequence[str] = field(default_factory=list)
    intraday_stop_reference: str | None = None
    recent_discord_excerpt: Sequence[str] = field(default_factory=list)
    current_model_answer: str | None = None


def _format_value(value: Any) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        if not value:
            return "unavailable"
        return ", ".join(_format_value(item) for item in value)
    return str(value)


def _get_nested(mapping: Mapping[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current


def _format_excerpt(lines: Sequence[str]) -> str:
    if not lines:
        return "- unavailable"
    return "\n".join(f"- {line}" for line in lines)


def _format_bullets(lines: Sequence[str]) -> str:
    if not lines:
        return "- unavailable"
    return "\n".join(f"- {line}" for line in lines)


def _expected_decision_for_signal_state(signal_state: str) -> str | None:
    return EXPECTED_DECISION_BY_SIGNAL_STATE.get(signal_state)


def _format_decision_consistency(data: QuickHandoffInput) -> str:
    signal_state = _format_value(data.signal_state)
    decision = _format_value(data.intraday_decision)
    expected = _expected_decision_for_signal_state(signal_state)

    if expected is None or decision == "unavailable":
        return "unavailable"
    if decision == expected:
        return f"consistent: {signal_state} -> {decision}"
    return f"inconsistent: {signal_state} expects {expected}, got {decision}"


def _current_answer_guardrail_status(answer: str | None) -> tuple[str, list[str]]:
    if answer is None or not str(answer).strip():
        return "unavailable", ["current model answer unavailable"]

    answer_text = str(answer).strip()
    first_line = next((line.strip() for line in answer_text.splitlines() if line.strip()), "")
    reasons: list[str] = []

    if not any(first_line.startswith(prefix) for prefix in EXPECTED_DECISION_PREFIXES):
        reasons.append("first non-empty line does not start with an allowed Decision prefix")

    lowered = answer_text.lower()
    for term in LIVE_EXECUTION_TERMS:
        if term.lower() in lowered:
            reasons.append(f"live execution-style wording detected: {term}")
            break

    if reasons:
        return "violation", reasons
    return "compliant", ["current model answer follows the required decision-first guardrail"]


def _guardrail_summary(
    data: QuickHandoffInput,
    decision_consistency: str,
    current_answer_status: str,
) -> tuple[str, list[str]]:
    findings: list[str] = []

    if decision_consistency.startswith("inconsistent"):
        findings.append(f"decision/state mismatch: {decision_consistency}")
    if current_answer_status == "violation":
        findings.append("current model answer violates required guardrails")
    if _format_value(data.signal_state) == "unavailable":
        findings.append("signal state is unavailable")

    if findings:
        return "blocked", findings

    if current_answer_status == "unavailable":
        findings.append("current model answer unavailable")
    if decision_consistency == "unavailable":
        findings.append("decision/state consistency unavailable")
    if data.signal_missing_data:
        findings.append("signal missing data present: " + _format_value(list(data.signal_missing_data)))

    if findings:
        return "attention", findings
    return "clear", ["all packet guardrail checks are clear"]


def _format_intraday_decision_summary(data: QuickHandoffInput) -> str:
    """Return a deterministic one-line action summary for the decision section."""
    decision = _format_value(data.intraday_decision)
    if decision == "진입":
        return "Strong stock with valid local signal. Entry may be considered only within the listed conditions."
    if decision == "대기":
        return "Strong or near-signal stock, but current entry is not confirmed. Avoid chase-buying and wait for pullback confirmation."
    if decision == "보류":
        return "Signal has conflicting evidence. Hold the decision until conflict conditions are resolved."
    if decision == "제외":
        return "Local signal is invalid or unavailable. Exclude from entry until required data and conditions recover."
    return "Intraday decision is unavailable from the current local inputs."


def build_quick_handoff_packet(data: QuickHandoffInput | Mapping[str, Any]) -> str:
    """Return a quick Markdown packet for ChatGPT web review.

    The packet is intentionally deterministic and fixture-friendly. It only
    uses values passed by the caller.
    """
    if isinstance(data, Mapping):
        data = QuickHandoffInput(**data)

    snapshot = data.snapshot
    route = data.route
    quote = snapshot.get("quote", {}) if isinstance(snapshot.get("quote", {}), Mapping) else {}
    indicators = snapshot.get("indicators", {}) if isinstance(snapshot.get("indicators", {}), Mapping) else {}
    flow = snapshot.get("flow", {}) if isinstance(snapshot.get("flow", {}), Mapping) else {}

    active_strategy = _format_value(list(data.active_strategy))
    route_triggers = _format_value(route.get("triggers"))
    route_intent = _format_value(route.get("intent"))
    route_reply_mode = _format_value(route.get("reply_mode"))
    decision_consistency = _format_decision_consistency(data)
    current_answer_status, current_answer_reasons = _current_answer_guardrail_status(data.current_model_answer)
    summary_status, summary_findings = _guardrail_summary(data, decision_consistency, current_answer_status)

    lines = [
        "# Quick ChatGPT trading review",
        "",
        "## Guardrail summary",
        f"- Overall status: {summary_status}",
        f"- Decision/state consistency: {decision_consistency}",
        f"- Current answer status: {current_answer_status}",
        f"- Signal state: {_format_value(data.signal_state)}",
        "### Summary findings",
        _format_bullets(summary_findings),
        "",
        "## Review request",
        f"- Time KST: {_format_value(data.time_kst)}",
        f"- Symbol: {_format_value(data.symbol)}",
        f"- User question: {_format_value(data.user_question)}",
        f"- Active strategy: {active_strategy}",
        f"- Signal state: {_format_value(data.signal_state)}",
        "",
        "## Intraday decision",
        f"- Decision: {_format_value(data.intraday_decision)}",
        f"- Strength: {_format_value(data.intraday_decision_strength)}",
        f"- Decision/state consistency: {decision_consistency}",
        f"- Summary: {_format_intraday_decision_summary(data)}",
        "### Decision reasons",
        _format_bullets(data.intraday_decision_reasons),
        "",
        "### Entry conditions",
        _format_bullets(data.intraday_entry_conditions),
        "",
        "### Invalid / wait conditions",
        _format_bullets(data.intraday_invalid_conditions),
        "",
        f"- Stop reference: {_format_value(data.intraday_stop_reference)}",
        "",
        "## Signal detail",
        "### Supporting factors",
        _format_bullets(data.signal_supporting_factors),
        "",
        "### Conflicting factors",
        _format_bullets(data.signal_conflicting_factors),
        "",
        "### Near factors",
        _format_bullets(data.signal_near_factors),
        "",
        "### Missing data",
        _format_bullets(data.signal_missing_data),
        "",
        "## Trigger route",
        f"- Intent: {route_intent}",
        f"- Triggers: {route_triggers}",
        f"- Reply mode: {route_reply_mode}",
        f"- Used active symbol: {_format_value(route.get('used_active_symbol'))}",
        "",
        "## Local market snapshot",
        f"- Snapshot time: {_format_value(snapshot.get('as_of'))}",
        f"- Current price: {_format_value(quote.get('current_price'))}",
        f"- Previous-close change pct: {_format_value(quote.get('previous_close_change_pct'))}",
        f"- Open/candle change pct: {_format_value(quote.get('open_or_candle_change_pct'))}",
        f"- High-to-current pct: {_format_value(quote.get('high_to_current_pct'))}",
        f"- Low-to-current pct: {_format_value(quote.get('low_to_current_pct'))}",
        f"- Volume: {_format_value(quote.get('volume'))}",
        f"- Quote source: {_format_value(quote.get('source'))}",
        "",
        "## Indicators",
        f"- RSI 1m: {_format_value(indicators.get('rsi_1m'))}",
        f"- RSI 5m: {_format_value(indicators.get('rsi_5m'))}",
        f"- RSI 30m: {_format_value(indicators.get('rsi_30m'))}",
        f"- BB 5m pct: {_format_value(indicators.get('bb_5m_pct'))}",
        f"- BB 30m pct: {_format_value(indicators.get('bb_30m_pct'))}",
        f"- Moving-average state: {_format_value(indicators.get('moving_average_state'))}",
        "",
        "## Flow",
        f"- Brokerage net quantity source: {_format_value(flow.get('brokerage_net_quantity_source'))}",
        f"- Brokerage net quantity: {_format_value(flow.get('brokerage_net_quantity'))}",
        f"- Futures foreign/institutional flow: {_format_value(flow.get('futures_foreign_institutional_flow'))}",
        f"- Futures flow notice: {FUTURES_UNAVAILABLE_NOTICE}",
        "",
        "## Recent Discord conversation excerpt",
        _format_excerpt(data.recent_discord_excerpt),
        "",
        "## Current model answer",
        _format_value(data.current_model_answer),
        "",
        "## Current answer guardrail check",
        f"- Status: {current_answer_status}",
        "### Guardrail findings",
        _format_bullets(current_answer_reasons),
        "",
        "## Required response format",
        "- The first line must start with exactly one of: `Decision: 진입`, `Decision: 대기`, `Decision: 보류`, `Decision: 제외`.",
        "- Do not answer with only a vague strength comment such as `strong stock`, `looks good`, or `watch it`.",
        "- State whether the current setup is `chase-buying`, `confirmed pullback`, `conflicted`, or `unavailable`.",
        "- Then provide short sections: `Reason`, `Entry conditions`, `Invalid / wait conditions`, and `Stop reference`.",
        "- Do not recommend or imply live trade execution; keep the output as local analysis for the user's decision.",
        "",
        "### Required answer template",
        "Decision: 진입|대기|보류|제외",
        "Setup: chase-buying|confirmed pullback|conflicted|unavailable",
        "Reason: <brief reason based only on the packet>",
        "Entry conditions:",
        "- <condition or unavailable>",
        "Invalid / wait conditions:",
        "- <condition or unavailable>",
        "Stop reference: <reference or unavailable>",
        "",
        "## Ask ChatGPT",
        "1. Start the answer using the required decision-first response format above.",
        "2. Is the signal valid, conflicted, near, invalid, or unavailable?",
        "3. Is the local intraday decision 진입, 대기, 보류, or 제외?",
        "4. Is the current price a chase-buying zone or a confirmed pullback zone?",
        "5. What entry, invalidation, and stop conditions should be checked before the user decides?",
        "6. Did the current model answer violate the trading analysis guardrails?",
        "",
    ]

    return "\n".join(lines)


__all__ = [
    "EXPECTED_DECISION_BY_SIGNAL_STATE",
    "EXPECTED_DECISION_PREFIXES",
    "FUTURES_UNAVAILABLE_NOTICE",
    "LIVE_EXECUTION_TERMS",
    "QuickHandoffInput",
    "build_quick_handoff_packet",
]
