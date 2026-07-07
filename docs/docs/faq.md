---
sidebar_position: 11
---

# FAQ

## Is Luminesk production-ready?

Luminesk is in active beta. It is suitable for local development and smaller operational setups. Test carefully before high-risk production workloads.

## Do I need Docker?

Yes. Luminesk uses Docker to run managed server processes.

## Can I run multiple servers?

Yes. Use unique tags and paths per server, then manage all servers through `nesk list`, filters, and per-tag operations.

## Do I always need to pass a tag?

No. Most commands can resolve the server from the current working directory if tag is omitted.

## Can I target by PID?

`stop` and `kill` accept PID-based targeting in addition to tag and directory resolution.

## How do I change Java runtime image?

Use:

```bash
nesk change-image <tag> --image <image>
```

## How do I update server core binaries?

Use:

```bash
nesk upgrade-core <tag>
```

Add `--redownload` to force refresh.

## Where should I start if something breaks?

1. `nesk diagnostic`
2. `nesk list`
3. `nesk attach <tag>`
4. [Troubleshooting](/docs/troubleshooting)
