"""The built-in command policy and the reviewer's escape pack."""

import json
import sys

import pytest
from conftest import write_pack

from rigmarket.catalog import validate_catalog
from rigmarket.cli import main
from rigmarket.manifest import ManifestError, validate_pack
from rigmarket.policy import declared_command_errors, run_errors
from rigmarket.runner import run_pack


def reviewer_pack(tmp_path):
    """The pack from the PR #2 review: curl, rm and sh, plus inline python network code."""
    victim = tmp_path / "mp_victim"
    victim.mkdir()
    (victim / "data.txt").write_text("keep me")
    outside = tmp_path / "mp_outside.txt"
    tests = [
        {"id": "wipe", "run": ["rm", "-rf", str(victim)]},
        {"id": "write-outside", "run": ["sh", "-c", f"echo pwned > {outside}"]},
        {"id": "fetch", "run": ["curl", "-s", "http://example.com"]},
        {"id": "net", "run": ["{python}", "-c", "import urllib.request; urllib.request.urlopen('http://example.com')"]},
    ]
    pack = write_pack(tmp_path, tests=tests)
    m = json.loads((pack / "pack.json").read_text())
    m["permissions"]["commands"] = ["curl", "rm", "sh", "{python}"]
    (pack / "pack.json").write_text(json.dumps(m))
    return pack, victim, outside


def test_reviewer_pack_fails_validate_and_never_runs(tmp_path, capsys):
    pack, victim, outside = reviewer_pack(tmp_path)
    with pytest.raises(ManifestError) as e:
        validate_pack(pack)
    msg = "\n".join(e.value.errors)
    for cmd in ("curl", "rm", "sh"):
        assert f"permissions.commands: {cmd!r} is forbidden by the built-in policy" in msg
    assert "option '-c' is not allowed" in msg
    assert validate_catalog(tmp_path)["demo-pack"]  # catalog validation reports it too
    assert main(["--root", str(tmp_path), "validate"]) == 1
    assert main(["--root", str(tmp_path), "test"]) == 1
    assert "invalid manifest" in capsys.readouterr().out
    with pytest.raises(ManifestError):
        run_pack(pack)
    assert (victim / "data.txt").read_text() == "keep me"  # nothing ran
    assert not outside.exists()


@pytest.mark.parametrize("cmd", ["sh", "bash", "rm", "curl", "wget", "nc", "ssh", "/bin/rm", "/usr/bin/curl", "env"])
def test_forbidden_commands(cmd):
    assert "forbidden by the built-in policy" in declared_command_errors([cmd])[0]
    assert "forbidden by the built-in policy" in run_errors([cmd, "x"], [cmd])[0]


def test_unlisted_command_is_not_allowlisted():
    assert "not in the built-in allowlist" in declared_command_errors(["jq"])[0]
    assert "not in the built-in allowlist" in run_errors(["/usr/local/bin/jq"], ["/usr/local/bin/jq"])[0]


@pytest.mark.parametrize(
    "args, needle",
    [
        ([], "needs a module"),
        (["-c", "print(1)"], "option '-c' is not allowed"),
        (["-I", "{pack}/x.py"], "option '-I' is not allowed"),
        (["-m", "http.server"], "-m 'http.server' is not allowed"),
        (["-m"], "is not allowed"),
        (["/tmp/x.py"], "must be a .py file inside the pack"),
        (["{pack}/data.txt"], "must be a .py file inside the pack"),
        (["{pack}/../x.py"], "escapes the pack"),
    ],
)
def test_python_argument_shapes(args, needle):
    (problem,) = run_errors(["{python}", *args], ["{python}"])
    assert needle in problem


def test_allowed_python_shapes():
    assert run_errors(["{python}", "-m", "rigmarket.checks", "agents", "{pack}/agents"], ["{python}"]) == []
    assert run_errors(["{python}", "{pack}/skills/x/run.py", "--input", "{}"], ["{python}"]) == []


def test_reserved_env_cannot_be_passed_through(tmp_path):
    pack = write_pack(tmp_path)
    m = json.loads((pack / "pack.json").read_text())
    m["permissions"]["env"] = ["PATH", "LD_PRELOAD"]
    (pack / "pack.json").write_text(json.dumps(m))
    with pytest.raises(ManifestError) as e:
        validate_pack(pack)
    assert "PATH is set by the runner" in str(e.value) and "LD_PRELOAD" in str(e.value)


def test_network_field_is_gone_from_the_schema(tmp_path):
    pack = write_pack(tmp_path)
    m = json.loads((pack / "pack.json").read_text())
    m["permissions"]["network"] = False
    (pack / "pack.json").write_text(json.dumps(m))
    with pytest.raises(ManifestError, match="Additional properties"):
        validate_pack(pack)


def test_python_is_the_interpreter_running_rigmarket():
    assert run_errors(["{python}", "-m", "rigmarket.checks"], ["{python}"]) == []
    assert sys.executable
