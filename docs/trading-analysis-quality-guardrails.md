# Trading analysis quality guardrails

This guide converts the 2026-06-10 trading review mistakes into repeatable rules for future market analysis.

The goal is not to make the agent more aggressive. The goal is to make every trading answer more data-grounded, less overconfident, and easier for the user to audit before deciding.

## Scope

Use this guide when preparing or reviewing:

- intraday market summaries;
- RSI 30 entry checks;
- short-cover track checks;
- brokerage net-flow interpretation;
- postmarket reports;
- next-day trading plans.

This guide is documentation only. It must not add live trading behavior, live API calls, Kiwoom credential requirements, or network-dependent default validation.

## Core rule: separate data from judgment

Every trading analysis should keep these layers separate:

| Layer | Meaning | Required handling |
|---|---|---|
| Observed data | Raw values from a named source. | State the source and basis. |
| Derived indicator | RSI, Bollinger position, high/low distance, volume ratio, or net flow. | State the formula/input basis when ambiguity exists. |
| Interpretation | What the data may imply. | Mark as interpretation, not fact. |
| Action support | Entry, pass, wait, size, exit, or risk checklist. | Present as decision support, not forced instruction. |

Do not collapse these layers into one confident conclusion. If the data is incomplete, say exactly which field is missing.

## Mistake patterns to prevent

### 1. Do not override a valid RSI 30 signal with vague market fear

The 2026-06-10 review identified a missed Doosan Tesna opportunity where a valid 1-minute RSI 30 signal was blocked by a broad “falling knife / wait” narrative.

Correct behavior:

1. State the signal first.
2. State conflicts second.
3. State risk controls third.
4. Leave the final decision to the user.

Preferred format:

```text
[Signal] 1-minute RSI is at or below 30.
[Conflict] Broad market is sharply down / supply is weak / volatility is high.
[Risk control] Use pre-defined size, stop, and invalidation level.
[Decision support] This is a valid system signal with elevated risk, not an automatic pass.
```

Forbidden behavior:

```text
Market is scary, so ignore the RSI 30 signal.
```

### 2. Use net quantity, not brokerage ranking, for brokerage flow

For brokerage flow analysis:

- `ka10002` net quantity is the basis for net buy/sell interpretation.
- `ka10040` ranking must not be treated as net quantity.
- If only ranking data is available, label it as ranking only and do not infer net buy/sell.

Required wording when data is incomplete:

```text
Brokerage ranking is available, but net quantity is not available. I cannot call this Shinhan/Kiwoom net buying or net selling without net-quantity data.
```

### 3. Do not erase the sign of sell quantities

If an API returns signed sell quantities, do not run `abs()` before net-flow interpretation unless the API contract explicitly requires it.

Required checks:

- preserve signed quantities;
- document whether negative values mean sell-side flow;
- compute net flow from the documented field semantics;
- never reverse net buy/sell because a sell quantity was forcibly converted to positive.

### 4. Label the price-change basis

Do not mix candle/open-based movement with previous-close-based daily change.

Required labels:

| Metric | Required label |
|---|---|
| Previous close based daily change | `전일 종가 기준` |
| Intraday open based candle change | `당일 시가/봉 시가 기준` |
| High-to-current drawdown | `당일 고가 대비` |
| Low-to-current rebound | `당일 저가 대비` |

If `ka10080` candle fields and `ka10001` daily quote fields disagree, do not treat one as wrong until the basis is checked.

### 5. Do not substitute unsupported futures investor flow

KOSPI200 futures foreign/institutional net flow must remain unavailable unless a confirmed futures-specific source is added.

Do not substitute it with:

- stock foreign flow;
- program trading data;
- empty futures response values;
- broad market index movement;
- inference from Samsung Electronics or SK hynix movement.

Required wording:

```text
KOSPI200 futures foreign/institutional net flow is unavailable from the current confirmed source. I will not substitute stock foreign flow or program trading data for it.
```

## Required intraday answer template

When the user asks whether a stock is buyable now, use this order:

1. **Signal**: RSI, Bollinger, moving average, price location.
2. **Source basis**: which field/source and whether the change is previous-close or candle/open based.
3. **Supply/demand**: brokerage net quantity only if `ka10002`-level net data is available.
4. **Risk**: invalidation price, stop logic, size boundary, and event risk.
5. **Decision support**: valid signal / wait / pass, with the reason.

Do not start with a tone-heavy command such as “관망하세요” or “추격 금지입니다.” The answer should first provide the data and then the risk framing.

## Required postmarket report checks

Before saving a close summary or postmarket review, check for these errors:

- duplicate stock rows in the same table;
- inconsistent index or large-cap numbers across report files;
- unlabeled estimates such as `~` values;
- unlabeled price-change basis;
- unsupported futures investor-flow claims;
- brokerage ranking described as net flow;
- action conclusions that do not follow the stated system rules.

If a field is estimated, label it as estimated. If a number comes from a conversation note rather than a verified quote source, label it as conversation-derived.

## RSI 30 decision support policy

RSI 30 is not an automatic buy. It is also not something to dismiss with a vague fear narrative.

Correct policy:

| Situation | Output |
|---|---|
| RSI ≤ 30 and all required filters pass | Valid system signal; present size and stop checklist. |
| RSI ≤ 30 but filters conflict | Valid signal with conflict; list the exact conflict. |
| RSI near 30 but not reached | Watch state; state the missing threshold. |
| RSI unavailable | No RSI judgment; request or fetch the missing RSI source. |

## Short-cover track policy

For the crash-market short-cover track, the agent must check the documented conditions rather than relying on a general feeling that the market is falling.

Required fields:

- daily drop at or below the configured threshold;
- 1-minute RSI threshold;
- volume ratio threshold;
- brokerage net-flow basis;
- time window;
- next-day event risk;
- predefined take-profit and stop-loss rule.

If one condition is missing, say which one is missing and do not present the setup as fully confirmed.

## Tone policy for trading support

Use respectful Korean and avoid directive scolding.

Preferred:

```text
현재 데이터로는 신호는 유효하지만, 리스크가 큽니다. 판단에 필요한 체크포인트를 정리하겠습니다.
```

Avoid:

```text
절대 들어가지 마세요.
관망하세요.
추격 금지입니다.
```

A hard stop is allowed only when a documented rule is violated, such as missing RSI, unsupported data substitution, wrong market, or a pre-defined invalidation level being broken.

## Default validation policy

Docs-only updates should still report expected local validation:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git status --short
```

The default validation path must remain local-only. Do not add live market API calls, network access, or Kiwoom credential requirements to the default test runner.
