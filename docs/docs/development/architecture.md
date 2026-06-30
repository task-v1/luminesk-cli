# Codebase Architecture

This page outlines the directory structures, packages, and code design conventions of **Luminesk**.

---

## Directory Layout

The codebase is structured under the `Luminesk/` directory:

```text
Luminesk/
├── __init__.py           # Package initialization
├── __main__.py           # PyInstaller execution hook
├── main.py               # Package entry point
│
├── cli/
│   ├── __init__.py
│   └── main.py           # Command parsing and UI rendering via Cyclopts & Rich
│
├── core/
│   ├── __init__.py
│   ├── config.py         # SQLite storage and configuration persistence
│   ├── diagnostic.py     # Remote resource connectivity checks
│   ├── launcher.py       # Container process launch supervision
│   ├── locales/          # Translation catalogs (en, ru, uk, ja, zh)
│   ├── manager.py        # Central operations workflow orchestrations
│   ├── messages.py       # i18n localization translation helpers
│   └── registry.py       # Online core registry parser and cache TTL manager
│
├── models/
│   ├── __init__.py
│   ├── launcher.py       # Dataclasses representing execution structures
│   ├── manager.py        # Dataclasses representing server status views
│   └── registry.py       # Dataclasses representing Maven/Jenkins/GitHub models
│
└── utils/
    ├── __init__.py
    ├── docker.py         # Docker command compiler and daemon queries
    ├── downloads.py      # Core download routers
    ├── errors.py         # Exception formatter helpers
    ├── github_releases.py# GitHub Releases crawler
    ├── http.py           # Re-usable HTTP client with retry logic
    ├── jenkins.py        # Jenkins CI job parser
    ├── maven.py          # Maven metadata XML resolver
    └── rich_utils.py     # Rich terminal styling definitions
```

---

## Key Modules Explanation

### CLI Routing (`cli/main.py`)
Parses arguments using `cyclopts.App`. Renders styling (like SUCCESS, INFO, or ERROR panels) using `rich.console` and formats tabular grids via `rich.table.Table`.

### State Manager (`core/config.py`)
Declares database schema tables (`settings`, `servers`), manages connection context pools, coordinates transactional read/write procedures (`BEGIN IMMEDIATE`), and updates server runtime variables.

### Operations Pipeline (`core/manager.py`)
Combines state mappings and runtime commands. Implements logic to prepare directories, wipe old Jars, and query providers.

### Provider Parsers (`utils/maven.py`, `utils/jenkins.py`, `utils/github_releases.py`)
Low-level networking classes that fetch version strings and package paths from their respective remote build channels.
