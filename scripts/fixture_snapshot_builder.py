#!/usr/bin/env python3
"""
Fixture-only snapshot builder.

This module builds deterministic local snapshot dictionaries for tests and
handoff development. It does not read files, write files, connect to external
services, or fetch market data.
"""
from __future__ import annotations

from typing import Any, Mapping


DEFAULT_AS_OF = "2026-06-11T10:35:00+09:00"
DEFAULT_SYMBOL = "HPSP"


def _merge(base: dict[str, Any], overrides: Mapping[str, Any] | None) -> dict[str, Any]:
    merged = dict(base)
    if overrides:
        merged.update(dict(overrides))
    return merged


def build_fixture_snapshot(
    *,
    symbol: str = DEFAULT_SYMBOL,
    as_of: str = DEFAULT_AS_OF,
    quote_overrides: Mapping[str, Any] | None = None,
    indicator_overrides: Mapping[str, Any] | None = None,
    flow_overrides: Mapping[str, Any] | None = None,
    top_level_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a valid local fixture snapshot dictionary.

    Override mappings can set values to `None`; this keeps unavailable values
    explicit while preserving required schema keys.
    """
    quote = _merge(
        {
            "current_price": 41250,
            "previous_close_change_pct": -1.2,
            "open_or_candle_change_pct": 0.4,
            "high_to_current_pct": -2.1,
            "low_to_current_pct": 1.8,
            "volume": 1250000,
            "source": "fixture",
        },
        quote_overrides,
    )
    indicators = _merge(
        {
            "rsi_1m": 29.8,
            "rsi_5m": 34.2,
            "rsi_30m": 41.0,
            "bb_5m_pct": 0.18,
            "bb_30m_pct": 0.42,
            "moving_average_state": "below_short_ma",
        },
        indicator_overrides,
    )
    flow = _merge(
        {
            "brokerage_net_quantity_source": "ka10002_or_unavailable",
            "brokerage_net_quantity": None,
            "futures_foreign_institutional_flow": "unavailable",
        },
        flow_overrides,
    )

    return _merge(
        {
            "as_of": as_of,
            "symbol": symbol,
            "quote": quote,
            "indicators": indicators,
            "flow": flow,
        },
        top_level_overrides,
    )


__all__ = [
    "DEFAULT_AS_OF",
    "DEFAULT_SYMBOL",
    "build_fixture_snapshot",
]
