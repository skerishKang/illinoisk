# Documentation index

This directory contains project policies, workflow guides, audit notes, and analysis guardrails for the `illinoisK` repository.

Use this page as the first stop after reading the root entry files:

1. `README.md`
2. `INDEX.md`
3. `AGENTS.md`

## Start here

| Document | Use when |
|---|---|
| `repository-structure.md` | Checking top-level directory roles, Git policy, and change separation rules. |
| `local-regression-checks.md` | Running the default local verification workflow before or after small PRs. |
| `conversation-sync-usage.md` | Adding, editing, or verifying Markdown conversation archives. |
| `trading-analysis-quality-guardrails.md` | Preparing trading analysis, intraday answers, close summaries, or postmarket reviews. |
| `discord-trading-skill-trigger-architecture.md` | Designing Discord natural-language trading triggers and local snapshot flow. |
| `chatgpt-handoff-packet-contract.md` | Building ChatGPT web review packets from Discord trading context. |
| `../handoff/README.md` | Saving ChatGPT review handoff packets and related chart references. |
| `../report/README.md` | Creating or editing close summaries and postmarket reviews. |

## Agent reading order

For normal repository work:

1. Read root `README.md`, `INDEX.md`, and `AGENTS.md`.
2. Read `docs/repository-structure.md` to confirm the target directory and Git policy.
3. Read `docs/local-regression-checks.md` before changing files.
4. Read a topic-specific guide from the table above.

For trading analysis or market reports, always include `docs/trading-analysis-quality-guardrails.md` before making conclusions.

For Discord trading assistant or ChatGPT web review handoff work, include `docs/discord-trading-skill-trigger-architecture.md` and `docs/chatgpt-handoff-packet-contract.md`.

For persistent handoff packet work, also include `handoff/README.md` before creating or editing files under `handoff/`.

For report files, also include `report/README.md` before creating or editing close summaries or postmarket reviews.

For conversation archive edits, always include `docs/conversation-sync-usage.md` and run the sync workflow after editing.

## Change separation reminder

Keep small PRs separated by purpose:

| Change type | Preferred scope |
|---|---|
| Docs workflow update | `docs/` and root entrypoint links only. |
| Strategy update | `strategies/` only, unless an entrypoint link is needed. |
| Conversation/report archive | Same-date archive and report files only. |
| Production code change | Code plus focused tests. |
| Live/API research note | Docs/audit note first; no default live behavior. |

Do not mix production code, archive content, and strategy changes in one PR unless the issue explicitly requires it.

## Local-only validation policy

The default regression runner is:

```bash
python3 tests/run_all.py
```

It must remain local-only. Do not add Kiwoom credential requirements, network access, or live market API calls to the default verification path.

For archive-related changes, run:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git status --short
```
