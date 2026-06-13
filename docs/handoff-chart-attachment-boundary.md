# Handoff chart attachment boundary

This document defines the local-only boundary for chart images, screenshots, and chart sidecar data that may be referenced during handoff packet review.

It is a documentation-only boundary. It does not add chart capture, chart file writing, image processing, or runtime behavior.

## Purpose

Chart context can be useful when reviewing a handoff packet, especially for:

- missed signal review;
- model answer review;
- entry, stop, or take-profit reasoning review;
- postmarket lessons;
- future regression fixture candidates.

However, chart images and sidecar data can also contain private account, broker, balance, order, timestamp, or unrelated personal information. Treat every chart attachment as local-only until a human operator confirms it is safe to preserve.

## Current status

The current handoff pipeline does not write chart attachments.

The current supported generated packet workflow is still Markdown-only unless a human manually adds sanitized references later:

```bash
python3 scripts/run_full_handoff_fixture.py \
  --scenario active-symbol-signal \
  --write-output handoff
```

Do not interpret this document as approval to add automatic chart writing.

## Allowed committed references

A committed handoff packet may reference a chart attachment only when all of these are true:

1. The attachment has durable review value.
2. The attachment is sanitized before commit.
3. The attachment is directly related to the packet's symbol, date, and review purpose.
4. The attachment path is deterministic and easy to audit.
5. The PR explains why the attachment belongs in Git.

Good examples:

- a sanitized chart image showing a missed technical signal that should become a future regression example;
- a manually redacted screenshot used for a postmarket lesson;
- a small sanitized sidecar file that records only non-private chart metadata needed for review.

## Keep local-only

Keep chart material local-only when it contains, or may contain:

- account numbers;
- broker identifiers;
- order IDs;
- balances, buying power, holdings, or P/L;
- access tokens, API keys, or session identifiers;
- Discord user IDs or private channel information;
- unrelated personal data;
- raw screenshots of a full desktop or trading terminal;
- noisy chart context that is not needed for future review.

If there is any uncertainty, keep the attachment local-only and paste a sanitized excerpt into ChatGPT web manually.

## Sanitization checklist

Before committing any chart attachment or chart sidecar, check:

1. Is the symbol and date visible only when needed for review?
2. Are account, balance, order, broker, and credential fields absent or redacted?
3. Are private usernames, channel names, window titles, and desktop notifications absent or redacted?
4. Is the attachment cropped to the smallest review-relevant area?
5. Is the attachment linked to a specific handoff packet or review purpose?
6. Is the file name deterministic and non-duplicative?
7. Does the PR explain why the attachment is safe and durable?

## Suggested paths

If chart attachments are committed manually, prefer paths under the same dated handoff review area:

```text
handoff/YYYY-MM-DD/assets/HHMM-symbol-purpose-chart.png
handoff/YYYY-MM-DD/assets/HHMM-symbol-purpose-chart.json
```

The `assets/` directory must not be populated automatically by the current writer. A future implementation issue must define any writer behavior separately.

## Sidecar data boundary

Sidecar data should be minimal and review-focused.

Allowed sidecar fields may include:

```text
symbol
date
purpose
timeframe
source_label
sanitization_status
review_note
```

Avoid sidecar fields such as:

```text
account_number
broker_account_id
order_id
balance
holding_quantity
access_token
session_id
discord_user_id
private_channel_id
raw_terminal_export
```

Use labels such as `sanitized`, `local-only`, `redacted`, or `unavailable` when the source status matters for review.

## Relationship to generated handoff packets

A generated handoff packet remains review material only. A chart attachment does not turn a packet into a trading signal or execution instruction.

Do not combine chart attachment work with:

- live Discord integration;
- Kiwoom or broker integration;
- OpenAI/API calls;
- network fetches;
- trading execution;
- automatic packet commits.

## Future implementation requirements

Before adding any chart write behavior, open a separate implementation issue.

That future issue should specify:

- exact CLI option shape;
- whether attachments are manual-only or writer-produced;
- deterministic asset path rules;
- overwrite behavior;
- sanitization enforcement or explicit local-only defaults;
- focused local tests;
- no-live-integration boundaries.

A future code PR should not reuse this docs-only issue as implementation approval.

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
