---
name: meta-install-verifier
description: Install a skill AND adversarially prove its done-test can go RED before certifying the install. This is a META skill — it operates on skills in the catalog, never on the content those skills produce.
trigger_conditions:
  - "A new or updated skill is about to be installed or certified in the catalog"
  - "A skill's done-test needs a plant-failure pass before it may be cited as a gate"
  - "An audit asks which installed skills have a verified red path"
doctrine_package: rig-adversarial-verification
bms_mode: A1
meta: true
diamond: D3
---

# Meta Install Verifier

## Purpose

This is a META skill: it operates on skills and their done-tests, not on content. A green that won't go red is theater — so installation is only half the job. This skill installs the skill, extracts its done-test, runs it green, then executes the skill's documented planted-failure fixture and certifies the install only if the same test goes RED on the broken input. No verified red path, no certification.

## Math claim (Deviatrix MathExec)

```yaml
math_claim:
  expression: "certified(S) <=> (T(S, good) = 0) AND (T(S, planted_bad) != 0);  separation z = 0.6745 * (g - median(B)) / MAD(B) >> 0"
  symbols: [S, T, good, planted_bad, g, B, z, MAD]
  assumptions:
    - "the done-test T is executable in the current environment, not a prose claim"
    - "the planted_bad fixture is derived from the skill's own Planted failure section, not invented at install time"
    - "exit codes are honored: green = 0, red != 0; stdout text alone is never the verdict"
  reference_population: "exit-code distribution B of the done-test over planted-bad fixture variants (broken inputs must cluster red, far from the green run g = 0)"
  estimator: "robust_madz"
  expected_result: "green run exits 0; every planted-bad variant exits non-zero with the documented RED message; install verdict CERTIFIED only when both hold"
  falsifier: "any planted-bad fixture that exits 0 (the test cannot go red — BLOCK with NO-RED-PATH), or any green fixture that exits non-zero (the test is broken — BLOCK with NO-GREEN-PATH)"
```

## Workflow

1. Install the skill into the catalog (`needle install <name>` or equivalent placement); record the installed path and sha256 of SKILL.md.
2. Parse the SKILL.md: require a Done test block and a Planted failure section; missing either → BLOCK `NO-RED-PATH-DOCUMENTED`.
3. Run the done-test on the good fixture; require exit 0, else BLOCK `NO-GREEN-PATH`.
4. Construct the planted-bad fixture exactly as documented (e.g. undefined symbol, mutated digest, 35σ auto-pass) and run the same test; require non-zero exit and the documented RED message, else BLOCK `NO-RED-PATH`.
5. Certify: write the install record `{name, path, sha256, green_exit, red_exit, red_message}` and seal it via meta-proof-sealer.
6. Record the certification event via rig-memory-os.

## Rig Memory OS integration

Every certification decision is recorded via `memory.record_event(kind="install_certified"|"install_blocked", name=..., red_exit=...)`. Skills that repeatedly fail the red-path check are proposed via `memory.propose_memory(...)` as untrusted gates.

## Done test

```bash
cd ~/Developer/needle-haystack && python3 artifacts/meta/mathexec_substrate.py self-test && python3 -c "
import pathlib, subprocess, sys
sk = pathlib.Path('artifacts/skills/meta-install-verifier/SKILL.md').read_text()
assert '## Planted failure' in sk and '## Done test' in sk, 'NO-RED-PATH-DOCUMENTED'
good = subprocess.run(['python3','artifacts/meta/mathexec_substrate.py','self-test'],capture_output=True)
assert good.returncode == 0, 'NO-GREEN-PATH'
bad = subprocess.run(['python3','-c','''
import sys; sys.path.insert(0, \"artifacts/meta\")
from mathexec_substrate import symbolic_check
r = symbolic_check(\"x**2 + y\", [\"x\"])
assert r[\"status\"] != \"PASS\", \"PLANTED FAILURE NOT CAUGHT\"
'''],capture_output=True)
assert bad.returncode == 0, 'NO-RED-PATH: undefined-symbol fixture was not caught'
print('INSTALL VERIFIER OK: green path green, planted undefined-symbol fixture caught')"
```

## Planted failure

Fixture: a candidate skill whose done-test passes on a deliberately broken input — concretely, `symbolic_check("x**2 + y", ["x"])` where `y` is undefined. The verifier MUST observe the check go RED (`status != "PASS"`); if it reports PASS for the undefined-symbol expression, the expected RED output is `AssertionError: PLANTED FAILURE NOT CAUGHT` and the install verdict is BLOCK `NO-RED-PATH`. A verifier that certifies a skill with no demonstrable red path is itself the failure being planted against.

## Examples

- `meta-install-verifier certify meta-proof-sealer` → runs its done-test green, mutates a packet digest, watches the chain verify exit non-zero, prints `CERTIFIED meta-proof-sealer (red path verified)`.
- `meta-install-verifier certify some-skill` where the done-test greps for the word "PASS" in its own output → planted fixture also prints PASS → `BLOCK some-skill: NO-RED-PATH`.

## Install

```bash
needle install meta-install-verifier
```
