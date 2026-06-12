# ChatGPT handoff packet contract

This document defines the Markdown packet format used to move a Discord trading situation into ChatGPT web review.

The goal is not to make ChatGPT a live trading executor. The goal is to let the user paste a structured, auditable context into ChatGPT for second-pass review, model-error analysis, chart interpretation, and next-step checklist generation.

## When to build a handoff packet

Build a handoff packet when the user says any of the following or similar phrases:

- `GPT 검토`
- `ChatGPT 검토`
- `정리해서 넘겨줘`
- `이거 너한테 물어보게 정리해줘`
- `복기용으로 저장`
- `차트랑 같이 넘기자`

The packet may be pasted directly into ChatGPT web or saved under `handoff/` for later GitHub-based review.

## File naming

If persisted in the repository, use:

```text
handoff/YYYY-MM-DD/HHMM-symbol-purpose.md
```

Examples:

```text
handoff/2026-06-11/1035-HPSP-gpt-review.md
handoff/2026-06-11/1305-doosan-tesna-rsi30.md
handoff/2026-06-11/1505-short-cover-track.md
```

Use Korean stock names only when they are filename-safe. Prefer stable ASCII aliases when possible.

## Required packet sections

A handoff packet must include these sections in order:

1. title;
2. review request;
3. market/session context;
4. active symbol context;
5. local market snapshot;
6. chart summary or chart attachment references;
7. recent Discord conversation excerpt;
8. current model answer, if any;
9. applicable rules;
10. known data gaps;
11. questions for ChatGPT;
12. expected output format.

## Markdown template

```markdown
# ChatGPT trading review handoff

## 1. Review request

- Date:
- Time KST:
- Symbol:
- Purpose: signal review / risk review / chart review / model-error review / postmarket review
- User question:

## 2. Market/session context

- Market mode:
- Active strategy:
- Watchlist:
- Position status:
- Trading session phase: premarket / regular / lunch / close-watch / postmarket

## 3. Active symbol context

- Active symbol:
- Why this symbol is active:
- Last trigger phrase:
- Last signal state:

## 4. Local market snapshot

```json
{
  "as_of": "",
  "symbol": "",
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

## 5. Chart summary or attachments

- 5-minute chart summary:
- 30-minute chart summary:
- Support/resistance:
- Volume pattern:
- Attached chart files:

## 6. Recent Discord conversation excerpt

```text
User:
Assistant:
User:
Assistant:
```

## 7. Current model answer to review

```text
Paste the Discord model's current answer here.
```

## 8. Applicable rules

- RSI 30 signal should not be overridden by vague market fear.
- Use `ka10002` net quantity for brokerage net flow.
- Do not treat `ka10040` ranking as net flow.
- Do not erase signed sell quantities with `abs()`.
- Label price-change basis clearly.
- Keep KOSPI200 futures foreign/institutional flow unavailable unless a confirmed futures-specific source exists.
- User makes the trading decision; model provides checkpoints.
- The model must not act as a no-trade veto.
- `제외` requires explicit invalidation data.
- `conflicted_signal` should be rendered as `대기`, with conflict-resolution conditions shown as wait/confirmation conditions, not automatic invalidation.
- Missing data should become `대기` with a missing trigger/data note, not generic 현금보유 or 내일 재검토.
- Do not tell the user to hold cash, stop trading, wait until tomorrow, or avoid trading unless a documented invalidation condition is present.

## 9. Known data gaps

- Missing data:
- Unverified estimates:
- Source conflicts:

## 10. Questions for ChatGPT

1. Did the current model answer violate any rules?
2. Is the signal valid, conflicted, near, invalid, or unavailable?
3. What data supports the conclusion?
4. What data is missing?
5. What should the user check before deciding?
6. How should the Discord model answer be improved?
7. Did the model use unsupported no-trade veto language?
8. If the answer says 제외, what exact invalidation condition supports it?
9. If invalidation is not proven, what entry trigger or 대기 condition should be shown?

## 11. Expected output format

Please answer in Korean with:

1. 판정: 진입 / 대기 / 제외
2. 신호 상태
3. 근거 데이터
4. 진입 트리거
5. 무효 조건 / 대기 조건
6. 익절 기준
7. 빠진 데이터
8. 기존 모델 답변의 no-trade veto 여부
9. 개선된 Discord 답변 예시
```

## Minimal quick-paste packet

When time is short, the assistant may build a compact packet:

```markdown
# Quick ChatGPT trading review

- Time KST:
- Symbol:
- User question:
- Active strategy:
- Signal state:
- 1m/5m/30m RSI:
- BB position:
- Price basis:
- Volume:
- ka10002 net flow:
- Futures flow: unavailable unless confirmed
- Recent Discord messages:
- Current model answer:
- Ask ChatGPT:
  1. Is the signal valid or conflicted?
  2. Did the model violate rules?
  3. What should be checked before deciding?
```

Use the full packet whenever possible. Use the compact packet only during active market hours when speed matters.

## Data labeling rules

Every handoff packet must label uncertain data.

Allowed labels:

| Label | Meaning |
|---|---|
| `verified` | Confirmed from local quote, broker API, or reliable source. |
| `local_kiwoom` | Retrieved from local Kiwoom REST/OpenAPI runtime. |
| `conversation-derived` | Copied from recent Discord/user conversation. |
| `estimated` | Approximate value, not verified. |
| `unavailable` | Not available from the current confirmed source. |
| `conflict` | Two sources disagree. |

Do not use bare `~` without `estimated`.

## Chart attachment rules

If chart images are included, the text packet must still include numeric context.

Minimum chart text summary:

- timeframe;
- current candle direction;
- prior swing high/low;
- RSI value or unavailable;
- Bollinger Band location or unavailable;
- volume expansion/contraction;
- support/resistance levels if known.

Do not ask ChatGPT to infer all numbers from a chart image when local numeric data is available.

## Model-answer review rules

When reviewing another model's Discord answer, ChatGPT should check:

- Did it separate observed data, indicator, interpretation, and action support?
- Did it state source/basis for important numbers?
- Did it dismiss a valid RSI 30 signal with vague fear?
- Did it misuse `ka10040` or unsupported brokerage data?
- Did it substitute unavailable futures flow with unrelated data?
- Did it use overly directive trading language?
- Did it give a checklist the user can decide from?

## Privacy and secret rules

Do not include:

- API keys;
- account numbers;
- access tokens;
- raw credential files;
- private brokerage identifiers not needed for review;
- personally sensitive information unrelated to the trade.

## Local validation

Docs-only changes should validate with:

```bash
python3 tests/run_all.py
git status --short
```

Default validation must not require Kiwoom credentials, Discord access, OpenAI access, network access, or live market API calls.
