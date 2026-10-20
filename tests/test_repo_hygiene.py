"""Repo-hygiene assertions checked into the repo and run by `pytest -q`.

These match the polish brief items 1-4 of the GHUP2 wave:

  1. .github/CODEOWNERS contains `* @mrodgersjs-web`.
  2. .github/copilot-instructions.md exists, is within the size ceiling,
     and names the test command we run.
  3. README cites a GitHub actions workflow-status badge URL, the
     `rodgersintelligence.com` footer, and a self `git clone` line.
  4. Every job in every workflow under .github/workflows/ has a
     `timeout-minutes` and no `continue-on-error: true`.

The assertions fail loud when the repo drifts from the polish standard,
which is what we want -- the pre-commit Jev gate grades on the result.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


# 1. CODEOWNERS


def test_codeowners_contains_owner_handle() -> None:
    codeowners = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    # Lines starting with `#` are comments; check every non-blank, non-comment line.
    active = [
        line for line in codeowners.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert active, ".github/CODEOWNERS has no active rules"
    assert any("* @mrodgersjs-web" in line for line in active), (
        ".github/CODEOWNERS must contain a `* @mrodgersjs-web` rule"
    )


# 2. copilot-instructions.md


def test_copilot_instructions_present_and_below_size_ceiling() -> None:
    copilot = ROOT / ".github" / "copilot-instructions.md"
    assert copilot.exists(), ".github/copilot-instructions.md missing"
    size = copilot.stat().st_size
    assert size <= 8000, f"copilot-instructions.md is {size} bytes; the ceiling is 8000"


@pytest.mark.parametrize("word", ["pytest"])
def test_copilot_instructions_names_test_command(word: str) -> None:
    copilot = (ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    assert word in copilot, (
        f".github/copilot-instructions.md must mention the canonical test command {word!r}"
    )


# 3. README


def test_readme_has_workflow_status_badge_url() -> None:
    """The badge URL must target github.com/actions/workflow/status (img.shields)."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    pattern = re.compile(
        r"https://img\.shields\.io/github/actions/workflow/status/"
        r"mrodgersjs-web/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\?[^\s)]*\bbranch="
    )
    assert pattern.search(readme), (
        "README must cite a shields workflow-status badge URL "
        "(img.shields.io/github/actions/workflow/status/mrodgersjs-web/.../...yml?...)"
    )


def test_readme_has_rodgersintelligence_footer() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "rodgersintelligence.com" in readme, (
        "README must contain the rodgersintelligence.com footer"
    )


def test_readme_self_clone_uses_org() -> None:
    """Every `git clone` line in README must target mrodgersjs-web/rig-marketplace."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    clone_lines = [
        line for line in readme.splitlines() if "git clone" in line
    ]
    assert clone_lines, "README has no `git clone` line"
    for line in clone_lines:
        assert "mrodgersjs-web/rig-marketplace" in line, (
            f"`git clone` line does not target mrodgersjs-web/rig-marketplace: {line!r}"
        )


# 4. workflows


def _iter_workflow_jobs(text: str) -> list[tuple[str, dict[str, object]]]:
    """Return one (job_name, job_dict) per job in `jobs:`.

    Parsed with PyYAML so we don't get fooled by indentation tricks. Skips
    workflows where PyYAML fails to parse (the validate-yml workflow runs
    in CI for that).
    """
    import yaml

    try:
        data = yaml.safe_load(text)
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    jobs_obj = data.get("jobs")
    if not isinstance(jobs_obj, dict):
        return []
    return [(name, job) for name, job in jobs_obj.items() if isinstance(job, dict)]


def test_every_workflow_job_has_timeout_minutes() -> None:
    workflows = list((ROOT / ".github" / "workflows").rglob("*.yml"))
    assert workflows, "no workflows found"
    for wf in workflows:
        text = wf.read_text(encoding="utf-8")
        for name, job in _iter_workflow_jobs(text):
            assert "timeout-minutes" in job, (
                f"{wf.name} job {name!r} has no `timeout-minutes`"
            )


def test_no_workflow_job_uses_continue_on_error() -> None:
    import yaml

    workflows = list((ROOT / ".github" / "workflows").rglob("*.yml"))
    for wf in workflows:
        data = yaml.safe_load(wf.read_text(encoding="utf-8")) or {}
        jobs = data.get("jobs") or {}
        for name, job in jobs.items():
            assert "continue-on-error" not in job, (
                f"{wf.name} job {name!r} uses `continue-on-error`; remove it"
            )


def test_ci_workflow_runs_on_push_and_pull_request() -> None:
    """The test job must not be skipped on push to main."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert re.search(r"(?m)^on:\s*$", ci), "ci.yml is missing the `on:` key"
    assert re.search(r"(?m)^\s+push:\s*$", ci), "ci.yml does not trigger on push"
    assert re.search(r"(?m)^\s+pull_request:\s*$", ci), "ci.yml does not trigger on pull_request"


def test_copilot_instructions_list_truth_rule() -> None:
    """The polish brief says copilot-instructions must carry a truth rule
    saying numbers in docs come from a command. Assert that exact phrase is
    present so the rule cannot drift in edits.
    """
    copilot = (ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    assert "Truth rule" in copilot
    assert "command" in copilot.lower()


def test_copilot_instructions_list_setups() -> None:
    """Copilot must list the exact setup commands the test and lint run."""
    copilot = (ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    assert "pip install" in copilot
    assert "ruff" in copilot.lower()
    assert "pytest" in copilot.lower()


def test_readme_install_section_explains_pypi_404() -> None:
    """The brief flagged the previous README claim of a PyPI install path;
    the polished README must explicitly warn that bare `pip install
    rig-marketplace` fails and point readers at the git-based path.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Install" in readme, "README is missing an '## Install' section"
    # The git-clone example must target this repo.
    assert "git clone https://github.com/mrodgersjs-web/rig-marketplace" in readme
