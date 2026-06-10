# illinoisK Index

## Repository purpose

This repository organizes market notes, watchlists, daily review logs, strategy notes, conversation archives, and agent operating rules.

It is not an automated trading system and should not execute live market actions by default.

## Entry points

- `README.md`: repository overview and default commands.
- `INDEX.md`: quick entry point for agents.
- `AGENTS.md`: operating rules and guardrails for agents.
- `docs/README.md`: documentation index and guide selection map.
- `docs/repository-structure.md`: repository layout and top-level directory roles.
- `docs/local-regression-checks.md`: local verification workflow.
- `docs/conversation-sync-usage.md`: conversation archive sync workflow.
- `docs/trading-analysis-quality-guardrails.md`: trading analysis error-prevention rules.
- `docs/discord-trading-skill-trigger-architecture.md`: Discord natural-language trading trigger architecture.
- `docs/chatgpt-handoff-packet-contract.md`: ChatGPT web review handoff packet contract.
- `report/README.md`: report writing guide for close summaries and postmarket reviews.

## Main directories

- `conversations/`: Git-tracked Markdown conversation archives.
- `report/`: market close and postmarket review reports.
- `strategies/`: strategy notes and system rules.
- `watchlist/`: stock watchlist notes.
- `daily-logs/`: daily review records.
- `scripts/`: local tooling for sync and scan helpers.
- `tests/`: local regression tests and test runner.
- `docs/`: project policies, audit notes, and workflow guides.

## Standard local verification

Run before and after small PRs:

```bash
python3 tests/run_all.py
```

Expected result:

```text
결과: 3개 통과, 0개 실패
```

## Conversation archive sync

Markdown files are the source archive. The SQLite DB is local and regenerable.

Default sync command:

```bash
python3 scripts/save_conversation.py sync
```

Optional keyword check:

```bash
python3 scripts/save_conversation.py sync --keyword "리노공업"
```

## Agent workflow

1. Read `README.md`, `INDEX.md`, and `AGENTS.md` first.
2. Use `docs/README.md` to choose the right documentation guide.
3. Use `docs/repository-structure.md` to check directory roles and Git policy.
4. Use `docs/local-regression-checks.md` before changing files.
5. Use `docs/conversation-sync-usage.md` after conversation archive edits.
6. Use `docs/trading-analysis-quality-guardrails.md` before trading analysis or reports.
7. Use `report/README.md` before creating or editing market reports.
8. Use `docs/discord-trading-skill-trigger-architecture.md` and `docs/chatgpt-handoff-packet-contract.md` before Discord trading assistant or ChatGPT handoff work.
9. Keep default checks local-only.
10. Do not require Kiwoom credentials, network access, or live market API calls for default tests.
11. Do not substitute unavailable futures investor data with unrelated stock foreign flow or program-trading data.
