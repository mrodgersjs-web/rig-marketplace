"""Counts in the docs must match what the code counts from the files."""

import json
import re

import pytest
from conftest import BUNDLED, REPO

from rigmarket.cli import main
from rigmarket.manifest import inventory


@pytest.mark.parametrize("name", BUNDLED)
def test_pack_md_counts_match_files(name):
    text = (REPO / "packs" / name / "PACK.md").read_text()
    stated = {k.lower(): int(v) for k, v in re.findall(r"^- (Agents|Harnesses|Skills): (\d+)$", text, re.M)}
    assert stated == inventory(REPO / "packs" / name).counts()


@pytest.mark.parametrize("name", BUNDLED)
def test_plugin_descriptions_match_files(name):
    pack = REPO / "packs" / name
    counts = inventory(pack).counts()
    descs = [json.loads((pack / ".claude-plugin" / "plugin.json").read_text())["description"]]
    catalog = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    descs += [p["description"] for p in catalog["plugins"] if p["name"] == name]
    for desc in descs:
        for n, kind in re.findall(r"(\d+) (agent|harness|skill)", desc):
            assert int(n) == counts[kind + ("es" if kind == "harness" else "s")], desc


def test_readme_table_is_cli_output(capsys):
    assert main(["--root", str(REPO), "list"]) == 0
    expected = capsys.readouterr().out.strip()
    readme = (REPO / "README.md").read_text()
    block = re.search(r"<!-- rigmarket list -->\n```\n(.*?)\n```", readme, re.S)
    assert block and block.group(1).strip() == expected
