# Handoff docs index

This index collects the local handoff review documents.

These documents are docs-only references. They describe fixture/local-only handoff packet review behavior and do not change runtime code.

## Documents

| Document | Purpose |
| --- | --- |
| `docs/handoff-guardrail-packet-behavior.md` | Full behavior guide for reading quick handoff packet guardrail sections. |
| `docs/handoff-packet-review-matrix.md` | Compact matrix for summary states, signal/decision mapping, snapshot and quote checks, current answer checks, and operator review posture. |
| `docs/handoff-guardrail-test-coverage.md` | Coverage map for local handoff guardrail tests and representative files. |
| `docs/full-handoff-write-output-usage.md` | Local usage guide for writing one full handoff fixture packet with `--write-output`. |

## Suggested order

1. Read `docs/handoff-guardrail-packet-behavior.md` for the detailed section-by-section explanation.
2. Use `docs/handoff-packet-review-matrix.md` as the compact checklist during packet review.
3. Check `docs/handoff-guardrail-test-coverage.md` when changing or reviewing guardrail tests.
4. Use `docs/full-handoff-write-output-usage.md` when persisting a full fixture packet with `scripts/run_full_handoff_fixture.py --write-output`.

## Local validation

For docs-only updates, use the standard local validation commands:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git diff --check
git status --short
```
