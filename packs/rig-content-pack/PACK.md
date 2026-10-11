# rig-content-pack

Prime content agents: long-form, short-form and editorial ops, with content-session goal harnesses.

- Agents: 25
- Harnesses: 8
- Skills: 0

The manifest is `pack.json` (format `rig.pack.v1`). `rigmarket validate` rejects it if these counts drift from the files.

## Done-tests

| id | checks |
|---|---|
| `agents-contract` | Every agent has frontmatter (name matches file, non-empty description) and the Operating contract and RLM Harness sections. |
| `harnesses-wellformed` | Every harness parses, its id matches the file name, every gate has a requirement and a proof, and the failure protocol names only declared gates. |

## Proof

```
rigmarket test rig-content-pack --out-dir evidence
RIG_SEAL_KEY=<32+ byte secret> rigmarket seal evidence/rig-content-pack.run.json
RIG_SEAL_KEY=<same secret> rigmarket verify --check-pack evidence/rig-content-pack.packet.json
```
