import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts/configure_trueforge_host.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("configure_trueforge_host", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _TrueForgeHandler(BaseHTTPRequestHandler):
    requests: list[tuple[str, str, dict[str, Any] | None]] = []

    def log_message(self, format: str, *args: object) -> None:
        return

    def _body(self) -> dict[str, Any] | None:
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return None
        value = json.loads(self.rfile.read(length))
        assert isinstance(value, dict)
        return value

    def _reply(self, status: int, value: dict[str, Any]) -> None:
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self) -> None:
        body = self._body()
        self.requests.append(("PUT", self.path, body))
        if self.path not in {
            "/api/v1/settings/sandbox-providers",
            "/api/v1/settings/model-providers",
            "/api/v1/settings/mcp-servers",
        } and not self.path.startswith("/api/v1/agents/"):
            self._reply(404, {"error": {"message": "not found"}})
            return
        self._reply(200, {"data": {}})

    def do_GET(self) -> None:
        self.requests.append(("GET", self.path, None))
        if self.path == "/api/v1/mcp-servers/preflight/tools":
            module = _load_module()
            self._reply(
                200,
                {
                    "data": [
                        {"name": name, "inputSchema": {"description": "x" * 2_000}}
                        for name in module.EXPECTED_TOOLS
                    ]
                },
            )
            return
        if self.path.startswith("/api/v1/agents?"):
            self._reply(200, {"data": [], "pagination": {"next_page_token": None}})
            return
        self._reply(404, {"error": {"message": "not found"}})

    def do_POST(self) -> None:
        body = self._body()
        self.requests.append(("POST", self.path, body))
        if self.path != "/api/v1/agents":
            self._reply(404, {"error": {"message": "not found"}})
            return
        self._reply(201, {"data": {"id": "agent-local-test"}})


@pytest.fixture
def fake_trueforge():
    _TrueForgeHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _TrueForgeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", _TrueForgeHandler.requests
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _secret(path: Path, value: str) -> None:
    path.write_text(json.dumps({"api_key": value}), encoding="utf-8")
    path.chmod(0o600)


def test_dry_run_never_reads_credentials_or_sends_requests(tmp_path, capsys):
    module = _load_module()
    missing = tmp_path / "missing.json"
    assert module.main(["--gateway-secret", str(missing), "--daytona-secret", str(missing)]) == 4
    output = json.loads(capsys.readouterr().out)
    assert output["state"] == "NOT_RUN"
    assert output["credentials_read"] is False
    assert output["requests_sent"] is False
    assert output["daytona_input"] == "DAYTONA_CREDENTIAL_MISSING"
    assert output["literal_approval_tools"] == ["apply_to_demo_source", "cleanup_run"]
    assert output["model_tool_roundtrip"]["executed"] is False


def test_execute_requires_daytona_before_any_http_request(tmp_path, fake_trueforge, capsys):
    module = _load_module()
    base_url, requests = fake_trueforge
    gateway = tmp_path / "gateway.json"
    _secret(gateway, "gateway-test-secret")
    missing_daytona = tmp_path / "daytona.json"
    code = module.main(
        [
            "--execute",
            "--trueforge-url",
            base_url,
            "--gateway-secret",
            str(gateway),
            "--daytona-secret",
            str(missing_daytona),
            "--agent-template",
            str(ROOT / "config/trueforge-agent.example.json"),
        ]
    )
    assert code == 4
    assert requests == []
    assert json.loads(capsys.readouterr().out)["error_code"] == "DAYTONA_CREDENTIAL_MISSING"


def test_provider_mcp_stage_continues_without_daytona_and_stops_before_agent(
    tmp_path, fake_trueforge, capsys
):
    module = _load_module()
    base_url, requests = fake_trueforge
    gateway = tmp_path / "gateway.json"
    _secret(gateway, "gateway-test-secret")
    code = module.main(
        [
            "--execute",
            "--stage",
            "provider-mcp",
            "--trueforge-url",
            base_url,
            "--gateway-secret",
            str(gateway),
            "--daytona-secret",
            str(tmp_path / "missing-daytona.json"),
            "--agent-template",
            str(ROOT / "config/trueforge-agent.example.json"),
        ]
    )
    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["state"] == "LOCAL_CONNECTORS_CONFIGURED"
    assert output["sandbox"] == "NOT_RUN"
    assert output["agent"] == "NOT_RUN"
    assert [item[:2] for item in requests] == [
        ("PUT", "/api/v1/settings/model-providers"),
        ("PUT", "/api/v1/settings/mcp-servers"),
        ("GET", "/api/v1/mcp-servers/preflight/tools"),
    ]


def test_execute_sends_exact_safe_manifests_without_running_tools(
    tmp_path, fake_trueforge, capsys
):
    module = _load_module()
    base_url, requests = fake_trueforge
    gateway = tmp_path / "gateway.json"
    daytona = tmp_path / "daytona.json"
    _secret(gateway, "gateway-test-secret")
    _secret(daytona, "daytona-test-secret")

    code = module.main(
        [
            "--execute",
            "--trueforge-url",
            base_url,
            "--gateway-secret",
            str(gateway),
            "--daytona-secret",
            str(daytona),
            "--agent-template",
            str(ROOT / "config/trueforge-agent.example.json"),
        ]
    )
    assert code == 0
    raw_output = capsys.readouterr().out
    assert "gateway-test-secret" not in raw_output
    assert "daytona-test-secret" not in raw_output
    output = json.loads(raw_output)
    assert output["state"] == "LOCAL_CONFIGURED"
    assert output["approval_invocations"] == 0
    assert output["model_turns"] == 0

    assert [item[:2] for item in requests] == [
        ("PUT", "/api/v1/settings/sandbox-providers"),
        ("PUT", "/api/v1/settings/model-providers"),
        ("PUT", "/api/v1/settings/mcp-servers"),
        ("GET", "/api/v1/mcp-servers/preflight/tools"),
        ("GET", "/api/v1/agents?agent_name=preflight&limit=100"),
        ("POST", "/api/v1/agents"),
    ]
    provider = requests[1][2]
    assert provider is not None
    assert provider["manifest"]["models"] == [
        {
            "model_id": "vm-polaris/openai",
            "name": "gpt-model",
            "properties": {"reasoning_efforts": ["none"]},
        }
    ]
    mcp = requests[2][2]
    assert mcp is not None and mcp["manifest"]["url"] == "http://127.0.0.1:8000/mcp"
    agent = requests[5][2]
    assert agent is not None
    assert agent["manifest"]["model"] == {"name": "openai/gpt-model"}
    assert agent["manifest"]["mcp_servers"][0]["require_approval_for_tools"] == [
        "apply_to_demo_source",
        "cleanup_run",
    ]
