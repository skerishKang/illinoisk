# Conversation sync usage

## Purpose

Use `sync` as the default local command after editing Markdown conversation archives.

The repository policy is:

- Markdown conversation files are the Git-tracked source archive.
- `DB/conversations.db` is a local, regenerable SQLite search index.
- Database files are not committed to Git.

## Default command

```bash
python3 scripts/save_conversation.py sync
```

This runs the normal Markdown import workflow, prints the conversation index, and shows the total number of indexed dates and messages.

## Sync with search verification

```bash
python3 scripts/save_conversation.py sync --keyword "ISC"
```

When `--keyword` is provided, `sync` also prints up to 10 search results after rebuilding the local SQLite index.

## Fresh environment setup

After cloning or pulling the repository on a new local environment, run:

```bash
python3 scripts/save_conversation.py sync
python3 scripts/save_conversation.py sync --keyword "ISC"
```

Expected behavior:

- Markdown archives are imported into the local SQLite index.
- The date index is printed.
- Total date and message counts are shown.
- Optional keyword search confirms that the regenerated index is usable.

## Operational rule

After adding or editing a conversation Markdown file:

1. Save the Markdown source file under `conversations/`.
2. Run `python3 scripts/save_conversation.py sync`.
3. Run `python3 scripts/save_conversation.py sync --keyword "<representative keyword>"` when a search check is needed.
4. Do not commit `DB/conversations.db`.
