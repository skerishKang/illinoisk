# Agent operating rules

## User context

- User: Chulwon Kang.
- Preferred style: respectful Korean, direct, data-based, no unsupported guesses.
- Trading context: RSI-based strategy, supply/demand checks, KOSPI/KOSDAQ distinction.

## Repository role

This repository is for organizing trading research, conversation archives, reports, watchlists, strategy notes, and local helper scripts.

It is not an automated trading system. Default agent behavior must not execute live trades or require live market API access.

## Required files to read first

1. `README.md`
2. `INDEX.md`
3. `docs/README.md`
4. `docs/repository-structure.md`
5. `docs/local-regression-checks.md`
6. `docs/trading-analysis-quality-guardrails.md` before trading analysis or reports
7. `report/README.md` before creating or editing market reports
8. `docs/discord-trading-skill-trigger-architecture.md` before Discord trading assistant work
9. `docs/chatgpt-handoff-packet-contract.md` before ChatGPT web handoff work
10. `docs/local-discord-handoff-implementation-plan.md` before Discord handoff code work
11. `handoff/README.md` before creating or editing persistent handoff packets
12. `docs/conversation-sync-usage.md` when editing conversation archives

## Default local verification

Run this before and after small PRs:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git diff --check
git status --short
```

Expected result:

```text
save_conversation.py sync: 12 dates / 271 messages
tests/run_all.py: 22개 통과, 0개 실패
git diff --check: 통과
git status: tracked files clean after commit
```

The runner and default checks must remain local-only. Do not add checks that require Kiwoom credentials, network access, or live market API calls.

## Conversation archive workflow

Markdown conversation files under `conversations/` are the Git-tracked source archive.

The SQLite DB is local and regenerable. Do not commit DB files.

Default sync command:

```bash
python3 scripts/save_conversation.py sync
```

Use `--keyword` when a focused search check is useful:

```bash
python3 scripts/save_conversation.py sync --keyword "리노공업"
```

## Market-data guardrails

- Do not infer unsupported market data.
- Do not replace unavailable KOSPI200 futures foreign/institutional flow with stock foreign flow.
- Do not replace unavailable KOSPI200 futures foreign/institutional flow with program-trading data.
- Keep `fetch_futures_frgn_inst()` unavailable unless a confirmed futures-specific source is added.

## Trading analysis quality guardrails

Before trading analysis or market reports, use `docs/trading-analysis-quality-guardrails.md`.

- Separate observed data, derived indicators, interpretation, and action support.
- State the source and basis for important numbers.
- Do not override a valid RSI 30 signal with vague market fear; present the signal, conflicts, and risk checklist.
- Use `ka10002` net quantity for brokerage net flow; do not treat `ka10040` ranking as net flow.
- Do not erase signed sell quantities with `abs()` when computing net flow.
- Label whether a price change is previous-close based, open/candle based, high-to-current, or low-to-current.
- Do not substitute unavailable futures investor flow with unrelated data.

## Discord trading and handoff guardrails

Before Discord trading assistant or ChatGPT handoff work, use:

- `docs/discord-trading-skill-trigger-architecture.md`
- `docs/chatgpt-handoff-packet-contract.md`
- `docs/local-discord-handoff-implementation-plan.md`

Before creating or editing persistent handoff packets, also use:

- `handoff/README.md`

Natural-language triggers should be preferred over slash-command-only operation. Keep local market snapshots local-only and do not make default tests depend on Discord, Kiwoom, OpenAI, network, or live market credentials.

## PR hygiene

- Keep strategy changes separate from archive/report changes.
- Keep production code changes separate from docs-only updates.
- Run the standard local validation workflow (`sync / run_all / git diff --check / git status --short`) before reporting completion. See `docs/local-regression-checks.md` for the full workflow.
- Report changed files, validation output, and whether the working tree is clean.
