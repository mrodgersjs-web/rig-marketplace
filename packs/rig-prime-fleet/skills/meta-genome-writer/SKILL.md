---
name: meta-genome-writer
description: Write the Opportunity/Idea/Proof Genome for a surviving candidate so it can be scored, recombined, and promoted through the RIG pipeline.
trigger_conditions:
  - "a candidate survives deviation scoring and lacks a genome record"
  - "a mesh or repair run emits a survivor needing structured provenance"
  - "an existing genome fails the completeness gate and must be rewritten"
doctrine_package: rig-doctrine
bms_mode: A1
meta: true
diamond: D2
---

# Meta Genome Writer

## Purpose
This is a META skill: it operates on pipeline candidates, not on end-user content. It takes a surviving candidate (from deviation, mesh, or contradiction repair) and writes its Genome — the structured record of Opportunity (what gap it attacks), Idea (the mechanism), and Proof (the evidence and certified scores) — so downstream skills can score, recombine, and promote it without re-deriving provenance. A candidate without a complete genome is invisible to the promotion pipeline.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "G = (w1*f_opportunity + w2*f_idea + w3*f_proof) / (w1 + w2 + w3), pass iff G >= 1.0 with each f in [0,1] and w = (1,1,2)"
  symbols: [G, w1, w2, w3, f_opportunity, f_idea, f_proof]
  assumptions:
    - "proof is double-weighted: a genome without evidence is worse than one without framing"
    - "each section completeness f is scored deterministically from required-field coverage"
    - "G = 1.0 requires every required field present; partial genomes are drafts, not genomes"
  reference_population: "completeness scores of genomes previously admitted to the promotion pipeline"
  estimator: "robust_madz"
  expected_result: "symbolic check passes (no undefined symbols, no zero-denominator risk) and G == 1.0 for a fully-written genome"
  falsifier: "G < 1.0 (any required field missing) or the expression fails symbolic validity (undefined symbol, denominator can vanish)"
```

## Workflow
1. Load the survivor candidate and its run artifacts (certified_z, repair log, mesh lineage).
2. Write the Opportunity section: target gap, population baseline, and why the median fails it.
3. Write the Idea section: the mechanism, the deviation engines used, and the sigma rung reached.
4. Write the Proof section: certified_z, estimator breakdown (MAD/Qn/bootstrap/alt-corpus), adversarial results, and reproducible commands.
5. Compute section completeness f for each section and the weighted genome score G; block promotion unless G == 1.0.
6. Commit the genome to the candidate record with content hash and link it into the lineage graph.

## Rig Memory OS integration
Writes call `memory.record_event` with `type: genome_write`, the candidate id, G, section completeness vector, and content hash. Completed genomes are submitted via `memory.propose_memory` as recombination material for future mesh runs.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py symbolic --expression "(w1*f1 + w2*f2 + w3*f3)/(w1 + w2 + w3)" --symbols w1,w2,w3,f1,f2,f3
```
The second command proves the genome completeness formula is symbolically valid (expected: `status: PASS`, no undefined symbols). The planted-failure fixture — a genome missing its Proof section — must drive the same check RED.

## Planted failure
Feed the writer a survivor with an empty Proof section, or equivalently run the symbolic gate with an undeclared symbol:
`python3 artifacts/meta/mathexec_substrate.py symbolic --expression "(w1*f1 + w2*f2)/(w1 + w2 + w3)" --symbols w1,w2,f1,f2`
Expected RED output: `status: FAIL` with `reason: "undefined symbols: ['w3']"`, and the writer reports `GENOME_INCOMPLETE: proof section missing` with G < 1.0, blocking promotion.

## Examples
```
/meta-genome-writer candidate=survivor-0412-17
/meta-genome-writer candidate=cand-88 --sections opportunity,proof
```

## Install
```bash
needle install meta-genome-writer
```
