# Handoff guardrail test coverage

This document maps the local handoff guardrail areas to representative tests and docs.

It is a docs-only coverage guide. It does not change runtime behavior, fixtures, or packet generation.

## Coverage map

| Area | Representative files | Coverage intent |
| --- | --- | --- |
| Signal state engine | `scripts/signal_state_engine.py`, `tests/test_signal_state_engine.py` | Classify fixture snapshots into `valid_signal`, `near_signal`, `conflicted_signal`, `invalid_signal`, and `unavailable`. |
| Signal detail rendering | `scripts/quick_handoff_packet.py`, `tests/test_quick_handoff_packet.py` | Keep supporting, conflicting, near, and missing-data details visible in handoff output. |
| Local intraday decision | `scripts/intraday_decision_engine.py`, related intraday decision tests | Convert signal states into local review decisions: `진입`, `대기`, `보류`, and `제외`. |
| Handoff packet decision section | `scripts/quick_handoff_packet.py`, `tests/test_quick_handoff_packet.py` | Render the intraday decision and related reasons inside the review packet. |
| Decision-first response format | `scripts/quick_handoff_packet.py`, `tests/test_quick_handoff_packet.py` | Preserve the required first-line `Decision: ...` response format guidance. |
| Decision/state consistency | `scripts/quick_handoff_packet.py`, `tests/test_quick_handoff_packet.py` | Detect whether the rendered decision matches the expected decision for the signal state. |
| Current answer guardrail | `scripts/quick_handoff_packet.py`, `tests/test_quick_handoff_packet.py` | Mark supplied answer text as compliant, unavailable, or violation based on packet response guardrails. |
| Guardrail summary | `scripts/quick_handoff_packet.py`, `tests/test_quick_handoff_packet.py` | Summarize packet findings into `clear`, `attention`, or `blocked` review status. |
| Quote and snapshot availability | `scripts/handoff_orchestrator.py`, handoff orchestrator tests | Force conservative `unavailable` / `제외` behavior when required quote or snapshot fields are missing or unusable. |
| Deterministic stale snapshot age | `scripts/handoff_orchestrator.py`, `tests/test_handoff_snapshot_age_guard.py` | Use caller-provided reference time to block stale or unparsable snapshot timing without wall-clock dependencies. |

## Current docs

| Document | Role |
| --- | --- |
| `docs/handoff-docs-index.md` | Entry point for local handoff review docs. |
| `docs/handoff-guardrail-packet-behavior.md` | Detailed behavior guide for packet guardrail sections. |
| `docs/handoff-packet-review-matrix.md` | Compact review matrix and checklist. |

## Review checklist

When adding or changing a handoff guardrail test, confirm:

1. The test uses deterministic fixture/local-only inputs.
2. The test does not require live market data, Discord, Kiwoom, OpenAI, or another external API.
3. The expected packet output keeps missing data visible.
4. Any unavailable quote or snapshot context remains conservative.
5. Decision/state mapping expectations are explicit.
6. The standard local validation command still passes.

## Validation

Standard local validation:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git status --short
```
