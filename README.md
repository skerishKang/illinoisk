# illinoisK

Repository for market notes, watchlists, daily review logs, strategy notes, conversation archives, and agent operating rules.

## Purpose

This repository keeps trading research organized. It is not an automated trading system and should not execute live market actions by default.

## Main files and directories

- `INDEX.md`: entry point for agents and quick project context.
- `AGENTS.md`: operating rules and trading context for agents.
- `docs/README.md`: documentation index and guide selection map.
- `docs/repository-structure.md`: repository layout and top-level directory roles.
- `docs/`: project policies, audit notes, and workflow guides.
- `handoff/README.md`: ChatGPT review handoff packet storage guide.
- `report/README.md`: report writing guide for close summaries and postmarket reviews.
- `watchlist/`: stock watchlist notes.
- `daily-logs/`: daily review records.
- `strategies/`: strategy notes and system rules.
- `conversations/`: Markdown conversation archives.
- `scripts/`: local tooling for conversation sync and market scan helpers.
- `tests/`: local regression tests and test runner.

## Local verification

Run the local regression suite before and after small PRs:

```bash
python3 tests/run_all.py
```

Expected clean result:

```text
결과: 3개 통과, 0개 실패
```

See `docs/local-regression-checks.md` for the full local verification workflow.

## Conversation archive workflow

Markdown conversation files are the Git-tracked source archive. The SQLite database is a local, regenerable search index and should not be committed.

Default sync command:

```bash
python3 scripts/save_conversation.py sync
```

See `docs/conversation-sync-usage.md` for details.

## Guardrails

- Keep default checks local-only.
- Do not require Kiwoom credentials, network access, or live market API calls for `tests/run_all.py`.
- Do not replace unavailable futures investor data with unrelated stock foreign flow or program-trading data.
