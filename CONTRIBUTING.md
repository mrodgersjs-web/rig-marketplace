# Contributing

Thanks for taking the time to make this catalog better. This document
covers the **catalog itself** — agents, harnesses, skills, and their
documentation. The host CLI (`rigmarket`) follows its own review bar.

## What we accept

- A **new pack** that the validator can ingest (schema, content,
  structure) and whose done-tests pass on a clean venv.
- A **bug fix** to the runner, the schema, or a bundled done-test,
  with a test that fails before the change and passes after.
- A **docs improvement** that resolves a real ambiguity without
  altering the validator's behavior.
- An **agent, harness, or skill** addition or correction in an
  existing pack, with the matching `pack.json` count incremented.

## What we reject

- "1000x", "novel-to-the-world", or any other superlative without a
  measured delta.
- A PR whose diff renames the project, the runtime, or the lexicon
  the brief already standardized on without first raising an
  architectural card.
- A signed-run evidence packet whose `RIG_SEAL_KEY` ever appeared in
  a PR description, commit message, or CI log.
- Any change that weakens containment, removes the OS-sandbox probe,
  or relaxes the argv policy without an accompanying threat-model
  update in `SECURITY.md`.

## Local setup

```
git clone https://github.com/mrodgersjs-web/rig-marketplace.git
cd rig-marketplace
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
ruff check .
pytest -q
```

The above is the **CI bar**. Anything that does not run clean on a
fresh clone with the above five commands will be sent back.

## Process

1. **Open an issue first** for any non-trivial change. Pack additions,
   schema changes, and CLI behavior changes are easy to discuss as
   text before code lands.
2. **Small logical commits.** Use Conventional Commit prefixes
   (`feat`, `fix`, `docs`, `test`, `ci`, `chore`). One commit per
   concern; squash before merge is the project's choice, not yours.
3. **Tests.** Every public function added or changed gets a test.
   Coverage below 80% on the package is not accepted.
4. **Lint clean.** `ruff check .` on the application source must pass.
5. **No secrets in the diff.** This includes keys, tokens, hostnames,
   and machine paths. Use `$(rig-builds)/...` for fleet-side
   references.
6. **No claim without evidence.** The README's pack table is
   generated; a PR that touches it must also touch the source that
   generated it. The `tests/test_docs.py` suite is what prevents
   drift.

## Review

The maintainer reviews every PR against the production standard in
`AGENTS.md`. Reviewer focus:

- Does this change ship a working capability, or is it a scaffold?
- Are machine paths and internal jargon out of the public surface?
- Does the test fixture actually exercise the code path, or does it
  only mirror the previous test's name?
- For any runnable code added under `packs/<pack>/skills/`, does
  the matching `done_tests[]` entry reject at least one failure
  mode?

## License

Your contribution is MIT-licensed under the same terms as the rest of
this project (`LICENSE`).
