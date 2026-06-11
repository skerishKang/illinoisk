#!/usr/bin/env python3
"""
Fixture-only local intraday decision layer.

Maps signal_state_engine states to actionable intraday decisions.
This module evaluates caller-provided signal state results and, when a
caller-provided snapshot is available, applies deterministic local risk/reward
guards. It does not read files, write files, connect to external services,
fetch market data, or use LLM/API calls.
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

# Signal state to decision mapping before quote-based risk/reward guards.
SIGNAL_TO_DECISION = {
    "valid_signal": "진입",
    "near_signal": "대기",
    "conflicted_signal": "보류",
    "invalid_signal": "제외",
    "unavailable": "제외",
}

MAX_STOP_DISTANCE_PCT = 3.0
MIN_REWARD_RISK_RATIO = 1.0
LATE_CHASE_HIGH_DISTANCE_PCT = 0.5
# Late-chase is evaluated only after wide-stop and reward/risk exclusion gates.
# At that point downside is already bounded and reward/risk is favorable, so the
# chase guard only needs a non-negative stop distance and a very small remaining
# upside to the known intraday high.
LATE_CHASE_MIN_BOUNCE_FROM_LOW_PCT = 0.0


@dataclass(frozen=True)
class IntradayDecisionResult:
    decision: str
    strength: str
    reasons: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    entry_conditions: list[str] = field(default_factory=list)
    invalid_conditions: list[str] = field(default_factory=list)
    stop_reference: str | None = None
    take_profit_reference: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision,
            "strength": self.strength,
            "reasons": list(self.reasons),
            "missing_data": list(self.missing_data),
            "entry_conditions": list(self.entry_conditions),
            "invalid_conditions": list(self.invalid_conditions),
            "stop_reference": self.stop_reference,
            "take_profit_reference": self.take_profit_reference,
        }


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _quote(snapshot: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(snapshot, Mapping):
        return {}
    value = snapshot.get("quote", {})
    return value if isinstance(value, Mapping) else {}


def _reward_pct_from_quote(quote: Mapping[str, Any]) -> float | None:
    high_to_current_pct = _as_float(quote.get("high_to_current_pct"))
    if high_to_current_pct is None:
        return None
    # Existing snapshots express this as negative when current is below the high.
    if high_to_current_pct <= 0:
        return abs(high_to_current_pct)
    # Current above the known high leaves no deterministic upside reference.
    return 0.0


def _risk_pct_from_quote(quote: Mapping[str, Any]) -> float | None:
    low_to_current_pct = _as_float(quote.get("low_to_current_pct"))
    if low_to_current_pct is None:
        return None
    return max(low_to_current_pct, 0.0)


def _is_late_chase_zone(quote: Mapping[str, Any]) -> bool:
    reward_pct = _reward_pct_from_quote(quote)
    risk_pct = _risk_pct_from_quote(quote)
    if reward_pct is None or risk_pct is None:
        return False
    return (
        reward_pct <= LATE_CHASE_HIGH_DISTANCE_PCT
        and risk_pct >= LATE_CHASE_MIN_BOUNCE_FROM_LOW_PCT
    )


def _format_pct(value: float) -> str:
    return f"{value:.2f}%"


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


def _base_stop_reference(signal_result: SignalStateResult) -> str | None:
    if signal_result.state == "valid_signal":
        return "RSI 30m <= 30 + BB 하단 근접 시 직전 저점 기준"
    if signal_result.state == "near_signal":
        return "RSI 30m 30~35 또는 BB 진입 시 확인 후 설정"
    return None


def _build_stop_reference(
    signal_result: SignalStateResult,
    decision: str,
    snapshot: Mapping[str, Any] | None = None,
) -> str | None:
    """Build stop loss reference price hint from signal state and snapshot quote."""
    if decision != "진입" and decision != "대기":
        return None

    base_reference = _base_stop_reference(signal_result) or "intraday low reference"
    risk_pct = _risk_pct_from_quote(_quote(snapshot))
    if risk_pct is not None:
        return f"{base_reference}; estimated stop distance {_format_pct(risk_pct)}"

    # This is a fixture-only module, so we can't compute actual stop prices
    # without a caller-provided quote. Return a descriptive reference.
    return base_reference


def _build_take_profit_reference(
    decision: str,
    snapshot: Mapping[str, Any] | None = None,
) -> str | None:
    """Build take-profit reference from caller-provided quote only."""
    if decision != "진입" and decision != "대기":
        return None

    reward_pct = _reward_pct_from_quote(_quote(snapshot))
    if reward_pct is None:
        return None
    return f"recent intraday high reference; estimated upside {_format_pct(reward_pct)}"


def _apply_risk_reward_gate(
    decision: str,
    reasons: list[str],
    entry_conditions: list[str],
    invalid_conditions: list[str],
    snapshot: Mapping[str, Any] | None,
) -> tuple[str, list[str], list[str], list[str]]:
    if decision != "진입":
        return decision, reasons, entry_conditions, invalid_conditions

    quote = _quote(snapshot)
    risk_pct = _risk_pct_from_quote(quote)
    reward_pct = _reward_pct_from_quote(quote)

    if risk_pct is None or reward_pct is None:
        return decision, reasons, entry_conditions, invalid_conditions

    ratio = reward_pct / risk_pct if risk_pct > 0 else float("inf")
    risk_summary = (
        "risk/reward gate: "
        f"upside {_format_pct(reward_pct)}, stop distance {_format_pct(risk_pct)}, "
        f"reward/risk {ratio:.2f}"
    )

    if risk_pct > MAX_STOP_DISTANCE_PCT:
        decision = "제외"
        reasons.append(f"리스크/보상 제외: 손절폭 {_format_pct(risk_pct)} > {_format_pct(MAX_STOP_DISTANCE_PCT)}")
        invalid_conditions.append(risk_summary)
        invalid_conditions.append("stop distance too wide for local intraday entry")
        return decision, reasons, entry_conditions, invalid_conditions

    if ratio <= MIN_REWARD_RISK_RATIO:
        decision = "제외"
        reasons.append(f"리스크/보상 제외: 기대수익이 손실위험보다 크지 않음 ({ratio:.2f})")
        invalid_conditions.append(risk_summary)
        invalid_conditions.append("expected upside must exceed downside risk")
        return decision, reasons, entry_conditions, invalid_conditions

    if _is_late_chase_zone(quote):
        decision = "대기"
        reasons.append("리스크/보상 대기: 당일 고점 근처 추격 진입 구간")
        invalid_conditions.append(risk_summary)
        invalid_conditions.append("late-chase guard: wait for pullback confirmation")
        return decision, reasons, entry_conditions, invalid_conditions

    entry_conditions.append(risk_summary)
    entry_conditions.append("risk/reward gate passed")
    return decision, reasons, entry_conditions, invalid_conditions


def evaluate_intraday_decision(
    signal_result: SignalStateResult,
    snapshot: Mapping[str, Any] | None = None,
) -> IntradayDecisionResult:
    """Evaluate a local intraday decision from a signal state result.

    This function is deterministic and side-effect free. It uses the
    SignalStateResult fields and optional caller-provided snapshot quote values
    to produce an actionable intraday decision.
    """
    # Validate input state
    if signal_result.state not in SIGNAL_STATES:
        raise ValueError(f"Unknown signal state: {signal_result.state}")

    # Map to base decision
    decision = SIGNAL_TO_DECISION[signal_result.state]

    # Build output fields
    reasons = _build_reasons(signal_result, decision)
    missing_data = _dedupe(signal_result.missing_data)
    entry_conditions = _build_entry_conditions(signal_result)
    invalid_conditions = _build_invalid_conditions(signal_result)

    decision, reasons, entry_conditions, invalid_conditions = _apply_risk_reward_gate(
        decision,
        reasons,
        entry_conditions,
        invalid_conditions,
        snapshot,
    )
    strength = _calculate_strength(signal_result, decision)
    stop_reference = _build_stop_reference(signal_result, decision, snapshot)
    take_profit_reference = _build_take_profit_reference(decision, snapshot)

    return IntradayDecisionResult(
        decision=decision,
        strength=strength,
        reasons=_dedupe(reasons),
        missing_data=missing_data,
        entry_conditions=_dedupe(entry_conditions),
        invalid_conditions=_dedupe(invalid_conditions),
        stop_reference=stop_reference,
        take_profit_reference=take_profit_reference,
    )


__all__ = [
    "DECISION_TYPES",
    "LATE_CHASE_HIGH_DISTANCE_PCT",
    "LATE_CHASE_MIN_BOUNCE_FROM_LOW_PCT",
    "MAX_STOP_DISTANCE_PCT",
    "MIN_REWARD_RISK_RATIO",
    "SIGNAL_TO_DECISION",
    "IntradayDecisionResult",
    "evaluate_intraday_decision",
]
