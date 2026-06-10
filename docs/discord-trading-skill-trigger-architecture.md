# Discord trading skill trigger architecture

This document defines the first implementation contract for the Discord trading assistant workflow.

The workflow should prefer natural-language skill triggers over slash-command-only operation. The user should be able to trade in a normal Discord stock thread, while the assistant detects important words, symbols, and trading situations.

## Goals

- Let the user speak naturally in the Discord stock thread.
- Detect trading intents without requiring memorized slash commands.
- Build local market snapshots from the existing Kiwoom REST/OpenAPI design when running locally.
- Support 5-minute and 30-minute chart/snapshot review.
- Generate ChatGPT web handoff packets for second-pass review outside Discord.
- Keep repository tests local-only and free of Kiwoom credentials, network access, and live market API calls.

## Non-goals

- Do not execute live trades by default.
- Do not require live market access in repository tests.
- Do not make GitHub-hosted checks depend on Kiwoom, Discord, or OpenAI credentials.
- Do not replace user judgment with automatic buy/sell instructions.
- Do not rely only on slash commands for normal operation.

## Core architecture

```text
Discord stock thread
  -> Message watcher
  -> Natural-language trigger router
  -> Active-symbol resolver
  -> Local market snapshot builder
  -> Rule-based signal engine
  -> Fast Discord analyst
  -> Risk/review card builder
  -> Optional ChatGPT handoff packet
  -> Review logger
```

## Natural-language trigger words

Initial Korean trigger words:

| Trigger | Intent |
|---|---|
| `신호` | Check whether a technical signal is valid. |
| `살까` | Build an entry checklist, not an automatic buy command. |
| `진입` | Build an entry checklist. |
| `손절` | Estimate invalidation and stop-reference levels. |
| `익절` | Estimate take-profit reference levels. |
| `수급` | Check brokerage/investor flow source and meaning. |
| `차트` | Review chart structure or build a chart snapshot. |
| `RSI` | Check RSI timeframe and threshold. |
| `BB` | Check Bollinger Band location. |
| `숏커버` | Check short-cover track conditions. |
| `위험` | Run risk-officer review. |
| `복기` | Save or summarize a review event. |
| `GPT` | Build a ChatGPT handoff packet. |
| `검토` | Build a review card or handoff packet depending on context. |

English aliases may be added later, but Korean triggers are the default because the live trading conversation is Korean.

## Symbol detection

A trigger should become stock-specific when the message includes a known symbol, Korean stock name, or alias.

Examples:

```text
HPSP 신호
두산테스나 진입
ISC 수급
원익IPS 위험
리노공업 차트
```

If no symbol is mentioned, use the current `active_symbol` from recent thread context.

Example:

```text
User: HPSP 지금 어때?
Assistant: ...
User: 신호 왔어?
```

The second message should resolve to `active_symbol = HPSP`.

## Active-symbol rules

The active symbol should update when:

- the user mentions a known stock name or ticker;
- a market snapshot is generated for a stock;
- a decision card is generated for a stock;
- a user explicitly switches focus, such as `다음은 ISC`.

The active symbol should not update when:

- the message only references broad market conditions;
- the model mentions an unrelated stock as a comparison;
- a report lists multiple watchlist stocks without a user focus change.

## Auto-reply policy

Avoid noisy auto-replies. The assistant should not produce a long response for every trigger.

### Immediate short reply

Use a short reply when the user clearly asks for action support:

```text
HPSP 신호 왔어?
두산테스나 들어가도 되나?
ISC 손절 어디?
```

### Offer review card instead of long reply

If intent is ambiguous, offer compact options:

```text
분석 가능: [신호검증] [리스크] [수급] [GPT패킷]
```

### Stay quiet

Stay quiet when:

- the trigger appears in a quoted old message;
- the user is casually discussing an old review;
- the message has no stock context and no active symbol;
- another assistant has already answered the same event.

## Local market snapshot builder

Local market snapshots may use the existing Kiwoom REST/OpenAPI design on the user's machine.

The repository contract must keep this boundary clear:

- local runtime may call Kiwoom REST/OpenAPI when explicitly configured by the user;
- GitHub, docs-only PRs, and default tests must not call Kiwoom;
- default tests must not require network access or live market credentials;
- live data fields should be labeled by source and timestamp.

## Snapshot contents

A stock-specific snapshot should prefer this shape:

```json
{
  "as_of": "2026-06-11T10:35:00+09:00",
  "symbol": "HPSP",
  "active_strategy": ["RSI_30", "short_cover_track"],
  "quote": {
    "current_price": null,
    "previous_close_change_pct": null,
    "open_or_candle_change_pct": null,
    "high_to_current_pct": null,
    "low_to_current_pct": null,
    "volume": null,
    "source": "local_kiwoom_or_unavailable"
  },
  "indicators": {
    "rsi_1m": null,
    "rsi_5m": null,
    "rsi_30m": null,
    "bb_5m_pct": null,
    "bb_30m_pct": null,
    "moving_average_state": null
  },
  "flow": {
    "brokerage_net_quantity_source": "ka10002_or_unavailable",
    "brokerage_net_quantity": null,
    "futures_foreign_institutional_flow": "unavailable"
  },
  "data_gaps": []
}
```

Use `null` and `unavailable` instead of inventing values.

## 5-minute and 30-minute chart support

The first chart support target is not tick-level scalping. The default review should focus on:

- 5-minute trend and immediate support/resistance;
- 30-minute trend and broader signal context;
- RSI threshold checks;
- Bollinger Band location;
- volume expansion or contraction;
- high-to-current and low-to-current context.

Chart images may be generated locally and attached to a handoff packet, but the text snapshot must still include the numeric basis.

## Signal engine responsibilities

The signal engine should be rule-based before the model interprets anything.

Required rule outputs:

- `valid_signal`
- `near_signal`
- `conflicted_signal`
- `no_signal`
- `unavailable`

Example:

```json
{
  "symbol": "HPSP",
  "signal_type": "RSI_30",
  "timeframe": "1m",
  "state": "valid_signal",
  "basis": "rsi_1m <= 30",
  "conflicts": ["market_index_weak"],
  "missing_data": []
}
```

The model may explain conflicts and risk, but should not erase a valid rule-based signal with vague market fear.

## Model role separation

| Role | Responsibility |
|---|---|
| Rule-based signal engine | Determine whether configured signal rules are met. |
| Fast Discord analyst | Explain current state quickly in the thread. |
| Risk reviewer | Find conflicts, missing data, unsupported claims, and rule violations. |
| Scribe | Write summaries, close reports, and review notes. |
| Evaluator | Score prior model decisions after outcomes are known. |
| ChatGPT web reviewer | Review structured handoff packets pasted by the user. |

Do not require all roles to be separate models at first. The first implementation may use one model plus rule-based checks, but the message contracts should keep the roles separate.

## Decision card format

Discord responses should prefer decision cards over free-form advice.

```text
[Decision Card]

Symbol: HPSP
State: valid_signal / conflicted_signal / near_signal / no_signal / unavailable
Trigger: RSI_30 / short_cover_track / risk_review / flow_review
Source time: 2026-06-11 10:35 KST

Observed data:
- Price:
- Previous-close change:
- 5m RSI:
- 30m RSI:
- BB location:
- Volume:
- ka10002 net flow:
- Futures flow: unavailable

Conflicts:
- ...

Checklist:
1. ...
2. ...
3. ...

Model role:
- Provide checkpoints only. User makes the decision.
```

## ChatGPT handoff trigger

When the user says `GPT`, `검토`, `ChatGPT`, or `정리해서 넘겨줘`, the assistant should build a handoff packet instead of only answering in Discord.

The handoff packet contract is defined in:

```text
docs/chatgpt-handoff-packet-contract.md
```

## GitHub handoff location

If the user wants persistent review, save handoff packets under:

```text
handoff/YYYY-MM-DD/HHMM-symbol-purpose.md
```

Examples:

```text
handoff/2026-06-11/1035-HPSP-gpt-review.md
handoff/2026-06-11/1305-doosan-tesna-rsi30.md
handoff/2026-06-11/1505-short-cover-track.md
```

Do not commit secret tokens, account numbers, raw credentials, or private brokerage identifiers.

## Safety and judgment policy

The assistant should provide decision support, not command execution.

Preferred wording:

```text
현재 데이터로는 신호는 유효하지만 충돌 요인이 있습니다. 판단에 필요한 체크포인트를 정리하겠습니다.
```

Avoid unsupported directives such as:

```text
무조건 사세요.
무조건 관망하세요.
지금 매도하세요.
```

Hard stops are allowed only when a documented rule violation or missing critical data makes the analysis invalid.

## Validation policy

Docs-only changes should validate with:

```bash
python3 tests/run_all.py
git status --short
```

Default validation must remain local-only. Do not add Kiwoom credential requirements, network access, Discord access, OpenAI access, or live market API calls to the default test path.
