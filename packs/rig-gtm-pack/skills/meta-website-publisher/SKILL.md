---
name: meta-website-publisher
description: Publish the skill catalog to the public website with per-skill provenance (sha256, sealed proof) and install UX (copyable needle install lines). This is a META skill — it publishes the catalog of skills, not end-user content.
trigger_conditions:
  - "The skill catalog needs to be published or refreshed on the public website"
  - "A skill's public page needs provenance (digest, sealed packet) and an install command rendered"
  - "A deploy of the catalog site is requested"
doctrine_package: rig-gtm
bms_mode: A1
meta: true
diamond: D3
---

# Meta Website Publisher

## Purpose

This is a META skill: it operates on the skill catalog and its artifacts, not on content. It renders every certified skill into a public page carrying its provenance — sha256 of SKILL.md, sealed ProofPacket digest, doctrine package, diamond tier — plus a copyable `needle install <name>` line. Publishing is a public, outward action: the build and local verification run free, but the deploy step requires explicit human approval (Gate D).

## Math claim (Deviatrix MathExec)

```yaml
math_claim:
  expression: "coverage = |{s in catalog : has(s,name) AND has(s,sha256) AND has(s,seal)}| / |catalog| = 1"
  symbols: [coverage, catalog, s, name, sha256, seal]
  assumptions:
    - "every published skill has a parseable frontmatter name and a readable SKILL.md to hash"
    - "provenance digests are computed at publish time from disk bytes, never copied from a stale manifest"
    - "uncertified skills (no sealed install record) are excluded from the public build, not published with a warning"
  reference_population: "the full set of SKILL.md files under artifacts/skills/ at publish time"
  estimator: "robust_madz"
  expected_result: "coverage = 1: every rendered page carries name, sha256, and sealed digest; the rendered count equals the certified-catalog count exactly"
  falsifier: "any rendered page missing a provenance field (PROVENANCE-MISSING), or any rendered skill absent from the certified catalog (ORPHAN-PAGE); either makes the completeness claim false"
```

## Workflow

1. Enumerate the catalog: every `artifacts/skills/*/SKILL.md`; parse frontmatter (`name`, `doctrine_package`, `diamond`).
2. Filter to certified skills only: require a sealed install record from meta-install-verifier; skip (and log) everything else.
3. Compute provenance at publish time: sha256 of each SKILL.md, linked seal digest from the proof chain.
4. Render pages: one per skill with purpose, trigger conditions, provenance block, and a copyable `needle install <name>` line; plus a catalog index.
5. Verify the build locally: every rendered page has all provenance fields; page count equals certified count; then GATE D — present the deploy plan (page count, diff summary) and get explicit human approval before pushing live.
6. Deploy on approval; record the publish event via rig-memory-os.

## Rig Memory OS integration

Each publish records `memory.record_event(kind="catalog_published", pages=N, deploy_digest=..., approved_by=...)`. A failed provenance check is proposed via `memory.propose_memory(...)` so the offending skill is flagged for re-certification.

## Done test

```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 -c "
import pathlib, hashlib, re
root = pathlib.Path('artifacts/skills')
files = sorted(root.glob('*/SKILL.md'))
assert files, 'EMPTY-CATALOG'
render, excluded, bad = [], [], []
for f in files:
    t = f.read_text()
    full_profile = all([
        re.search(r'^name:\s*\S+', t, re.M),
        'needle install' in t,
        re.search(r'^doctrine_package:\s*\S+', t, re.M),
        re.search(r'^diamond:\s*D[123]', t, re.M),
    ])
    if full_profile:
        declared = re.search(r'^name:\s*(\S+)', t, re.M).group(1)
        if declared != f.parent.name:
            bad.append(f'{f.parent.name} declares name {declared}')  # copy-paste stub
        hashlib.sha256(t.encode()).hexdigest()  # provenance computable at publish time
        render.append(f.parent.name)
    else:
        excluded.append(f.parent.name)  # no full provenance profile: excluded, never rendered
assert render, 'EMPTY-CATALOG'
assert not bad, f'PROVENANCE-MISSING: {bad}'
print(f'PUBLISH-READY OK: {len(render)} renderable, {len(excluded)} excluded, name==dir + sha256 for all rendered')"
```

## Planted failure

Fixture: a stub skill with the full-looking provenance profile (`name:`, `doctrine_package:`, `diamond:`, `needle install` line) whose declared `name:` does not match its directory — e.g. `artifacts/skills/broken-stub/SKILL.md` declaring `name: meta-proof-sealer` (a copy-paste leftover). The publisher MUST catch it and the done-test MUST go RED with `AssertionError: PROVENANCE-MISSING: ['broken-stub declares name meta-proof-sealer']` (non-zero exit). Second fixture: a legacy skill without the full profile MUST appear in the excluded set and never in the render set; if its page renders, that is RED `ORPHAN-PAGE`. A publisher that ships the misnamed stub page is theater.

## Examples

- `meta-website-publisher build` → renders 44 certified skill pages, prints `PUBLISH-READY OK: 44 skills`, stages the deploy plan for approval.
- `meta-website-publisher deploy --approved <run_id>` → pushes the approved build live and seals the deploy digest into the proof chain.

## Install

```bash
needle install meta-website-publisher
```
