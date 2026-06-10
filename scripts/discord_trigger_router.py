#!/usr/bin/env python3
"""
Fixture-only Discord trading trigger router.

This module does not connect to Discord, Kiwoom, OpenAI, or any network
service. It converts one plain text message plus optional local context into a
small intent result for later handoff workflow slices.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


TRIGGER_TO_INTENT = {
    "신호": "signal_review",
    "RSI": "signal_review",
    "BB": "signal_review",
    "차트": "chart_review",
    "수급": "flow_review",
    "살까": "entry_check",
    "진입": "entry_check",
    "손절": "stop_check",
    "익절": "take_profit_check",
    "숏커버": "short_cover_review",
    "위험": "risk_review",
    "복기": "review_log",
    "GPT": "chatgpt_handoff",
    "검토": "review_request",
}

INTENT_PRIORITY = [
    "chatgpt_handoff",
    "risk_review",
    "entry_check",
    "stop_check",
    "take_profit_check",
    "signal_review",
    "short_cover_review",
    "flow_review",
    "chart_review",
    "review_log",
    "review_request",
]

DEFAULT_SYMBOL_ALIASES = {
    "HPSP": "HPSP",
    "두산테스나": "두산테스나",
    "ISC": "ISC",
    "원익IPS": "원익IPS",
    "리노공업": "리노공업",
}

BROAD_MARKET_TERMS = ("코스피", "코스닥", "시장", "지수", "선물", "환율")


@dataclass(frozen=True)
class TriggerRoute:
    message: str
    triggers: list[str] = field(default_factory=list)
    intent: str = "no_action"
    symbol: str | None = None
    reply_mode: str = "stay_quiet"
    used_active_symbol: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "message": self.message,
            "triggers": list(self.triggers),
            "intent": self.intent,
            "symbol": self.symbol,
            "reply_mode": self.reply_mode,
            "used_active_symbol": self.used_active_symbol,
        }


def _contains_word(message: str, needle: str) -> bool:
    if needle.isascii():
        return needle.lower() in message.lower()
    return needle in message


def detect_triggers(message: str) -> list[str]:
    """Return configured trigger words found in message, preserving config order."""
    return [trigger for trigger in TRIGGER_TO_INTENT if _contains_word(message, trigger)]


def resolve_intent(triggers: Iterable[str]) -> str:
    """Resolve one intent from trigger words using deterministic priority."""
    intents = {TRIGGER_TO_INTENT[trigger] for trigger in triggers}
    for intent in INTENT_PRIORITY:
        if intent in intents:
            return intent
    return "no_action"


def detect_symbol(
    message: str,
    symbol_aliases: dict[str, str] | None = None,
) -> str | None:
    """Return the first known symbol or alias found in a message."""
    aliases = symbol_aliases or DEFAULT_SYMBOL_ALIASES
    for alias, canonical in aliases.items():
        if _contains_word(message, alias):
            return canonical
    return None


def _is_broad_market_only(message: str, triggers: list[str], symbol: str | None) -> bool:
    if symbol is not None or not triggers:
        return False
    return any(term in message for term in BROAD_MARKET_TERMS)


def resolve_reply_mode(intent: str, symbol: str | None, broad_market_only: bool) -> str:
    """Decide how noisy the assistant should be for the routed message."""
    if intent == "no_action":
        return "stay_quiet"
    if symbol:
        if intent in {"signal_review", "entry_check", "stop_check", "take_profit_check"}:
            return "short_review"
        if intent == "chatgpt_handoff":
            return "build_handoff_packet"
        return "offer_review_card"
    if broad_market_only:
        return "offer_market_review"
    return "stay_quiet"


def route_message(
    message: str,
    *,
    active_symbol: str | None = None,
    symbol_aliases: dict[str, str] | None = None,
) -> TriggerRoute:
    """Route one plain text message into a fixture-only trigger result.

    The router is intentionally deterministic and side-effect free. It does not
    read files, connect to Discord, fetch prices, write handoff packets, or use
    external services.
    """
    normalized_message = message.strip()
    triggers = detect_triggers(normalized_message)
    explicit_symbol = detect_symbol(normalized_message, symbol_aliases)
    used_active_symbol = explicit_symbol is None and bool(active_symbol) and bool(triggers)
    symbol = explicit_symbol or (active_symbol if used_active_symbol else None)
    intent = resolve_intent(triggers)
    broad_market_only = _is_broad_market_only(normalized_message, triggers, symbol)
    reply_mode = resolve_reply_mode(intent, symbol, broad_market_only)

    return TriggerRoute(
        message=normalized_message,
        triggers=triggers,
        intent=intent,
        symbol=symbol,
        reply_mode=reply_mode,
        used_active_symbol=used_active_symbol,
    )


__all__ = [
    "DEFAULT_SYMBOL_ALIASES",
    "TRIGGER_TO_INTENT",
    "TriggerRoute",
    "detect_symbol",
    "detect_triggers",
    "resolve_intent",
    "resolve_reply_mode",
    "route_message",
]
