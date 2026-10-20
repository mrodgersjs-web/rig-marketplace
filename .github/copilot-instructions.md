# rig-marketplace — copilot instructions

## What it is
Governed catalog of prime-agent plugin packs. `rigmarket` CLI
validates each pack's `pack.json`, runs done-tests in a throwaway
copy, and seals results into HMAC-signed evidence packets that a
verifier rejects if anything was edited.

## Layout
- `src/rigmarket/` — package (`pack.py`, `runner.py`, `policy.py`,
  `seal.py`, `verify.py`, `cli.py`, `sandbox.py`, `__main__.py`).
- `packs/` — five packs (content/design/engineering/gtm/prime-fleet).
- `src/rigmarket/pack.schema.json` — `rig.pack.v1` JSON Schema.
- `tests/` — pytest suite.
- `docs/architecture.md` — three-layer design notes.
- `.github/workflows/ci.yml` — CI: matrix pytest on Linux, macOS
  enforced-sandbox job.

## Setup and tests
```
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
ruff check .
pytest -q
```

## Conventions
Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `ci:`,
`build:`, `chore:`). Every public-code change ships a test. No
secrets; `RIG_SEAL_KEY` is per CI run, never in the repo. No machine
paths (`/Users/...`, `~/Developer/...`, `$HOME/Developer/...`) —
docs use `$(rig-builds)`. No prices, no client names, no
credential/military/personnel claims. Banned words: unlock, empower,
synergy, leverage, disrupt, hustle, utilize, iterate, optimize. No
em dashes.

## Truth rule
Every README number must come from a command just ran. `## Packs`
counts come from `rigmarket list`. Coverage numbers come from
`pytest --cov=rigmarket --cov-report=term-missing`. Drifted counts
fail CI.

## Do not touch
`packs/`, `mcp/`, `.rig/`, `evidence/`, `build/`, `.rig/hooks/pre-tool`.

## Done-test
`pytest -q` and `ruff check .` must be clean on a fresh venv.
