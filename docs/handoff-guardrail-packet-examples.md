# Handoff guardrail packet examples

This guide gives fixture/local-only examples for interpreting quick handoff packet guardrail states.

The examples are not trading advice, not executable signals, and not live integration output. They are simplified packet snippets for operator review.

Use this guide together with `docs/handoff-guardrail-packet-behavior.md`.

## Example 1: clear fresh packet

A clear packet has no guardrail findings. The signal state and local decision agree, the current answer is compliant, and required context is present.

```text
## Guardrail summary
- Overall status: clear
- Decision/state consistency: consistent: valid_signal -> 진입
- Current answer status: compliant
- Signal state: valid_signal
### Summary findings
- all packet guardrail checks are clear

## Intraday decision
- Decision: 진입
- Strength: strong
- Decision/state consistency: consistent: valid_signal -> 진입
- Summary: 진입 / strong

## Current answer guardrail check
- Status: compliant
### Guardrail findings
- current model answer follows the required decision-first guardrail
```

Interpretation:

- The packet can be reviewed normally.
- The first-line decision format is compliant.
- The packet is still fixture/local-only; it does not authorize live execution.

## Example 2: attention from missing context

An attention packet has no hard contradiction, but some input context is incomplete. This should not be treated as a confident entry signal.

```text
## Guardrail summary
- Overall status: attention
- Decision/state consistency: consistent: near_signal -> 대기
- Current answer status: compliant
- Signal state: near_signal
### Summary findings
- signal missing data present: brokerage net quantity unavailable

## Intraday decision
- Decision: 대기
- Strength: weak
- Decision/state consistency: consistent: near_signal -> 대기
- Summary: 대기 / weak

## Signal detail
### Missing data
- brokerage net quantity unavailable
```

Interpretation:

- The packet is readable, but incomplete.
- The conservative action is to wait or review manually.
- Missing data must remain visible; do not silently fill it with unrelated substitute data.

## Example 3: blocked stale snapshot

A stale snapshot is a hard guardrail because the packet may no longer describe the current market state. When the stale snapshot age guard fires, the effective signal state becomes `unavailable`, and the decision becomes `제외`.

```text
## Guardrail summary
- Overall status: blocked
- Decision/state consistency: consistent: unavailable -> 제외
- Current answer status: compliant
- Signal state: unavailable
### Summary findings
- signal state is unavailable

## Intraday decision
- Decision: 제외
- Strength: unavailable
- Decision/state consistency: consistent: unavailable -> 제외
- Summary: 제외 / unavailable

## Signal detail
### Missing data
- snapshot stale: 301s old
```

Interpretation:

- Treat the packet as blocked even if older indicators looked favorable.
- `MAX_SNAPSHOT_AGE_SECONDS` is `180`, so `301s old` is beyond the deterministic threshold.
- The stale guard uses the caller-provided `snapshot_reference_time` or fallback `time_kst`; it does not call wall-clock time.

## Example 4: blocked current answer violation

The current answer guardrail checks an existing model answer before it is reused. If the answer does not start with one of the exact allowed decision lines, or if it contains live execution-style wording, the packet is blocked.

```text
## Guardrail summary
- Overall status: blocked
- Decision/state consistency: consistent: valid_signal -> 진입
- Current answer status: violation
- Signal state: valid_signal
### Summary findings
- current model answer violates required guardrails

## Current model answer
신호는 좋아 보입니다. 바로 매수하세요.

## Current answer guardrail check
- Status: violation
### Guardrail findings
- first non-empty line does not exactly match an allowed Decision line
- live execution-style wording detected: 바로 매수
```

Interpretation:

- The existing answer should not be reused as-is.
- A valid answer must begin with exactly one of:
  - `Decision: 진입`
  - `Decision: 대기`
  - `Decision: 보류`
  - `Decision: 제외`
- Direct execution wording remains disallowed even when the local signal looks favorable.

## Example 5: blocked decision/state mismatch

A decision/state mismatch means the rendered decision conflicts with the expected mapping for the signal state.

```text
## Guardrail summary
- Overall status: blocked
- Decision/state consistency: inconsistent: valid_signal expects 진입, got 대기
- Current answer status: compliant
- Signal state: valid_signal
### Summary findings
- decision/state mismatch: inconsistent: valid_signal expects 진입, got 대기

## Intraday decision
- Decision: 대기
- Strength: weak
- Decision/state consistency: inconsistent: valid_signal expects 진입, got 대기
```

Interpretation:

- Treat this as a packet integrity issue.
- Do not average the two fields or choose the more favorable one.
- Fix the fixture or orchestrator input before using the packet for review.

## Example 6: unavailable futures flow context

When KOSPI200 futures foreign/institutional flow is unavailable, the packet must not substitute stock foreign flow or program trading data as if it were equivalent.

```text
## Signal detail
### Missing data
- KOSPI200 futures foreign/institutional flow unavailable

## Required response format
- Do not substitute stock foreign flow or program trading data for unavailable KOSPI200 futures foreign/institutional flow.
```

Interpretation:

- Keep the futures flow gap visible.
- Program trading or stock foreign flow may be separate context, but it is not a replacement for unavailable KOSPI200 futures flow.
- If this missing context matters to the strategy, the packet should remain conservative.

## Operator checklist

Before treating a packet as reviewable, check:

1. `Overall status` is not `blocked`.
2. `Decision/state consistency` is not `inconsistent`.
3. `Current answer status` is not `violation`.
4. `Signal state` is not `unavailable` unless the decision is conservatively `제외`.
5. Missing KOSPI200 futures flow has not been replaced by stock foreign flow or program trading data.
6. No line implies live order placement or direct execution.

## Validation

This document is docs-only. Standard local validation remains:

```bash
python3 scripts/save_conversation.py sync
python3 tests/run_all.py
git status --short
```
