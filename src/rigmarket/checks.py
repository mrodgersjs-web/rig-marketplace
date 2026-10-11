"""Content checks that packs call from their done-tests.

    python -m rigmarket.checks agents DIR [--expect N] [--section "## Heading" ...]
    python -m rigmarket.checks harnesses DIR [--expect N]
    python -m rigmarket.checks skills DIR [--expect N]

Each prints a JSON summary and exits 0 when every file passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

TIERS = ("halt", "degrade", "stop")


def _frontmatter(text: str) -> tuple[dict | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---", 4)
    if end == -1:
        return None, text
    try:
        meta = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return None, text
    return (meta if isinstance(meta, dict) else None), text[end + 4 :]


def check_agent(path: Path, sections: list[str]) -> list[str]:
    meta, body = _frontmatter(path.read_text("utf-8"))
    if meta is None:
        return ["missing or unparseable YAML frontmatter"]
    errs = []
    if meta.get("name") != path.stem:
        errs.append(f"frontmatter name {meta.get('name')!r} != file name {path.stem!r}")
    if not isinstance(meta.get("description"), str) or not meta["description"].strip():
        errs.append("empty description")
    lines = {ln.rstrip() for ln in body.splitlines()}
    for s in sections:
        if s not in lines:
            errs.append(f"missing section {s!r}")
    return errs


def _gates(doc: dict) -> list[dict]:
    """Harness gates come in two shapes: grouped by category, or a flat list."""
    out = []
    for g in (doc.get("identity_lock") or {}).get("gates") or []:
        out.append(g)
    for entry in doc.get("capability_gates") or []:
        if isinstance(entry, dict) and isinstance(entry.get("gates"), list):
            out.extend(entry["gates"])
        else:
            out.append(entry)
    return out


def check_harness(path: Path) -> list[str]:
    try:
        doc = yaml.safe_load(path.read_text("utf-8"))
    except yaml.YAMLError as e:
        return [f"invalid YAML: {e}"]
    if not isinstance(doc, dict):
        return ["not a YAML mapping"]
    errs = []
    hid = doc.get("harness_id")
    # File names may add a suffix to the id (hB-01-blog-post -> hB-01-blog-post-session.yaml).
    if not isinstance(hid, str) or not (path.stem == hid or path.stem.startswith(hid + "-")):
        errs.append(f"harness_id {hid!r} does not match file name {path.stem!r}")
    dod = doc.get("definition_of_done")
    if not isinstance(dod, list) or not dod or not all(isinstance(x, str) and x.strip() for x in dod):
        errs.append("definition_of_done must be a non-empty list of strings")
    gates = _gates(doc)
    if not doc.get("capability_gates"):
        errs.append("no capability_gates")
    ids: set[str] = set()
    for g in gates:
        if not isinstance(g, dict):
            errs.append(f"gate is not a mapping: {g!r}")
            continue
        gid = str(g.get("id", ""))
        if not gid:
            errs.append("gate without id")
        elif gid in ids:
            errs.append(f"duplicate gate id {gid}")
        ids.add(gid)
        for key in ("requirement", "proof"):
            if not isinstance(g.get(key), str) or not g[key].strip():
                errs.append(f"gate {gid}: missing {key}")
        tier = g.get("failure_tier")
        if tier is not None and tier not in TIERS:
            errs.append(f"gate {gid}: unknown failure_tier {tier!r}")
    protocol = doc.get("failure_protocol") or {}
    for tier in TIERS:
        for gid in protocol.get(f"{tier}_gates") or []:
            if str(gid) not in ids:
                errs.append(f"failure_protocol.{tier}_gates names undeclared gate {gid}")
    return errs


def check_skill(skill_dir: Path) -> list[str]:
    meta, _ = _frontmatter((skill_dir / "SKILL.md").read_text("utf-8"))
    if meta is None:
        return ["SKILL.md: missing or unparseable YAML frontmatter"]
    errs = []
    if meta.get("name") != skill_dir.name:
        errs.append(f"SKILL.md name {meta.get('name')!r} != directory {skill_dir.name!r}")
    if not isinstance(meta.get("description"), str) or not meta["description"].strip():
        errs.append("SKILL.md: empty description")
    run_py = skill_dir / "run.py"
    if run_py.exists():
        try:
            compile(run_py.read_text("utf-8"), str(run_py), "exec")
        except SyntaxError as e:
            errs.append(f"run.py does not compile: {e}")
    return errs


def run_check(kind: str, directory: Path, expect: int | None, sections: list[str]) -> dict:
    directory = Path(directory)
    if kind == "agents":
        items = sorted(directory.glob("*.md"))
        results = {p.name: check_agent(p, sections) for p in items}
    elif kind == "harnesses":
        items = sorted(directory.glob("*.yaml"))
        results = {p.name: check_harness(p) for p in items}
    elif kind == "skills":
        items = sorted(p.parent for p in directory.glob("*/SKILL.md"))
        results = {p.name: check_skill(p) for p in items}
    else:
        raise ValueError(f"unknown check {kind!r}")
    failures = {k: v for k, v in results.items() if v}
    count_ok = expect is None or expect == len(results)
    return {
        "check": kind,
        "checked": len(results),
        "expected": expect,
        "count_ok": count_ok,
        "failed": len(failures),
        "failures": failures,
        "status": "PASS" if not failures and count_ok and results else "FAIL",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m rigmarket.checks")
    ap.add_argument("kind", choices=["agents", "harnesses", "skills"])
    ap.add_argument("directory", type=Path)
    ap.add_argument("--expect", type=int, default=None, help="exact number of items required")
    ap.add_argument("--section", action="append", default=[], help="heading every agent must contain")
    args = ap.parse_args(argv)
    if not args.directory.is_dir():
        print(json.dumps({"check": args.kind, "status": "FAIL", "reason": f"not a directory: {args.directory}"}))
        return 1
    summary = run_check(args.kind, args.directory, args.expect, args.section)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
