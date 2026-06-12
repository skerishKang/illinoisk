# Local regression checks

## Purpose

Use this document as the canonical local verification guide before and after small PRs in this repository.

The default local regression command is:

```bash
python3 tests/run_all.py
```

This command is intentionally local-only. It must not require Kiwoom credentials, network access, or live market API calls.

## What the runner checks

`tests/run_all.py` currently runs the current local regression suite. Keep this list category-based instead of pinning every command, because individual checks can be split or renamed without making the docs stale:

- script syntax checks for local helper modules
- conversation import regression tests
- futures unavailable stub tests
- Discord trigger router tests
- quick handoff packet tests
- handoff orchestrator tests
- stale snapshot age guard tests
- snapshot schema validator tests
- fixture snapshot builder tests
- signal state engine tests
- intraday decision engine tests
- intraday handoff review runner tests

These checks cover local-only behavior for conversation import, unavailable futures data handling, handoff packet rendering, guardrail summaries, snapshot freshness, fixture construction, signal-state classification, intraday decisions, and the local review CLI.

## Standard workflow

Before starting a new PR:

```bash
git checkout main
git pull origin main
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git diff --check
git status --short
```

Before merging a PR locally or through GitHub:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git diff --check
git status --short
```

Expected clean result:

```text
결과: 22개 통과, 0개 실패
git diff --check: 통과
git status --short 출력 없음
```

## Guardrails

Do not replace this local runner with a command that requires live credentials, network access, or market API calls.

If a future test needs a live external dependency, keep it outside `tests/run_all.py` unless the repository explicitly adds a separate live-test opt-in policy.
