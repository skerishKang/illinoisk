#!/usr/bin/env python3
"""
Fixture-only local intraday decision layer.

Maps signal_state_engine states to actionable intraday decisions.
This module evaluates caller-provided signal state results. It does not
read files, write files, connect to external services, fetch market data,
or use LLM/API calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from signal_state_engine import SignalStateResult, SIGNAL_STATES


DECISION_TYPES = (
    "진입",
    "대기",
    "보류",
    "제외",
)

# Signal state to decision mapping
SIGNAL_TO_DECISION = {
    "valid_signal": "진입",
    "near_signal": "대기",
    "conflicted_signal": "보류",
    "invalid_signal": "제외",
    "unavailable": "제외",
}


@dataclass(frozen=True)
class IntradayDecisionResult:
    decision: str
    strength: str
    reasons: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    entry_conditions: list[str] = field(default_factory=list)
    invalid_conditions: list[str] = field(default_factory=list)
    stop_reference: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision,
            "strength": self.strength,
            "reasons": list(self.reasons),
            "missing_data": list(self.missing_data),
            "entry_conditions": list(self.entry_conditions),
            "invalid_conditions": list(self.invalid_conditions),
            "stop_reference": self.stop_reference,
        }


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _calculate_strength(signal_result: SignalStateResult, decision: str) -> str:
    """Calculate decision strength based on signal state and factors."""
    if decision == "진입":
        # Strong if multiple supporting factors, moderate if just 2
        support_count = len(signal_result.supporting_factors)
        if support_count >= 3:
            return "강함"
        if support_count >= 2:
            return "보통"
        return "약함"

    if decision == "대기":
        near_count = len(signal_result.near_factors)
        if near_count >= 2:
            return "보통"
        return "약함"

    if decision == "보류":
        conflicting_count = len(signal_result.conflicting_factors)
        if conflicting_count >= 2:
            return "강함"
        return "보통"

    return "해당없음"


def _build_reasons(signal_result: SignalStateResult, decision: str) -> list[str]:
    """Build human-readable reasons for the decision."""
    reasons: list[str] = []

    if decision == "진입":
        if signal_result.supporting_factors:
            reasons.extend([f"지원 요인: {f}" for f in signal_result.supporting_factors])
        if signal_result.active_strategy:
            reasons.append(f"활성 전략: {', '.join(signal_result.active_strategy)}")

    elif decision == "대기":
        if signal_result.near_factors:
            reasons.extend([f"접근 요인: {f}" for f in signal_result.near_factors])
        if signal_result.active_strategy:
            reasons.append(f"관찰 전략: {', '.join(signal_result.active_strategy)}")

    elif decision == "보류":
        if signal_result.conflicting_factors:
            reasons.extend([f"충돌 요인: {f}" for f in signal_result.conflicting_factors])
        if signal_result.supporting_factors:
            reasons.extend([f"지원 요인: {f}" for f in signal_result.supporting_factors])

    elif decision == "제외":
        if signal_result.state == "invalid_signal":
            reasons.append("신호 불충분: 지지 요인 없음 또는 신호 조건 미달")
        elif signal_result.state == "unavailable":
            reasons.append("데이터 불충분: 핵심 지표 값 없음")
        if signal_result.missing_data:
            reasons.append("누락 데이터: " + ", ".join(signal_result.missing_data[:3]))

    return _dedupe(reasons)


def _build_entry_conditions(signal_result: SignalStateResult) -> list[str]:
    """Build entry conditions from supporting factors."""
    conditions: list[str] = []
    if signal_result.supporting_factors:
        conditions.extend(signal_result.supporting_factors)
    if signal_result.active_strategy:
        conditions.extend([f"전략: {s}" for s in signal_result.active_strategy])
    return _dedupe(conditions)


def _build_invalid_conditions(signal_result: SignalStateResult) -> list[str]:
    """Build invalid/exclusion conditions from conflicting and missing factors."""
    conditions: list[str] = []
    if signal_result.conflicting_factors:
        conditions.extend(signal_result.conflicting_factors)
    if signal_result.missing_data:
        conditions.extend(signal_result.missing_data)
    if not signal_result.supporting_factors and not signal_result.near_factors:
        conditions.append("지지/접근 요인 없음")
    return _dedupe(conditions)


def _build_stop_reference(signal_result: SignalStateResult, decision: str) -> str | None:
    """Build stop loss reference price hint from signal state."""
    if decision != "진입" and decision != "대기":
        return None

    # This is a fixture-only module, so we can't compute actual stop prices.
    # Return a descriptive reference that handoff packet can use.
    if signal_result.state == "valid_signal":
        return "RSI 30m <= 30 + BB 하단 근접 시 직전 저점 기준"
    if signal_result.state == "near_signal":
        return "RSI 30m 30~35 또는 BB 진입 시 확인 후 설정"
    return None


def evaluate_intraday_decision(signal_result: SignalStateResult) -> IntradayDecisionResult:
    """Evaluate a local intraday decision from a signal state result.

    This function is deterministic and side-effect free. It only uses the
    SignalStateResult fields to produce an actionable intraday decision.
    """
    # Validate input state
    if signal_result.state not in SIGNAL_STATES:
        raise ValueError(f"Unknown signal state: {signal_result.state}")

    # Map to decision
    decision = SIGNAL_TO_DECISION[signal_result.state]

    # Build output fields
    strength = _calculate_strength(signal_result, decision)
    reasons = _build_reasons(signal_result, decision)
    missing_data = _dedupe(signal_result.missing_data)
    entry_conditions = _build_entry_conditions(signal_result)
    invalid_conditions = _build_invalid_conditions(signal_result)
    stop_reference = _build_stop_reference(signal_result, decision)

    return IntradayDecisionResult(
        decision=decision,
        strength=strength,
        reasons=reasons,
        missing_data=missing_data,
        entry_conditions=entry_conditions,
        invalid_conditions=invalid_conditions,
        stop_reference=stop_reference,
    )


__all__ = [
    "DECISION_TYPES",
    "SIGNAL_TO_DECISION",
    "IntradayDecisionResult",
    "evaluate_intraday_decision",
]