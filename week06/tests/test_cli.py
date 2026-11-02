"""No-key tests for behavior 17: without a key nothing is billed, and --compare still works."""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def run(*args, cwd=HERE):
    env = {k: v for k, v in os.environ.items() if k != "OPENROUTER_API_KEY"}
    return subprocess.run([sys.executable, *args], cwd=cwd, env=env, capture_output=True, text=True)


def test_generate_without_key_exits_1_and_bills_nothing(tmp_path):
    prompts = tmp_path / "p.json"
    prompts.write_text("[]")
    r = run(str(HERE / "generate.py"), str(prompts), "--out", str(tmp_path / "out"))
    assert r.returncode == 1
    assert "OPENROUTER_API_KEY" in r.stderr
    assert not (tmp_path / "out").exists()


def test_critique_without_key_exits_1(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]")
    r = run(str(HERE / "critique.py"), str(manifest))
    assert r.returncode == 1
    assert "OPENROUTER_API_KEY" in r.stderr


def test_compare_needs_no_key(tmp_path):
    entry = {"name": "x", "critique": {"checks": [{"requirement": "a", "met": True}]}, "text_read": "HIKE"}
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps([entry]))
    b.write_text(json.dumps([{**entry, "text_read": "HIKF"}]))
    r = run(str(HERE / "critique.py"), "--compare", str(a), str(b))
    assert r.returncode == 0
    assert "1 image(s)" in r.stdout
