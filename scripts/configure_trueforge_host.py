#!/usr/bin/env python3
"""Configure pinned TrueForge with its isolated standalone Linux sandbox.

Dry-run is the default. ``--execute`` reads the protected Gateway credential
and performs only settings/agent configuration requests against a loopback
TrueForge server. It never invokes an MCP tool or creates a model turn.

TrueForge 0.2.1 exposes Daytona only through the sandbox-provider settings API.
Its local sandbox is instead an automatic standalone fallback after the startup
SRT probe succeeds. The pinned Linux transport currently shares one readable
Code Mode socket parent among same-UID sandboxes, so complete mode refuses to
save an agent until a separately reviewed runtime fix provides session-scoped
bridge isolation. It never stores a fake local-provider manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

TRUEFORGE_DEFAULT = "http://127.0.0.1:18790"
GATEWAY_BASE_URL = "https://gateway.truefoundry.ai"
GATEWAY_MODEL_ID = "vm-polaris/openai"
GATEWAY_MODEL_NAME = "gpt-model"
MODEL_FQN = "openai/gpt-model"
MCP_URL = "http://127.0.0.1:8000/mcp"
EXPECTED_TOOLS = (
    "register_candidate",
    "start_rehearsal",
    "get_run",
    "get_source_status",
    "capture_baseline",
    "apply_to_clone",
    "validate_rehearsal",
    "get_report",
    "apply_to_demo_source",
    "cleanup_run",
)
APPROVAL_TOOLS = ("apply_to_demo_source", "cleanup_run")
MAX_SECRET_JSON_BYTES = 16_384
MAX_RESPONSE_BYTES = 1_048_576
LOCAL_SANDBOX_ISOLATION_BLOCKER = "LOCAL_SANDBOX_SESSION_ISOLATION_UNVERIFIED"
LOCAL_SANDBOX_MAIN_PATCH_SHA256 = (
    "021bfb63b5f6e072aa53fe40d1e7a150ea2ec4112bc412bc840b7eb3a0bc13fb"
)
LOCAL_SANDBOX_CORE_PATCH_SHA256 = (
    "dc08e4e0f1bb6ce08b66882911e08de74c5995be0ee0f0353da29d3e79b993f8"
)
LOCAL_SANDBOX_CORE_ESM_PATCH_SHA256 = (
    "70149fff33b0a2faff9047bb991a5dd6e910b4b85e99764ab879f4c183461cea"
)
DEFAULT_TRUEFORGE_MAIN_JS = Path(
    "integration/node_modules/@truefoundry/trueforge/dist/main.js"
)


class BootstrapError(Exception):
    """A fixed, credential-safe bootstrap failure."""

    def __init__(self, code: str, exit_code: int = 2) -> None:
        super().__init__(code)
        self.code = code
        self.exit_code = exit_code
        self.operation: str | None = None
        self.completed: tuple[str, ...] = ()


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise BootstrapError("JSON_DUPLICATE_KEY")
        value[key] = item
    return value


def _load_json(path: Path, error_prefix: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as error:
        raise BootstrapError(f"{error_prefix}_MISSING", 4) from error
    except OSError as error:
        raise BootstrapError(f"{error_prefix}_UNAVAILABLE", 4) from error
    if len(raw) > MAX_SECRET_JSON_BYTES:
        raise BootstrapError(f"{error_prefix}_TOO_LARGE")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except BootstrapError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BootstrapError(f"{error_prefix}_INVALID") from error
    if not isinstance(value, dict):
        raise BootstrapError(f"{error_prefix}_INVALID")
    return value


def _read_secret(path: Path, error_prefix: str) -> str:
    if os.name != "nt":
        try:
            mode = stat.S_IMODE(path.stat().st_mode)
        except FileNotFoundError as error:
            raise BootstrapError(f"{error_prefix}_MISSING", 4) from error
        except OSError as error:
            raise BootstrapError(f"{error_prefix}_UNAVAILABLE", 4) from error
        if mode & 0o077:
            raise BootstrapError(f"{error_prefix}_PERMISSIONS")
    value = _load_json(path, error_prefix)
    if set(value) != {"api_key"}:
        raise BootstrapError(f"{error_prefix}_INVALID")
    api_key = value["api_key"]
    if not isinstance(api_key, str) or not api_key.strip():
        raise BootstrapError(f"{error_prefix}_INVALID")
    return api_key


def _validate_trueforge_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed.port is None
    ):
        raise BootstrapError("TRUEFORGE_URL_NOT_LOOPBACK")
    return value.rstrip("/")


def _agent_payload(template_path: Path) -> dict[str, Any]:
    value = _load_json(template_path, "AGENT_TEMPLATE")
    if set(value) != {"name", "description", "manifest"}:
        raise BootstrapError("AGENT_TEMPLATE_INVALID")
    if value.get("name") != "preflight" or not isinstance(value.get("description"), str):
        raise BootstrapError("AGENT_TEMPLATE_INVALID")
    manifest = value.get("manifest")
    if not isinstance(manifest, dict):
        raise BootstrapError("AGENT_TEMPLATE_INVALID")
    servers = manifest.get("mcp_servers")
    if not isinstance(servers, list) or len(servers) != 1 or not isinstance(servers[0], dict):
        raise BootstrapError("AGENT_TEMPLATE_INVALID")
    server = servers[0]
    if (
        server.get("name") != "preflight"
        or server.get("enable_tools") != list(EXPECTED_TOOLS)
        or server.get("require_approval_for_tools") != list(APPROVAL_TOOLS)
    ):
        raise BootstrapError("AGENT_TOOL_POLICY_INVALID")
    config = manifest.get("config")
    if not isinstance(config, dict):
        raise BootstrapError("AGENT_TEMPLATE_INVALID")
    sandbox = config.get("sandbox")
    if (
        not isinstance(sandbox, dict)
        or sandbox.get("enabled") is not True
        or sandbox.get("file_downloads") is not False
    ):
        raise BootstrapError("AGENT_SANDBOX_REQUIRED")
    if config.get("dynamic_sub_agents") != {"enabled": False}:
        raise BootstrapError("AGENT_DYNAMIC_SUBAGENTS_FORBIDDEN")

    configured = deepcopy(value)
    configured_manifest = configured["manifest"]
    # TrueForge 0.2.1 forwards reasoning_effort="none" to the Responses API.
    # The approved alias resolves to a non-reasoning model, so omit params.
    configured_manifest["model"] = {"name": MODEL_FQN}
    return configured


class TrueForgeClient:
    def __init__(self, base_url: str, timeout_seconds: int) -> None:
        self.base_url = _validate_trueforge_url(base_url)
        self.timeout_seconds = timeout_seconds
        # Provider and sandbox PUT bodies contain secrets. They must go only to
        # the explicitly validated loopback host, regardless of host proxy env.
        self.opener = build_opener(ProxyHandler({}), _NoRedirectHandler())

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        expected_status: int = 200,
    ) -> dict[str, Any]:
        data = None
        headers = {
            "Accept": "application/json",
            "User-Agent": "Preflight/0.1 trueforge-host-bootstrap",
        }
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout_seconds) as response:
                if response.status != expected_status:
                    raise BootstrapError(f"TRUEFORGE_HTTP_{response.status}", 5)
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except HTTPError as error:
            if 300 <= error.code < 400:
                raise BootstrapError("TRUEFORGE_REDIRECT_REFUSED", 5) from error
            raise BootstrapError(f"TRUEFORGE_HTTP_{error.code}", 5) from error
        except (URLError, TimeoutError, OSError) as error:
            raise BootstrapError("TRUEFORGE_UNAVAILABLE", 5) from error
        if len(raw) > MAX_RESPONSE_BYTES:
            raise BootstrapError("TRUEFORGE_RESPONSE_TOO_LARGE", 5)
        try:
            value = json.loads(raw.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise BootstrapError("TRUEFORGE_RESPONSE_INVALID", 5) from error
        if not isinstance(value, dict):
            raise BootstrapError("TRUEFORGE_RESPONSE_INVALID", 5)
        return value


def _provider_body(api_key: str) -> dict[str, Any]:
    return {
        "manifest": {
            "type": "openai",
            "base_url": GATEWAY_BASE_URL,
            "auth": {"api_key": api_key},
            "models": [
                {
                    "model_id": GATEWAY_MODEL_ID,
                    "name": GATEWAY_MODEL_NAME,
                    "properties": {"reasoning_efforts": ["none"]},
                }
            ],
        }
    }


def _mcp_body() -> dict[str, Any]:
    return {
        "manifest": {
            "type": "remote",
            "name": "preflight",
            "url": MCP_URL,
            "description": "Preflight migration rehearsal MCP (loopback only).",
        }
    }


def _verify_tools(response: dict[str, Any]) -> None:
    data = response.get("data")
    if not isinstance(data, list):
        raise BootstrapError("MCP_TOOL_LIST_INVALID", 5)
    names: list[str] = []
    for item in data:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise BootstrapError("MCP_TOOL_LIST_INVALID", 5)
        names.append(item["name"])
    if len(names) != len(set(names)) or set(names) != set(EXPECTED_TOOLS):
        raise BootstrapError("MCP_TOOL_SET_MISMATCH", 5)


def _save_agent(client: TrueForgeClient, payload: dict[str, Any]) -> tuple[str, str]:
    query = urlencode({"agent_name": "preflight", "limit": 100})
    listed = client.request("GET", f"/api/v1/agents?{query}")
    data = listed.get("data")
    if not isinstance(data, list):
        raise BootstrapError("AGENT_LIST_INVALID", 5)
    exact = [item for item in data if isinstance(item, dict) and item.get("name") == "preflight"]
    if len(exact) > 1:
        raise BootstrapError("AGENT_NAME_AMBIGUOUS", 5)
    if not exact:
        saved = client.request("POST", "/api/v1/agents", body=payload, expected_status=201)
        action = "created"
    else:
        agent_id = exact[0].get("id")
        if not isinstance(agent_id, str) or not agent_id:
            raise BootstrapError("AGENT_LIST_INVALID", 5)
        saved = client.request(
            "PUT",
            f"/api/v1/agents/{agent_id}",
            body={"description": payload["description"], "manifest": payload["manifest"]},
        )
        action = "updated"
    saved_data = saved.get("data")
    if not isinstance(saved_data, dict) or not isinstance(saved_data.get("id"), str):
        raise BootstrapError("AGENT_RESPONSE_INVALID", 5)
    return action, saved_data["id"]


def _step(operation: str, completed: list[str], callback):
    try:
        return callback()
    except BootstrapError as error:
        error.operation = operation
        error.completed = tuple(completed)
        raise


def _verify_local_sandbox_patch(main_js: Path) -> None:
    core_js = main_js.parent.parent.parent / "trueforge-core/dist/core/sandbox/Sandbox.js"
    for path, expected in (
        (main_js, LOCAL_SANDBOX_MAIN_PATCH_SHA256),
        (core_js, LOCAL_SANDBOX_CORE_PATCH_SHA256),
        (core_js.with_suffix(".mjs"), LOCAL_SANDBOX_CORE_ESM_PATCH_SHA256),
    ):
        try:
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise OSError
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise BootstrapError(LOCAL_SANDBOX_ISOLATION_BLOCKER, 5) from error
        if actual != expected:
            raise BootstrapError(LOCAL_SANDBOX_ISOLATION_BLOCKER, 5)


def _verify_local_sandbox(client: TrueForgeClient, main_js: Path) -> None:
    try:
        client.request("GET", "/api/v1/settings/sandbox-providers")
    except BootstrapError as error:
        if error.code != "TRUEFORGE_HTTP_404":
            raise
    else:
        # A persisted provider takes precedence over the standalone fallback.
        raise BootstrapError("LOCAL_SANDBOX_PROVIDER_CONFLICT", 5)

    capabilities = client.request("GET", "/api/v1/capabilities")
    data = capabilities.get("data")
    sandbox = data.get("sandbox") if isinstance(data, dict) else None
    if not isinstance(sandbox, dict) or sandbox.get("enabled") is not True:
        raise BootstrapError("LOCAL_SANDBOX_UNAVAILABLE", 5)
    # Capability=true proves availability, not same-UID session isolation. The
    # exact reviewed patch narrows read access to the current Code Mode socket
    # and strips an agent-provided TFY_MCP_SOCK before transport injection.
    _verify_local_sandbox_patch(main_js.resolve())


def _plan(stage: str) -> dict[str, Any]:
    return {
        "ok": False,
        "state": "NOT_RUN",
        "error_code": "EXPLICIT_EXECUTE_REQUIRED",
        "credentials_read": False,
        "requests_sent": False,
        "stage": stage,
        "sandbox_mode": "standalone_local_fallback",
        "sandbox_provider_secret_required": False,
        "sandbox_precondition": (
            "not_checked_for_provider-mcp"
            if stage == "provider-mcp"
            else "startup_probe_supported_no_provider_and_session_bridge_isolated"
        ),
        "known_blocker": None if stage == "provider-mcp" else LOCAL_SANDBOX_ISOLATION_BLOCKER,
        "model_provider": "openai",
        "model_alias": GATEWAY_MODEL_ID,
        "model_resource": MODEL_FQN,
        "reasoning_parameter": "omitted",
        "mcp_url": MCP_URL,
        "business_tools": list(EXPECTED_TOOLS),
        "literal_approval_tools": list(APPROVAL_TOOLS),
        "model_tool_roundtrip": {
            "executed": False,
            "create_session": "POST /api/v1/sessions with agent.name=preflight",
            "create_turn": "POST /api/v1/sessions/{session_id}/turns",
            "safe_prompt": "Call get_run once for supplied nonexistent UUIDs; report RUN_NOT_FOUND.",
            "poll": "GET /api/v1/sessions/{session_id}/turns/{turn_id} with a bounded deadline",
        },
    }


def execute(args: argparse.Namespace) -> dict[str, Any]:
    base_url = _validate_trueforge_url(args.trueforge_url)
    payload = _agent_payload(args.agent_template)
    # Read and validate every local input before the first HTTP mutation.
    gateway_key = _read_secret(args.gateway_secret, "GATEWAY_CREDENTIAL")
    client = TrueForgeClient(base_url, args.timeout_seconds)
    completed: list[str] = []
    if args.stage == "complete":
        _step(
            "local_sandbox",
            completed,
            lambda: _verify_local_sandbox(client, args.trueforge_main_js),
        )
        completed.append("local_sandbox")
    _step(
        "model_provider",
        completed,
        lambda: client.request(
            "PUT", "/api/v1/settings/model-providers", body=_provider_body(gateway_key)
        ),
    )
    completed.append("model_provider")
    _step(
        "mcp_connector",
        completed,
        lambda: client.request("PUT", "/api/v1/settings/mcp-servers", body=_mcp_body()),
    )
    completed.append("mcp_connector")
    tools = _step(
        "mcp_tool_schema",
        completed,
        lambda: client.request("GET", "/api/v1/mcp-servers/preflight/tools"),
    )
    _step("mcp_tool_schema", completed, lambda: _verify_tools(tools))
    completed.append("mcp_tool_schema")
    if args.stage == "provider-mcp":
        return {
            "ok": True,
            "state": "LOCAL_CONNECTORS_CONFIGURED",
            "completed": completed,
            "model_alias": GATEWAY_MODEL_ID,
            "model_resource": MODEL_FQN,
            "reasoning_parameter": "omitted",
            "mcp_url": MCP_URL,
            "sandbox": "NOT_CHECKED",
            "agent": "NOT_RUN",
            "approval_invocations": 0,
            "model_turns": 0,
            "next_step": (
                "Apply and independently review the session-scoped Code Mode bridge fix; "
                "run its two-session host canary, then rerun this bootstrap in complete mode."
            ),
        }
    agent_action, agent_id = _step(
        "agent", completed, lambda: _save_agent(client, payload)
    )
    completed.append(f"agent_{agent_action}")
    return {
        "ok": True,
        "state": "LOCAL_SANDBOX_CONFIGURED",
        "completed": completed,
        "model_alias": GATEWAY_MODEL_ID,
        "model_resource": MODEL_FQN,
        "reasoning_parameter": "omitted",
        "mcp_url": MCP_URL,
        "sandbox": "STANDALONE_LOCAL_FALLBACK",
        "agent_id": agent_id,
        "literal_approval_tools": list(APPROVAL_TOOLS),
        "approval_invocations": 0,
        "model_turns": 0,
        "next_step": "Run the bounded read-only MCP bridge trace and direct approval pauses; do not approve either literal gate.",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--stage", choices=("complete", "provider-mcp"), default="complete")
    parser.add_argument("--trueforge-url", default=TRUEFORGE_DEFAULT)
    parser.add_argument(
        "--gateway-secret", type=Path, default=Path("/var/lib/preflight/gateway.secret.json")
    )
    parser.add_argument(
        "--agent-template", type=Path, default=Path("config/preflight-agent.yaml")
    )
    parser.add_argument(
        "--trueforge-main-js", type=Path, default=DEFAULT_TRUEFORGE_MAIN_JS
    )
    parser.add_argument("--timeout-seconds", type=int, default=15)
    args = parser.parse_args(argv)
    if args.timeout_seconds < 1 or args.timeout_seconds > 60:
        raise BootstrapError("TIMEOUT_INVALID")
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
        result = execute(args) if args.execute else _plan(args.stage)
        print(json.dumps(result, separators=(",", ":")))
        return 0 if result.get("ok") else 4
    except BootstrapError as error:
        failure: dict[str, Any] = {
            "ok": False,
            "state": "BLOCKED_EXTERNAL",
            "error_code": error.code,
        }
        if error.operation is not None:
            failure["operation"] = error.operation
            failure["completed"] = list(error.completed)
        print(
            json.dumps(failure, separators=(",", ":"))
        )
        return error.exit_code
    except Exception:
        print(
            json.dumps(
                {"ok": False, "state": "BLOCKED_EXTERNAL", "error_code": "BOOTSTRAP_INTERNAL_ERROR"},
                separators=(",", ":"),
            )
        )
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
