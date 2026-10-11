"""Load and validate pack manifests (pack.json) against the JSON Schema and the files on disk."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

import jsonschema

MANIFEST_NAME = "pack.json"
PLACEHOLDERS = {"python", "pack"}
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def load_schema() -> dict:
    return json.loads(resources.files("rigmarket").joinpath("pack.schema.json").read_text("utf-8"))


@dataclass
class Inventory:
    agents: list[str] = field(default_factory=list)
    harnesses: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {"agents": len(self.agents), "harnesses": len(self.harnesses), "skills": len(self.skills)}


def inventory(pack_dir: Path) -> Inventory:
    """Count what is actually in the pack. This is the only source of counts."""
    pack_dir = Path(pack_dir)
    inv = Inventory()
    if (pack_dir / "agents").is_dir():
        inv.agents = sorted(p.name for p in (pack_dir / "agents").glob("*.md"))
    if (pack_dir / "harnesses").is_dir():
        inv.harnesses = sorted(p.name for p in (pack_dir / "harnesses").glob("*.yaml"))
    if (pack_dir / "skills").is_dir():
        inv.skills = sorted(p.parent.name for p in (pack_dir / "skills").glob("*/SKILL.md"))
    return inv


class ManifestError(Exception):
    def __init__(self, pack: str, errors: list[str]):
        self.pack = pack
        self.errors = errors
        super().__init__(f"{pack}: " + "; ".join(errors))


def load_manifest(pack_dir: Path) -> dict:
    path = Path(pack_dir) / MANIFEST_NAME
    if not path.is_file():
        raise ManifestError(Path(pack_dir).name, [f"missing {MANIFEST_NAME}"])
    try:
        data = json.loads(path.read_text("utf-8"))
    except json.JSONDecodeError as e:
        raise ManifestError(Path(pack_dir).name, [f"{MANIFEST_NAME} is not valid JSON: {e}"]) from e
    return data


def schema_errors(manifest: dict) -> list[str]:
    validator = jsonschema.Draft202012Validator(load_schema())
    errs = []
    for err in sorted(validator.iter_errors(manifest), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errs.append(f"schema: {loc}: {err.message}")
    return errs


def semantic_errors(manifest: dict, pack_dir: Path) -> list[str]:
    """Checks a JSON Schema cannot express: names, counts and done-test commands vs disk."""
    pack_dir = Path(pack_dir)
    errs: list[str] = []
    if manifest.get("name") != pack_dir.name:
        errs.append(f"name {manifest.get('name')!r} does not match directory {pack_dir.name!r}")

    plugin_path = pack_dir / ".claude-plugin" / "plugin.json"
    if not plugin_path.is_file():
        errs.append("missing .claude-plugin/plugin.json")
    else:
        plugin = json.loads(plugin_path.read_text("utf-8"))
        for key in ("name", "version"):
            if plugin.get(key) != manifest.get(key):
                errs.append(f"plugin.json {key} {plugin.get(key)!r} != pack.json {key} {manifest.get(key)!r}")

    declared = manifest.get("contract", {}).get("provides", {})
    actual = inventory(pack_dir).counts()
    for kind, n in actual.items():
        if declared.get(kind) != n:
            errs.append(f"contract.provides.{kind} declares {declared.get(kind)} but the pack has {n}")

    allowed = set(manifest.get("permissions", {}).get("commands", []))
    seen: set[str] = set()
    for test in manifest.get("done_tests", []):
        tid = test.get("id", "?")
        if tid in seen:
            errs.append(f"duplicate done-test id {tid!r}")
        seen.add(tid)
        run = test.get("run") or []
        if run and run[0] not in allowed:
            errs.append(f"done-test {tid!r}: command {run[0]!r} not in permissions.commands")
        for arg in run:
            for name in _PLACEHOLDER_RE.findall(arg):
                if name not in PLACEHOLDERS:
                    errs.append(f"done-test {tid!r}: unknown placeholder {{{name}}}")
            if ".." in Path(arg.replace("{pack}", "")).parts:
                errs.append(f"done-test {tid!r}: argument {arg!r} escapes the pack with '..'")
    return errs


def validate_pack(pack_dir: Path) -> dict:
    """Return the manifest if it is valid, else raise ManifestError with every problem found."""
    pack_dir = Path(pack_dir)
    manifest = load_manifest(pack_dir)
    errs = schema_errors(manifest)
    if not errs:
        errs = semantic_errors(manifest, pack_dir)
    if errs:
        raise ManifestError(pack_dir.name, errs)
    return manifest
