import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]


def run_probe(path: Path, *, template: bool = True) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(ROOT / "scripts/probe_trueforge_config.py"), str(path)]
    if template:
        command.append("--template")
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)


def test_saved_agent_template_preserves_ten_tools_and_two_literal_gates():
    result = run_probe(ROOT / "config/trueforge-agent.example.json")
    assert result.returncode == 0, result.stderr or result.stdout
    observed = json.loads(result.stdout)
    assert observed == {
        "business_tool_count": 10,
        "dynamic_subagents_enabled": False,
        "human_gates": ["apply_to_demo_source", "cleanup_run"],
        "model_configured": False,
        "ok": True,
        "sandbox_enabled": True,
        "status": "VALID_TEMPLATE",
        "trueforge_schema_version": "0.2.1-observed",
    }


def test_deployment_validation_rejects_placeholder_model():
    result = run_probe(ROOT / "config/trueforge-agent.example.json", template=False)
    assert result.returncode == 2
    assert json.loads(result.stdout) == {
        "ok": False,
        "error_code": "MODEL_RESOURCE_NOT_CONFIGURED",
    }


def test_config_probe_rejects_removed_literal_gate(tmp_path):
    value = json.loads((ROOT / "config/trueforge-agent.example.json").read_text(encoding="utf-8"))
    value["manifest"]["mcp_servers"][0]["require_approval_for_tools"] = ["cleanup_run"]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    result = run_probe(path)
    assert result.returncode == 2
    assert json.loads(result.stdout)["error_code"] == "HUMAN_GATE_LIST_INVALID"


def test_config_probe_accepts_only_exact_authorized_alias_without_reasoning(tmp_path):
    template = json.loads(
        (ROOT / "config/trueforge-agent.example.json").read_text(encoding="utf-8")
    )
    template["manifest"]["model"] = {"name": "openai/gpt-model"}
    accepted = tmp_path / "accepted.json"
    accepted.write_text(json.dumps(template), encoding="utf-8")
    result = run_probe(accepted, template=False)
    assert result.returncode == 0, result.stdout
    assert json.loads(result.stdout)["status"] == "VALID_CONFIG"

    template["manifest"]["model"] = {"name": "openai/other"}
    rejected = tmp_path / "rejected.json"
    rejected.write_text(json.dumps(template), encoding="utf-8")
    result = run_probe(rejected, template=False)
    assert result.returncode == 2
    assert json.loads(result.stdout)["error_code"] == "MODEL_PARAMS_INVALID"
