# `upgrade-core` command

Command to upgrade the current engine version or redownload it from scratch.

---

## Syntax

### Upgrade Engine to Latest Version
```bash
nesk upgrade-core [tag] [options]
```
- **Alias**: `upcore`

---

## Options for `upgrade-core`

- `-r`, `--redownload`: Downloads the core from scratch without checking version hashes. Use this if the local core executable is missing or corrupted.

---

## Operations details
:::warning
Before upgrading a core, **the server must be stopped**. If you attempt to run these commands on an active server, the CLI will throw a safety error.
:::

### How `upgrade-core` works:
1. Queries the remote repository provider (Maven, Jenkins, etc.) to fetch the latest compiled version metadata.
2. Compares the retrieved version with the `core_hash` stored in the server's database profile.
3. If a newer build exists (or `--redownload` is passed), it downloads the fresh JAR file, removes the older JAR to conserve disk space, and updates the local metadata.

---

## Examples

### Upgrade the server in current directory
```bash
nesk upgrade-core
```

### Force redownload of the core from scratch
```bash
nesk upgrade-core --redownload
```
