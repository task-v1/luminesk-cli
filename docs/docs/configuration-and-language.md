---
sidebar_position: 8
---

# Configuration & Language

Luminesk stores configuration and server state in a user-level config directory using SQLite.

## What is stored

- current CLI language;
- default server path;
- server registrations and runtime metadata.

## Change CLI language

Show current and available languages:

```bash
nesk change-lang
```

Set language:

```bash
nesk change-lang en
```

## Server tags

Tags are normalized to lowercase and must match:

- allowed characters: letters, digits, `-`, `_`, `.`;
- no spaces.

## Memory limit format

`create --memory` accepts values like:

- `512m`
- `1g`
- `2048m`

Invalid formats fail validation.

## Runtime image format

`create --image` and `change-image --image` require a non-empty Docker image reference without spaces.

## Notes

- Omitting some arguments starts interactive prompts.
- Most server commands resolve the server by current directory when tag is omitted.

See [Command Reference](/docs/command-reference) for exact command signatures.
