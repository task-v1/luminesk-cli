---
sidebar_position: 4
---

# Templates and Inputs

Inputs make one recipe configurable without turning it into executable install
logic. Templates substitute those typed values into files; runtime fields can
use non-secret values where the manifest permits interpolation.

## Declare inputs

```toml
[inputs.server_name]
type = "string"
default = "Minecraft Server"
prompt = "Server name"
pattern = "^.{1,80}$"

[inputs.memory]
type = "string"
default = "4g"
pattern = "^[1-9][0-9]*[mMgG]$"

[inputs.port]
type = "integer"
default = 25565
min = 1
max = 65535

[inputs.eula]
type = "boolean"
required = true
prompt = "Accept the Minecraft EULA"
```

Input types are `string`, `integer`, and `boolean`. Defaults must have the same
TOML scalar type. Integer `min`/`max` and string `pattern` validation run again
when package values are resolved. `pattern` is a Python regular expression
matched against the complete value.

`prompt` is descriptive metadata. The current CLI does not automatically ask
that prompt; a required input without a default must be supplied explicitly.

## Supply values

```bash
nesk plan --dir ./recipe \
  --set eula=true \
  --set server_name="My Server" \
  --set memory=6g \
  --set port=25566
```

`--set KEY=VALUE` is repeatable. Integer text is converted with Python's integer
parser. Boolean text accepts only case-insensitive `true` or `false`. An
unknown name, duplicate name across value/file forms, empty assignment, wrong
type, failed regex, or out-of-range integer is an error.

Install/update values have this precedence:

1. a `--set` or `--set-file` override;
2. an existing non-secret instance value during update;
3. the manifest default;
4. missing—allowed only when the input is not required and nothing references
   it during rendering/runtime creation.

Successful install/update persists non-secret resolved values in instance
state. `start` and `restart` combine those saved values with command-line
overrides, but runtime overrides are not persisted and do not re-render files.

## Secret inputs

```toml
[inputs.rcon_password]
type = "string"
required = true
secret = true
prompt = "RCON password"
```

Supply a secret from a file, never a process argument:

```bash
nesk install ./recipe --dir ./instance \
  --set-file rcon_password=./secrets/rcon-password.txt
```

The input file must be UTF-8 and at most 64 KiB. Luminesk removes one trailing
LF or CRLF. Secret inputs:

- cannot declare a default;
- are rejected by `--set` and must use `--set-file`;
- are excluded from persisted instance state and normal JSON output;
- may be referenced only in rendered file content, not runtime image/argv,
  workdir, memory, mounts, ports, stop/restart fields, or checks;
- cause the rendered file mode to be owner-only (`0600`, or `0700` when the
  file is explicitly executable).

The original secret still exists in the input file and rendered instance file;
protect both. Because the value is not persisted, provide it again when a later
update must re-render the secret-bearing file.

## Top-level template tree

Declare one recipe-relative directory:

```toml
template = "template"
```

```text
template/
├── eula.txt.tmpl
├── server.properties.tmpl
└── defaults.yml
```

- Directories and regular files keep their relative layout.
- A filename ending in `.tmpl` is decoded as UTF-8, rendered, and installed
  without the suffix.
- Other regular files are copied byte-for-byte.
- Output ownership defaults to `generated`; `[ownership]` can override matching
  paths to `preserve` or `data`.
- A collision with source/build/`[[files]]` output is rejected.

Template collection rejects symlinks, hardlinks, and special files. It is
bounded to 4,096 regular files, 16 MiB per file, and 64 MiB total.

For `template/server.properties.tmpl`:

```text
motd=${input.server_name}
server-port=${input.port}
```

For `template/eula.txt.tmpl`:

```text
eula=${input.eula}
```

Boolean rendering is lowercase. Placeholders with no resolved value fail the
package build; unknown text outside `${input.NAME}` remains unchanged.

## Explicit `[[files]]` templates

Use `[[files]]` when source and target names differ, when one source directory
needs a single ownership mode, or when executable behavior is explicit:

```toml
[[files]]
source = "config/server.properties.in"
target = "server.properties"
mode = "preserve"
template = true

[[files]]
source = "scripts/healthcheck.sh.in"
target = "bin/healthcheck"
mode = "managed"
template = true
executable = true
```

With `template = true`, every regular source file is rendered as UTF-8. The
source filename is not modified automatically—`target` is exact. A directory
source is copied recursively below the target. Symlinks and special files are
rejected.

Use one of the four ownership modes deliberately:

- `managed` for recipe content replaced only while the installed digest is
  unchanged;
- `generated` for rendered output with the same conflict protection;
- `preserve` for a seed file whose existing user copy always wins;
- `data` for user-owned directories/files. An absent data-mode source creates
  an empty target directory.

## Executable files and reproducible modes

Recipe host permissions are not copied into packages. Normal files are `0644`,
directories are `0755`, and only a declared `executable = true` or matching
`[ownership].executable` path adds the owner executable bit. Secret-bearing
files remain owner-only. This keeps package metadata stable across Linux,
macOS, and Windows recipe authors.

## Input interpolation outside files

Non-secret `${input.NAME}` values can appear in runtime strings, argv elements,
mount source/target, port values, and check fields. Port strings are stricter:
they must consist only of one input reference in the manifest, then resolve to
an integer from 1 through 65535.

```toml
[runtime]
image = "eclipse-temurin:21-jre"
command = ["java", "-Xmx${input.memory}", "-jar", "server.jar", "nogui"]
memory = "${input.memory}"

[[runtime.ports]]
name = "game"
host = "${input.port}"
container = "${input.port}"
```

Source provider options and package metadata are not template fields. Put
version selection in the provider's own supported option instead of expecting
generic interpolation.

## Safe configuration workflow

For files users will edit, such as `server.properties`, set an explicit
preserve policy and preview updates:

```toml
[ownership]
preserve = ["server.properties"]
data = ["world", "plugins"]
```

```bash
nesk plan --dir ./recipe --set eula=true
nesk install ./recipe --dir ./test-instance --set eula=true --dry-run
nesk diff --dir ./instance
nesk update --dir ./instance --dry-run
```

See [Ownership and User Data](/docs/ownership) for the exact update behavior.
