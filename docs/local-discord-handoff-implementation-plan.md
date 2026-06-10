# Local Discord handoff implementation plan

This document defines the staged implementation plan for the local Discord trading handoff workflow.

It is intentionally docs-only. Production code should be added in later, smaller PRs after this plan is accepted.

## Goal

Build a local workflow that can turn a natural Discord trading conversation into a structured ChatGPT review handoff packet.

The first implementation should support:

- natural-language trigger detection;
- active-symbol tracking;
- local market snapshot injection;
- quick and full handoff packet generation;
- `handoff/YYYY-MM-DD/` file output;
- optional chart image and JSON snapshot references;
- model answer capture;
- postmarket review logging;
- local-only tests with fixtures.

## Non-goals

- No live trade execution.
- No default network calls in tests.
- No default dependency on Discord, Kiwoom, OpenAI, or live market access.
- No strategy changes in the first implementation slice.
- No rewrite of existing reports or conversation archives.

## Related guides

Read these first:

- `docs/discord-trading-skill-trigger-architecture.md`
- `docs/chatgpt-handoff-packet-contract.md`
- `handoff/README.md`
- `docs/trading-analysis-quality-guardrails.md`
- `docs/local-regression-checks.md`

## Proposed module boundaries

The exact file names may change, but the implementation should keep these responsibilities separate.

| Module | Responsibility |
|---|---|
| Message watcher | Receive or import Discord thread messages. |
| Trigger router | Detect natural-language trigger words and intent. |
| Active-symbol resolver | Decide which stock the current message refers to. |
| Snapshot builder | Attach local quote, indicator, flow, and chart summary data. |
| Signal state engine | Convert snapshot values into rule states such as valid, near, conflicted, unavailable. |
| Packet generator | Render quick/full Markdown handoff packets. |
| Handoff writer | Save packets and optional snapshot files under `handoff/YYYY-MM-DD/`. |
| Model answer capture | Preserve the current Discord model answer for later review. |
| Postmarket logger | Group important events for later reports and evaluation. |

## Staged implementation

### Stage 1: Fixture-only trigger router

Implement trigger detection without Discord integration.

Inputs:

- plain text message;
- optional recent thread context;
- optional known symbol list.

Outputs:

- detected trigger words;
- intent label;
- detected symbol, if any;
- whether the assistant should reply, offer options, or stay quiet.

Example output:

```json
{
  "message": "HPSP 신호 왔어?",
  "triggers": ["신호"],
  "intent": "signal_review",
  "symbol": "HPSP",
  "reply_mode": "short_review"
}
```

Test policy:

- fixture-only tests;
- no Discord connection;
- no live market data;
- no secrets.

### Stage 2: Active-symbol resolver

Implement active-symbol state from recent messages.

Rules:

- explicit stock mention updates active symbol;
- direct follow-up without a stock uses active symbol;
- broad market comments should not update active symbol;
- model comparisons should not accidentally switch active symbol;
- user focus-switch phrases should update active symbol.

Example:

```text
User: HPSP 지금 어때?
Assistant: ...
User: 신호 왔어?
```

The second user message resolves to `HPSP`.

Test policy:

- use small text fixtures;
- include Korean stock names and ASCII aliases;
- include no-symbol follow-up cases;
- include multi-symbol watchlist cases.

### Stage 3: Snapshot schema and fixture builder

Define a local market snapshot schema before wiring any live provider.

The snapshot should match the existing handoff contract:

```json
{
  "as_of": "2026-06-11T10:35:00+09:00",
  "symbol": "HPSP",
  "quote": {
    "current_price": null,
    "previous_close_change_pct": null,
    "open_or_candle_change_pct": null,
    "high_to_current_pct": null,
    "low_to_current_pct": null,
    "volume": null,
    "source": "fixture_or_local"
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

The first code slice should support fixture snapshots only.

Live local provider wiring should be a later explicit slice.

### Stage 4: Rule-based signal state engine

Implement rule outputs before model interpretation.

Allowed states:

- `valid_signal`
- `near_signal`
- `conflicted_signal`
- `no_signal`
- `unavailable`

Initial supported checks:

- RSI 30 check;
- Bollinger Band location check;
- short-cover track placeholder;
- flow unavailable handling;
- missing-data handling.

The signal engine should not produce buy/sell instructions.

It should produce a state and explain missing or conflicting data.

### Stage 5: Quick handoff packet generator

Generate compact Markdown suitable for pasting into ChatGPT web during active market hours.

Required fields:

- time KST;
- symbol;
- user question;
- trigger intent;
- signal state;
- active strategy;
- RSI values if available;
- Bollinger Band values if available;
- price-change basis;
- volume;
- `ka10002` net flow or `unavailable`;
- futures flow `unavailable` unless confirmed;
- recent Discord excerpt;
- current model answer if available;
- questions for ChatGPT.

Test policy:

- compare Markdown output against fixture snapshots;
- ensure unavailable fields are not omitted silently;
- ensure no bare `~` estimates.

### Stage 6: Full handoff packet generator

Generate the complete format defined in:

```text
docs/chatgpt-handoff-packet-contract.md
```

Full packets should be used for:

- missed signal review;
- important entry/exit decision review;
- current model answer audit;
- chart review;
- postmarket review source packet.

Test policy:

- validate required section headings;
- validate applicable rules are included;
- validate known data gaps are explicit;
- validate expected output format is present.

### Stage 7: Handoff file writer

Write packets to:

```text
handoff/YYYY-MM-DD/HHMM-symbol-purpose.md
```

Rules:

- use KST for date and time;
- sanitize filenames;
- prefer stable ASCII aliases if needed;
- do not overwrite an existing packet unless explicitly requested;
- optionally write `*-snapshot.json` next to the Markdown packet;
- optionally reference chart images without committing private screenshots.

Test policy:

- use a temporary directory;
- validate path generation;
- validate overwrite protection;
- validate filename sanitization.

### Stage 8: Chart artifact references

Add support for referencing chart images and JSON snapshots.

Recommended optional outputs:

```text
handoff/YYYY-MM-DD/HHMM-symbol-purpose.md
handoff/YYYY-MM-DD/HHMM-symbol-5m.png
handoff/YYYY-MM-DD/HHMM-symbol-30m.png
handoff/YYYY-MM-DD/HHMM-symbol-snapshot.json
```

Initial implementation may only write references, not generate images.

Image generation can be a later slice if local OHLCV data is available.

### Stage 9: Model answer capture

Capture the current Discord model answer so ChatGPT can review it.

The captured answer should include:

- timestamp;
- model name if known;
- exact text;
- associated symbol;
- associated trigger;
- whether the user flagged it for review.

Do not capture unrelated private messages.

### Stage 10: Postmarket review logger

Group important intraday handoff packets into later review material.

Good candidates:

- missed RSI 30 signal;
- conflicted signal;
- model answer that may have violated guardrails;
- short-cover track event;
- chart pattern that should be compared later;
- user decision point with outcome.

This logger should not edit report files in the first slice.

A later slice may use these packets to draft or improve market reports.

## Local provider boundary

Local market data providers should be injected behind an interface.

The default implementation in tests should be a fixture provider.

Suggested provider states:

| State | Meaning |
|---|---|
| `fixture` | Static local test data. |
| `local_stub` | Local no-op provider for development. |
| `local_live` | Explicit local runtime connected to user-approved market data source. |
| `unavailable` | Source not configured or unavailable. |

Default tests must use `fixture` or `local_stub` only.

## Secret-free development rules

Do not commit:

- access keys;
- tokens;
- account numbers;
- credential files;
- raw private screenshots;
- personal identifiers unrelated to the trade.

If a test needs realistic data, use sanitized fixtures.

If a handoff packet references private chart images, write `local only, not committed` in the Markdown packet.

## Suggested first code PR

The first code PR should be small:

```text
Add fixture-only Discord trigger router
```

Suggested scope:

- one parser/router module;
- one fixture file;
- focused tests for trigger words, active symbol basics, and reply mode;
- no Discord integration;
- no live market provider;
- no handoff file writer yet.

## Suggested second code PR

```text
Add ChatGPT quick handoff packet generator
```

Suggested scope:

- fixture snapshot input;
- quick Markdown output;
- required fields present;
- unavailable fields retained;
- tests only use fixtures.

## Suggested third code PR

```text
Add handoff file writer
```

Suggested scope:

- KST path builder;
- filename sanitization;
- write Markdown to temporary or configured local path;
- no overwrite by default;
- fixture-only tests.

## Acceptance checklist before code begins

- Natural-language triggers documented.
- Handoff packet contract documented.
- Handoff directory storage rules documented.
- Implementation stages documented.
- First code slice is fixture-only.
- Default tests remain local-only.
- No live execution, no credential requirement, no network requirement.

## Validation

Docs-only changes should validate with:

```bash
python3 tests/run_all.py
git status --short
```

If future code slices modify conversation archives, also run:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git status --short
```
