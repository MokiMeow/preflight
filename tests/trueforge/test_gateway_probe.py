import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_responses_stream_state_machine():
    result = subprocess.run(
        ["node", "--test", str(ROOT / "tests/trueforge/test_responses_stream.mjs")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "tests 3" in result.stdout
    assert "pass 3" in result.stdout


def test_probe_blocks_without_ignored_route_config():
    result = subprocess.run(
        ["node", str(ROOT / "scripts/probe_gateway_responses.mjs")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4
    assert json.loads(result.stdout) == {
        "ok": False,
        "state": "BLOCKED_EXTERNAL",
        "error_code": "ROUTE_CONFIG_MISSING",
    }


def test_probe_does_not_execute_without_explicit_flag(tmp_path):
    route = {
        "adapter": "openai",
        "api_family": "responses",
        "base_url": "https://gateway.invalid/authorized-path",
        "model": "gateway/gpt-6-sol",
        "reasoning_effort": "high",
        "api_key_env": "PREFLIGHT_GATEWAY_API_KEY",
        "timeout_seconds": 30,
    }
    config = tmp_path / "route.json"
    config.write_text(json.dumps(route), encoding="utf-8")
    result = subprocess.run(
        [
            "node",
            str(ROOT / "scripts/probe_gateway_responses.mjs"),
            f"--config={config}",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4
    observed = json.loads(result.stdout)
    assert observed["state"] == "NOT_RUN"
    assert observed["error_code"] == "EXPLICIT_EXECUTE_REQUIRED"
    assert "gateway.invalid" not in result.stdout
