# Security

## Reporting a vulnerability

Email **security@rodgersintelligence.com**. Do not open a public
GitHub issue for suspected vulnerabilities. We acknowledge reports
within two business days and ship a fix or a documented mitigation
on a published timeline for any in-scope advisory.

## Supported versions

This table lists the versions of `rigmarket` and the catalog itself
that currently receive security fixes.

| version | status |
|---|---|
| 1.1.x | supported |
| 1.0.x | supported until 2027-04-19 (six months after 1.1.0 release) |
| older | unsupported |

## Threat model: what `rigmarket test` does and does not contain

`rigmarket test` runs the pack's declared done-tests in a copy of the
pack inside a temporary directory. The runner checks whether the host
has an **enforced** OS-level sandbox and refuses to run without one
(exit code 3) unless `--allow-uncontained` is passed.

What enforced containment gives you:

- **Network denied** in the runner profile (no DNS, no outbound TCP/UDP).
- **Writes outside the run directory denied** at the OS layer.
- **Symlinks in the pack** are rejected at validation time.
- **Catalog sources** that resolve through a symlink are rejected.

What enforced containment does **not** cover:

- **Reads** are not restricted. A script can read any file your user
  account can read and print it into the run document's output tail.
- **Local IPC** is not restricted on the macOS profile.
- **Child processes** are allowed, but they inherit the same network
  and write denial.
- **CPU and memory** are not bounded — a pack can spin until the host
  dies. Run packs you do not trust in a throwaway VM or container.

The **key** in `RIG_SEAL_KEY` is the trust anchor for evidence
packets. Anyone holding the key can sign a hand-written run document;
`seal` only refuses documents that are internally inconsistent.
Treat the key as a CI secret or a per-developer file outside git.

## Out of scope for this repo

- The catalogue contents (agents, harnesses, skills) are content;
  advisories about a specific pack belong with its maintainer.
- MCP server `mcp/server.py` depends on external RIG tooling and is
  not exercised by CI; the threat model for MCP-aware tooling is
  separate.
- The RIG lattice hooks in `.rig/hooks/` are an internal
  infrastructure adapter. Their security model lives in the lattice
  project itself.

## Known limitations

- **No Linux enforced backend yet.** On Linux the runner refuses by
  default and only runs with `--allow-uncontained`; the `unshare
  --user --net` backend on Linux offers write-denial via process
  namespace plus a verifier-level canary check, but it does not
  block writes through the user's other privileges, so the probe
  correctly reports `enforced: false`. CI on Linux therefore
  exercises the uncontained branch by design and `verify` rejects
  those packets by default.
- **Python-only argv.** The current command policy only allows
  `{python}` and a narrow shape of `python -m ...` /
  `python <file-under-pack>`. Inline `-c` is rejected. A pack that
  needs a non-Python tool must vendor it inside the pack and run it
  via Python.
