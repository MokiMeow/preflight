"""Credential-free boundary probes for the installed connected-runtime packages."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import multiprocessing
import os
import socket
import sqlite3
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import UUID, uuid4

from preflight.artifacts import canonical_json
from preflight.config import Settings
from preflight.models import (
    CheckResult,
    CoverageEntry,
    PublicEvidence,
    PublicTableEvidence,
    ReportPayload,
    TxOutcome,
)
from preflight.offline import verify_report
from preflight.report import seal_report
from preflight.service import RehearsalService
from preflight.verdict import invariant_requirements

ROOT = Path(__file__).parents[2]
SENTINEL = "n16-secret-bearing-input-output-sentinel"


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


class _CaptureServer(ThreadingHTTPServer):
    api_authorized = False
    otlp_requests: list[tuple[dict[str, str], bytes]]

    def __init__(self, address: tuple[str, int]):
        super().__init__(address, _CaptureHandler)
        self.otlp_requests = []


class _CaptureHandler(BaseHTTPRequestHandler):
    server: _CaptureServer

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path not in {"/config", "/sandbox?limit=1"}:
            self.send_error(404)
            return
        self.server.api_authorized = self.headers.get("Authorization") == f"Bearer {SENTINEL}"
        body = json.dumps(
            {"version": SENTINEL}
            if self.path == "/config"
            else {"items": [], "secret_bearing_output": SENTINEL}
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            chunks = []
            while True:
                size_line = self.rfile.readline().split(b";", 1)[0].strip()
                size = int(size_line, 16)
                if size == 0:
                    self.rfile.readline()
                    break
                chunks.append(self.rfile.read(size))
                self.rfile.read(2)
            body = b"".join(chunks)
        else:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
        if self.path == "/v1/traces":
            self.server.otlp_requests.append((dict(self.headers), body))
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_error(404)


def _run_daytona_probe(port: int, *, telemetry_enabled: bool) -> subprocess.CompletedProcess[str]:
    script = """
import { Daytona } from './integration/node_modules/@daytona/sdk/esm/index.js';
const client = new Daytona({
  apiKey: process.env.N16_SENTINEL,
  apiUrl: process.env.N16_API_URL,
  target: 'local-test',
  useDeprecatedPolling: true,
  otelEnabled: process.env.N16_ENABLE_OTEL === 'true',
});
for await (const _sandbox of client.list({ limit: 1 })) { /* exhaust one page */ }
await client[Symbol.asyncDispose]();
"""
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("DAYTONA_OTEL")
        and not key.startswith("DAYTONA_EXPERIMENTAL_OTEL")
        and not key.startswith("OTEL_")
    }
    env.update(
        {
            "N16_SENTINEL": SENTINEL,
            "N16_API_URL": f"http://127.0.0.1:{port}",
            "N16_ENABLE_OTEL": "true" if telemetry_enabled else "false",
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": f"http://127.0.0.1:{port}/v1/traces",
            "OTEL_EXPORTER_OTLP_PROTOCOL": "http/protobuf",
            "OTEL_METRICS_EXPORTER": "none",
            "OTEL_LOGS_EXPORTER": "none",
        }
    )
    return subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_n16_daytona_telemetry_default_and_enabled_export_do_not_leak_secret_data():
    """Default is off; an enabled local exporter receives spans without header/body values."""
    sdk_source = (
        ROOT / "integration/node_modules/@daytona/sdk/esm/Daytona.js"
    ).read_text(encoding="utf-8")
    assert "new OTLPTraceExporter" in sdk_source
    assert "OTLPLogExporter" not in sdk_source
    assert "logRecordProcessors" not in sdk_source

    server = _CaptureServer(("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        disabled = _run_daytona_probe(port, telemetry_enabled=False)
        assert disabled.returncode == 0, disabled.stderr or disabled.stdout
        assert server.api_authorized is True
        assert server.otlp_requests == []

        enabled = _run_daytona_probe(port, telemetry_enabled=True)
        assert enabled.returncode == 0, enabled.stderr or enabled.stdout
        assert server.otlp_requests, "enabled SDK telemetry did not reach the loopback sentinel"
        for headers, raw in server.otlp_requests:
            decoded = gzip.decompress(raw) if headers.get("Content-Encoding") == "gzip" else raw
            assert SENTINEL.encode("utf-8") not in decoded
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _candidate_arguments(sql: bytes, contract: dict) -> dict:
    return {
        "request_id": str(uuid4()),
        "sql_utf8_b64": base64.b64encode(sql).decode("ascii"),
        "expected_migration_sha256": hashlib.sha256(sql).hexdigest(),
        "contract": contract,
        "operator_id": "n19-test-operator",
    }


def _serve_slow_get_run(state_dir: str, port: int) -> None:
    from preflight.server import make_server

    class SlowDeliveryService(RehearsalService):
        def call(self, tool: str, arguments: dict) -> dict:
            result = super().call(tool, arguments)
            if tool == "get_run":
                time.sleep(0.4)
            return result

    service = SlowDeliveryService(Settings(state_dir=Path(state_dir)))
    make_server(service).run(transport="streamable-http", host="127.0.0.1", port=port)


def test_n19_cancelled_get_run_delivery_reconnects_without_mutating_business_run(tmp_path):
    service = RehearsalService(Settings(state_dir=tmp_path), restart=False)
    contract = json.loads((ROOT / "config/contract.example.json").read_text(encoding="utf-8"))
    sql = (ROOT / "fixtures/good.sql").read_bytes()
    registered = service.call("register_candidate", _candidate_arguments(sql, contract))
    assert registered["ok"] is True
    run_id = str(uuid4())
    service.store.create_run(
        {
            "run_id": run_id,
            "candidate_id": registered["data"]["candidate_id"],
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
    before = service.store.get_run(run_id)
    service.executor.shutdown(wait=True)

    port = _unused_port()
    process = multiprocessing.Process(target=_serve_slow_get_run, args=(str(tmp_path), port))
    process.start()
    try:
        _wait_for_listener(port)
        node_script = """
import { Client } from './integration/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import { StreamableHTTPClientTransport } from './integration/node_modules/@modelcontextprotocol/sdk/dist/esm/client/streamableHttp.js';

const endpoint = new URL(process.env.N19_ENDPOINT);
const args = { request_id: process.env.N19_REQUEST_ID, run_id: process.env.N19_RUN_ID };
const first = new Client({ name: 'n19-interrupted-observer', version: '1.0.0' });
await first.connect(new StreamableHTTPClientTransport(endpoint));
const abort = new AbortController();
const pending = first.callTool({ name: 'get_run', arguments: args }, undefined, { signal: abort.signal });
setTimeout(() => abort.abort(), 40);
let interrupted = false;
try { await pending; } catch { interrupted = true; }
await first.close();

const second = new Client({ name: 'n19-reconnected-observer', version: '1.0.0' });
await second.connect(new StreamableHTTPClientTransport(endpoint));
const observed = await second.callTool({
  name: 'get_run',
  arguments: { request_id: process.env.N19_REQUEST_ID_2, run_id: process.env.N19_RUN_ID },
});
await second.close();
process.stdout.write(JSON.stringify({ interrupted, observed: observed.structuredContent }));
"""
        env = os.environ.copy()
        env.update(
            {
                "N19_ENDPOINT": f"http://127.0.0.1:{port}/mcp",
                "N19_REQUEST_ID": str(uuid4()),
                "N19_REQUEST_ID_2": str(uuid4()),
                "N19_RUN_ID": run_id,
            }
        )
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
        assert observed["interrupted"] is True
        envelope = observed["observed"]
        assert envelope["ok"] is True
        assert envelope["data"]["phase"] == "REGISTERED"
        assert envelope["data"]["revision"] == before["revision"]
        assert envelope["data"]["candidate_id"] == before["candidate_id"]
    finally:
        process.terminate()
        process.join(timeout=5)

    after = RehearsalService(Settings(state_dir=tmp_path), restart=False)
    try:
        durable = after.store.get_run(run_id)
        assert durable["phase"] == before["phase"] == "REGISTERED"
        assert durable["revision"] == before["revision"] == 0
        assert durable["candidate_id"] == before["candidate_id"]
        with sqlite3.connect(tmp_path / "preflight.sqlite3") as connection:
            event_codes = [row[0] for row in connection.execute("SELECT code FROM events")]
        assert event_codes == ["RUN_CREATED"]
    finally:
        after.executor.shutdown(wait=True)


def _evidence() -> PublicEvidence:
    return PublicEvidence(
        tables=[
            PublicTableEvidence(
                name="public.customers",
                row_count=3,
                schema_sha256="a" * 64,
                preserved_sha256="b" * 64,
                full_sha256="c" * 64,
                schema_summary=[{"name": "id", "type": "integer", "nullable": False}],
            )
        ]
    )


def _report_without_connected_trace_ids() -> ReportPayload:
    requirements = invariant_requirements()
    return ReportPayload(
        evidence_backend="unit_fixture",
        run_id=UUID("00000000-0000-0000-0000-000000000026"),
        candidate_id=UUID("00000000-0000-0000-0000-000000000027"),
        operator_id="n26-test-operator",
        created_at="2026-09-26T00:00:00Z",
        source_instance_id="preflight-source",
        snapshot_id="preflight-snapshot",
        clone_instance_id="preflight-clone",
        engine_major=18,
        dependency_versions={"preflight": "0.1.0", "postgresql": "18"},
        migration_sha256="d" * 64,
        contract_sha256="e" * 64,
        before=_evidence(),
        after=_evidence(),
        checks=[
            CheckResult(
                id=requirement.id,
                category=requirement.kind,
                status="pass",
                before=True,
                after=True,
            )
            for requirement in requirements
        ],
        validation_requirements=requirements,
        impact_summary=[
            CoverageEntry(
                table="public.customers",
                column="account_tier",
                operation="add_column",
                rule="all_equal",
                complete=True,
            )
        ],
        migration=TxOutcome(outcome="committed", elapsed_ms=42),
        backup_available=True,
        verdict="PASS",
        apply_eligible_at_report_time=True,
        untested_risks=["connected trace identifiers were not observed"],
    )


def test_n26_missing_connected_trace_ids_do_not_change_sealed_report_identity():
    payload = _report_without_connected_trace_ids()
    encoded_payload = canonical_json(payload.model_dump(mode="json"))
    for absent in (b"gateway_request_id", b"aws_request_id", b"sandbox_trace_id"):
        assert absent not in encoded_payload

    sealed = seal_report(payload)
    result = verify_report(
        canonical_json(sealed.model_dump(mode="json")), expected_digest=sealed.report_sha256
    )
    assert result["integrity"] == "VALID"
    assert result["anchor_status"] == "EXPECTED_DIGEST_MATCH"
    assert result["declared_verdict"] == result["recomputed_verdict"] == "PASS"
