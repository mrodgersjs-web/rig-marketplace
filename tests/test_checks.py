import json

from conftest import AGENT

from rigmarket.checks import main, run_check

HARNESS = """harness_id: hX-01-demo
harness_name: Demo
identity_lock:
  gates:
    - id: "0.1"
      requirement: "say the phrase"
      proof: "log line"
capability_gates:
  - category: "Core"
    gates:
      - id: "1.1"
        requirement: "do the thing"
        proof: "file exists"
        failure_tier: halt
definition_of_done:
  - "all gates pass"
failure_protocol:
  halt_gates: ["1.1"]
"""


def test_agent_checks(tmp_path):
    (tmp_path / "good.md").write_text(AGENT.format(name="good"))
    (tmp_path / "misnamed.md").write_text(AGENT.format(name="other"))
    (tmp_path / "bare.md").write_text("# no frontmatter\n")
    (tmp_path / "nosection.md").write_text(AGENT.format(name="nosection").replace("## Plugin contract (prime)", ""))
    r = run_check("agents", tmp_path, None, ["## Operating contract", "## Plugin contract (prime)"])
    assert r["status"] == "FAIL" and r["checked"] == 4 and r["failed"] == 3
    assert "good.md" not in r["failures"]
    assert "frontmatter name 'other'" in r["failures"]["misnamed.md"][0]
    assert "frontmatter" in r["failures"]["bare.md"][0]
    assert r["failures"]["nosection.md"] == ["missing section '## Plugin contract (prime)'"]


def test_harness_checks(tmp_path):
    (tmp_path / "hX-01-demo-session.yaml").write_text(HARNESS)
    assert run_check("harnesses", tmp_path, 1, [])["status"] == "PASS"
    (tmp_path / "hX-02-other.yaml").write_text(HARNESS)  # id does not match file name
    (tmp_path / "hX-03.yaml").write_text(HARNESS.replace("hX-01-demo", "hX-03").replace('proof: "file exists"', ""))
    (tmp_path / "hX-04.yaml").write_text(HARNESS.replace("hX-01-demo", "hX-04").replace('["1.1"]', '["9.9"]'))
    (tmp_path / "hX-05.yaml").write_text("harness_id: [unclosed\n")
    f = run_check("harnesses", tmp_path, None, [])["failures"]
    assert "does not match file name" in f["hX-02-other.yaml"][0]
    assert f["hX-03.yaml"] == ["gate 1.1: missing proof"]
    assert f["hX-04.yaml"] == ["failure_protocol.halt_gates names undeclared gate 9.9"]
    assert "invalid YAML" in f["hX-05.yaml"][0]


def test_skill_checks(tmp_path):
    good = tmp_path / "good-skill"
    good.mkdir()
    (good / "SKILL.md").write_text("---\nname: good-skill\ndescription: ok\n---\n")
    (good / "run.py").write_text("print('ok')\n")
    broken = tmp_path / "broken-skill"
    broken.mkdir()
    (broken / "SKILL.md").write_text("---\nname: wrong\ndescription: ok\n---\n")
    (broken / "run.py").write_text("def x(:\n")
    f = run_check("skills", tmp_path, None, [])["failures"]
    assert list(f) == ["broken-skill"]
    assert "!= directory" in f["broken-skill"][0] and "does not compile" in f["broken-skill"][1]


def test_count_mismatch_fails_even_when_files_pass(tmp_path, capsys):
    (tmp_path / "a.md").write_text(AGENT.format(name="a"))
    assert main(["agents", str(tmp_path), "--expect", "2"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["count_ok"] is False and out["failed"] == 0


def test_empty_directory_fails(tmp_path):
    assert run_check("agents", tmp_path, None, [])["status"] == "FAIL"


def test_missing_directory_fails(tmp_path):
    assert main(["skills", str(tmp_path / "nope")]) == 1
