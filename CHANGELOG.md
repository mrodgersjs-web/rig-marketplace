# Changelog

All notable changes to this project are recorded here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-10-19

### Changed

- **Drop "RLM"** in favor of plain language. The agent contract heading
  is now `## Plugin contract (prime)` instead of `## RLM Harness (prime)`.
  Done-test descriptions, pack.json `contract.agent_sections` lists, and
  the schema mention "Plugin contract" consistently.
- **Parameterize machine paths.** Every reference of the form
  `~/Developer/...` or `$HOME/Developer/...` in a tracked file has been
  rewritten to `$(rig-builds)/...`. The catalog validator never expands
  that placeholder; it is a documentation variable the operator sets
  in their own fleet. See `docs/architecture.md` for the rule.
- **Runtime string.** The pack.json `contract.runtime` field reads
  `plugin runtime (context held in the runtime kernel, not the prompt)`
  where it previously read `prime-agent (RLM: ...)`. Validation does
  not enforce a specific runtime string.

### Fixed

- `pyproject.toml` declared `jsonschema` as an unstated import; the
  runtime dependency list now includes it. `pip install .` from a
  clean venv works on Python 3.10+ without manual dep installs.
- The package `__init__.py` now ships, so `from rigmarket import
  __version__, sandbox` (used by the CLI) resolves.
- `ruff check .` is now clean for the application source
  (`src/rigmarket/`, `tests/`) at line length 120; the vendored
  `packs/` tree, MCP server, and RIG lattice hooks are excluded
  (`extend-exclude`).

### Added

- `docs/architecture.md` — three-layer diagram, contract, run-and-prove
  sequence, `$(rig-builds)` semantics, extension map, performance budget.

## [1.0.0] - 2026-10-10

Initial release of the five-pack prime-agent catalog with a manifest
schema, an HMAC-sealed evidence packet, command-policy enforcement,
and a containment-gated runner. The version in `pack.json` per pack
stays `1.0.0` for the catalog; the catalog validator version is
`1.1.0`.
