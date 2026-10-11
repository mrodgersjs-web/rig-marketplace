# rig-engineering-pack

Prime engineering agents: architecture, code, performance and review, with code-session goal harnesses.

- Agents: 25
- Harnesses: 8
- Skills: 1

The manifest is `pack.json` (format `rig.pack.v1`). `rigmarket validate` rejects it if these counts drift from the files.

## Done-tests

| id | checks |
|---|---|
| `agents-contract` | Every agent has frontmatter (name matches file, non-empty description) and the Operating contract and RLM Harness sections. |
| `harnesses-wellformed` | Every harness parses, its id matches the file name, every gate has a requirement and a proof, and the failure protocol names only declared gates. |
| `skills-wellformed` | Every SKILL.md frontmatter name matches its directory and every run.py compiles. |

## Proof

```
rigmarket test rig-engineering-pack --out-dir evidence
RIG_SEAL_KEY=<32+ byte secret> rigmarket seal evidence/rig-engineering-pack.run.json
RIG_SEAL_KEY=<same secret> rigmarket verify --check-pack evidence/rig-engineering-pack.packet.json
```
