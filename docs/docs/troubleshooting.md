---
sidebar_position: 10
---

# Troubleshooting

This page uses **symptom → cause → resolution**.

## `nesk diagnostic` fails

**Symptom**

- one or more source checks show failed status.

**Likely causes**

- network outage;
- provider endpoint unavailable;
- DNS/proxy restrictions.

**Resolution**

1. Re-run `nesk diagnostic`.
2. Verify internet/proxy access from your shell.
3. Retry later if provider endpoints are down.

## Docker not found / Docker commands fail

**Symptom**

- startup fails with Docker-related errors.

**Likely causes**

- Docker is not installed;
- Docker daemon is not running;
- current user lacks Docker access.

**Resolution**

1. Install Docker and ensure `docker` is in PATH.
2. Start Docker daemon/Desktop.
3. Validate with `docker ps`.

## Server start fails after creation

**Symptom**

- `nesk start` fails or exits immediately.

**Likely causes**

- invalid runtime image;
- broken core download/provider response;
- invalid server configuration for selected core.

**Resolution**

1. Confirm image with `nesk change-image <tag> --image <valid-image>`.
2. Run `nesk diagnostic`.
3. Re-download core: `nesk upgrade-core <tag> --redownload`.
4. Attach logs: `nesk attach <tag>`.

## `upgrade-core` reports missing hash guidance

**Symptom**

- upgrade suggests redownload due to missing hash metadata.

**Likely cause**

- server metadata lacks prior core hash.

**Resolution**

Run:

```bash
nesk upgrade-core <tag> --redownload
```

## `delete` refuses running server

**Symptom**

- delete fails because server must be stopped.

**Likely cause**

- runtime is still running or loop controller remains active.

**Resolution**

1. Stop server: `nesk stop <tag>`.
2. If loop-related, retry with `--force` where appropriate.
3. Re-run delete: `nesk delete <tag>`.

## Invalid status filter in `list`

**Symptom**

- `nesk list --status <value>` fails.

**Likely cause**

- only `running` and `stopped` are accepted.

**Resolution**

Use one of:

```bash
nesk list --status running
nesk list --status stopped
```

## Need more context

- [Command Reference](/docs/command-reference)
- [Server Lifecycle](/docs/server-lifecycle)
- [Runtime & Docker Model](/docs/runtime-and-docker)
