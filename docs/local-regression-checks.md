# Local regression checks

## Purpose

Use this document as the canonical local verification guide before and after small PRs in this repository.

The default local regression command is:

```bash
python3 tests/run_all.py
```

This command is intentionally local-only. It must not require Kiwoom credentials, network access, or live market API calls.

## What the runner checks

`tests/run_all.py` currently runs:

```bash
python3 -m py_compile scripts/scan_golden_cross.py
python3 tests/test_save_conversation_import.py
python3 tests/test_scan_golden_cross_futures_stub.py
```

These checks cover:

- `scan_golden_cross.py` syntax validity
- Markdown conversation import and indexing behavior
- legacy Hermes conversation parsing behavior
- futures unavailable stub regression behavior

## Standard workflow

Before starting a new PR:

```bash
git checkout main
git pull origin main
python3 tests/run_all.py
git status --short
```

Before merging a PR locally or through GitHub:

```bash
python3 tests/run_all.py
git status --short
```

Expected clean result:

```text
결과: 3개 통과, 0개 실패
git status --short 출력 없음
```

## Guardrails

Do not replace this local runner with a command that requires live credentials, network access, or market API calls.

If a future test needs a live external dependency, keep it outside `tests/run_all.py` unless the repository explicitly adds a separate live-test opt-in policy.
