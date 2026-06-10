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

    lines = [
        "# Quick ChatGPT trading review",
        "",
        "## Review request",
        f"- Time KST: {_format_value(data.time_kst)}",
        f"- Symbol: {_format_value(data.symbol)}",
        f"- User question: {_format_value(data.user_question)}",
        f"- Active strategy: {active_strategy}",
        f"- Signal state: {_format_value(data.signal_state)}",
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
        "## Ask ChatGPT",
        "1. Is the signal valid, conflicted, near, invalid, or unavailable?",
        "2. Did the current model answer violate the trading analysis guardrails?",
        "3. What data supports the conclusion?",
        "4. What data is missing?",
        "5. What should be checked before the user decides?",
        "",
    ]

    return "\n".join(lines)


__all__ = [
    "FUTURES_UNAVAILABLE_NOTICE",
    "QuickHandoffInput",
    "build_quick_handoff_packet",
]
