# Handoff packet review matrix

This guide is a docs-only companion to `docs/handoff-guardrail-packet-behavior.md`.

Start with `docs/handoff-guardrail-packet-behavior.md` for the full section-by-section behavior guide, then use this matrix as a compact review checklist.

It summarizes how an operator should read common quick handoff packet states. The matrix is fixture/local-only and describes review semantics only. It does not add runtime behavior.

## Summary status matrix

| Overall status | Typical packet condition | Review posture |
| --- | --- | --- |
| `clear` | Required fields are present, the state mapping is aligned, and the current answer check is compliant. | Normal local review. |
| `attention` | Some context is missing or unavailable, but no hard contradiction is shown. | Cautious local review. Missing data remains visible. |
| `blocked` | A hard guardrail finding is present, such as unavailable signal state, state mapping mismatch, or answer-format violation. | Do not reuse the packet conclusion without fixing the underlying packet input. |

## Signal state and decision mapping

| Signal state | Expected local decision | Notes |
| --- | --- | --- |
| `valid_signal` | `진입` | Only meaningful when required packet context is fresh and complete. |
| `near_signal` | `대기` | Indicates watch/review posture, not a final confirmation. |
| `conflicted_signal` | `보류` | Indicates mixed inputs. |
| `invalid_signal` | `제외` | Indicates the local criteria do not support review continuation. |
| `unavailable` | `제외` | Used when required packet context is missing, stale, or unusable. |

A mismatch between the signal state and expected decision is a packet integrity issue. The operator should fix the packet input or orchestrator path instead of choosing the more favorable field.

## Snapshot and quote matrix

| Packet input condition | Guardrail effect | Review posture |
| --- | --- | --- |
| Positive numeric `quote.current_price` and usable `snapshot.as_of` | Quote/timestamp guard may pass. | Continue to other guardrails. |
| Missing, unavailable, non-numeric, or non-positive `quote.current_price` | Effective signal state becomes `unavailable`. | Conservative review posture. |
| Missing or unavailable `snapshot.as_of` | Effective signal state becomes `unavailable`. | Conservative review posture. |
| Unparsable `snapshot.as_of` when a reference time is supplied | Effective signal state becomes `unavailable`. | Conservative review posture. |
| Snapshot age greater than `MAX_SNAPSHOT_AGE_SECONDS` | Effective signal state becomes `unavailable`. | Conservative review posture. |

`MAX_SNAPSHOT_AGE_SECONDS` is `180`. The age check is deterministic and depends on caller-provided `snapshot_reference_time` or fallback `time_kst`.

## Current answer check matrix

| Current answer status | Meaning | Review posture |
| --- | --- | --- |
| `compliant` | The answer follows the required first-line decision format and avoids disallowed wording. | It can be read as part of local review. |
| `unavailable` | No current answer was supplied. | Review the packet without relying on previous answer text. |
| `violation` | The answer format or wording violates packet guardrails. | Do not reuse the answer text as-is. |

Allowed first lines are exactly:

- `Decision: 진입`
- `Decision: 대기`
- `Decision: 보류`
- `Decision: 제외`

## Missing futures-flow context

If KOSPI200 futures foreign/institutional flow is unavailable, the packet must keep that gap visible. Stock foreign flow and program trading data may be separate context, but they are not replacements for unavailable KOSPI200 futures flow.

## Operator checklist

Before treating a packet as reviewable, confirm:

1. `Overall status` is not `blocked`.
2. `Decision/state consistency` is not `inconsistent`.
3. `Current answer status` is not `violation`.
4. `Signal state` is not `unavailable` unless the local decision is conservatively `제외`.
5. Missing KOSPI200 futures-flow context has not been replaced by a different data source.
6. The packet remains fixture/local-only.

## Validation

This is a docs-only guide. Standard local validation remains:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git status --short
```
