# Handoff guardrail packet behavior

This guide explains how to read the local quick handoff packet guardrail sections.

The packet is a deterministic fixture/local-only review aid. It does not fetch live market data, does not call Discord, Kiwoom, OpenAI, or any external API, and does not place or recommend live orders. It only summarizes caller-provided snapshot and decision fields so a human or downstream review step can see whether the packet is safe to interpret.

## Recommended reading order

Read the packet from top to bottom, but treat the guardrail sections as gates:

1. Start with `## Guardrail summary`.
2. Check `## Intraday decision` for the final local decision and decision/state consistency.
3. Review `## Signal detail` for supporting, conflicting, near, and missing-data factors.
4. Review `## Current answer guardrail check` before reusing or trusting any existing model answer.
5. Only then read the original snapshot/request details.

If any top-level guardrail is blocked, the packet should be treated conservatively even if some indicators look favorable.

## Guardrail summary states

The `Guardrail summary` section compresses the main packet checks into one overall status.

| Status | Meaning | Operator interpretation |
| --- | --- | --- |
| `clear` | No packet guardrail findings are present. | The packet can be reviewed normally, still within fixture/local-only limits. |
| `attention` | The packet has incomplete context, missing signal data, or unavailable review fields, but no hard contradiction was detected. | Review cautiously. Do not treat the packet as a confident entry signal. |
| `blocked` | A hard guardrail condition is present, such as signal unavailable, decision/state mismatch, or current answer violation. | Treat the handoff as blocked. The conservative decision should dominate. |

The summary does not replace the detailed sections. It is a quick triage line for whether the packet is safe to keep reading as an actionable local review.

## Decision/state consistency

The packet maps signal states to expected local decisions:

| Signal state | Expected decision |
| --- | --- |
| `valid_signal` | `진입` |
| `near_signal` | `대기` |
| `conflicted_signal` | `보류` |
| `invalid_signal` | `제외` |
| `unavailable` | `제외` |

`Decision/state consistency` is `consistent` when the rendered intraday decision matches this mapping. It is `inconsistent` when the packet says, for example, `Signal state: valid_signal` but `Decision: 대기`. It is `unavailable` when the packet cannot compare the fields reliably.

An inconsistent decision/state pair should be treated as a packet integrity problem, not as a trading signal.

## Snapshot and quote guards

The handoff orchestrator applies conservative local guards before the final decision is rendered.

A snapshot is forced to effective `unavailable` when required quote or timestamp inputs are missing or unusable, including:

- `quote.current_price` missing, unavailable, non-numeric, or non-positive.
- `snapshot.as_of` missing or unavailable.
- `snapshot.as_of` present but unparsable when a reference time is supplied.
- `snapshot_reference_time` or fallback `time_kst` unparsable when used as the deterministic reference time.
- Snapshot age greater than `MAX_SNAPSHOT_AGE_SECONDS`.

`MAX_SNAPSHOT_AGE_SECONDS` is `180`. A snapshot older than 180 seconds relative to the caller-provided reference time is stale. Stale snapshots force the effective signal state to `unavailable`, and the intraday decision mapping then produces `Decision: 제외`.

This age guard is deterministic. It does not call the wall clock. The caller must provide `snapshot_reference_time` or `time_kst` for age comparison.

## Current answer guardrail check

The current answer guardrail checks an existing or previously generated model answer, if one is supplied in the packet input.

The first non-empty line must exactly match one of the allowed decision lines:

- `Decision: 진입`
- `Decision: 대기`
- `Decision: 보류`
- `Decision: 제외`

The guardrail also detects live execution-style wording such as direct buy/sell/order language. A violation here means the current answer should not be reused as-is. It does not change live systems or send any order; it only marks the packet for review.

## Missing futures flow guardrail

When KOSPI200 futures foreign/institutional flow is unavailable, the packet must not substitute stock foreign flow or program trading data as if it were the same signal. Missing futures flow should remain visible as missing context.

This preserves the local-only boundary and prevents the handoff from turning incomplete futures flow context into a false confirmation.

## Non-goals

This packet behavior does not provide:

- Discord live integration.
- Kiwoom live market calls.
- OpenAI/API calls.
- File-writing runtime behavior.
- Live trade execution.
- Automatic substitution from stock foreign flow or program trading data to unavailable KOSPI200 futures foreign/institutional flow.

## Validation

For a docs-only change to this guide, the standard local validation remains:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git status --short
```
