# Local handoff write dry-run design

This note defines a future local-only dry-run design for the full handoff fixture write pipeline.

It is a design document only. It does not add a CLI option, change runtime behavior, or make the runner write files differently.

## Purpose

Operators sometimes need to confirm the deterministic packet path before writing a full handoff fixture packet.

The current supported write command is still:

```bash
python3 scripts/run_full_handoff_fixture.py \
  --scenario active-symbol-signal \
  --write-output handoff
```

A future dry-run mode should answer one narrow question:

```text
Where would this command write the packet, and would the existing guards allow it?
```

It should not create, overwrite, delete, or modify any files.

## Non-goals

A dry-run mode must not:

- create parent directories;
- create packet Markdown files;
- overwrite existing packet files;
- write chart images;
- write snapshot JSON or sidecar metadata;
- call Discord, Kiwoom, OpenAI/API, network services, or live market data;
- trigger trading execution behavior;
- weaken the existing `--write-output ROOT_DIR` overwrite and parent-directory guards.

## Proposed future CLI shape

If implemented later, prefer an explicit read-only option:

```bash
python3 scripts/run_full_handoff_fixture.py \
  --scenario active-symbol-signal \
  --write-output handoff \
  --dry-run
```

The option should be valid only with one explicit `--scenario NAME` and `--write-output ROOT_DIR`.

It should stay invalid with:

```text
--all-scenarios --write-output ROOT_DIR --dry-run
--dry-run without --write-output ROOT_DIR
--dry-run without --scenario NAME
--overwrite --dry-run
```

`--overwrite --dry-run` should be rejected because dry-run should report default write safety, not simulate replacement semantics.

## Proposed output shape

A successful dry-run should print a stable, parseable summary:

```text
would write handoff packet: handoff/2026-06-13/1035-HPSP-full_handoff_active-symbol-signal.md
status=ok
reason=ready
```

If the parent directory is missing, it should not create it:

```text
would write handoff packet: handoff/2026-06-13/1035-HPSP-full_handoff_active-symbol-signal.md
status=blocked
reason=parent_missing
```

If the target file already exists, it should not overwrite it:

```text
would write handoff packet: handoff/2026-06-13/1035-HPSP-full_handoff_active-symbol-signal.md
status=blocked
reason=exists
```

The exact text can be refined during implementation, but it should preserve these ideas:

- print the deterministic path;
- say whether a normal write would be allowed;
- reuse existing guard reasons where possible;
- avoid writing any files.

## Guardrail expectations

A future dry-run implementation should share the same deterministic path generator as `--write-output`.

It should inspect the filesystem only enough to answer guard questions:

- does the intended parent directory exist?
- does the intended target file already exist?
- is the command shape valid?

It should not inspect unrelated files or remote services.

## Test expectations for a future implementation

A future code PR should add focused local tests for:

1. dry-run prints the expected deterministic path;
2. dry-run does not create a missing parent directory;
3. dry-run does not create a packet file;
4. dry-run reports `parent_missing` consistently;
5. dry-run reports `exists` consistently;
6. dry-run rejects `--all-scenarios --write-output ROOT_DIR --dry-run`;
7. dry-run rejects `--overwrite --dry-run`;
8. default stdout-only behavior remains unchanged;
9. existing write-output behavior remains unchanged.

Those tests should remain fixture-only and local-only.

## Relationship to current workflow

Until a future implementation issue adds the option, operators should continue using the existing safe workflow:

```bash
mkdir -p handoff/2026-06-13
python3 scripts/run_full_handoff_fixture.py \
  --scenario active-symbol-signal \
  --write-output handoff
```

Use `docs/full-handoff-write-output-usage.md` for the current supported workflow and generated packet commit policy.

## Validation for this docs-only note

For docs-only updates, run:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git diff --check
git status --short
```

Expected result:

```text
tests/run_all.py: 26/26 passed
git diff --check: clean
git status --short: tracked files clean after commit; existing untracked fixtures/ and reports/ may remain
```
