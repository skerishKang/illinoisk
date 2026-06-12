# Repository structure

This document describes the current `illinoisK` repository layout and the intended role of each top-level area.

## Root entry files

| Path | Role |
|---|---|
| `README.md` | Repository overview and default commands. |
| `INDEX.md` | Fast entry point for agents. |
| `AGENTS.md` | Agent operating rules, guardrails, and verification expectations. |

Agents should read these files first before making changes.

## Main directories

| Directory | Role | Git policy |
|---|---|---|
| `conversations/` | Markdown conversation archives by date. | Tracked source archive. |
| `report/` | Market close, postmarket, and review reports. | Tracked. |
| `strategies/` | Strategy notes and system rules. | Tracked. |
| `watchlist/` | Stock watchlist notes. | Tracked. |
| `daily-logs/` | Daily review records. | Tracked. |
| `docs/` | Project policies, workflow guides, and audit notes. | Tracked. |
| `scripts/` | Local helper scripts for sync and market scan support. | Tracked. |
| `tests/` | Local regression tests and test runner. | Tracked. |
| `DB/` | Local SQLite search index output. | Not tracked; regenerable. |

## Conversation archive model

Markdown files under `conversations/` are the source of truth for conversation archives.

The SQLite database is only a local search index. Regenerate it with:

```bash
python3 scripts/save_conversation.py sync
```

Use keyword verification when needed:

```bash
python3 scripts/save_conversation.py sync --keyword "리노공업"
```

Do not commit `.db`, `.sqlite`, or `.sqlite3` files.

## Local verification model

The canonical local validation workflow is:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git diff --check
git status --short
```

The regression step is expected to stay local-only. It must not require Kiwoom credentials, network access, or live market API calls.

See `docs/local-regression-checks.md` for the detailed workflow.

## Change separation rules

Keep small PRs separated by purpose:

| Change type | Preferred PR scope |
|---|---|
| Strategy update | Strategy files only. |
| Conversation/report archive | Same-date archive/report files together. |
| Docs-only workflow update | Docs and entrypoint files only. |
| Production code change | Code plus focused tests. |
| Live/API research note | Docs/audit note first; no default live behavior. |

## Market-data guardrails

- Do not infer unsupported market data.
- Do not replace unavailable KOSPI200 futures foreign/institutional flow with stock foreign flow.
- Do not replace unavailable KOSPI200 futures foreign/institutional flow with program-trading data.
- Keep futures investor data unavailable until a confirmed futures-specific source is added.
