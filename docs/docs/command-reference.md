---
sidebar_position: 5
---

# Command Reference

All commands are available under the `nesk` entrypoint.

## Global flags

- `--help`, `-h`: show help.
- `--version`, `-v`: show version.

## `diagnostic` (aliases: `check`, `diag`)

Checks core provider endpoints.

**Expected outcome**

- Success: table of checks and exit code `0`.
- Failure: one or more failed checks, non-zero exit.

## `cores` (alias: `c`)

Lists available core providers.

**Expected outcome**

- Prints core names and descriptions.

## `create` (aliases: `new`, `init`)

Creates a new managed server.

**Options**

- `--name`, `-n`: display name.
- `--dir`, `-d`: server directory path.
- `--core`, `-c`: core identifier.
- `--tag`, `-t`: unique server tag.
- `--force`, `-f`: allow replacing existing target directory/path conflicts.
- `--memory`, `-m`: Docker memory limit (default `1g`).
- `--image`, `-i`: runtime Docker image.

**Expected outcome**

- Creates/registers server metadata and downloads core executable.
- Prints success panel with core/image/memory/path details.
- If required values are omitted, interactive prompts are shown.

## `start` (alias: `s`)

Starts a server.

**Arguments**

- `[tag]`: optional; if omitted, Luminesk resolves by current directory.

**Options**

- `--loop`, `-l`: restart loop mode.
- `--detached`, `-d`: start in background without attaching.

**Expected outcome**

- Starts Docker-backed runtime.
- Returns process exit code when attached, or immediate success in detached mode.

## `attach` (alias: `a`)

Attaches to a running server log stream.

**Arguments**

- `[tag]`: optional; resolves by current directory if omitted.

**Expected outcome**

- Attaches to active server runtime logs.

## `upgrade-core` (alias: `upcore`)

Upgrades server core to the latest available version.

**Arguments**

- `[tag]`: optional; resolves by current directory if omitted.

**Options**

- `--redownload`, `-r`: force download even when hash comparison is unavailable or unchanged.

**Expected outcome**

- Updates executable/hash when newer core exists.
- Prints "already up to date" when no update is needed.

## `change-image` (alias: `image`)

Changes runtime Docker image for a stopped server.

**Arguments**

- `[tag]`: optional; resolves by current directory if omitted.

**Options**

- `--image`, `-i`: Docker image name.

**Expected outcome**

- Validates image and saves it to server metadata.
- Fails if image is invalid/unavailable or server cannot be modified.

## `stop` (alias: `st`)

Gracefully stops a server.

**Arguments**

- `[tag|pid]`: optional. You can target by server tag, PID, or current directory.

**Options**

- `--force`, `-f`: force stop behavior (required for some loop-mode cases).

**Expected outcome**

- Sends stop signal and prints action details.
- In loop mode without force, can stop server process while keeping loop controller active and show guidance.

## `kill` (alias: `k`)

Force-kills a server.

**Arguments**

- `[tag|pid]`: optional. You can target by server tag, PID, or current directory.

**Options**

- `--force`, `-f`: force behavior for loop controller scenarios.

**Expected outcome**

- Sends kill signal and prints action details.

## `delete` (alias: `d`)

Deletes a stopped server from Luminesk state.

**Arguments**

- `[tag]`: optional; resolves by current directory if omitted.

**Options**

- `--yes`, `-y`: skip confirmation prompt.

**Expected outcome**

- Removes Luminesk metadata and unregisters the server.
- Refuses deletion when server is running/loop-active.

## `list` (aliases: `ls`, `l`)

Lists managed servers with runtime info.

**Options**

- `--tag`, `-t`: filter by tag.
- `--status`, `-s`: filter by `running` or `stopped`.
- `--core`, `-c`: filter by core id.

**Expected outcome**

- Shows table with status, pid, uptime, last start/stop, image, and path.
- Shows info message when no servers or no matches.

## `change-lang` (alias: `lang`)

Changes CLI language.

**Arguments**

- `[lang]`: target language code. If omitted, prints current and available languages.

**Expected outcome**

- Saves selected language into user config.
- Subsequent CLI help/messages use the new language.

## Related guides

- [Server Lifecycle](/docs/server-lifecycle)
- [Cores & Upgrades](/docs/cores-and-upgrades)
- [Configuration & Language](/docs/configuration-and-language)
- [Troubleshooting](/docs/troubleshooting)
