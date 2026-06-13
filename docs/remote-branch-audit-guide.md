# Remote branch audit guide

This guide defines a safe review workflow for remote feature branches that appear after normal PR work.

It was added after a broad remote-branch grep matched many `origin/docs/*` branches that were unrelated to the just-finished PR. The rule is simple: do not remove broad branch groups without mapping each branch to its purpose first.

## Purpose

Use this guide when checking whether remote branches are current, stale, merged, active, or intentionally preserved.

This is an audit workflow only. It does not define an automatic cleanup script.

## Default rule

Do not delete branches from a broad prefix match such as:

```bash
git branch -r | grep "origin/docs/"
```

A prefix match is an inventory signal, not a deletion list.

## Safe inventory commands

Start from an up-to-date main branch:

```bash
cd /mnt/d/illinoisk
git switch main
git pull --ff-only origin main
git fetch --prune
```

List remote branches by prefix:

```bash
git branch -r | grep "origin/docs/" || true
git branch -r | grep "origin/scripts/" || true
```

For a specific branch, use a narrow check:

```bash
git branch -r | grep "origin/docs/example-branch-name" || true
```

## Branch classification

Classify each branch before any deletion decision.

| Category | Meaning | Action |
| --- | --- | --- |
| Active | Still tied to an open PR, open issue, or ongoing local work. | Keep. |
| Merged and disposable | PR is merged, branch is no longer needed, and no local-only recovery value remains. | May delete after explicit approval. |
| Closed but preserved | PR or issue is closed, but branch intentionally preserves context or old experiments. | Keep or document separately. |
| Unknown | No clear PR, issue, or owner decision. | Keep until investigated. |
| Current task residue | Branch was created for the current task and the task is merged and verified. | Delete after verification. |

## Required checks before deletion

Before deleting a remote branch, record:

1. branch name;
2. related PR number, issue number, or reason no PR exists;
3. PR state if applicable;
4. whether the branch has been merged or superseded;
5. whether any local patch or recovery branch still depends on it;
6. explicit operator approval for deletion.

Do not rely on `git branch -r --merged origin/main` alone. Squash merges may not always appear as directly merged branch histories.

## Current-task branch check

When a task branch is known exactly, use a narrow grep:

```bash
git branch -r | grep "origin/docs/local-handoff-write-pipeline-audit" || true
```

A narrow check avoids confusing unrelated `origin/docs/*` branches with the current PR branch.

## Deletion command template

Use this only after the required checks and explicit approval:

```bash
git push origin --delete BRANCH_NAME
git fetch --prune
```

Example shape:

```bash
git push origin --delete docs/example-branch-name
git fetch --prune
```

Do not paste a generated list of many branches into this command without reviewing each entry.

## Reporting format

Use this table when reporting remote branch audit results:

```text
| Branch | Related PR/Issue | State | Decision | Notes |
| --- | --- | --- | --- | --- |
| origin/docs/example | PR #000 | merged | delete candidate | verified, no local dependency |
| origin/docs/unknown | unknown | unknown | keep | needs investigation |
```

## Validation for docs-only updates

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
