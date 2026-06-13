# Full handoff write-output usage

This guide documents the canonical local workflow for writing a full handoff fixture packet to a deterministic Markdown file.

The workflow is local-only. It does not call Kiwoom, Discord, OpenAI/API, network services, live market data, or any trading execution path.

## When to use

Use `--write-output` when an operator wants to persist one full fixture packet for later ChatGPT web review or GitHub-based review.

Good uses:

- checking the exact full packet produced for one fixture scenario;
- preserving a deterministic review packet before changing handoff code or docs;
- confirming overwrite and parent-directory guards behave as expected.

Do not use it as a live trading action. The generated packet is review material only.

## Canonical command

The supported CLI shape is:

```bash
python3 scripts/run_full_handoff_fixture.py \
  --scenario active-symbol-signal \
  --write-output handoff
```

This writes one full handoff fixture packet under the supplied root directory.

For the current fixture date/time, the expected path is:

```text
handoff/2026-06-13/1035-HPSP-full_handoff_active-symbol-signal.md
```

The runner prints the written path on success:

```text
wrote handoff packet: handoff/2026-06-13/1035-HPSP-full_handoff_active-symbol-signal.md
```

## Required parent directory

`--write-output` does not create parent directories automatically.

Before writing, create the date directory intentionally:

```bash
mkdir -p handoff/2026-06-13
python3 scripts/run_full_handoff_fixture.py \
  --scenario active-symbol-signal \
  --write-output handoff
```

If the parent directory is missing, the command exits non-zero and reports `reason=parent_missing`.

This guard prevents accidental new handoff date directories from being created by a typo or wrong root path.

## Existing file guard

By default, an existing packet is not overwritten.

A second write to the same path exits non-zero and reports `reason=exists`:

```bash
python3 scripts/run_full_handoff_fixture.py \
  --scenario active-symbol-signal \
  --write-output handoff
```

Use `--overwrite` only when replacing the existing packet is intentional:

```bash
python3 scripts/run_full_handoff_fixture.py \
  --scenario active-symbol-signal \
  --write-output handoff \
  --overwrite
```

`--overwrite` is valid only with `--write-output ROOT_DIR`.

## Invalid combinations

The runner rejects these forms:

```bash
# Missing scenario
python3 scripts/run_full_handoff_fixture.py --write-output handoff

# Overwrite without write-output
python3 scripts/run_full_handoff_fixture.py --scenario active-symbol-signal --overwrite

# Batch output is intentionally unsupported
python3 scripts/run_full_handoff_fixture.py --all-scenarios --write-output handoff
```

The write mode is intentionally one-scenario-at-a-time. Use `--all-scenarios` only for stdout review.

## Supported and unsupported option names

Supported:

```text
--scenario NAME
--write-output ROOT_DIR
--overwrite
```

Unsupported and intentionally not part of the contract:

```text
--write
--output-root
```

Do not add aliases unless a future issue explicitly changes the CLI contract.

## Local validation

After changing this workflow or related tests, run:

```bash
python3 tests/test_run_full_handoff_fixture.py
python3 tests/run_all.py
git diff --check
git status --short
```

Expected focused result after PR #151:

```text
test_run_full_handoff_fixture.py: 11/11 passed
tests/run_all.py: 26/26 passed
git diff --check: clean
git status --short: tracked files clean after commit
```

Existing local-only `fixtures/` or `reports/` directories may remain untracked if they were already present before the change.

## Related documents

- `handoff/README.md` for persistent packet naming, privacy, and commit policy.
- `docs/chatgpt-handoff-packet-contract.md` for full packet section contract.
- `docs/handoff-guardrail-test-coverage.md` for local test coverage mapping.
