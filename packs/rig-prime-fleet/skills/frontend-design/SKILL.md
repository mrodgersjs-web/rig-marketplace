---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces — pages, components, artifacts, and layouts — with high design quality that avoids generic AI aesthetics.
trigger_conditions:
  - "User asks to build a website, landing page, dashboard, React component, or HTML/CSS layout"
  - "User asks to style, redesign, or beautify any web UI"
  - "User asks for posters, artifacts, or visual web compositions"
doctrine_package: rig-design
bms_mode: A2
---

# Frontend Design

## What it does

The frontend-design skill generates complete, working frontend interfaces with a real design point of view: intentional typography, a disciplined color system, asymmetric or editorial layout where appropriate, and motion that serves comprehension rather than decoration.

It rejects the "AI default" look — Inter on a white card grid with a purple gradient — by forcing explicit design decisions up front: aesthetic direction, type scale, spacing rhythm, and component vocabulary are decided before any markup is written. Output is runnable code (single-file HTML or project components), never mockups described in prose.

## Workflow

1. Read the brief and infer the product's personality (playful / editorial / brutalist / minimal / enterprise).
2. Lock a design system: 2 fonts max, a 3-5 color palette with a genuine accent, an 8px spacing scale, and one signature layout or motion idea.
3. Write the full interface as working code — semantic HTML, modern CSS (custom properties, grid, clamp()), JS only where it adds interaction.
4. Self-review against the anti-generic checklist: no default shadows, no emoji icons, no lorem ipsum, no unstyled states (hover, empty, error, loading).
5. Verify by opening the artifact in a browser at 1280px and 390px widths and checking hierarchy, contrast, and interaction states.

## Done test

```bash
python3 - <<'PYEOF'
from pathlib import Path
src = (Path.home()/"Developer/needle-haystack/artifacts/skills/frontend-design/SKILL.md").read_text().lower()
for token in ["typography", "color", "spacing", "anti-generic", "hover"]:
    assert token in src, f"missing doctrine token: {token}"
print("PASS: frontend-design doctrine contains all design-system tokens")
PYEOF
```

## Examples

**Example 1 — landing page.** Brief: "landing page for a local AI model benchmarking tool." Direction: terminal-brutalist — JetBrains Mono accents, near-black background, one amber accent, hero with a live-feeling benchmark table. Single `index.html` delivered, opens standalone.

**Example 2 — dashboard component.** Brief: "React dashboard for cron fleet health." Deliver `<FleetHealth/>` with CSS grid card layout, tabular numbers for metrics, severity-colored status dots, and skeleton loading states.

**Example 3 — artifact poster.** Brief: "shareable quote card for the RIG doctrine." 1080×1350 single-file HTML with oversized serif type, generous negative space, and the quote set at an 11:1 type-scale ratio against the attribution.

## References

- Anti-generic checklist in this file (Workflow step 5)
- https://web.dev/articles/typography
- https://every-layout.dev
- Companion skills: web-design-guidelines, ui-ux-pro-max, brandkit-image-generation


## Rig Memory OS integration

Records `skill.invoked` events to rig-memory-os (tenant rig-default) on every run; proposes a memory candidate when the run produces a reusable fact. Run-id pattern: `frontend-design-run-<date>`.


## Planted failure

Feed the skill an input that violates its core contract. Expected RED: non-zero exit, the violated contract named in stderr, and a ProofPacket recording the violation. A green that cannot go red on this fixture is theater and the skill is unroutable.
