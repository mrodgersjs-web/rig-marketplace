---
name: web-design-guidelines
description: Review UI code against Web Interface Guidelines — accessibility, interaction states, typography, spacing, and UX best practices — and return file:line findings.
trigger_conditions:
  - "User asks to review my UI, check accessibility, audit design, or review UX"
  - "User asks to check a site against best practices"
  - "Before shipping any new or modified interface"
doctrine_package: rig-design
bms_mode: A2
---

# Web Design Guidelines

## What it does

The web-design-guidelines skill is a review pass for interface code. It reads the actual markup and styles and produces concrete, file:line findings across five axes: accessibility (contrast, focus, ARIA, keyboard paths), interaction states (hover/focus/active/disabled/loading/empty/error), typography (scale, measure, line height), spacing rhythm, and responsive behavior.

It is a reviewer, not a generator — it pairs with frontend-design, which builds, while this skill verifies that what was built holds up to scrutiny. Findings are severity-tagged so the fix order is obvious.

## Workflow

1. Collect the UI surface: templates, components, stylesheets, and any client JS touching the DOM.
2. Run the accessibility axis: color contrast ratios, focus visibility, label association, keyboard operability, reduced-motion handling.
3. Run the interaction axis: every clickable element has hover/focus/active states; every async action has loading and error states; every list has an empty state.
4. Run the typography/spacing axes: line length 45-75ch, line-height 1.4-1.7 for body, consistent spacing scale (no magic pixel values).
5. Run the responsive axis: check 320px, 768px, 1280px, 1920px for overflow, reflow, and touch target size (>=44px).
6. Emit findings as `path:line — [severity] issue → fix`, ordered critical to cosmetic.

## Done test

```bash
python3 - <<'PYEOF'
from pathlib import Path
src = (Path.home()/"Developer/needle-haystack/artifacts/skills/web-design-guidelines/SKILL.md").read_text().lower()
axes = ["accessibility", "interaction", "typography", "spacing", "responsive"]
missing = [a for a in axes if a not in src]
assert not missing, f"missing review axes: {missing}"
print("PASS: all 5 review axes present")
PYEOF
```

## Examples

**Example 1 — contrast.** `button.tsx:44 — [critical] text #9CA3AF on #FFFFFF is 2.8:1 → darken to #4B5563 (7.0:1).`

**Example 2 — missing state.** `Feed.tsx:91 — [high] async list renders nothing while fetching → add skeleton; empty result renders blank page → add empty-state copy.`

**Example 3 — measure.** `article.css:12 — [medium] body copy at 92ch line length → cap with max-width: 68ch.`

## References

- https://www.w3.org/WAI/WCAG22/quickref/
- https://web.dev/articles/learn-css
- Companion skills: accessibility, frontend-design, wcag-audit-patterns


## Rig Memory OS integration

Records `skill.invoked` events to rig-memory-os (tenant rig-default) on every run; proposes a memory candidate when the run produces a reusable fact. Run-id pattern: `web-design-guidelines-run-<date>`.


## Planted failure

Feed the skill an input that violates its core contract. Expected RED: non-zero exit, the violated contract named in stderr, and a ProofPacket recording the violation. A green that cannot go red on this fixture is theater and the skill is unroutable.
