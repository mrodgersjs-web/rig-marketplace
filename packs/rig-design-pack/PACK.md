# rig-design-pack

Prime design agents: design systems, UX research and visual direction, with two design skills.

- Agents: 25
- Harnesses: 0
- Skills: 2

The manifest is `pack.json` (format `rig.pack.v1`). `rigmarket validate` rejects it if these counts drift from the files.

## Done-tests

| id | checks |
|---|---|
| `agents-contract` | Every agent has frontmatter (name matches file, non-empty description) and the Operating contract and RLM Harness sections. |
| `skills-wellformed` | Every SKILL.md frontmatter name matches its directory and every run.py compiles. |

## Proof

```
rigmarket test rig-design-pack --out-dir evidence
RIG_SEAL_KEY=<32+ byte secret> rigmarket seal evidence/rig-design-pack.run.json
RIG_SEAL_KEY=<same secret> rigmarket verify --check-pack evidence/rig-design-pack.packet.json
```
