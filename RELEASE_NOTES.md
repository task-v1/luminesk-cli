# Luminesk CLI 2.0.0

Luminesk 2.0 replaces the imperative 1.x server manager with a reproducible,
Docker-first recipe composer for Java and Bedrock servers.

## Highlights

- Declarative `luminesk.toml` recipes and immutable `luminesk.lock` resolution.
- Deterministic, verified `.lumineskpkg` packages.
- Transactional installs and ownership-aware updates with rollback.
- Commit-pinned GitHub recipes without requiring a local Git executable.
- Bounded downloads and extraction, artifact hashes, and OCI image digests.
- Stable JSON output and exit codes for automation.
- Decision-ready catalog tables and unified install Preview payloads.
- Official PaperMC Java and Lumi Bedrock recipes with configurable non-root users.
- Linux, macOS, and Windows bundles for AMD64 and ARM64.

## Breaking changes

The 2.0 recipe, lockfile, package, registry, and instance-state contracts are
not compatible with 1.x. There is no in-place conversion. Back up and stop the
old instance, install a fresh 2.0 recipe into an empty directory, and copy only
the user-owned data supported by that recipe. Follow the complete
[migration guide](docs/docs/migrating-to-2.0.md).

Python installations require Python 3.13 or newer. Docker Engine or Docker
Desktop is required for runtime operations and declared recipe builds.

## Verification

Release assets include build-provenance attestations, a CycloneDX runtime SBOM,
and `SHA256SUMS`. The wheel, source distribution, six platform bundles, security
corpus, dependency audits, documentation build, and a real Docker lifecycle are
all release gates. The release workflow also exercises the published catalog
through PaperMC install/start/validate/stop, rejects assets that do not match the
installer matrix, and permits tags only from the repository's default branch.
