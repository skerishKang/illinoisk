#!/usr/bin/env python3
"""
Fixture-only snapshot schema validator.

This module validates local snapshot fixture shape before handoff packet
construction. It does not read files, write files, connect to external services,
or fetch market data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


REQUIRED_TOP_LEVEL_KEYS = ("as_of", "symbol", "quote", "indicators", "flow")
REQUIRED_QUOTE_KEYS = (
    "current_price",
    "previous_close_change_pct",
    "open_or_candle_change_pct",
    "high_to_current_pct",
    "low_to_current_pct",
    "volume",
    "source",
)
REQUIRED_INDICATOR_KEYS = (
    "rsi_1m",
    "rsi_5m",
    "rsi_30m",
    "bb_5m_pct",
    "bb_30m_pct",
    "moving_average_state",
)
REQUIRED_FLOW_KEYS = (
    "brokerage_net_quantity_source",
    "brokerage_net_quantity",
    "futures_foreign_institutional_flow",
)


@dataclass(frozen=True)
class SnapshotValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
        }


def _missing_keys(mapping: Mapping[str, Any], keys: tuple[str, ...], prefix: str) -> list[str]:
    return [f"missing {prefix}.{key}" for key in keys if key not in mapping]


def _section(snapshot: Mapping[str, Any], name: str, errors: list[str]) -> Mapping[str, Any] | None:
    value = snapshot.get(name)
    if not isinstance(value, Mapping):
        errors.append(f"{name} must be mapping")
        return None
    return value


def validate_snapshot_schema(snapshot: Any) -> SnapshotValidationResult:
    """Validate local fixture snapshot shape.

    `None` values are allowed for data fields so unavailable market data can be
    represented explicitly. Missing sections or keys are reported as errors.
    """
    errors: list[str] = []

    if not isinstance(snapshot, Mapping):
        return SnapshotValidationResult(ok=False, errors=["snapshot must be mapping"])

    errors.extend(_missing_keys(snapshot, REQUIRED_TOP_LEVEL_KEYS, "snapshot"))

    quote = _section(snapshot, "quote", errors) if "quote" in snapshot else None
    indicators = _section(snapshot, "indicators", errors) if "indicators" in snapshot else None
    flow = _section(snapshot, "flow", errors) if "flow" in snapshot else None

    if quote is not None:
        errors.extend(_missing_keys(quote, REQUIRED_QUOTE_KEYS, "quote"))
    if indicators is not None:
        errors.extend(_missing_keys(indicators, REQUIRED_INDICATOR_KEYS, "indicators"))
    if flow is not None:
        errors.extend(_missing_keys(flow, REQUIRED_FLOW_KEYS, "flow"))

    return SnapshotValidationResult(ok=not errors, errors=errors)


def require_valid_snapshot_schema(snapshot: Any) -> Mapping[str, Any]:
    """Return snapshot when valid, otherwise raise ValueError with all errors."""
    result = validate_snapshot_schema(snapshot)
    if not result.ok:
        raise ValueError("; ".join(result.errors))
    return snapshot


__all__ = [
    "REQUIRED_FLOW_KEYS",
    "REQUIRED_INDICATOR_KEYS",
    "REQUIRED_QUOTE_KEYS",
    "REQUIRED_TOP_LEVEL_KEYS",
    "SnapshotValidationResult",
    "require_valid_snapshot_schema",
    "validate_snapshot_schema",
]
