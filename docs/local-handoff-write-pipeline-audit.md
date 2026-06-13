# Local handoff write pipeline audit

This audit note records the current local-only handoff write pipeline after PR #144, PR #146, PR #149, PR #151, and PR #153.

The pipeline is intentionally fixture-first and review-only. It prepares Markdown packets for human or ChatGPT web review, but it does not perform live trading actions or call external services.

## Current baseline

| Area | Current state |
| --- | --- |
| Deterministic path generation | Implemented for handoff packet paths using date, time, symbol, and purpose inputs. |
| Guarded UTF-8 write helper | Implemented with explicit overwrite behavior and deterministic write errors. |
| Full fixture runner write mode | Implemented as `--scenario NAME --write-output ROOT_DIR [--overwrite]`. |
| Default runner behavior | Remains stdout-only unless `--write-output` is explicitly supplied. |
| Batch runner behavior | `--all-scenarios` remains stdout-only and does not write files. |
| Parent directory behavior | Parent date directory must already exist; the runner does not create it automatically. |
| Existing file behavior | Existing packet is refused unless `--overwrite` is supplied. |
| Operator documentation | Documented in `docs/full-handoff-write-output-usage.md` and summarized in `handoff/README.md`. |
| Focused regression coverage | `tests/test_run_full_handoff_fixture.py` covers full packet output and write-output guards. |
| Default regression count | `tests/run_all.py` remains at 26 checks. |

## Completed PR chain

| PR | Purpose |
| --- | --- |
| #144 | Add deterministic handoff packet path generator and overwrite guard. |
| #146 | Add local handoff packet write helper with overwrite guard. |
| #149 | Add optional full handoff fixture packet write mode using canonical `--write-output`. |
| #151 | Add extra regression coverage for full handoff write-output behavior. |
| #153 | Document the full handoff write-output workflow. |

## Canonical write contract

The canonical local write command is:

```bash
mkdir -p handoff/2026-06-13
python3 scripts/run_full_handoff_fixture.py \
  --scenario active-symbol-signal \
  --write-output handoff
```

The optional replacement command is:

```bash
python3 scripts/run_full_handoff_fixture.py \
  --scenario active-symbol-signal \
  --write-output handoff \
  --overwrite
```

Supported write-mode options:

```text
--scenario NAME
--write-output ROOT_DIR
--overwrite
```

Unsupported aliases:

```text
--write
--output-root
```

The unsupported aliases were intentionally not retained after the final Stage 8 decision. Future CLI changes should be introduced through a new issue and should preserve the current default stdout-only behavior.

## Local-only boundary

The current pipeline must remain local-only by default.

It must not require or trigger:

- live Discord bot integration;
- Kiwoom credentials or live market API access;
- OpenAI/API calls;
- network access;
- trading execution behavior;
- account numbers, API keys, or broker tokens;
- automatic writes into `handoff/` without an explicit `--write-output` root;
- automatic chart image commits;
- snapshot JSON or sidecar metadata writes.

A generated handoff packet is review material only. It is not a trading signal executor.

## Guardrail decisions

### Default stdout remains safe

Running one scenario without `--write-output` prints to stdout only:

```bash
python3 scripts/run_full_handoff_fixture.py --scenario active-symbol-signal
```

This remains the safest default for tests, review, and ad hoc inspection.

### Single-scenario write only

`--write-output` is valid only with one explicit `--scenario NAME`.

`--all-scenarios --write-output` is intentionally rejected so batch writes cannot create multiple files by accident.

### Parent directory is explicit

The date directory must exist before the write.

This makes the operator confirm the intended root and date path instead of allowing the runner to create new repository directories due to a typo.

### Existing packet is protected

The runner refuses an existing target path by default.

`--overwrite` is the only accepted replacement mechanism and is valid only together with `--write-output ROOT_DIR`.

## Validation baseline

Current expected local checks:

```bash
python3 tests/test_run_full_handoff_fixture.py
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git diff --check
git status --short
```

Expected state after Stage 8 completion:

```text
tests/test_run_full_handoff_fixture.py: 11/11 passed
tests/run_all.py: 26/26 passed
git diff --check: clean
git status --short: tracked files clean after commit; existing untracked fixtures/ and reports/ may remain
```

## Next safe slices

Prefer these future slices before any live integration:

1. Add an explicit generated-packet fixture review note if a real handoff packet needs human review.
2. Add docs for how operators should decide whether a generated packet belongs in Git.
3. Add a local dry-run command summary if operators need a single command to show the expected write path without writing.
4. Add chart attachment documentation before adding any chart write behavior.
5. Add live Discord/Kiwoom/OpenAI integration only after a separate boundary audit and opt-in configuration design.

Avoid combining live integration, file persistence, chart handling, and trading logic in one PR.

## Related documents

- `docs/full-handoff-write-output-usage.md`
- `docs/handoff-docs-index.md`
- `handoff/README.md`
- `docs/chatgpt-handoff-packet-contract.md`
- `docs/handoff-guardrail-test-coverage.md`
