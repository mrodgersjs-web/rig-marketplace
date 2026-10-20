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
rigmarket test --out-dir evidence  # run every pack's done-tests (needs an enforced sandbox, see Containment)
export RIG_SEAL_KEY=...            # 32+ bytes; keep it out of git
rigmarket seal evidence/rig-gtm-pack.run.json          # -> evidence/rig-gtm-pack.packet.json
rigmarket verify --check-pack evidence/*.packet.json
```

Exit codes: 0 ok, 1 a check failed or a packet was rejected, 2 usage error (for example no key),
3 refused: no enforced OS sandbox on this host, so no pack code was run.

## The pack format (`rig.pack.v1`)

Schema: [`src/rigmarket/pack.schema.json`](src/rigmarket/pack.schema.json) (JSON Schema 2020-12).

| field | meaning |
|---|---|
| `name`, `version` | must match the directory name and `.claude-plugin/plugin.json` |
| `contract.provides` | number of agents, harnesses and skills; rejected if it differs from the files |
| `contract.agent_sections` | headings every agent must contain (the bundled packs require `## Operating contract` and `## Plugin contract (prime)`) |
| `permissions.commands` | executables done-tests may start, capped by the built-in policy (below) |
| `permissions.env` | environment variables passed through; all others are dropped. `PATH`, `HOME`, `TMPDIR` and loader variables cannot be listed |
| `permissions.writes_pack` | if false, a done-test that changes any pack file fails |
| `done_tests[]` | `id`, `run` (argv list), optional `expect_exit`, `expect_stdout_contains`, `timeout_s` |
| `includes` | other packs whose files this pack must carry unchanged |

Placeholders in `run`: `{python}` (the interpreter running rigmarket) and `{pack}` (the temp copy of the pack).
Any other `{name}` placeholder, duplicate test ids, and `..` in a path are rejected at validation time.

There is no network permission. Network access is not something a pack can ask for; see
[Containment](#containment) for when it is denied.

### Command policy

`src/rigmarket/policy.py` caps what a pack may declare. `rigmarket validate` (and therefore `rigmarket test`)
rejects a pack that breaks it, and the runner checks it again right before starting each process.

- The only executable allowed today is `{python}`. Anything else is rejected as "not in the built-in allowlist".
- Shells, inline-code interpreters, file removers and movers, privilege tools and network clients (`sh`, `bash`,
  `env`, `perl`, `node`, `rm`, `mv`, `dd`, `find`, `sudo`, `curl`, `wget`, `nc`, `ssh`, `git`, `pip` and others)
  are rejected by name as "forbidden by the built-in policy", including as absolute paths such as `/bin/rm`.
- `{python}` may run only `-m rigmarket.checks ...` or a `.py` file inside the pack (`{pack}/...`).
  Inline code (`-c`) and other interpreter options are rejected.

## What a done-test run records

`rigmarket test` validates the pack first and refuses to run an invalid one. It then runs each test with
its timeout inside a private run directory (see Containment). For each test it records the argv, exit code, expected exit code, SHA-256 of stdout
and of stderr, the last 2,000 characters of output, duration in milliseconds, and the reasons it failed.
The run document also carries the SHA-256 of `pack.json` and a hash of every file in the pack.

The bundled done-tests use `python -m rigmarket.checks` to check agent frontmatter and sections, harness
structure (ids, gates with a requirement and a proof, failure protocol naming only declared gates) and skill
frontmatter, and they execute each bundled `run.py` meta-skill, including cases where it must fail closed.

## Containment

A pack script is still Python: it can try anything the user running `rigmarket test` can do. The command
policy only checks `argv[0]`; a `{python}` script can still open files by absolute path, start `/bin/sh`
through `subprocess` or use the network. Only an OS sandbox can stop that, so **`rigmarket test` refuses to run
pack code unless an OS sandbox is enforced** and exits 3 with `REFUSED`. Every run prints the backend first:

```
isolation: backend=sandbox-exec enforced=true network=denied writes_outside_run_dir=denied (...)
```

| host | backend | network | writes outside the run directory | `enforced` | default `rigmarket test` |
|---|---|---|---|---|---|
| macOS, not inside another sandbox | `sandbox-exec` profile | denied | denied | true | runs |
| Linux with unprivileged user namespaces | `unshare --user --net` | denied | **not contained** | false | refuses |
| anything else, or nested inside another sandbox (where `sandbox-exec` cannot start) | none | **not enforced** | **not contained** | false | refuses |

`enforced` comes from a probe, not from a binary existing: the runner starts `sandbox-exec` with the run
profile and checks that a write outside a scratch run directory is actually refused by the OS.

What `enforced: true` does not cover: reads are not restricted (a script can read files your user can read
and print them into the run document's output tail), child processes may start (their writes and network
are denied too), and local IPC is not restricted. Run packs you do not trust in a throwaway VM or container
as well.

`rigmarket test --allow-uncontained` runs anyway on a host without an enforced sandbox. Use it only for packs
you already trust (this repo's CI uses it on Linux runners for the bundled packs). Those runs record
`isolation.enforced: false`, and `rigmarket verify` rejects their packets (`uncontained`) unless the verifier
also passes `--allow-uncontained`. `RIGMARKET_ISOLATION=none` forces the backend to none (so the default
refuses).

Hygiene and tamper checks, on every host. These are **not** a sandbox and are not reported as one:

- The run directory holds the pack copy (the working directory), `HOME`, `TMPDIR`, a `bin/` directory and a
  canary directory. `PATH` is only that `bin/`, which links `python`/`python3` to the running interpreter, so
  `rm`, `sh` or `curl` are not found by name (a script can still call `/bin/sh` by path).
- Before and after each test the runner snapshots the canary directory, the source pack and the catalog root
  (excluding `.git`, virtualenvs and caches). Any change fails the test with "changed files outside the run
  directory". Writes anywhere else are not seen by this check; `isolation.snapshot_scope` says so.

Symlinks: a pack may not contain symlinks (`validate` reports "symlinks are not allowed in a pack: <path>"),
and a catalog `source` must be a real directory inside the marketplace root. Hashing never follows a link.

## Evidence packets (`rig.proofpacket.v1`)

`rigmarket seal` signs the run document with HMAC-SHA256 (Python `hmac`/`hashlib`) using the key in
`RIG_SEAL_KEY`. The packet stores a key fingerprint, never the key. `rigmarket seal` refuses documents whose
status disagrees with their results.

`rigmarket verify` rejects a packet that is:

- not a packet (`bad-schema`), unsigned (`unsigned`), or signed with another algorithm (`bad-alg`)
- sealed with a different key (`wrong-key`)
- edited in any field after sealing (`bad-signature`), even if the edit recomputes the inner digest
- a record of a run without enforced OS containment (`uncontained`), unless `--allow-uncontained` is given;
  packets from older versions without `isolation.enforced` count as uncontained
- a record of failing done-tests (`failed-tests`), unless `--allow-fail` is given
- with `--check-pack`: older than the current pack files (`pack-changed`, `manifest-changed`)

What a packet proves, and what it does not: the signature shows that someone holding `RIG_SEAL_KEY` sealed
this exact run document and that nobody edited it since. It does not prove the tests ran. A key holder can
write a run document by hand and seal it; `seal` only refuses documents that are internally inconsistent.
Treat the key as the trust anchor and keep it to the machine or CI job that runs the tests.

CI generates a fresh key per run. On Linux runners (no enforced sandbox) it checks that the default
`rigmarket test` refuses, runs the bundled packs with `--allow-uncontained`, checks that `verify` rejects
those packets by default, then seals, verifies with `--allow-uncontained`, checks that a tampered packet is
rejected, and uploads the packets. A macOS job runs the default flow under `sandbox-exec`, runs the full test
suite with `RIGMARKET_REQUIRE_ENFORCED=1` (no containment test may skip), and checks that an in-pack escape
script fails without writing outside.

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
- An enforced backend for Linux (for example bubblewrap or Landlock) so Linux hosts can run untrusted packs
  without `--allow-uncontained`; today only macOS `sandbox-exec` counts as enforced.
- Read restriction and IPC restriction inside the macOS profile.
- Run attestation: binding a packet to the runner that produced it, so a key holder cannot seal a hand-written run.
- Public-key signatures so a verifier does not need the sealing secret.
- `mcp/server.py` (stdio MCP server) depends on external RIG tooling and is not exercised by CI.
- Paid distribution. No payment or entitlement code is in this repo.
