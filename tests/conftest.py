import json
import secrets
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BUNDLED = ["rig-engineering-pack", "rig-content-pack", "rig-design-pack", "rig-gtm-pack", "rig-prime-fleet"]

AGENT = """---
name: {name}
description: "A test agent."
---

# Test agent

## Operating contract

- Doctrine package: test

## RLM Harness (prime)

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
            "runtime": "prime-agent",
            "provides": {"agents": 1, "harnesses": 0, "skills": 0},
            "agent_sections": ["## Operating contract", "## RLM Harness (prime)"],
        },
        "permissions": {"commands": ["{python}"], "env": [], "writes_pack": False, "network": False},
        "done_tests": tests or [
            {
                "id": "agents-contract",
                "run": ["{python}", "-m", "rigmarket.checks", "agents", "{pack}/agents", "--expect", "1",
                        "--section", "## Operating contract"],
                "expect_stdout_contains": ['"status": "PASS"'],
            }
        ],
    }
    manifest.update(overrides)
    (pack / "pack.json").write_text(json.dumps(manifest, indent=2))
    catalog = root / ".claude-plugin" / "marketplace.json"
    catalog.parent.mkdir(exist_ok=True)
    plugins = json.loads(catalog.read_text())["plugins"] if catalog.exists() else []
    plugins.append({"name": name, "source": f"./packs/{name}"})
    catalog.write_text(json.dumps({"name": "test", "plugins": plugins}))
    return pack


def py(code: str) -> list[str]:
    return ["{python}", "-c", code]


@pytest.fixture
def key(monkeypatch) -> bytes:
    k = secrets.token_hex(32)
    monkeypatch.setenv("RIG_SEAL_KEY", k)
    return k.encode()


@pytest.fixture
def python() -> str:
    return sys.executable
