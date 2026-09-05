---
sidebar_position: 1
---

# Creating a Custom Recipe

This tutorial builds a small Paper Java core recipe. It demonstrates the
manifest contract and test workflow; the named Minecraft version, image,
memory, and ownership list are examples derived from the repository's reference
fixtures, not guaranteed production recommendations. Review upstream support,
licenses, EULA terms, ports, and resource needs for your deployment.

## 1. Create the recipe directory

```bash
nesk init --dir ./my-paper-core --name my-paper-core
```

`init` creates a valid-shaped starter whose artifact URL is intentionally
non-working. Replace that manifest and add this template tree:

```text
my-paper-core/
├── luminesk.toml
└── template/
    ├── eula.txt.tmpl
    └── server.properties.tmpl
```

The finished manifest is shown below, followed by an explanation of each
design decision.

```toml
manifest_version = 1
template = "template"

[package]
name = "my-paper-core"
version = "0.1.0"
display_name = "My Paper Core"
kind = "core"
game = "minecraft"
edition = "java"
summary = "A Paper Java server maintained by Example Org"
keywords = ["paper", "java", "plugins"]
license = "MIT"
authors = ["Example Org"]

[package.repository]
url = "https://github.com/example/my-paper-core"

[inputs.server_name]
type = "string"
default = "Minecraft Server"
prompt = "Server name"
pattern = "^.{1,80}$"

[inputs.eula]
type = "boolean"
required = true
prompt = "Accept the Minecraft EULA"

[inputs.memory]
type = "string"
default = "4g"
prompt = "Java heap and container memory limit"
pattern = "^[1-9][0-9]*[mMgG]$"

[inputs.port]
type = "integer"
default = 25565
min = 1
max = 65535

[[sources]]
id = "core"
type = "paper"
target = "server.jar"
max_size = 536870912

[sources.options]
minecraft = "1.21.8"
build = "latest"

[[files]]
source = "data/world"
target = "world"
mode = "data"

[[files]]
source = "data/world_nether"
target = "world_nether"
mode = "data"

[[files]]
source = "data/world_the_end"
target = "world_the_end"
mode = "data"

[[files]]
source = "data/plugins"
target = "plugins"
mode = "data"

[ownership]
preserve = ["server.properties"]
data = ["world", "world_nether", "world_the_end", "plugins"]

[runtime]
image = "eclipse-temurin:21-jre"
command = ["java", "-Xms${input.memory}", "-Xmx${input.memory}", "-jar", "server.jar", "nogui"]
workdir = "/server"
memory = "${input.memory}"
stop_signal = "SIGINT"
stop_timeout = 30
restart = "unless-stopped"
read_only_root = true

[[runtime.mounts]]
source = "."
target = "/server"
mode = "rw"

[[runtime.ports]]
name = "game"
host = "${input.port}"
container = "${input.port}"
protocol = "tcp"

[[checks]]
id = "core-present"
phase = "post-build"
kind = "file"
path = "server.jar"

[[checks]]
id = "properties-installed"
phase = "post-install"
kind = "file"
path = "server.properties"

[[checks]]
id = "ready"
phase = "readiness"
kind = "log-regex"
pattern = "Done .* For help, type"
timeout = 120
required = true

[update]
strategy = "transactional"
backup = ["world", "world_nether", "world_the_end", "plugins", "server.properties"]
retain_backups = 3
rollback_on_failure = true
```

## 2. Describe identity and inputs

`package.version` versions your recipe. Bump it whenever published recipe
content changes so operators can distinguish revisions. It is separate from
the Minecraft/Paper artifact selected by the `core` source.

The recipe deliberately has no default for `eula`: an operator must supply the
boolean explicitly. Other inputs have usable defaults and validation. The port
input is shared by Docker publication; the memory input is used both in Java's
argv and Docker's memory limit.

Create `template/eula.txt.tmpl`:

```text
eula=${input.eula}
```

Create `template/server.properties.tmpl`:

```text
motd=${input.server_name}
server-port=${input.port}
```

Every `.tmpl` file must be UTF-8. Luminesk renders the placeholders and removes
the `.tmpl` suffix in package output.

## 3. Resolve the server binary

The `paper` provider selects a Paper build for the requested Minecraft version.
`build = "latest"` means the latest build whose Paper channel is `STABLE` at
lock time. The lock records the exact Minecraft/build identity, URL, size, and
upstream SHA-256. To prioritize immutability over automatic discovery, set an
explicit integer build and update it deliberately.

The source target `server.jar` is a package-relative destination. It is also
the path used by the Java argv and the post-build file check.

## 4. Define templates and user data

Top-level template output is `generated` by default. The ownership override
marks `server.properties` as `preserve`, so an operator's later changes win
over new recipe content.

Each `mode = "data"` file declaration above names a source directory that does
not need to exist. For data mode only, an absent source creates an empty target
directory. Paper can then populate worlds and plugins without making their
contents Luminesk-managed. If you want seed data, create the corresponding
directory in the recipe and put regular files in it.

Think carefully before marking a config file `preserve`: future recipe changes
will not update an existing copy. Use `generated` when input changes should
replace an untouched file, and use `managed` for immutable recipe content.

## 5. Define Docker runtime and readiness

The image tag is convenient in source; `nesk lock` resolves it to a repository
digest. Runtime commands are argv, never shell text. The explicit root mount
makes instance files visible at `/server`; the root filesystem outside that
mount remains read-only.

The readiness regex matches Paper's normal startup log. Validate it against the
exact server release you deploy. A required timeout removes a newly started
container. During update, Luminesk then restores and restarts the previous
instance.

`post-build` checks package staging. `post-install` checks the applied instance.
Both phases currently support only file checks.

## 6. Validate, lock, and plan

Static validation does not contact providers:

```bash
nesk validate --dir ./my-paper-core --static
```

Resolve providers and the Docker image, then create the lock:

```bash
nesk validate --dir ./my-paper-core --resolve
nesk lock --dir ./my-paper-core
```

Review `luminesk.lock`, but do not edit it. Package assembly needs the required
EULA value, so exercise it with `plan`:

```bash
nesk plan --dir ./my-paper-core \
  --set eula=true \
  --set server_name="Development Server" \
  --set memory=2g
```

`nesk validate --build` has no input flags. For a recipe with a required input
and no default, `plan` or a test install is the correct full package-rendering
exercise after static/resolve validation.

## 7. Test a local install

Install into a separate empty directory so the recipe source remains clean:

```bash
nesk install ./my-paper-core \
  --dir ./test-paper \
  --set eula=true \
  --set server_name="Development Server" \
  --set memory=2g \
  --dry-run

nesk install ./my-paper-core \
  --dir ./test-paper \
  --set eula=true \
  --set server_name="Development Server" \
  --set memory=2g \
  --yes
```

Then exercise the lifecycle:

```bash
nesk validate --dir ./test-paper --instance
nesk start --dir ./test-paper
nesk status --dir ./test-paper
nesk logs --dir ./test-paper
nesk validate --dir ./test-paper --readiness
nesk stop --dir ./test-paper
```

Inspect the rendered files, ownership behavior, port, memory usage, graceful
shutdown, and startup logs. Test with disposable worlds before treating the
recipe as production-ready.

## 8. Test a real recipe update

A local recipe install stores an immutable untracked snapshot; `nesk update`
does not follow later edits in the original local directory. To test the remote
update path, publish the recipe to a review branch and install that branch:

```bash
nesk install example/my-paper-core@main \
  --dir ./tracked-paper \
  --set eula=true \
  --yes
```

Change the recipe, bump `package.version`, validate it, and push the branch.
Then review and apply from the tracked test instance:

```bash
nesk outdated --dir ./tracked-paper
nesk diff --dir ./tracked-paper
nesk update --dir ./tracked-paper --dry-run
nesk update --dir ./tracked-paper --yes
nesk status --dir ./tracked-paper
nesk logs --dir ./tracked-paper
```

Verify that edited `server.properties`, worlds, and plugins were preserved;
untouched managed files changed as planned; readiness passed; and a deliberate
failed readiness condition restores the previous package/runtime. Keep an
independent backup while testing rollback.

## 9. Optional Dockerfile build

Use `[build]` only when a provider artifact and templates cannot produce the
package directly:

```toml
[build]
file = ".luminesk/Dockerfile"
output = "/out"
timeout = 1200
cpu = 2
memory = "2g"
network = false
```

There is no `[permissions]` table. Declaring `[build]` enables the isolated
Docker build; `network = true` explicitly allows its default Docker network.
Review every Dockerfile and keep networking disabled unless the build truly
needs it.

Use the [`luminesk.toml` Reference](/docs/manifest-reference) when extending
the recipe with another provider, platform-specific artifacts, checks, or
mounts.
