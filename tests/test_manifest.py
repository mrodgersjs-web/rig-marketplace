import json

import pytest
from conftest import BUNDLED, REPO, write_pack

from rigmarket.catalog import validate_catalog
from rigmarket.manifest import ManifestError, inventory, validate_pack


def edit(pack, fn):
    m = json.loads((pack / "pack.json").read_text())
    fn(m)
    (pack / "pack.json").write_text(json.dumps(m))


def errors(pack):
    with pytest.raises(ManifestError) as e:
        validate_pack(pack)
    return " | ".join(e.value.errors)


@pytest.mark.parametrize("name", BUNDLED)
def test_bundled_packs_validate(name):
    m = validate_pack(REPO / "packs" / name)
    assert m["contract"]["provides"] == inventory(REPO / "packs" / name).counts()


def test_bundled_catalog_has_no_errors():
    report = validate_catalog(REPO)
    assert sorted(report) == sorted(BUNDLED)
    assert all(errs == [] for errs in report.values()), report


def test_minimal_pack_validates(tmp_path):
    assert validate_pack(write_pack(tmp_path))["name"] == "demo-pack"


def test_rejects_missing_manifest(tmp_path):
    pack = write_pack(tmp_path)
    (pack / "pack.json").unlink()
    assert "missing pack.json" in errors(pack)


def test_rejects_invalid_json(tmp_path):
    pack = write_pack(tmp_path)
    (pack / "pack.json").write_text("{not json")
    assert "not valid JSON" in errors(pack)


@pytest.mark.parametrize(
    "mutate, needle",
    [
        (lambda m: m.pop("done_tests"), "'done_tests' is a required property"),
        (lambda m: m.update(version="1.0"), "version"),
        (lambda m: m.update(extra=1), "Additional properties"),
        (lambda m: m.update(schema="rig.pack.v0"), "schema"),
        (lambda m: m.update(done_tests=[]), "done_tests"),
        (lambda m: m["permissions"].pop("writes_pack"), "writes_pack"),
        (lambda m: m["permissions"].update(env=["lower"]), "env"),
        (lambda m: m["contract"]["provides"].update(agents=-1), "agents"),
    ],
)
def test_schema_rejections(tmp_path, mutate, needle):
    pack = write_pack(tmp_path)
    edit(pack, mutate)
    msg = errors(pack)
    assert msg.startswith("schema:") and needle in msg


def test_rejects_declared_count_that_does_not_match_files(tmp_path):
    pack = write_pack(tmp_path)
    edit(pack, lambda m: m["contract"]["provides"].update(agents=25))
    assert "declares 25 but the pack has 1" in errors(pack)


def test_rejects_name_not_matching_directory(tmp_path):
    pack = write_pack(tmp_path)
    edit(pack, lambda m: m.update(name="other-pack"))
    assert "does not match directory" in errors(pack)


def test_rejects_plugin_json_version_drift(tmp_path):
    pack = write_pack(tmp_path)
    (pack / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "demo-pack", "version": "2.0.0"}))
    assert "plugin.json version" in errors(pack)


def test_rejects_forbidden_command_even_if_not_declared(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "x", "run": ["bash", "-c", "true"]}])
    assert "command 'bash' is forbidden by the built-in policy" in errors(pack)


def test_rejects_unknown_placeholder(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "x", "run": ["{python}", "{home}/x.py"]}])
    assert "unknown placeholder {home}" in errors(pack)


def test_rejects_duplicate_test_ids(tmp_path):
    t = {"id": "x", "run": ["{python}", "-m", "rigmarket.checks", "agents", "{pack}/agents"]}
    pack = write_pack(tmp_path, tests=[t, t])
    assert "duplicate done-test id 'x'" in errors(pack)


def test_rejects_path_escaping_pack(tmp_path):
    pack = write_pack(tmp_path, tests=[{"id": "x", "run": ["{python}", "{pack}/../evil.py"]}])
    assert "escapes the pack" in errors(pack)


def test_catalog_rejects_include_drift(tmp_path):
    write_pack(tmp_path, name="small-pack")
    big = write_pack(tmp_path, name="big-pack", includes=["small-pack"])
    assert validate_catalog(tmp_path) == {"small-pack": [], "big-pack": []}
    (big / "agents" / "demo-agent.md").write_text((big / "agents" / "demo-agent.md").read_text() + "\nedit\n")
    assert validate_catalog(tmp_path)["big-pack"] == ["includes small-pack: agents/demo-agent.md differs"]


def test_catalog_rejects_unknown_include_and_unlisted_pack(tmp_path):
    write_pack(tmp_path, includes=["ghost-pack"])
    report = validate_catalog(tmp_path, ["demo-pack", "nope"])
    assert report["demo-pack"] == ["includes unknown pack 'ghost-pack'"]
    assert "not listed" in report["nope"][0]
