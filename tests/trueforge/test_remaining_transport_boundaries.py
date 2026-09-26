"""Local assertions for the remaining N20/N21/N22/N29 integration boundaries.

These tests use loopback servers and explicit no-AWS/no-PostgreSQL test doubles.
They do not represent a connected Gateway, RDS, Daytona, or human-gate run.
"""

from __future__ import annotations

import base64
import hashlib
import json
import multiprocessing
import socket
import sqlite3
import subprocess
import time
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from starlette.testclient import TestClient

from preflight.config import Settings
from preflight.server import make_server, serve
from preflight.service import RehearsalService

ROOT = Path(__file__).parents[2]


def _unused_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _wait_for_listener(port: int) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("loopback MCP server did not start")


def _database_counts(path: Path) -> dict[str, int]:
    with sqlite3.connect(path) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in tables
        }


def _candidate_arguments(sql: bytes, contract: dict) -> dict:
    return {
        "request_id": str(uuid4()),
        "sql_utf8_b64": base64.b64encode(sql).decode("ascii"),
        "expected_migration_sha256": hashlib.sha256(sql).hexdigest(),
        "contract": contract,
        "operator_id": "remaining-boundary-test",
    }


class _LongCloudOperationTestDouble(RehearsalService):
    """Simulate a blocked cloud worker without importing or calling AWS."""

    def call(self, tool: str, arguments: dict) -> dict:
        if tool == "start_rehearsal":
            time.sleep(3)
            return {
                "ok": False,
                "request_id": arguments.get("request_id"),
                "run_id": None,
                "state": None,
                "data": {"message": "LOCAL_LONG_OPERATION_CANCELLED"},
                "error_code": "LOCAL_LONG_OPERATION_CANCELLED",
                "retryable": False,
            }
        return super().call(tool, arguments)


def _serve_long_cloud_test_double(state_dir: str, port: int) -> None:
    service = _LongCloudOperationTestDouble(
        Settings(state_dir=Path(state_dir)), restart=False
    )
    make_server(service).run(
        transport="streamable-http", host="127.0.0.1", port=port
    )


def test_n20_loopback_server_rejects_disallowed_host_and_origin(tmp_path):
    """The selected MCP SDK applies its loopback DNS-rebinding policy."""
    service = RehearsalService(Settings(state_dir=tmp_path), restart=False)
    try:
        app = make_server(service).streamable_http_app(host="127.0.0.1")
        with TestClient(app) as client:
            bad_host = client.post(
                "/mcp",
                headers={"Host": "attacker.invalid", "Content-Type": "application/json"},
                json={},
            )
            bad_origin = client.post(
                "/mcp",
                headers={
                    "Host": "127.0.0.1:8000",
                    "Origin": "https://attacker.invalid",
                    "Content-Type": "application/json",
                },
                json={},
            )
        assert bad_host.status_code == 421
        assert bad_host.text == "Invalid Host header"
        assert bad_origin.status_code == 403
        assert bad_origin.text == "Invalid Origin header"

        with patch("mcp.server.MCPServer.run") as run:
            serve(service, port=18765)
        run.assert_called_once_with(
            transport="streamable-http", host="127.0.0.1", port=18765
        )
        assert _database_counts(tmp_path / "preflight.sqlite3") == {
            "apply_attempts": 0,
            "events": 0,
            "idempotency": 0,
            "records": 0,
            "runs": 0,
        }
    finally:
        service.executor.shutdown(wait=True)


def test_n21_status_stays_responsive_and_cancelled_delivery_claims_no_rollback(tmp_path):
    """A no-AWS blocked worker cannot monopolize the MCP status transport."""
    service = RehearsalService(Settings(state_dir=tmp_path), restart=False)
    contract = json.loads((ROOT / "config/contract.example.json").read_text(encoding="utf-8"))
    sql = (ROOT / "fixtures/good.sql").read_bytes()
    registered = service.call("register_candidate", _candidate_arguments(sql, contract))
    assert registered["ok"] is True
    candidate_id = registered["data"]["candidate_id"]
    run_id = str(uuid4())
    service.store.create_run(
        {
            "run_id": run_id,
            "candidate_id": candidate_id,
            "source_instance_id": "preflight-demo-source",
            "database_name": "preflight_demo",
            "account_id": "000000000000",
            "region": "us-east-1",
            "created_at": "2026-09-26T00:00:00Z",
            "snapshot_id": "preflight-snapshot",
            "clone_instance_id": "preflight-clone",
            "resource_expires_at": "2026-09-27T00:00:00Z",
        }
    )
    before_run = service.store.get_run(run_id)
    before_counts = _database_counts(tmp_path / "preflight.sqlite3")
    service.executor.shutdown(wait=True)

    port = _unused_port()
    process = multiprocessing.Process(
        target=_serve_long_cloud_test_double, args=(str(tmp_path), port)
    )
    process.start()
    try:
        _wait_for_listener(port)
        node_script = """
import { Client } from './integration/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import { StreamableHTTPClientTransport } from './integration/node_modules/@modelcontextprotocol/sdk/dist/esm/client/streamableHttp.js';

const endpoint = new URL(process.env.N21_ENDPOINT);
const slow = new Client({ name: 'n21-slow-test-double', version: '1.0.0' });
await slow.connect(new StreamableHTTPClientTransport(endpoint));
const abort = new AbortController();
const pending = slow.callTool({
  name: 'start_rehearsal',
  arguments: {
    request_id: process.env.N21_START_REQUEST,
    candidate_id: process.env.N21_CANDIDATE_ID,
    source_instance_id: 'preflight-demo-source',
    database_name: 'preflight_demo',
  },
}, undefined, { signal: abort.signal });
await new Promise((resolve) => setTimeout(resolve, 150));

const observer = new Client({ name: 'n21-status-observer', version: '1.0.0' });
await observer.connect(new StreamableHTTPClientTransport(endpoint));
const started = performance.now();
const status = await observer.callTool({
  name: 'get_run',
  arguments: { request_id: process.env.N21_STATUS_REQUEST, run_id: process.env.N21_RUN_ID },
});
const elapsedMs = performance.now() - started;
abort.abort();
let interrupted = false;
try { await pending; } catch { interrupted = true; }
await observer.close();
await slow.close();
process.stdout.write(JSON.stringify({ elapsedMs, interrupted, status: status.structuredContent }));
"""
        env = {
            **__import__("os").environ,
            "N21_ENDPOINT": f"http://127.0.0.1:{port}/mcp",
            "N21_START_REQUEST": str(uuid4()),
            "N21_STATUS_REQUEST": str(uuid4()),
            "N21_CANDIDATE_ID": candidate_id,
            "N21_RUN_ID": run_id,
        }
        result = subprocess.run(
            ["node", "--input-type=module", "--eval", node_script],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        observed = json.loads(result.stdout)
        assert observed["elapsedMs"] < 1_000
        assert observed["interrupted"] is True
        assert observed["status"]["ok"] is True
        assert observed["status"]["data"]["phase"] == "REGISTERED"
        assert observed["status"]["data"]["revision"] == 0
    finally:
        process.terminate()
        process.join(timeout=5)

    after = RehearsalService(Settings(state_dir=tmp_path), restart=False)
    try:
        after_run = after.store.get_run(run_id)
        assert after_run["phase"] == before_run["phase"] == "REGISTERED"
        assert after_run["revision"] == before_run["revision"] == 0
        assert _database_counts(tmp_path / "preflight.sqlite3") == before_counts
    finally:
        after.executor.shutdown(wait=True)


def test_n22_incomplete_stream_and_partial_mutation_arguments_have_no_effect(tmp_path):
    """Both the stream decoder and all mutation schemas fail before persistence."""
    expression = """
import { ToolCallState } from './scripts/responses_stream_state.mjs';
const state = new ToolCallState();
state.accept({ type: 'response.created', response: { id: 'response_partial' } });
state.accept({
  type: 'response.output_item.added',
  item: { type: 'function_call', id: 'item_partial', call_id: 'call_partial', name: 'status' },
});
state.accept({ type: 'response.function_call_arguments.delta', item_id: 'item_partial', delta: '{' });
state.accept({ type: 'response.completed', response: { id: 'response_partial' } });
let code = null;
try { state.finish(); } catch (error) { code = error.code; }
process.stdout.write(JSON.stringify({ code }));
"""
    decoded = subprocess.run(
        ["node", "--input-type=module", "--eval", expression],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert decoded.returncode == 0, decoded.stderr
    assert json.loads(decoded.stdout) == {"code": "TOOL_ARGUMENTS_INVALID"}

    service = RehearsalService(Settings(state_dir=tmp_path), restart=False)
    try:
        before = _database_counts(tmp_path / "preflight.sqlite3")
        for tool in (
            "register_candidate",
            "start_rehearsal",
            "capture_baseline",
            "apply_to_clone",
            "validate_rehearsal",
            "apply_to_demo_source",
            "cleanup_run",
        ):
            result = service.call(tool, {"request_id": str(uuid4())})
            assert result["ok"] is False, tool
            assert result["error_code"] == "INVALID_INPUT", tool
        assert _database_counts(tmp_path / "preflight.sqlite3") == before
    finally:
        service.executor.shutdown(wait=True)


def test_n29_inventory_notices_and_public_claims_remain_qualified():
    inventory = json.loads(
        (ROOT / "integration/dependency-inventory.json").read_text(encoding="utf-8")
    )
    components = inventory["components"]
    assert inventory["component_count"] == len(components)
    assert all(component.get("version") for component in components)
    assert all(
        component.get("integrity")
        for component in components
        if component["ecosystem"] == "npm"
    )
    assert set(inventory["locks"]) == {
        "integration/package-lock.json_sha256",
        "uv.lock_sha256",
    }
    assert all(len(digest) == 64 for digest in inventory["locks"].values())

    by_name = {component["name"]: component for component in components}
    assert by_name["pglast"]["license_declared"] == "GPL-3.0-or-later"
    assert by_name["@truefoundry/trueforge"]["license_declared"] == "MIT"
    assert by_name["preflight-rehearsal"]["license_declared"] == "UNDECIDED"
    notices = (ROOT / "integration/THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    for required in (
        "pglast 8.4",
        "GPL-3.0-or-later",
        "Preserve that declaration and the\nupstream notices",
        "@truefoundry/trueforge 0.2.1",
        "transitive dependencies retain their own licenses",
        "requires review against the distributed package before\npublication",
        "project itself has no selected license",
        "UNDECIDED",
    ):
        assert required in notices

    public_docs = [ROOT / "README.md", ROOT / "START_HERE.md", ROOT / "CLAUDE.md"]
    public_docs.extend(sorted((ROOT / "docs").glob("*.md")))
    public_docs.extend(sorted((ROOT / "integration").glob("*.md")))
    corpus = "\n".join(path.read_text(encoding="utf-8") for path in public_docs).lower()
    assert (
        "this is an inventory/control requirement, not a claim that a particular "
        "distribution has been legally cleared"
    ) in corpus
    for unsupported_claim in (
        "legal clearance complete",
        "all dependencies are mit",
        "approved for redistribution",
        "license review complete",
    ):
        assert unsupported_claim not in corpus
