"""rigmarket: catalog validator for the rig-marketplace agent packs.

A "pack" is a self-contained directory that ships:

    pack.json         the manifest (declared counts, permissions, runnable tests)
    PACK.md           human-readable summary
    agents/*.md       one Markdown file per agent, with YAML frontmatter
    harnesses/*.yaml  one YAML file per harness, with a top-level harness_id
    skills/<name>/SKILL.md
                      one SKILL.md per skill, with YAML frontmatter
    skills/<name>/run.py
                      optional executable core for runnable skills

Validation rules enforced by the CLI:

* Every agent has frontmatter with `name:` matching the file stem and a
  non-empty `description:`.
* Every harness parses as YAML and declares `harness_id` matching the file stem.
* Every SKILL.md declares `name:` matching its parent directory.
* Every declared count in `pack.json.contract.provides` matches the number
  of files on disk.
"""

__version__ = "1.1.0"
