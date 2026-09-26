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


def test_probe_accepts_only_the_explicit_authorized_non_sol_alias(tmp_path):
    base_route = {
        "adapter": "openai",
        "api_family": "responses",
        "base_url": "https://gateway.truefoundry.ai",
        "model": "vm-polaris/openai",
        "reasoning_effort": "none",
        "api_key_env": "PREFLIGHT_GATEWAY_API_KEY",
        "timeout_seconds": 30,
    }
    accepted = tmp_path / "accepted.json"
    accepted.write_text(json.dumps(base_route), encoding="utf-8")
    accepted_result = subprocess.run(
        [
            "node",
            str(ROOT / "scripts/probe_gateway_responses.mjs"),
            f"--config={accepted}",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert accepted_result.returncode == 4
    accepted_output = json.loads(accepted_result.stdout)
    assert accepted_output["state"] == "NOT_RUN"
    assert accepted_output["model"] == "vm-polaris/openai"
    assert accepted_output["reasoning_effort"] == "none"

    wrong_effort = tmp_path / "wrong-effort.json"
    wrong_effort.write_text(
        json.dumps({**base_route, "reasoning_effort": "high"}), encoding="utf-8"
    )
    wrong_effort_result = subprocess.run(
        [
            "node",
            str(ROOT / "scripts/probe_gateway_responses.mjs"),
            f"--config={wrong_effort}",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert wrong_effort_result.returncode == 2
    assert json.loads(wrong_effort_result.stdout)["error_code"] == "ROUTE_EFFORT_NOT_NONE"

    for index, model in enumerate(
        ["vm-polaris/openai-other", "other/openai", "gateway/gpt-6-astra"]
    ):
        rejected = tmp_path / f"rejected-{index}.json"
        rejected.write_text(json.dumps({**base_route, "model": model}), encoding="utf-8")
        rejected_result = subprocess.run(
            [
                "node",
                str(ROOT / "scripts/probe_gateway_responses.mjs"),
                f"--config={rejected}",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert rejected_result.returncode == 2
        assert json.loads(rejected_result.stdout) == {
            "ok": False,
            "state": "BLOCKED_EXTERNAL",
            "error_code": "ROUTE_MODEL_INVALID",
        }


def test_probe_omits_reasoning_for_none_and_preserves_high():
    module = (ROOT / "scripts/probe_gateway_responses.mjs").as_uri()
    expression = (
        f'import {{ reasoningRequestOptions }} from "{module}"; '
        "console.log(JSON.stringify({"
        "none: reasoningRequestOptions('none'), "
        "high: reasoningRequestOptions('high')"
        "}));"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", expression],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "none": {},
        "high": {"reasoning": {"effort": "high"}},
    }
