#!/usr/bin/env python3
"""
Fixture-only handoff orchestration.

This module connects the local trigger router to the quick Markdown packet
generator. It does not write files, connect to external services, fetch market
data, or call models.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence

from discord_trigger_router import route_message
from intraday_decision_engine import evaluate_intraday_decision
from quick_handoff_packet import build_quick_handoff_packet
from signal_state_engine import evaluate_signal_state
from snapshot_schema_validator import require_valid_snapshot_schema


@dataclass(frozen=True)
class HandoffOrchestrationInput:
    message: str
    snapshot: Mapping[str, Any]
    current_model_answer: str | None = None
    recent_messages: Sequence[str] = field(default_factory=list)
    active_symbol: str | None = None
    signal_state: str | None = None
    active_strategy: Sequence[str] = field(default_factory=list)
    time_kst: str | None = None


@dataclass(frozen=True)
class HandoffOrchestrationResult:
    packet_markdown: str
    route: Mapping[str, Any]
    symbol: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_markdown": self.packet_markdown,
            "route": dict(self.route),
            "symbol": self.symbol,
        }


def _snapshot_symbol(snapshot: Mapping[str, Any]) -> str | None:
    value = snapshot.get("symbol")
    return str(value) if value else None


def _snapshot_time(snapshot: Mapping[str, Any]) -> str:
    value = snapshot.get("as_of")
    return str(value) if value else "unavailable"


def build_handoff_from_message(
    data: HandoffOrchestrationInput | Mapping[str, Any],
) -> HandoffOrchestrationResult:
    """Route a message and return a quick handoff Markdown packet.

    The orchestration is deterministic and fixture-only. It validates the
    caller-provided snapshot, then calls `route_message()`, evaluates the local
    signal state and intraday decision, and calls `build_quick_handoff_packet()`
    with local data only.
    """
    if isinstance(data, Mapping):
        data = HandoffOrchestrationInput(**data)

    snapshot = require_valid_snapshot_schema(data.snapshot)
    signal_result = evaluate_signal_state(snapshot)

    route = route_message(
        data.message,
        active_symbol=data.active_symbol,
        recent_messages=data.recent_messages,
    ).to_dict()

    symbol = route.get("symbol") or data.active_symbol or _snapshot_symbol(snapshot) or "unavailable"
    time_kst = data.time_kst or _snapshot_time(snapshot)
    signal_state = data.signal_state if data.signal_state is not None else signal_result.state
    active_strategy = list(data.active_strategy) or list(signal_result.active_strategy)

    effective_signal_result = replace(signal_result, state=signal_state)
    intraday_decision = evaluate_intraday_decision(effective_signal_result)

    packet_markdown = build_quick_handoff_packet(
        {
            "time_kst": time_kst,
            "symbol": symbol,
            "user_question": data.message,
            "route": route,
            "snapshot": snapshot,
            "signal_state": signal_state,
            "active_strategy": active_strategy,
            "signal_supporting_factors": list(signal_result.supporting_factors),
            "signal_conflicting_factors": list(signal_result.conflicting_factors),
            "signal_near_factors": list(signal_result.near_factors),
            "signal_missing_data": list(signal_result.missing_data),
            "intraday_decision": intraday_decision.decision,
            "intraday_decision_strength": intraday_decision.strength,
            "intraday_decision_reasons": list(intraday_decision.reasons),
            "intraday_entry_conditions": list(intraday_decision.entry_conditions),
            "intraday_invalid_conditions": list(intraday_decision.invalid_conditions),
            "intraday_stop_reference": intraday_decision.stop_reference,
            "recent_discord_excerpt": list(data.recent_messages),
            "current_model_answer": data.current_model_answer,
        }
    )

    return HandoffOrchestrationResult(
        packet_markdown=packet_markdown,
        route=route,
        symbol=str(symbol),
    )


__all__ = [
    "HandoffOrchestrationInput",
    "HandoffOrchestrationResult",
    "build_handoff_from_message",
]
