#!/usr/bin/env python3
"""
Fixture-only Discord trading trigger router.

This module does not connect to Discord, Kiwoom, OpenAI, or any network
service. It converts plain text messages plus optional local context into small
intent results for later handoff workflow slices.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence


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
FOCUS_SWITCH_TERMS = ("다음은", "이번엔", "이번에는", "이제", "봐줘", "보자", "체크")
MODEL_COMPARISON_TERMS = ("모델", "GPT", "ChatGPT", "니모트론", "Nimotron", "답변", "비교")


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


@dataclass(frozen=True)
class ActiveSymbolResolution:
    active_symbol: str | None
    source: str = "none"
    message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "active_symbol": self.active_symbol,
            "source": self.source,
            "message": self.message,
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


def _has_broad_market_context(message: str) -> bool:
    return any(term in message for term in BROAD_MARKET_TERMS)


def _has_model_comparison_context(message: str) -> bool:
    return any(_contains_word(message, term) for term in MODEL_COMPARISON_TERMS)


def _has_focus_switch_context(message: str) -> bool:
    return any(term in message for term in FOCUS_SWITCH_TERMS)


def resolve_active_symbol(
    messages: Sequence[str],
    *,
    current_active_symbol: str | None = None,
    symbol_aliases: dict[str, str] | None = None,
) -> ActiveSymbolResolution:
    """Resolve active symbol from recent plain text messages.

    This is fixture-only conversation state logic. It does not connect to
    Discord or fetch market data. It walks recent messages in order and updates
    the active symbol only when a message clearly points to a stock, while broad
    market-only or model-comparison messages preserve the prior active symbol.
    """
    active_symbol = current_active_symbol
    source = "provided" if current_active_symbol else "none"
    source_message = None

    for raw_message in messages:
        message = raw_message.strip()
        if not message:
            continue

        explicit_symbol = detect_symbol(message, symbol_aliases)
        if explicit_symbol is None:
            continue

        if _has_broad_market_context(message) and not _has_focus_switch_context(message):
            continue

        if _has_model_comparison_context(message) and not _has_focus_switch_context(message):
            continue

        active_symbol = explicit_symbol
        source_message = message
        source = "focus_switch" if _has_focus_switch_context(message) else "explicit_symbol"

    return ActiveSymbolResolution(
        active_symbol=active_symbol,
        source=source,
        message=source_message,
    )


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
    recent_messages: Sequence[str] | None = None,
    symbol_aliases: dict[str, str] | None = None,
) -> TriggerRoute:
    """Route one plain text message into a fixture-only trigger result.

    The router is intentionally deterministic and side-effect free. It does not
    read files, connect to Discord, fetch prices, write handoff packets, or use
    external services.
    """
    normalized_message = message.strip()
    resolved_active_symbol = active_symbol
    if recent_messages is not None:
        resolved_active_symbol = resolve_active_symbol(
            recent_messages,
            current_active_symbol=active_symbol,
            symbol_aliases=symbol_aliases,
        ).active_symbol

    triggers = detect_triggers(normalized_message)
    explicit_symbol = detect_symbol(normalized_message, symbol_aliases)
    used_active_symbol = explicit_symbol is None and bool(resolved_active_symbol) and bool(triggers)
    symbol = explicit_symbol or (resolved_active_symbol if used_active_symbol else None)
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
    "ActiveSymbolResolution",
    "DEFAULT_SYMBOL_ALIASES",
    "TRIGGER_TO_INTENT",
    "TriggerRoute",
    "detect_symbol",
    "detect_triggers",
    "resolve_active_symbol",
    "resolve_intent",
    "resolve_reply_mode",
    "route_message",
]
