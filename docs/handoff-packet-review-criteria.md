# Handoff packet review criteria

This note defines when a locally produced handoff packet example is useful enough to preserve for future review.

It is a documentation-only note. It does not add packet examples, code changes, chart files, screenshots, or runtime behavior.

## Purpose

A packet example can help reviewers understand whether the handoff workflow is clear, deterministic, and safe to inspect.

Most packet examples should stay local. Only a small, sanitized, durable example should be considered for a documentation or fixture PR.

## Keep local by default

Keep a packet example local when it is only useful for a one-time check, a temporary debugging session, or a private review.

Keep it local when it contains or may reveal:

- account details;
- personal identifiers;
- private notes;
- unreviewed copied text;
- raw screenshots or chart material;
- temporary paths;
- noisy data that is not needed for future review.

When unsure, keep the example local and summarize the relevant behavior in a PR instead of committing the packet.

## Commit-worthy examples

A packet example may be worth preserving only when it has durable review value.

Good candidates are examples that show:

- a stable guardrail section layout;
- a deterministic packet path or naming rule;
- a representative fixture scenario;
- a regression case that is hard to understand from unit tests alone;
- a sanitized post-review lesson that future maintainers can inspect.

A committed example should be small, focused, and tied to a clear review purpose.

## Review checklist

Before preserving a packet example, check:

1. Does the example explain something future reviewers will need?
2. Is the example fully sanitized?
3. Is the example tied to a named scenario or review purpose?
4. Is the file path deterministic and easy to audit?
5. Is the example smaller than a raw operator dump?
6. Does the PR explain why the example belongs in the repository?
7. Could a short documentation excerpt replace the full packet?

If the answer to item 7 is yes, prefer the shorter documentation excerpt.

## Suggested committed path

If a future PR preserves a packet example, prefer a clearly labeled path such as:

```text
handoff/YYYY-MM-DD/examples/HHMM-symbol-purpose.md
```

Do not place review examples beside active local output unless the PR explains why the path is safe and stable.

## PR expectations

A PR that preserves a packet example should explain:

- why the example is useful;
- what was removed or sanitized;
- which scenario or review purpose it covers;
- whether related assets are absent, local-only, or separately documented;
- why the example is better than a short excerpt.

The PR should avoid mixing example preservation with code behavior changes.

## Relationship to current writer

The current writer remains an explicit local output helper. It should not automatically decide that a packet example belongs in Git.

Promotion from local output to a preserved example is a human review decision.

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
