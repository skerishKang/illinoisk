#!/usr/bin/env python3
"""
Fixture-only rule-based signal state engine.

This module evaluates caller-provided local snapshot dictionaries. It does not
read files, write files, connect to external services, fetch market data, or use
LLM/API calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


SIGNAL_STATES = (
    "valid_signal",
    "near_signal",
    "conflicted_signal",
    "invalid_signal",
    "unavailable",
)

KA10040_RANKING_NOTICE = (
    "ka10040 ranking data is not treated as brokerage net quantity flow."
)
FUTURES_FLOW_UNAVAILABLE_NOTICE = (
    "futures foreign/institutional flow is unavailable and was not substituted."
)


@dataclass(frozen=True)
class SignalStateResult:
    state: str
    supporting_factors: list[str] = field(default_factory=list)
    conflicting_factors: list[str] = field(default_factory=list)
    near_factors: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    active_strategy: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "state": self.state,
            "supporting_factors": list(self.supporting_factors),
            "conflicting_factors": list(self.conflicting_factors),
            "near_factors": list(self.near_factors),
            "missing_data": list(self.missing_data),
            "active_strategy": list(self.active_strategy),
        }


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _section(snapshot: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = snapshot.get(name, {})
    return value if isinstance(value, Mapping) else {}


def _is_unavailable(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"", "unavailable", "none", "null", "n/a"}
    return False


def _source_allows_brokerage_net_quantity(source: Any) -> bool:
    source_text = str(source or "").lower()
    if "ka10040" in source_text or "ranking" in source_text:
        return False
    return "ka10002" in source_text or "net" in source_text or "fixture" in source_text


def _score_rsi(
    indicators: Mapping[str, Any],
    supporting: list[str],
    conflicting: list[str],
    near: list[str],
    missing: list[str],
    strategies: list[str],
) -> None:
    rsi_1m = _as_float(indicators.get("rsi_1m"))
    rsi_5m = _as_float(indicators.get("rsi_5m"))
    rsi_30m = _as_float(indicators.get("rsi_30m"))

    if rsi_30m is None:
        missing.append("RSI 30m unavailable")
    elif rsi_30m <= 30:
        supporting.append("RSI 30m is at or below 30")
        strategies.append("RSI_30")
    elif rsi_30m <= 35:
        near.append("RSI 30m is near the oversold threshold")
        strategies.append("RSI_30_NEAR")
    elif rsi_30m >= 70:
        conflicting.append("RSI 30m is overbought")

    if rsi_5m is None:
        missing.append("RSI 5m unavailable")
    elif rsi_5m <= 30:
        supporting.append("RSI 5m is at or below 30")
        strategies.append("RSI_5")
    elif rsi_5m <= 35:
        near.append("RSI 5m is near the oversold threshold")
        strategies.append("RSI_5_NEAR")
    elif rsi_5m >= 70:
        conflicting.append("RSI 5m is overbought")

    if rsi_1m is None:
        missing.append("RSI 1m unavailable")
    elif rsi_1m <= 30:
        supporting.append("RSI 1m is at or below 30")
        strategies.append("RSI_1")
    elif rsi_1m <= 35:
        near.append("RSI 1m is near the oversold threshold")
        strategies.append("RSI_1_NEAR")
    elif rsi_1m >= 75:
        conflicting.append("RSI 1m is sharply overbought")


def _score_bollinger(
    indicators: Mapping[str, Any],
    supporting: list[str],
    conflicting: list[str],
    near: list[str],
    missing: list[str],
    strategies: list[str],
) -> None:
    bb_5m = _as_float(indicators.get("bb_5m_pct"))
    bb_30m = _as_float(indicators.get("bb_30m_pct"))

    if bb_5m is None:
        missing.append("BB 5m pct unavailable")
    elif bb_5m <= 0.20:
        supporting.append("BB 5m pct is near the lower band")
        strategies.append("BB_5M_LOWER")
    elif bb_5m <= 0.35:
        near.append("BB 5m pct is approaching the lower band")
        strategies.append("BB_5M_NEAR_LOWER")
    elif bb_5m >= 0.85:
        conflicting.append("BB 5m pct is near the upper band")

    if bb_30m is None:
        missing.append("BB 30m pct unavailable")
    elif bb_30m <= 0.20:
        supporting.append("BB 30m pct is near the lower band")
        strategies.append("BB_30M_LOWER")
    elif bb_30m <= 0.35:
        near.append("BB 30m pct is approaching the lower band")
        strategies.append("BB_30M_NEAR_LOWER")
    elif bb_30m >= 0.85:
        conflicting.append("BB 30m pct is near the upper band")


def _score_moving_average(
    indicators: Mapping[str, Any],
    supporting: list[str],
    conflicting: list[str],
    near: list[str],
    missing: list[str],
    strategies: list[str],
) -> None:
    state = indicators.get("moving_average_state")
    if _is_unavailable(state):
        missing.append("moving_average_state unavailable")
        return

    state_text = str(state).strip().lower()
    bullish_terms = ("above_short", "bullish", "reclaim", "golden", "above_vwap")
    bearish_terms = ("breakdown", "bearish", "below_long", "death")

    if any(term in state_text for term in bullish_terms):
        supporting.append(f"moving average state supports: {state}")
        strategies.append("MA_SUPPORT")
    elif any(term in state_text for term in bearish_terms):
        conflicting.append(f"moving average state conflicts: {state}")
    elif "below_short" in state_text:
        missing.append(f"moving average confirmation still needed: {state}")
    else:
        missing.append(f"moving average state is neutral: {state}")


def _score_flow(
    flow: Mapping[str, Any],
    supporting: list[str],
    conflicting: list[str],
    missing: list[str],
    strategies: list[str],
) -> None:
    source = flow.get("brokerage_net_quantity_source")
    quantity = _as_float(flow.get("brokerage_net_quantity"))
    source_text = str(source or "").lower()

    if "ka10040" in source_text or "ranking" in source_text:
        missing.append(KA10040_RANKING_NOTICE)
    elif quantity is None:
        missing.append("brokerage net quantity unavailable")
    elif not _source_allows_brokerage_net_quantity(source):
        missing.append("brokerage net quantity source is not confirmed as net flow")
    elif quantity > 0:
        supporting.append("brokerage net quantity is positive")
        strategies.append("BROKERAGE_NET_BUY")
    elif quantity < 0:
        conflicting.append("brokerage net quantity is negative")
    else:
        missing.append("brokerage net quantity is zero")

    futures_flow = flow.get("futures_foreign_institutional_flow")
    if _is_unavailable(futures_flow):
        missing.append(FUTURES_FLOW_UNAVAILABLE_NOTICE)
    else:
        missing.append("futures foreign/institutional flow is present but not scored by this fixture rule")


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _resolve_state(
    supporting: list[str],
    conflicting: list[str],
    near: list[str],
    missing: list[str],
) -> str:
    if not supporting and not conflicting and not near:
        core_missing = [
            item
            for item in missing
            if item.startswith("RSI ")
            or item.startswith("BB ")
            or item == "moving_average_state unavailable"
        ]
        return "unavailable" if len(core_missing) >= 6 else "invalid_signal"
    if supporting and conflicting:
        return "conflicted_signal"
    if len(supporting) >= 2:
        return "valid_signal"
    if supporting or near:
        return "near_signal"
    return "invalid_signal"


def evaluate_signal_state(snapshot: Mapping[str, Any]) -> SignalStateResult:
    """Evaluate a local snapshot and return a deterministic signal state.

    The rules intentionally avoid broad market-fear overrides. RSI values around
    30 remain valid signal evidence when confirmed by other local indicators.
    Unavailable futures foreign/institutional flow is reported as missing data;
    stock foreign flow or program trading fields are not used as substitutes.
    """
    indicators = _section(snapshot, "indicators")
    flow = _section(snapshot, "flow")

    supporting: list[str] = []
    conflicting: list[str] = []
    near: list[str] = []
    missing: list[str] = []
    strategies: list[str] = []

    _score_rsi(indicators, supporting, conflicting, near, missing, strategies)
    _score_bollinger(indicators, supporting, conflicting, near, missing, strategies)
    _score_moving_average(indicators, supporting, conflicting, near, missing, strategies)
    _score_flow(flow, supporting, conflicting, missing, strategies)

    supporting = _dedupe(supporting)
    conflicting = _dedupe(conflicting)
    near = _dedupe(near)
    missing = _dedupe(missing)
    strategies = _dedupe(strategies)
    state = _resolve_state(supporting, conflicting, near, missing)

    return SignalStateResult(
        state=state,
        supporting_factors=supporting,
        conflicting_factors=conflicting,
        near_factors=near,
        missing_data=missing,
        active_strategy=strategies,
    )


__all__ = [
    "FUTURES_FLOW_UNAVAILABLE_NOTICE",
    "KA10040_RANKING_NOTICE",
    "SIGNAL_STATES",
    "SignalStateResult",
    "evaluate_signal_state",
]
