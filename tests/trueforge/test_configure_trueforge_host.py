import importlib.util
import json
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts/configure_trueforge_host.py"
AGENT_TEMPLATE = ROOT / "config/preflight-agent.yaml"
PATCH_SCRIPT = ROOT / "scripts/patch_trueforge_local_sandbox.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("configure_trueforge_host", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _TrueForgeHandler(BaseHTTPRequestHandler):
    requests: list[tuple[str, str, dict[str, Any] | None]] = []
    provider_redirect: str | None = None
    sandbox_provider_configured = False
    sandbox_enabled = True

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
        if self.path == "/api/v1/settings/model-providers" and self.provider_redirect:
            self.send_response(307)
            self.send_header("Location", self.provider_redirect)
            self.end_headers()
            return
        if self.path not in {
            "/api/v1/settings/model-providers",
            "/api/v1/settings/mcp-servers",
        } and not self.path.startswith("/api/v1/agents/"):
            self._reply(404, {"error": {"message": "not found"}})
            return
        self._reply(200, {"data": {}})

    def do_GET(self) -> None:
        self.requests.append(("GET", self.path, None))
        if self.path == "/api/v1/settings/sandbox-providers":
            if self.sandbox_provider_configured:
                self._reply(200, {"data": {"manifest": {"type": "daytona"}}})
            else:
                self._reply(404, {"error": {"message": "not configured"}})
            return
        if self.path == "/api/v1/capabilities":
            self._reply(
                200,
                {
                    "data": {
                        "sandbox": {"enabled": self.sandbox_enabled},
                        "settings": {"enabled": True},
                    }
                },
            )
            return
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


class _CaptureHandler(BaseHTTPRequestHandler):
    requests: list[tuple[str, str]] = []

    def log_message(self, format: str, *args: object) -> None:
        return

    def _record(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)
        self.requests.append((self.command, self.path))
        self.send_response(502)
        self.end_headers()

    do_GET = _record
    do_POST = _record
    do_PUT = _record


@pytest.fixture
def fake_trueforge():
    _TrueForgeHandler.requests = []
    _TrueForgeHandler.provider_redirect = None
    _TrueForgeHandler.sandbox_provider_configured = False
    _TrueForgeHandler.sandbox_enabled = True
    server = ThreadingHTTPServer(("127.0.0.1", 0), _TrueForgeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", _TrueForgeHandler.requests
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture
def capture_server():
    _CaptureHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _CaptureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", _CaptureHandler.requests
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _secret(path: Path, value: str) -> None:
    path.write_text(json.dumps({"api_key": value}), encoding="utf-8")
    path.chmod(0o600)


def _execute_args(base_url: str, gateway: Path, *, stage: str = "complete") -> list[str]:
    return [
        "--execute",
        "--stage",
        stage,
        "--trueforge-url",
        base_url,
        "--gateway-secret",
        str(gateway),
        "--agent-template",
        str(AGENT_TEMPLATE),
    ]


def _patched_runtime(tmp_path: Path) -> Path:
    scope = tmp_path / "node_modules/@truefoundry"
    main = scope / "trueforge/dist/main.js"
    core = scope / "trueforge-core/dist/core/sandbox/Sandbox.js"
    core_esm = core.with_suffix(".mjs")
    main.parent.mkdir(parents=True)
    core.parent.mkdir(parents=True)
    installed = ROOT / "integration/node_modules/@truefoundry"
    shutil.copyfile(installed / "trueforge/dist/main.js", main)
    shutil.copyfile(installed / "trueforge-core/dist/core/sandbox/Sandbox.js", core)
    shutil.copyfile(installed / "trueforge-core/dist/core/sandbox/Sandbox.mjs", core_esm)
    result = subprocess.run(
        [sys.executable, str(PATCH_SCRIPT), "--main-js", str(main), "--apply"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout
    return main


def test_dry_run_never_reads_credentials_or_sends_requests(tmp_path, capsys):
    module = _load_module()
    missing = tmp_path / "missing.json"
    assert module.main(["--gateway-secret", str(missing)]) == 4
    output = json.loads(capsys.readouterr().out)
    assert output["state"] == "NOT_RUN"
    assert output["credentials_read"] is False
    assert output["requests_sent"] is False
    assert output["sandbox_mode"] == "standalone_local_fallback"
    assert output["sandbox_provider_secret_required"] is False
    assert output["known_blocker"] == "LOCAL_SANDBOX_SESSION_ISOLATION_UNVERIFIED"
    assert output["literal_approval_tools"] == ["apply_to_demo_source", "cleanup_run"]
    assert output["model_tool_roundtrip"]["executed"] is False


def test_provider_mcp_stage_stops_before_sandbox_and_agent(tmp_path, fake_trueforge, capsys):
    module = _load_module()
    base_url, requests = fake_trueforge
    gateway = tmp_path / "gateway.json"
    _secret(gateway, "gateway-test-secret")
    code = module.main(_execute_args(base_url, gateway, stage="provider-mcp"))
    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["state"] == "LOCAL_CONNECTORS_CONFIGURED"
    assert output["sandbox"] == "NOT_CHECKED"
    assert output["agent"] == "NOT_RUN"
    assert [item[:2] for item in requests] == [
        ("PUT", "/api/v1/settings/model-providers"),
        ("PUT", "/api/v1/settings/mcp-servers"),
        ("GET", "/api/v1/mcp-servers/preflight/tools"),
    ]
    provider = requests[0][2]
    assert provider is not None
    assert provider["manifest"]["models"] == [
        {
            "model_id": "vm-polaris/openai",
            "name": "gpt-model",
            "properties": {"reasoning_efforts": ["none"]},
        }
    ]
    mcp = requests[1][2]
    assert mcp is not None and mcp["manifest"]["url"] == "http://127.0.0.1:8000/mcp"


def test_complete_refuses_unavailable_local_sandbox_before_mutation(
    tmp_path, fake_trueforge, capsys
):
    module = _load_module()
    base_url, requests = fake_trueforge
    _TrueForgeHandler.sandbox_enabled = False
    gateway = tmp_path / "gateway.json"
    _secret(gateway, "gateway-test-secret")
    code = module.main(_execute_args(base_url, gateway))
    assert code == 5
    assert json.loads(capsys.readouterr().out)["error_code"] == "LOCAL_SANDBOX_UNAVAILABLE"
    assert [request[:2] for request in requests] == [
        ("GET", "/api/v1/settings/sandbox-providers"),
        ("GET", "/api/v1/capabilities"),
    ]


def test_complete_refuses_persisted_provider_before_mutation(tmp_path, fake_trueforge, capsys):
    module = _load_module()
    base_url, requests = fake_trueforge
    _TrueForgeHandler.sandbox_provider_configured = True
    gateway = tmp_path / "gateway.json"
    _secret(gateway, "gateway-test-secret")
    code = module.main(_execute_args(base_url, gateway))
    assert code == 5
    assert json.loads(capsys.readouterr().out)["error_code"] == (
        "LOCAL_SANDBOX_PROVIDER_CONFLICT"
    )
    assert [request[:2] for request in requests] == [
        ("GET", "/api/v1/settings/sandbox-providers")
    ]


def test_complete_refuses_unscoped_code_mode_bridge_before_mutation(
    tmp_path, fake_trueforge, capsys
):
    module = _load_module()
    base_url, requests = fake_trueforge
    gateway = tmp_path / "gateway.json"
    _secret(gateway, "gateway-test-secret")
    code = module.main(_execute_args(base_url, gateway))
    assert code == 5
    output = json.loads(capsys.readouterr().out)
    assert output["error_code"] == "LOCAL_SANDBOX_SESSION_ISOLATION_UNVERIFIED"
    assert output["operation"] == "local_sandbox"
    assert output["completed"] == []
    assert [request[:2] for request in requests] == [
        ("GET", "/api/v1/settings/sandbox-providers"),
        ("GET", "/api/v1/capabilities"),
    ]


def test_complete_saves_exact_agent_only_with_guarded_local_runtime(
    tmp_path, fake_trueforge, capsys
):
    module = _load_module()
    base_url, requests = fake_trueforge
    gateway = tmp_path / "gateway.json"
    _secret(gateway, "gateway-test-secret")
    args = _execute_args(base_url, gateway)
    args.extend(["--trueforge-main-js", str(_patched_runtime(tmp_path))])
    code = module.main(args)
    assert code == 0, capsys.readouterr().out
    output = json.loads(capsys.readouterr().out)
    assert output["state"] == "LOCAL_SANDBOX_CONFIGURED"
    assert output["approval_invocations"] == 0
    assert output["model_turns"] == 0
    assert [request[:2] for request in requests] == [
        ("GET", "/api/v1/settings/sandbox-providers"),
        ("GET", "/api/v1/capabilities"),
        ("PUT", "/api/v1/settings/model-providers"),
        ("PUT", "/api/v1/settings/mcp-servers"),
        ("GET", "/api/v1/mcp-servers/preflight/tools"),
        ("GET", "/api/v1/agents?agent_name=preflight&limit=100"),
        ("POST", "/api/v1/agents"),
    ]
    agent = requests[-1][2]
    assert agent is not None
    assert agent["manifest"]["model"] == {"name": "openai/gpt-model"}
    assert agent["manifest"]["mcp_servers"][0]["require_approval_for_tools"] == [
        "apply_to_demo_source",
        "cleanup_run",
    ]


def test_transport_ignores_proxy_environment(
    tmp_path, fake_trueforge, capture_server, monkeypatch, capsys
):
    module = _load_module()
    base_url, requests = fake_trueforge
    proxy_url, proxy_requests = capture_server
    gateway = tmp_path / "gateway.json"
    _secret(gateway, "gateway-test-secret")
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(name, proxy_url)
    monkeypatch.setenv("NO_PROXY", "")
    code = module.main(_execute_args(base_url, gateway, stage="provider-mcp"))
    assert code == 0, capsys.readouterr().out
    assert proxy_requests == []
    assert requests


def test_transport_refuses_redirect_without_forwarding_secret(
    tmp_path, fake_trueforge, capture_server, capsys
):
    module = _load_module()
    base_url, requests = fake_trueforge
    receiver_url, receiver_requests = capture_server
    _TrueForgeHandler.provider_redirect = receiver_url + "/capture"
    gateway = tmp_path / "gateway.json"
    _secret(gateway, "gateway-test-secret")
    code = module.main(_execute_args(base_url, gateway, stage="provider-mcp"))
    assert code == 5
    output_text = capsys.readouterr().out
    assert "gateway-test-secret" not in output_text
    assert json.loads(output_text)["error_code"] == "TRUEFORGE_REDIRECT_REFUSED"
    assert [request[:2] for request in requests] == [
        ("PUT", "/api/v1/settings/model-providers")
    ]
    assert receiver_requests == []


def test_agent_template_has_exact_gates_and_valid_installed_agent_spec():
    template = json.loads(AGENT_TEMPLATE.read_text(encoding="utf-8"))
    manifest = template["manifest"]
    server = manifest["mcp_servers"][0]
    assert server["enable_tools"] == list(_load_module().EXPECTED_TOOLS)
    assert server["require_approval_for_tools"] == [
        "apply_to_demo_source",
        "cleanup_run",
    ]
    assert manifest["config"]["sandbox"] == {"enabled": True, "file_downloads": False}
    assert "Never call apply_to_demo_source or cleanup_run\nfrom generated code" in manifest[
        "instructions"
    ]

    program = """
const fs = require('node:fs');
const { AgentSpecSchema } = require('./integration/node_modules/@truefoundry/trueforge-core/dist/agent-session/schemas/agentSpec.js');
const doc = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const parsed = AgentSpecSchema.safeParse(doc.manifest);
if (!parsed.success) { process.stderr.write(JSON.stringify(parsed.error.issues)); process.exit(1); }
"""
    result = subprocess.run(
        ["node", "-e", program, str(AGENT_TEMPLATE)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
