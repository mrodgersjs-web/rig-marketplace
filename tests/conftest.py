import hashlib
import json
import os
import secrets
import sys
from pathlib import Path

import pytest

from rigmarket import sandbox
from rigmarket.runner import run_pack

REPO = Path(__file__).resolve().parents[1]
# True only where an OS backend really denies network and writes outside the run dir (probed).
ENFORCED = sandbox.describe()["enforced"]
# On such hosts the suite exercises the real default flow. Elsewhere the default refuses to run pack
# code, so tests of the runner's own logic opt in explicitly; the refusal itself is tested separately.
UNCONTAINED_FLAG = [] if ENFORCED else ["--allow-uncontained"]
if os.environ.get("RIGMARKET_REQUIRE_ENFORCED") == "1" and not ENFORCED:
    raise RuntimeError(f"RIGMARKET_REQUIRE_ENFORCED=1 but containment is not enforced: {sandbox.describe()}")


def run_any(pack, **kw):
    """run_pack with the default flow where containment is enforced, explicit opt-in elsewhere."""
    return run_pack(pack, allow_uncontained=not ENFORCED, **kw)


BUNDLED = ["rig-engineering-pack", "rig-content-pack", "rig-design-pack", "rig-gtm-pack", "rig-prime-fleet"]

AGENT = """---
name: {name}
description: "A test agent."
---

# Test agent

## Operating contract

- Doctrine package: test

## Plugin contract (prime)

Runtime: prime-agent
"""


def write_pack(root: Path, name: str = "demo-pack", tests: list | None = None, **overrides) -> Path:
    """Create a minimal valid pack plus a marketplace catalog under root."""
    pack = root / "packs" / name
    (pack / "agents").mkdir(parents=True)
    (pack / ".claude-plugin").mkdir()
    (pack / "agents" / "demo-agent.md").write_text(AGENT.format(name="demo-agent"))
    (pack / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": name, "version": "1.0.0"}))
    manifest = {
        "schema": "rig.pack.v1",
        "name": name,
        "version": "1.0.0",
        "description": "A pack used by the test suite.",
        "contract": {
            "runtime": "plugin-runtime",
            "provides": {"agents": 1, "harnesses": 0, "skills": 0},
            "agent_sections": ["## Operating contract", "## Plugin contract (prime)"],
        },
        "permissions": {"commands": ["{python}"], "env": [], "writes_pack": False},
        "done_tests": tests or [
            {
                "id": "agents-contract",
                "run": ["{python}", "-m", "rigmarket.checks", "agents", "{pack}/agents", "--expect", "1",
                        "--section", "## Operating contract"],
                "expect_stdout_contains": ['"status": "PASS"'],
            }
        ],
    }
    for test in manifest["done_tests"]:
        for arg in test["run"]:
            if arg in SCRIPTS:
                (pack / arg.removeprefix("{pack}/")).write_text(SCRIPTS[arg])
    manifest.update(overrides)
    (pack / "pack.json").write_text(json.dumps(manifest, indent=2))
    catalog = root / ".claude-plugin" / "marketplace.json"
    catalog.parent.mkdir(exist_ok=True)
    plugins = json.loads(catalog.read_text())["plugins"] if catalog.exists() else []
    plugins.append({"name": name, "source": f"./packs/{name}"})
    catalog.write_text(json.dumps({"name": "test", "plugins": plugins}))
    return pack


SCRIPTS: dict[str, str] = {}


def py(code: str) -> list[str]:
    """A done-test that runs `code` as a script file inside the pack (inline -c is not allowed)."""
    arg = "{pack}/_t_" + hashlib.sha256(code.encode()).hexdigest()[:12] + ".py"
    SCRIPTS[arg] = code + "\n"
    return ["{python}", arg]


@pytest.fixture
def key(monkeypatch) -> bytes:
    k = secrets.token_hex(32)
    monkeypatch.setenv("RIG_SEAL_KEY", k)
    return k.encode()


@pytest.fixture
def python() -> str:
    return sys.executable
