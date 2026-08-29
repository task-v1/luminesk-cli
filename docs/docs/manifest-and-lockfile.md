---
sidebar_position: 7
---

# Manifest and Lockfile

`luminesk.toml` is the only recipe entrypoint. Unknown keys are errors. The
declaration `manifest_version = 1` is the current file-format revision used by
Nesk 2.0; it is not a product compatibility switch.

## Main tables

| Section | Declares |
| --- | --- |
| `[package]` | Recipe name, version, description, and target platforms. |
| `[inputs.*]` | Typed string, integer, or boolean build/runtime inputs. |
| `[[sources]]` | Provider, version policy, target, size limit, and network policy. |
| `[[files]]` | Recipe files, destination, ownership, template, and executable bit. |
| `[build]` | Optional bounded Dockerfile build and its output directory. |
| `[runtime]` | Docker image, argv command, workdir, limits, user, and restart policy. |
| `[[runtime.mounts]]` | Instance-relative sources and absolute container targets. |
| `[[runtime.ports]]` | Named TCP or UDP mappings. |
| `[[checks]]` | Post-build files/commands and runtime readiness checks. |
| `[update]` | Backup paths, retention, and rollback policy. |
| `[permissions]` | Explicit build permission; host commands remain forbidden. |

Paths must be canonical relative POSIX paths and portable across supported
platforms. Runtime container paths must be absolute. Commands are TOML arrays,
for example `command = ["java", "-jar", "server.jar"]`; shell strings are not
accepted.

## Lockfile rules

`nesk lock` writes `luminesk.lock` crash-safely. It contains:

- manifest SHA-256 and target platform;
- provider, resolved version/revision, URL, size, digest, and target for each
  source;
- exact runtime image repository digest;
- exact Dockerfile base image digests when a build exists;
- exact recipe commit and tracking policy for remote installs.

Do not hand-edit the lockfile. Regenerate it and review the diff.
