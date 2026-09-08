---
sidebar_position: 3
---

# Source Providers

Each `[[sources]]` entry resolves one artifact, stores its bytes in the
content-addressed cache, and records the result in `luminesk.lock`. The manifest
schema exposes exactly ten source types:

```text
http                 github-release       gitlab-release
maven                github-source        gitlab-job-artifact
jenkins              mojang-version       paper
local-file
```

Provider metadata chooses an artifact; the fetcher then enforces `max_size`,
computes the actual SHA-256, and records the actual byte size. If the provider
supplies an expected size or SHA-256, those must match too.

## Common fields and resolution rules

```toml
[[sources]]
id = "core"
type = "http"
target = "server.jar"
max_size = 536870912
extract = false
platforms = []
allow_http = false
allow_private_network = false

[sources.options]
url = "https://downloads.example.org/server.jar"
version = "1.0.0"
```

- `id` is a unique lowercase identifier and can be passed as `COMPONENT` to
  `nesk update`.
- `target` is relative to package output. `.` is valid only for an extracted
  source.
- `max_size` defaults to 512 MiB and bounds decoded download bytes.
- `extract = true` invokes bounded safe archive extraction. It rejects unsafe
  paths, links, device/special entries, excessive file counts/expanded size,
  and suspicious compression ratios.
- `platforms` limits resolution to target strings such as `linux/amd64`.
- `allow_http = true` permits plain HTTP for a configurable provider URL.
- `allow_private_network = true` permits loopback, private, and other blocked
  address ranges. Both switches expand trust and should be exceptional.

Remote metadata is bounded to 2 MiB. Metadata and artifact requests allow at
most five redirects, revalidate every destination, and do not forward
credentials to a different host. URLs reject embedded credentials and
fragments. HTTPS and public destinations are the defaults.

## Version selectors

Providers do not share one universal version grammar:

- GitHub Release and Maven understand exact versions, `latest`/`*`, and simple
  comma-separated SemVer comparisons such as `>=1.20.0,<2.0.0`.
- Their comparison grammar supports `>`, `>=`, `<`, `<=`, `=`, and `==` with
  three-component versions. It does not support caret, tilde, or compound OR.
- `channel = "stable"` excludes SemVer prereleases. The schema accepts other
  non-empty channel strings; any other value stops that stable-only filter.
- GitLab Release accepts `latest`/`*` or an exact tag, not SemVer ranges.
- Jenkins, Paper, Mojang, and GitHub Source use provider-specific selectors
  documented below.

Mutable selectors are resolved when the lock is created. The lock stores the
selected identity and exact fetched bytes, so later frozen work uses the cache
instead of asking the provider again.

## `http`

| Option | Type | Required | Default | Behavior |
| --- | --- | --- | --- | --- |
| `url` | URL | yes | — | Artifact URL; HTTPS unless common `allow_http` is true. |
| `version` | string | no | `pinned` | User-declared identity copied to lock `version` and `sourceRevision`; it does not alter the URL. |

```toml
[[sources]]
id = "core"
type = "http"
target = "server.jar"
max_size = 268435456

[sources.options]
url = "https://downloads.example.org/server-1.0.0.jar"
version = "1.0.0"
```

HTTP performs no metadata version discovery. Prefer immutable/versioned URLs.
The first successful lock hashes whatever the URL returns; later frozen work
uses those cached bytes. A new connected lock may accept changed bytes and
produce a different digest, so review lock diffs.

## `github-release`

| Option | Type | Required | Default | Behavior |
| --- | --- | --- | --- | --- |
| `repository` | string | yes | — | GitHub `OWNER/REPO`. |
| `asset` | string | yes | — | Shell-style name pattern; exactly one release asset must match. |
| `version` | string | no | `latest` | Exact tag, `latest`/`*`, or supported SemVer constraint. |
| `channel` | string | no | `stable` | Stable filters draft/prerelease results as described above. |

```toml
[[sources]]
id = "core"
type = "github-release"
target = "server.jar"

[sources.options]
repository = "ExampleOrg/example-server"
version = ">=1.4.0,<2.0.0"
asset = "example-server-*.jar"
channel = "stable"
```

Exact tags use GitHub's tag endpoint. Stable `latest` uses GitHub's latest
release endpoint. Constraint resolution inspects at most the first 100 release
records, ignores drafts, applies the prerelease filter, and selects the highest
matching SemVer. Ambiguous asset globs are rejected rather than guessed.

If GitHub supplies an asset digest and size, both are verified. Set
`GITHUB_TOKEN` to authenticate API metadata requests; credentials are stripped
if a redirect changes host.

## `github-source`

| Option | Type | Required | Default | Behavior |
| --- | --- | --- | --- | --- |
| `repository` | string | yes | — | GitHub `OWNER/REPO`. |
| `ref` | string | no | `main` | Branch, tag, or commit understood by GitHub's commits API. |
| `path` | path | no | repository root | Select one file or directory from the resolved archive. |

```toml
[[sources]]
id = "distribution"
type = "github-source"
target = "server"
extract = true

[sources.options]
repository = "ExampleOrg/example-server"
ref = "v1.4.2"
path = "dist/server"
```

This type requires `extract = true`. Luminesk resolves `ref` to an exact
40-character commit SHA and downloads that commit's tarball. GitHub's single
archive root is removed, then optional `path` is copied to `target`. A selected
file or directory must exist and cannot be a link. The fetched archive itself
is cached and locked by SHA-256. `GITHUB_TOKEN` is supported.

Do not confuse this artifact provider with `nesk install OWNER/REPO`: direct
recipe acquisition fetches a recipe manifest and its declared assets, whereas
`github-source` is declared inside a recipe to populate package content.

## `gitlab-release`

| Option | Type | Required | Default | Behavior |
| --- | --- | --- | --- | --- |
| `project` | string | yes | — | GitLab project id or namespace/path accepted by the API. |
| `asset` | string | yes | — | Shell-style release link name pattern; exactly one match required. |
| `version` | string | no | `latest` | `latest`, `*`, or exact release tag. |
| `base_url` | URL | no | `https://gitlab.com` | GitLab instance root. |

```toml
[[sources]]
id = "core"
type = "gitlab-release"
target = "server.jar"

[sources.options]
project = "example-group/example-server"
version = "v1.4.2"
asset = "example-server.jar"
```

The selected release link may be absolute or relative to `base_url`. Lock
`sourceRevision` is the release commit id when GitLab supplies one, otherwise
the tag. This provider does not evaluate SemVer comparison expressions. Set
`GITLAB_TOKEN` for a `PRIVATE-TOKEN` metadata header when needed.

## `gitlab-job-artifact`

| Option | Type | Required | Default | Behavior |
| --- | --- | --- | --- | --- |
| `project` | string | yes | — | GitLab project id or namespace/path. |
| `job` | string | yes | — | Exact successful job name. |
| `artifact` | path | yes | — | Exact path inside the selected job artifact; not a glob. |
| `ref` | string | no | `main` | Exact job ref. |
| `base_url` | URL | no | `https://gitlab.com` | GitLab instance root. |

```toml
[[sources]]
id = "core"
type = "gitlab-job-artifact"
target = "server.jar"

[sources.options]
project = "example-group/example-server"
ref = "main"
job = "release"
artifact = "build/server.jar"
```

Luminesk requests up to 100 successful jobs and chooses the highest job id whose
name and ref both match. The artifact URL is then pinned to that numeric job id;
lock revision is its commit id when available, otherwise `job-ID`.
`GITLAB_TOKEN` is supported.

## `maven`

| Option | Type | Required | Default | Behavior |
| --- | --- | --- | --- | --- |
| `repository` | URL | yes | — | Maven repository root. |
| `group` | string | yes | — | Maven group id, converted from dots to path segments. |
| `artifact` | string | yes | — | Artifact id. |
| `version` | string | yes | — | Exact SemVer, `latest`/`*`, supported comparison constraint, or exact `-SNAPSHOT`. |
| `extension` | string | no | `jar` | Artifact extension. |
| `classifier` | string | no | none | Optional classifier suffix. |
| `channel` | string | no | `stable` | Stable excludes SemVer prereleases. |

```toml
[[sources]]
id = "core"
type = "maven"
target = "server.jar"

[sources.options]
repository = "https://repo.example.org/releases"
group = "org.example"
artifact = "example-server"
version = ">=1.4.0,<2.0.0"
extension = "jar"
channel = "stable"
```

Luminesk parses `maven-metadata.xml`, selects the highest supported version, and
constructs the standard artifact URL. An exact `-SNAPSHOT` selector resolves
the matching extension/classifier to its timestamped version metadata. If a
valid `.sha256` sidecar exists it is enforced; absent, empty, malformed, or
unavailable sidecars are ignored and the fetched artifact's SHA-256 is still
recorded. XML external entities are rejected.

The selector engine expects semantic three-component versions except for an
exact `-SNAPSHOT`. Repository-specific non-SemVer schemes may not resolve.

## `jenkins`

| Option | Type | Required | Default | Behavior |
| --- | --- | --- | --- | --- |
| `base_url` | URL | yes | — | Jenkins root URL. |
| `job` | string | yes | — | Job path appended below `/job/`. |
| `artifact` | path/pattern string | yes | — | Shell-style match against filename or relative artifact path; exactly one required. |
| `build` | integer or string | no | `lastSuccessfulBuild` | Jenkins build selector. |

```toml
[[sources]]
id = "core"
type = "jenkins"
target = "server.jar"

[sources.options]
base_url = "https://ci.example.org"
job = "example-server/main"
build = 142
artifact = "build/libs/example-server.jar"
```

Metadata supplies the numeric build, artifacts, optional size, and preferably
`lastBuiltRevision.SHA1`. If no source SHA exists, `build-N` is used as the lock
revision. A symbolic selector remains in the artifact URL; use an integer build
to avoid a moving Jenkins alias between metadata and download. Even with a
symbolic selector, the downloaded bytes are hashed and frozen work requires
that exact cached digest.

There is no Jenkins credential environment integration in this provider. Use a
public endpoint or a separately controlled accessible URL; credentials embedded
in the URL are invalid.

## `mojang-version`

| Option | Type | Required | Default | Behavior |
| --- | --- | --- | --- | --- |
| `version` | string | no | `latest` | `latest`, `latest-release`, `latest-snapshot`, or an exact Mojang version id. |

```toml
[[sources]]
id = "core"
type = "mojang-version"
target = "server.jar"

[sources.options]
version = "latest-release"
```

This provider follows Mojang's official Java version manifest, selects exactly
one version, and requires that version to expose a dedicated server download.
It enforces Mojang's declared size and records the fetched server JAR's SHA-256.
It is for the Java server artifact, not Bedrock Dedicated Server.

## `paper`

| Option | Type | Required | Default | Behavior |
| --- | --- | --- | --- | --- |
| `minecraft` | string | yes | — | Exact Minecraft version, `latest`/`*`, or an `x` series such as `1.21.x`. |
| `build` | integer or string | no | `latest` | `latest` stable Paper build or an exact integer build id. |

```toml
[[sources]]
id = "core"
type = "paper"
target = "server.jar"

[sources.options]
minecraft = "1.21.8"
build = "latest"
```

For `latest`, `*`, or an `x` series, Luminesk chooses the highest numeric
Minecraft version reported by Paper's Fill v3 API. `build = "latest"` then
chooses the highest build marked `STABLE`. An integer selects that exact build
regardless of channel. The `server:default` download must include size and
SHA-256; both are verified.

An explicit Minecraft version avoids silently crossing game versions. The
example matches the repository reference fixture and is not a promise that it
is the best production version when you read this page.

## `local-file`

| Option | Type | Required | Default | Behavior |
| --- | --- | --- | --- | --- |
| `path` | path | yes | — | Regular file inside the recipe root. |
| `version` | string | no | `local` | User-declared lock identity. |

```toml
[[sources]]
id = "core"
type = "local-file"
target = "server.jar"

[sources.options]
path = "artifacts/server.jar"
version = "dev-build-42"
```

No network resolver is used. The file must remain inside the recipe root, be a
regular file, and fit `max_size`. Its SHA-256 becomes both the cached artifact
digest and immutable source revision. Recipe acquisition includes declared
local files in its bounded snapshot.

## Lock and offline behavior

`nesk lock` and connected installs resolve metadata and ensure every selected
artifact is present in the content cache. The lock captures:

- provider type, selected `version`, and immutable-ish `sourceRevision`;
- final URL (or `local:PATH`), target, actual size, and actual SHA-256;
- media type when the provider reports one;
- the target platform that controlled `platforms` filtering.

`--frozen` requires an unchanged manifest, matching target, matching recipe
origin when applicable, and every locked digest in the verified cache. It does
not fall back to the network for missing bytes. Check the cache with:

```bash
nesk cache verify
nesk lock --dir ./recipe --frozen
nesk plan --dir ./recipe --frozen
```

Use `nesk cache prune --dry-run` before deleting old blobs needed by offline
deployments.
