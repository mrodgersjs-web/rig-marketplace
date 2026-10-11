"""The marketplace catalog (.claude-plugin/marketplace.json) and cross-pack checks."""

from __future__ import annotations

import json
from pathlib import Path

from .hashing import sha256_file
from .manifest import ManifestError, inventory, validate_pack

CATALOG = Path(".claude-plugin") / "marketplace.json"


def find_root(start: Path | None = None) -> Path:
    here = Path(start or Path.cwd()).resolve()
    for p in (here, *here.parents):
        if (p / CATALOG).is_file():
            return p
    raise FileNotFoundError(f"no {CATALOG} found in {here} or its parents")


def load_catalog(root: Path) -> dict:
    return json.loads((Path(root) / CATALOG).read_text("utf-8"))


def pack_dirs(root: Path) -> dict[str, Path]:
    """Map plugin name -> pack directory, in catalog order."""
    root = Path(root)
    out = {}
    for plugin in load_catalog(root).get("plugins", []):
        out[plugin["name"]] = (root / plugin["source"]).resolve()
    return out


def include_errors(manifest: dict, pack_dir: Path, packs: dict[str, Path]) -> list[str]:
    """A pack that 'includes' another must carry every one of its files byte-for-byte."""
    errs = []
    for other in manifest.get("includes", []):
        if other not in packs:
            errs.append(f"includes unknown pack {other!r}")
            continue
        src = packs[other]
        for sub in ("agents", "harnesses", "skills"):
            base = src / sub
            if not base.is_dir():
                continue
            for f in sorted(p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
                rel = f.relative_to(src)
                mine = pack_dir / rel
                if not mine.is_file():
                    errs.append(f"includes {other}: missing {rel.as_posix()}")
                elif sha256_file(mine) != sha256_file(f):
                    errs.append(f"includes {other}: {rel.as_posix()} differs")
    return errs


def validate_catalog(root: Path, names: list[str] | None = None) -> dict[str, list[str]]:
    """Validate each pack (all catalog packs by default). Returns pack name -> errors."""
    root = Path(root)
    packs = pack_dirs(root)
    report: dict[str, list[str]] = {}
    targets = names or list(packs)
    for name in targets:
        if name not in packs:
            report[name] = [f"{name!r} is not listed in {CATALOG.as_posix()}"]
            continue
        pack_dir = packs[name]
        if not pack_dir.is_dir():
            report[name] = [f"catalog source {pack_dir} does not exist"]
            continue
        try:
            manifest = validate_pack(pack_dir)
        except ManifestError as e:
            report[name] = e.errors
            continue
        report[name] = include_errors(manifest, pack_dir, packs)
    return report


def listing(root: Path) -> list[dict]:
    rows = []
    for name, pack_dir in pack_dirs(root).items():
        counts = inventory(pack_dir).counts()
        try:
            manifest = json.loads((pack_dir / "pack.json").read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            manifest = {}
        rows.append({
            "name": name,
            "version": manifest.get("version", "?"),
            **counts,
            "done_tests": len(manifest.get("done_tests", [])),
        })
    return rows
