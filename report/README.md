# Report writing guide

This directory contains market close summaries, postmarket reviews, and related trading review reports.

Use this guide before creating or editing files under `report/`.

## Report types and filenames

| Report type | Filename pattern | Purpose |
|---|---|---|
| Close summary | `YYYY-MM-DD-close-summary.md` | Same-day market close summary, key stock table, technical snapshot, and next-session checklist. |
| Postmarket review | `YYYY-MM-DD-postmarket-review.md` | Deeper review of what worked, what failed, and what must change before the next trading day. |

Do not mix strategy changes into report files. If a report discovers a strategy update, document the lesson in the report and update the strategy file in a separate PR unless the issue explicitly says otherwise.

## Required source and basis labels

Every important number must identify what it is based on.

| Field | Required handling |
|---|---|
| Index level and daily change | Label whether verified quote, conversation-derived, or estimated. |
| Large-cap price and percent change | Label as previous-close based when using daily quote data. |
| Stock row percent change | State whether previous-close based, open/candle based, high-to-current, or low-to-current. |
| Volume | Use raw numeric value when available; label estimated values clearly. |
| RSI / Bollinger / moving averages | State timeframe, such as 1-minute, 30-minute, or daily. |
| Brokerage flow | Use net quantity only when net-quantity data is available. |
| Futures investor flow | Keep unavailable unless a confirmed futures-specific source exists. |

Allowed uncertainty labels:

- `verified`: confirmed from a quote/report source;
- `conversation-derived`: copied from a conversation note or earlier manual observation;
- `estimated`: approximate value and not verified;
- `unavailable`: not supported by the current confirmed source.

Do not use `~` by itself. Write `estimated: ~7,950pt` or explain the estimate in the note column.

## Close-summary required sections

A close summary should include, in this order:

1. report title with date and time;
2. market index table;
3. watched-stock close table;
4. supply/demand and market features;
5. technical snapshot;
6. next-session strategy checklist;
7. report quality notes or unresolved data gaps.

The watched-stock table must not contain duplicate rows for the same stock. If the same stock needs two comments, keep one row and combine the notes.

## Postmarket-review required sections

A postmarket review should include:

1. report title, 작성일, 시장, and 매매 여부;
2. market flow summary;
3. what went well;
4. what went wrong;
5. fixes already made;
6. lessons for the next trading day;
7. related files.

Separate facts from interpretation. Do not turn a review lesson into a forced trading command.

## Consistency checks before saving

Before saving any report, check:

- no duplicate stock rows in the same table;
- index and large-cap numbers do not conflict across same-date report files;
- every estimated value is labeled as estimated;
- every conversation-derived number is labeled as conversation-derived;
- all percent changes identify their basis;
- RSI and Bollinger values include timeframe;
- brokerage net flow is not inferred from ranking-only data;
- KOSPI200 futures foreign/institutional flow is not replaced with stock foreign flow, program trading data, or index movement;
- report conclusions do not conflict with `docs/trading-analysis-quality-guardrails.md`.

## Futures investor-flow policy

KOSPI200 futures foreign/institutional net flow must stay `unavailable` unless a confirmed futures-specific source is added.

Do not substitute unavailable futures flow with:

- stock foreign flow;
- program trading data;
- empty futures response values;
- broad market index movement;
- Samsung Electronics or SK hynix movement.

Required wording when unavailable:

```text
KOSPI200 futures foreign/institutional net flow is unavailable from the current confirmed source. This report does not substitute stock foreign flow or program trading data for it.
```

## Trading-analysis guide dependency

Before writing report conclusions, read:

```text
docs/trading-analysis-quality-guardrails.md
```

In particular, apply these rules:

- separate observed data, derived indicators, interpretation, and action support;
- do not override valid RSI 30 signals with vague market fear;
- use `ka10002` net quantity for brokerage net flow;
- do not erase signed sell quantities with `abs()`;
- label price-change basis clearly;
- keep unsupported futures investor flow unavailable.

## Local validation

For report-only changes, run:

```bash
python3 tests/run_all.py
git status --short
```

If a report change also edits conversation archives, run:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git status --short
```

Default validation must remain local-only. Do not add Kiwoom credential requirements, network access, or live market API calls to the default test path.
