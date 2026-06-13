# Handoff directory guide

This directory stores structured trading context packets that can be pasted into ChatGPT web or reviewed later through GitHub.

Use this directory when a Discord trading situation needs a second-pass review, model-error analysis, chart interpretation, or postmarket follow-up.

## Purpose

The `handoff/` directory is not a live trading executor and should not contain secrets. It is a temporary-to-durable bridge between:

1. Discord trading conversation;
2. local market snapshots from the user's machine;
3. chart images or chart summaries;
4. ChatGPT web review;
5. later GitHub-based postmarket review.

## File naming

Use this path format:

```text
handoff/YYYY-MM-DD/HHMM-symbol-purpose.md
```

Examples:

```text
handoff/2026-06-11/0935-HPSP-signal-review.md
handoff/2026-06-11/1035-HPSP-gpt-review.md
handoff/2026-06-11/1305-doosan-tesna-rsi30.md
handoff/2026-06-11/1505-short-cover-track.md
handoff/2026-06-11/1540-market-close-review.md
```

Use KST for the `HHMM` prefix. Prefer stable ASCII aliases in filenames when Korean names may be inconvenient.

## Packet types

| Packet type | Use when | Typical purpose |
|---|---|---|
| Quick packet | Active market, time-sensitive review. | Paste fast into ChatGPT web for signal/risk check. |
| Full packet | Important trade decision or model-error review. | Preserve full market context, Discord excerpt, current model answer, and questions. |
| Chart packet | Chart image or local OHLCV snapshot is central. | Review 5-minute and 30-minute structure. |
| Postmarket packet | After market close. | Convert trading events into report/review improvements. |

## Quick packet vs full packet

Use a quick packet when the market is open and speed matters.

A quick packet must still include:

- time KST;
- symbol or active symbol;
- user question;
- active strategy;
- signal state;
- 1-minute, 5-minute, or 30-minute RSI when available;
- Bollinger Band location when available;
- price-change basis;
- volume;
- `ka10002` net flow or `unavailable`;
- futures flow as `unavailable` unless confirmed;
- recent Discord messages;
- current model answer if available;
- exact question for ChatGPT.

Use a full packet when reviewing a significant decision, missed signal, model mistake, or postmarket lesson.

The full packet format is defined in:

```text
docs/chatgpt-handoff-packet-contract.md
```

## Local full fixture write-output workflow

Use the local fixture runner when one full handoff fixture packet should be persisted to a deterministic Markdown path:

```bash
mkdir -p handoff/2026-06-13
python3 scripts/run_full_handoff_fixture.py \
  --scenario active-symbol-signal \
  --write-output handoff
```

The current fixture writes this path:

```text
handoff/2026-06-13/1035-HPSP-full_handoff_active-symbol-signal.md
```

Important guards:

- `--write-output` writes one scenario only and requires `--scenario NAME`.
- The date parent directory must already exist; it is not created automatically.
- Existing packets are not overwritten unless `--overwrite` is supplied.
- `--write` and `--output-root` are not supported aliases.

See `docs/full-handoff-write-output-usage.md` for the full usage guide, invalid combinations, and validation commands.

## Chart files and attachments

When chart images are generated locally, save them next to the Markdown packet.

Recommended names:

```text
handoff/YYYY-MM-DD/HHMM-symbol-purpose.md
handoff/YYYY-MM-DD/HHMM-symbol-5m.png
handoff/YYYY-MM-DD/HHMM-symbol-30m.png
handoff/YYYY-MM-DD/HHMM-symbol-snapshot.json
```

If images are not committed, the Markdown packet should still describe them:

```text
Chart attachments:
- 5m chart: local only, not committed
- 30m chart: local only, not committed
```

Chart packets must include numeric context even when an image exists:

- timeframe;
- current candle direction;
- prior swing high/low;
- RSI value or `unavailable`;
- Bollinger Band location or `unavailable`;
- volume expansion/contraction;
- support/resistance levels if known.

Do not ask ChatGPT to infer all numbers from an image when local numeric data is available.

## Data labels

Every uncertain value must be labeled.

| Label | Meaning |
|---|---|
| `verified` | Confirmed from local quote, broker API, or reliable source. |
| `local_kiwoom` | Retrieved from local Kiwoom REST/OpenAPI runtime. |
| `conversation-derived` | Copied from recent Discord/user conversation. |
| `estimated` | Approximate value, not verified. |
| `unavailable` | Not available from the current confirmed source. |
| `conflict` | Two sources disagree. |

Do not use bare `~` without the `estimated` label.

## Local Kiwoom boundary

Local handoff generation may use the existing Kiwoom REST/OpenAPI design on the user's machine when explicitly configured.

Repository defaults must remain safe:

- no Kiwoom credentials in Git;
- no account numbers or tokens in handoff packets;
- no live API requirement in default tests;
- no network requirement in default tests;
- no GitHub-hosted check should require Kiwoom, Discord, OpenAI, or live market access.

## Futures investor-flow rule

KOSPI200 futures foreign/institutional net flow must remain `unavailable` unless a confirmed futures-specific source exists.

Do not substitute unavailable futures flow with:

- stock foreign flow;
- program trading data;
- empty futures response values;
- broad market index movement;
- Samsung Electronics or SK hynix movement.

Required wording when unavailable:

```text
KOSPI200 futures foreign/institutional net flow is unavailable from the current confirmed source. This handoff does not substitute stock foreign flow or program trading data for it.
```

## Active-market handoff workflow

Use this flow during market hours:

```text
Discord trigger detected
  -> resolve active symbol
  -> build local snapshot
  -> apply rule-based signal state
  -> include recent Discord excerpt
  -> include current model answer if any
  -> create quick or full handoff packet
  -> user pastes packet into ChatGPT web
  -> user brings ChatGPT result back to Discord if useful
```

The assistant should not automatically execute trades based on handoff results.

## Postmarket handoff workflow

Use this flow after market close:

```text
collect important Discord events
  -> group by symbol or strategy
  -> preserve model answer and actual outcome
  -> label mistakes and data gaps
  -> create postmarket handoff packet
  -> use ChatGPT review to improve report, strategy, or model prompts
```

Postmarket handoff packets may later feed:

- `report/YYYY-MM-DD-postmarket-review.md`;
- `report/YYYY-MM-DD-close-summary.md`;
- strategy updates under `strategies/`;
- future model-evaluation notes.

Keep those follow-up changes separate unless the issue explicitly combines them.

## ChatGPT web paste procedure

When the user wants ChatGPT web review:

1. Open the Markdown handoff packet.
2. Copy the entire packet.
3. Paste it into ChatGPT web.
4. Add any chart image if needed.
5. Ask for Korean output using the expected output format in the packet.
6. Bring the answer back into Discord or save it as a later review note.

For very urgent reviews, use the quick packet and paste only the compact context.

## Privacy and secret rules

Never include:

- Kiwoom API keys;
- OpenAI API keys;
- Discord bot tokens;
- account numbers;
- access tokens;
- raw credential files;
- private brokerage identifiers not needed for review;
- unrelated personal information;
- screenshots that expose account balances or private account identifiers unless intentionally sanitized.

If a screenshot includes private data, sanitize it before committing or paste only the relevant chart region into ChatGPT web.

## Commit policy

Commit handoff packets only when they are useful for later review.

Good candidates:

- missed RSI 30 signal;
- model answer that may have violated rules;
- important short-cover track event;
- chart structure that needs later comparison;
- postmarket review source packet.

Poor candidates:

- ordinary noisy Discord chatter;
- duplicate packets for the same event;
- packets containing secrets;
- packets with unverified estimates but no labels.
