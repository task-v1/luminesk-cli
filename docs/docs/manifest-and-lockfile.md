---
sidebar_position: 7
---

# Recipes, Manifests, and Locks

A recipe is a directory with exactly one entry point named `luminesk.toml`.
That manifest expresses intent: what the package is, how sources resolve, which
files are generated or protected, and how the instance runs. Recipe-owned
template files, declared files, local artifacts, and an optional Dockerfile sit
beside it.

Luminesk treats the manifest as a strict public contract. Unknown keys are
errors. Paths are portable relative POSIX paths unless a field explicitly
describes a container path. Commands are TOML arrays of arguments; shell
command strings and host-command permissions do not exist in the schema.

```toml
manifest_version = 1
```

`manifest_version` is the version of the manifest file format. It is not the
Luminesk product version and must remain `1` until a new manifest schema is
introduced.

## From recipe to instance

```text
recipe directory
  luminesk.toml + declared assets
          │ nesk lock / install
          ▼
  luminesk.lock + verified content cache
          │ deterministic package build
          ▼
       .lumineskpkg
          │ transactional apply
          ▼
installed instance
  payload + manifest + lock + .luminesk_cli state
```

- `luminesk.toml` remains human-authored intent.
- `luminesk.lock` is generated canonical JSON with exact resolution results.
- `.lumineskpkg` is a deterministic, independently verified ZIP transaction
  boundary, normally built in a temporary directory by CLI workflows.
- An installed instance is mutable operational state. Its ownership ledger
  separates Luminesk-managed content from user data.

Do not hand-edit `luminesk.lock`, package metadata, or `.luminesk_cli/` state.
Change the recipe, regenerate resolution, inspect the plan, and apply it.

## Author workflow

```bash
nesk init --dir ./my-core --name my-core
nesk validate --dir ./my-core --static
nesk lock --dir ./my-core
nesk plan --dir ./my-core
```

Resolution and build levels can access providers, the content cache, and
Docker. A plan builds a temporary package but does not install it. Install a
local recipe into a separate empty directory before publishing it.

Continue with [Creating a Custom Recipe](/docs/creating-a-recipe) for a
practical core, and use the complete
[`luminesk.toml` Reference](/docs/manifest-reference) for every public field.
