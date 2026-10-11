# RIG Marketplace
<p align="center"><img src="assets/rig-marketplace-hero.png" alt="RIG Marketplace governed agent pack catalog" width="100%" /></p>

<p align="center"><img src="docs/rig-marketplace-demo.gif" alt="demo" width="720" /></p>

[![ci](https://github.com/mrodgersjs-web/rig-marketplace/actions/workflows/ci.yml/badge.svg)](https://github.com/mrodgersjs-web/rig-marketplace/actions/workflows/ci.yml)

Governed prime-agent plugin packs. Each pack ships a manifest (`pack.json`) that declares its contract,
its permissions and its done-tests. The `rigmarket` CLI validates the manifest, runs the done-tests in a
throwaway copy of the pack, and seals the results into an HMAC-signed evidence packet that a verifier
rejects if anything was edited.

## Packs

Counts below are the output of `rigmarket list`, which counts the files. A test fails if this table drifts.

<!-- rigmarket list -->
```
pack                   version  agents harnesses skills done-tests
rig-engineering-pack   1.0.0        25         8      1          3
rig-content-pack       1.0.0        25         8      0          2
rig-design-pack        1.0.0        25         0      2          2
rig-gtm-pack           1.0.0        28        10      2          7
rig-prime-fleet        1.0.0       122        32     23         25
```

`rig-prime-fleet` carries every agent, harness and skill of the four smaller packs byte for byte
(declared with `includes` and checked by `rigmarket validate`), plus the fleet's own meta-agents and meta-skills.

## Quick start

```
pip install .                      # Python 3.10+; depends on jsonschema and PyYAML
rigmarket list                     # packs and counts
rigmarket validate                 # schema + on-disk checks for every pack in the catalog
rigmarket test --out-dir evidence  # run every pack's done-tests, write <pack>.run.json
export RIG_SEAL_KEY=...            # 32+ bytes; keep it out of git
rigmarket seal evidence/rig-gtm-pack.run.json          # -> evidence/rig-gtm-pack.packet.json
rigmarket verify --check-pack evidence/*.packet.json
```

Exit codes: 0 ok, 1 a check failed or a packet was rejected, 2 usage error (for example no key).

## The pack format (`rig.pack.v1`)

Schema: [`src/rigmarket/pack.schema.json`](src/rigmarket/pack.schema.json) (JSON Schema 2020-12).

| field | meaning |
|---|---|
| `name`, `version` | must match the directory name and `.claude-plugin/plugin.json` |
| `contract.provides` | number of agents, harnesses and skills; rejected if it differs from the files |
| `contract.agent_sections` | headings every agent must contain (the bundled packs require `## Operating contract` and `## RLM Harness (prime)`) |
| `permissions.commands` | allowed `argv[0]` for done-tests |
| `permissions.env` | environment variables passed through; all others are dropped |
| `permissions.writes_pack` | if false, a done-test that changes any pack file fails |
| `permissions.network` | declared only; not enforced (see Roadmap) |
| `done_tests[]` | `id`, `run` (argv list), optional `expect_exit`, `expect_stdout_contains`, `timeout_s` |
| `includes` | other packs whose files this pack must carry unchanged |

Placeholders in `run`: `{python}` (the interpreter running rigmarket) and `{pack}` (the temp copy of the pack).
Any other `{name}` placeholder, a command outside `permissions.commands`, duplicate test ids, and `..`
in a path are rejected at validation time.

## What a done-test run records

`rigmarket test` validates the pack first and refuses to run an invalid one. It copies the pack to a temp
directory, sets `HOME` to a temp directory, passes only `PATH` and the declared variables, and runs each
test with its timeout. For each test it records the argv, exit code, expected exit code, SHA-256 of stdout
and of stderr, the last 2,000 characters of output, duration in milliseconds, and the reasons it failed.
The run document also carries the SHA-256 of `pack.json` and a hash of every file in the pack.

The bundled done-tests use `python -m rigmarket.checks` to check agent frontmatter and sections, harness
structure (ids, gates with a requirement and a proof, failure protocol naming only declared gates) and skill
frontmatter, and they execute each bundled `run.py` meta-skill, including cases where it must fail closed.

## Evidence packets (`rig.proofpacket.v1`)

`rigmarket seal` signs the run document with HMAC-SHA256 (Python `hmac`/`hashlib`) using the key in
`RIG_SEAL_KEY`. The packet stores a key fingerprint, never the key. `rigmarket seal` refuses documents whose
status disagrees with their results.

`rigmarket verify` rejects a packet that is:

- not a packet (`bad-schema`), unsigned (`unsigned`), or signed with another algorithm (`bad-alg`)
- sealed with a different key (`wrong-key`)
- edited in any field after sealing (`bad-signature`), even if the edit recomputes the inner digest
- a record of failing done-tests (`failed-tests`), unless `--allow-fail` is given
- with `--check-pack`: older than the current pack files (`pack-changed`, `manifest-changed`)

CI generates a fresh key per run, seals and verifies every bundled pack, checks that a tampered packet is
rejected, and uploads the packets as a build artifact.

## Install the agents

Claude Code:
```
claude plugin marketplace add mrodgersjs-web/rig-marketplace
claude plugin install rig-gtm-pack@rig-marketplace
```
OMP / Hermes / manual: copy `packs/<pack>/agents/*.md` into `~/.omp/agent/agents/` and `skills/*` into your skills path.

These install paths use the catalog in `.claude-plugin/marketplace.json`; CI validates that catalog but does
not run Claude Code itself.

## Development

```
pip install -e ".[dev]"
ruff check .
pytest -q
```

## Roadmap

- Per-agent done-tests and reward environments. Agents reference a prime-agent environment path that lives
  outside this repo; today the done-tests are per pack.
- Network isolation for done-tests. `permissions.network` is recorded but not enforced.
- Public-key signatures so a verifier does not need the sealing secret.
- `mcp/server.py` (stdio MCP server) depends on external RIG tooling and is not exercised by CI.
- Paid distribution. No payment or entitlement code is in this repo.
