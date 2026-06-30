# `diagnostic` command

Verifies the availability and health of remote core registries and download repositories.

---

## Syntax

```bash
nesk diagnostic
```

### Aliases:
- `check`
- `diag`

---

## Purpose

To prevent failures during server creation or engine updates, `diagnostic` tests the connectivity to all package sources defined in the registry. It sends HTTP requests to the release endpoints of Maven hosts, Jenkins CI jobs, and GitHub API servers to ensure they are online and responding.

---

## Output Format

The command displays a table of components and their reachability status:

```text
┌─────────────────────────────────────────────────────────────┐
│ Component           │ Status │ Description                  │
├─────────────────────┼────────┼──────────────────────────────┤
│ Nukkit Source       │ OK     │ 200 OK                       │
│ PowerNukkitX Source │ OK     │ 200 OK                       │
│ Nukkit-MOT Source   │ OK     │ 200 OK                       │
│ Lumi Source         │ OK     │ 200 OK                       │
└─────────────────────┴────────┴──────────────────────────────┘
```

- **Success**: If all sources respond successfully, the command prints:
  `Repository diagnostics finished. All sources responded successfully.` and exits with code `0`.
- **Failure**: If one or more servers are down, slow, or returning error codes, it highlights the failing components in red:
  `Repository diagnostics found failing sources.` and exits with code `1`.
