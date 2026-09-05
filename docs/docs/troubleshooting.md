---
sidebar_position: 10
---

# Troubleshooting

Start with the smallest check that matches the failing layer:

```bash
nesk doctor
docker version
nesk validate --dir INSTANCE --instance
nesk status --dir INSTANCE
nesk diff --dir INSTANCE
nesk cache verify
```

`nesk doctor` checks both that the Docker executable is on `PATH` and that the
current user can reach the daemon. `docker version` prints the underlying
client/server detail.
Add `--json --non-interactive` when collecting diagnostics in automation. Process
exit codes identify the failing layer; the JSON `error.code` is its string name.

## Installation and command discovery

### `nesk: command not found`

**Likely cause.** The tool was installed into a directory that the current shell
does not search, or a newly changed `PATH` has not reached this terminal.

**Check.** For uv, run `uv tool list`, then inspect the executable directory
reported by `uv tool dir --bin`. For pipx, run `pipx list`. On Windows, also
open a new terminal after changing `PATH`.

**Fix.** Run `uv tool update-shell`, start a new shell, and retry:

```bash
uv tool install luminesk-cli
uv tool update-shell
nesk --version
```

For a pipx installation, run `pipx ensurepath` and start a new terminal.

If you installed a standalone release bundle, invoke `nesk` or `nesk.exe` from
the extracted directory or add that exact directory to `PATH`.

### Installation rejects the Python version

**Cause.** The Python package requires Python 3.13 or newer.

**Check.** Run `python --version` and `uv python list`.

**Fix.** Install a supported interpreter and let uv select it. A standalone
release bundle is an alternative when you do not want to manage Python.

### A downloaded executable does not start

**Likely causes.** The archive does not match the operating system or CPU, it was
not extracted before execution, or the Unix executable bit was lost.

**Check.** Compare the asset name with the platform table in
[Installation](./installation.md), verify the release checksum, and check the
extracted file type.

**Fix.** Download the correct archive again, verify it, extract it, and on Linux
or macOS run `chmod +x nesk` if necessary. Do not bypass an operating-system
security warning until the file and its release source have been verified.

## Docker

### `nesk doctor` says Docker is missing

**Cause.** The `docker` client is absent or not on `PATH`.

**Check and fix.** Install Docker for the current platform, open a new terminal,
and run:

```bash
nesk doctor
docker version
```

### `nesk doctor` succeeds but a later Docker operation fails

**Cause.** The daemon state or permissions may have changed after `doctor`, or
the operation may need registry, image, port, or mount access that `doctor`
does not exercise.

**Check.** `docker version` must show both client and server sections. On macOS
and Windows, confirm Docker Desktop is running. On Linux, inspect the daemon and
socket permissions using your distribution's Docker instructions.

**Fix.** Run `nesk doctor` again, then inspect the operation's runtime error and
Docker detail. Docker daemon access is security-sensitive; do not make its
socket world-writable.

### Docker cannot pull or use the locked image

**Likely causes.** Registry connectivity or authentication failed, the image is
unavailable for this CPU architecture, or a mutable tag changed during a new
resolution.

**Check.** Inspect `runtime.image` in `luminesk.lock`, then test that exact
digest with Docker. For a recipe checkout, also run:

```bash
nesk validate --dir RECIPE --resolve
```

**Fix.** Restore registry access or credentials, or choose an image published
for the host architecture. Recipe authors should choose an appropriate image
tag and regenerate the lock; operators should not hand-edit an installed lock.

## Catalog, network, and sources

### Catalog search is empty or stale

**Check.** Inspect the configured catalog and its last verified revision:

```bash
nesk catalog status
nesk catalog verify
nesk catalog update
nesk search QUERY
```

**Fix.** Restore network access and rerun `catalog update` to download the
official catalog again. If another verified revision is already cached, activate
it by exact 40-character commit with `nesk catalog use REVISION`. Do not suppress
the verification error or replace the catalog pointer by hand.

### A remote install asks for confirmation

This is expected. Luminesk prints the recipe origin, resolved revision,
build-code status, destination, and download count before trusting a remote
recipe. Review it, then rerun with `--yes`. Automation must use both
`--non-interactive` and `--yes`; Luminesk will not silently approve remote code.

### Source resolution times out or returns no artifact

**Likely causes.** The provider is unavailable, the recipe selector matches no
release or asset, credentials are required, or the response exceeds a bounded
network limit.

**Check.** Use `nesk validate --dir RECIPE --resolve` and read the source ID in
the error. Compare that source's selectors with the provider's current metadata.

**Fix.** Restore connectivity, correct the provider URL/selectors, or pin a
known valid version. Luminesk does not accept an ambiguous match. See
[Source Providers](./sources.md) for each provider's selection rules.

### A checksum or digest check fails

Treat this as a security failure, not as a transient warning. It can mean that
an upstream artifact changed, the declared checksum is wrong, a download was
corrupted, or cached content was modified.

```bash
nesk cache verify
nesk validate --dir RECIPE --resolve
```

Do not edit the lock to match unreviewed bytes. Verify the artifact from its
authoritative source and update the recipe or lock only after review. When a
locked cached blob is encountered with the wrong digest, Luminesk removes that
blob and rejects the operation; repeat the connected resolution only after the
security cause has been understood so it can fetch verified content again.

### The cache is large

Preview an age-based cleanup before applying it:

```bash
nesk cache prune --max-age 30 --dry-run
nesk cache prune --max-age 30
```

Pruning may make later frozen operations fail until their exact blobs have been
fetched again by a connected operation.

## Recipe and manifest validation

### TOML is invalid or a key is unknown

**Check.** Run static validation in the recipe directory:

```bash
nesk validate --dir RECIPE --static
```

The manifest schema is closed: misspelled and unsupported keys are errors.
Correct the TOML at the path named in the diagnostic. Do not add an undeclared
`[permissions]` table; build permission is represented by the presence of
`[build]`, with `[build].network` controlling build-network access.

### A required input is missing

Pass non-secret values with `--set NAME=VALUE` and secrets with
`--set-file NAME=PATH`:

```bash
nesk plan --dir RECIPE --set port=25565 --set-file rcon_password=./secret.txt
```

`validate --resolve` has no input flags. If a later phase needs a required input
without a default, use `plan` or a dry-run install with the required values.

### A template fails to render

**Likely causes.** A referenced input is missing, syntax is invalid, content
violates its output mode, or a rendered path is unsafe.

**Check.** Run `nesk plan` with all required inputs, then inspect the template
and its `mode`, `max_size`, and destination. Template access is limited to
declared inputs; environment variables and arbitrary host files are unavailable.

### A local file source is rejected

`local-file` paths must remain inside the recipe directory and must resolve to
regular files. Move the artifact into the recipe tree, declare its digest when
appropriate, and rerun static and resolve validation. Symlink or `..` escapes
are rejected.

### Build validation fails

Run the phases separately to locate the boundary:

```bash
nesk validate --dir RECIPE --resolve
nesk validate --dir RECIPE --build
```

Check the Dockerfile path, context, locked source inputs, network setting,
resource limits, and post-build file checks. A recipe with `[build]` executes
reviewed Docker build code; inspect it before approving a remote recipe.

## Lock and frozen mode

### `--frozen` fails

Frozen mode requires all three of these conditions:

- `luminesk.toml` matches the manifest digest in `luminesk.lock`;
- the lock target matches the current operating system and architecture;
- every locked source blob is already present and verifies in the content cache.

Run `nesk cache verify`. For a recipe checkout, use a connected `nesk lock` to
resolve and cache current inputs after reviewing the change. For an installed
instance, preview `nesk update`; do not replace its lock with one generated from
an unrelated checkout.

### The lock target does not match this machine

Locks are target-specific. Generate the lock and test the recipe on the target
operating system and architecture. There is no public target override that makes
a foreign lock executable on the current host.

### Instance state does not match the lockfile

**Likely cause.** A control file was edited or copied manually, or a transaction
was interrupted.

**Check.** Run:

```bash
nesk validate --dir INSTANCE --instance
nesk diff --dir INSTANCE
```

If a transaction is pending, recover it first. Otherwise restore the instance's
verified control files from backup or perform a reviewed update. Do not hand-edit
`.luminesk_cli` state to force the digests to agree.

## Install and ownership conflicts

### The destination already contains files

Remote recipe installs require a safe destination and will not merge arbitrary
pre-existing content. Select a new empty directory. To adopt an existing server,
install beside it and copy only recipe-declared `data` or `preserve` paths after
an offline backup; Luminesk has no command that converts an arbitrary directory
into a managed instance.

### Install or update refuses a managed file

**Cause.** A file recorded as `managed` or `generated` no longer matches its
last applied digest. Luminesk refuses to overwrite that operator modification.

**Check.** Run:

```bash
nesk diff --dir INSTANCE
nesk update --dir INSTANCE --dry-run
```

**Fix.** Save the edit, then either express it as a recipe/template change, move
it to a recipe-declared `preserve` or `data` path, or restore the last applied
file. There is no force flag that bypasses an ownership conflict.

### A post-install check fails

Read the failing check ID and expected path. Correct the recipe, artifact, input,
or file mapping and retry. A failed transaction attempts to restore the previous
files and control state; validate the instance before starting it.

## Runtime and readiness

### The container exits immediately

Start without waiting only when you need to observe an early process failure:

```bash
nesk start --dir INSTANCE --no-wait
nesk status --dir INSTANCE
nesk logs --dir INSTANCE
```

Check the image, command argument array, mounted paths, file permissions, memory
limit, and required inputs. Stop the failed container before retrying. Remember
that Luminesk passes an argv array directly—shell expansion and shell operators
do not run.

### The host port is already in use

Inspect Docker containers and the host's listening ports, then stop the
conflicting service or select a different declared port input. Use `nesk plan`
to confirm the rendered host-to-container mapping before starting. Do not expose
a service on a public interface unless that is intentional.

### The process cannot read or write a mount

Compare recipe mount targets, ownership modes, Docker bind mounts, and
`runtime.run_as`. Confirm the host source exists and that its permissions match
the numeric container user. Correct ownership deliberately; avoid broad
world-writable permissions as a shortcut.

### Readiness times out

**Check.** Inspect the declared readiness kind, timeout, retries, command or
pattern, and port interpolation. For a currently running instance:

```bash
nesk validate --dir INSTANCE --readiness
nesk logs --dir INSTANCE
```

Log-based readiness diagnostics are saved under
`.luminesk_cli/logs/readiness-*.log`. A normal `start` removes a newly created
container when required readiness fails, so Docker logs may no longer be
available afterward; the saved diagnostic log is the durable evidence for
log-regex checks. Use `--no-wait` only for diagnosis, not to declare the server
healthy.

### Update readiness fails

If the instance was running before the update, Luminesk stops it, applies the
new plan, starts it, and evaluates required readiness. A failure attempts to
restore the prior filesystem/control state and restart the prior runtime.

Check the original error and any separate rollback detail. Then run `status`,
`validate --instance`, and `diff`. If rollback was incomplete, stop runtime
activity and use `recover` as described below.

## Interrupted transactions and recovery

### An operation says that a transaction is pending

Do not delete the journal or backup directory. Stop the instance if it is still
running, then restore the recorded backup:

```bash
nesk recover --dir INSTANCE
nesk validate --dir INSTANCE --instance
nesk diff --dir INSTANCE
```

When a journal exists, `recover` selects its matching backup. Without a journal,
it selects the newest retained transaction backup and fails if none exists.
Review the resulting instance before starting it.

### The global index lost an instance

Rebuild index entries only from valid current Luminesk instance state:

```bash
nesk import INSTANCE
nesk import /srv/minecraft --scan
```

`--scan` recursively searches descendants for `.luminesk_cli/state.json` and
validates each recorded instance root. Import does not convert legacy or
arbitrary server directories.

## Collecting a useful problem report

Include the Luminesk version and platform, the failing command, its numeric exit
status, and sanitized JSON output. Also include `nesk doctor`, `docker version`,
the relevant validation phase, and the recipe source/revision. Remove secret
input values, credentials, private URLs, and world/player data. Do not publish
the contents of `.luminesk_cli` blindly; it can contain persisted input values
and operational metadata.
