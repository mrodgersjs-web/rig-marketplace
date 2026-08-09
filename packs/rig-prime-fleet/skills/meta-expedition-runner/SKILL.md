---
name: meta-expedition-runner
description: Run the Deviatrix 3-expedition loop — positive tail, negative tail, repaired tail — on a topic and certify the deviation of the best candidate with MathExec.
trigger_conditions:
  - "run an expedition on <topic>"
  - "3-expedition loop"
  - "deviate this idea to ±30σ and prove it"
  - "generate and certify off-median candidates"
doctrine_package: rig-deviate
bms_mode: A1
meta: true
diamond: D1
---

# Meta Expedition Runner

## Purpose
This is a META skill: it orchestrates deviation engines over candidate artifacts, not content directly. It executes the Deviatrix 3-expedition protocol — Expedition 1 searches the positive tail (+σ), Expedition 2 searches the negative tail (−σ), Expedition 3 repairs the best candidate's weakest dimension — and certifies the winner against a reference population. An expedition that cannot beat the median says so honestly.

## Math claim (Deviatrix MathExec)
```yaml
math_claim:
  expression: "z_certified = min(z_MAD, z_Qn, z_bootstrap_lower, z_alternate_corpus)"
  symbols: [z_certified, z_MAD, z_Qn, z_bootstrap_lower, z_alternate_corpus]
  assumptions:
    - "candidate scores are heavy-tailed; the conservative minimum across estimators is the honest claim"
    - "30σ is a wall, not a floor — the loop searches toward ±30σ but never auto-passes at the wall"
    - "reference population is the same-topic baseline corpus, not a generic one"
  reference_population: "score distribution of prior same-topic baseline candidates (un-deviated LLM-median outputs)"
  estimator: robust_madz
  expected_result: "the repaired-tail winner certifies z_certified >= 3 (real deviation) or the run reports NO-PASS with all three expedition score tables"
  falsifier: "if the unmodified baseline seed, run through the loop with engines disabled, certifies above 3σ, the scoring pipeline is gamed and the claim is false"
```

## Workflow
1. Seed: generate or accept the baseline candidate for the topic and score it; this anchors the reference population.
2. Expedition 1 (positive tail): run the selected deviation engines toward +σ rungs; score every candidate; keep the top-k.
3. Expedition 2 (negative tail): deliberately invert — search −σ rungs (the contrarian/minimalist direction); score; keep top-k. The loop MUST explore both tails; single-tail runs are invalid.
4. Expedition 3 (repaired tail): take the overall winner, identify its weakest scored dimension, apply a targeted repair engine, re-score.
5. Certify: run the MathExec adversarial pass (`adversarial --score <winner> --baseline <reference scores>`); z_certified is the conservative minimum across estimators.
6. Report: winner + z_certified + full expedition tables, or an honest NO-PASS if no candidate beats the baseline.

## Rig Memory OS integration
Records each expedition via `memory.record_event("expedition_run", {topic, winner_sigma, z_certified, pass})` and proposes winning engine-combination patterns via `memory.propose_memory("engine_combo", ...)` so future expeditions on similar topics start from proven rung ladders.

## Done test
```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 artifacts/meta/mathexec_substrate.py adversarial --score 42 --baseline "38,39,40,40,41"
```
The self-test validates all three MathExec passes; the adversarial call certifies a genuine winner (42 vs a tight 38–41 baseline) and must return a certified z well above 3. The planted-failure case below MUST go RED.

## Planted failure
Fixture: run the loop with the winner's "score" copied from the baseline median — e.g. `adversarial --score 40 --baseline "38,39,40,40,41"` simulating an expedition whose engines were no-ops (candidate indistinguishable from the LLM median). Expected RED output: z_certified collapses to ~0 across every estimator and the run reports NO-PASS — "no certified deviation; expedition failed to escape the median." If a median clone reports PASS, the certification layer is RED.

## Examples
```
needle run meta-expedition-runner --topic "category-creation thesis for RIG" --engines GRAVITON,BREAKER,COLLIDER
needle run meta-expedition-runner --seed artifact.md --tail both --certify
```

## Install
```bash
needle install meta-expedition-runner
```
