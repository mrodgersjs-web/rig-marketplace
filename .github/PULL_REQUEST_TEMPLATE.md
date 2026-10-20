## What

One paragraph: what this PR ships and why.

## How

The mechanical change in one sentence per file touched. Tests added in
the same commit where the behavior changed.

## Verification

```
$ python3 -m venv .venv && source .venv/bin/activate
$ pip install -e '.[dev]'
$ ruff check .
$ pytest -q
```

Paste the actual output below. If the failure you are fixing is the
reason this PR exists, paste the failing output before the fix and
the passing output after the fix.

```
<paste here>
```

## Checklist

- [ ] Tests added in the same commit as the behavior they cover
- [ ] `ruff check .` clean on application source
- [ ] `pytest -q --cov` shows coverage stays at or above 80%
- [ ] No `~/Developer/...` or `$HOME/Developer/...` paths added to
      tracked files; use `$(rig-builds)/...` instead
- [ ] No "1000x", "novel", or other superlative claims added
- [ ] No prices, no client names, no personal data
- [ ] No `RIG_SEAL_KEY` in this diff, the PR description, or the
      commit message
- [ ] Documentation updated where the public surface changed

## Linked issue

Closes #<number>.
