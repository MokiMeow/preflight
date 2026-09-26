"""N21 local HTTP MCP responsiveness while the real mutation lock is held.

This is a SQLite and loopback fault simulation. It makes no PostgreSQL, AWS,
provider, Daytona, source-apply, or rollback claim.
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import json
import multiprocessing
import os
import socket
import subprocess
import time
from pathlib import Path
from uuid import uuid4

from preflight.config import Settings
from preflight.models import PreflightError
from preflight.service import RehearsalService
from preflight.storage import utc_now

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


def _create_baselined_run(state_dir: Path) -> tuple[str, str]:
    service = RehearsalService(Settings(state_dir=state_dir), restart=False)
    sql = (ROOT / "fixtures/good.sql").read_bytes()
    contract = json.loads((ROOT / "config/contract.example.json").read_text(encoding="utf-8"))
    candidate = service.call(
        "register_candidate",
        {
            "request_id": str(uuid4()),
            "sql_utf8_b64": base64.b64encode(sql).decode("ascii"),
            "expected_migration_sha256": hashlib.sha256(sql).hexdigest(),
            "contract": contract,
            "operator_id": "n21-http-local",
        },
    )
    assert candidate["ok"] is True
    candidate_id = candidate["data"]["candidate_id"]
    run_id = str(uuid4())
    service.store.create_run(
        {
            "run_id": run_id,
            "candidate_id": candidate_id,
            "source_instance_id": "n21-local-source",
            "database_name": "preflight_demo",
            "snapshot_id": "n21-local-snapshot",
            "clone_instance_id": "n21-local-clone",
            "created_at": utc_now(),
        }
    )
    for old, new in (
        ("REGISTERED", "SNAPSHOTTING"),
        ("SNAPSHOTTING", "RESTORING"),
        ("RESTORING", "READY"),
        ("READY", "BASELINED"),
    ):
        service.store.transition(run_id, old, new)
    service.executor.shutdown(wait=True)
    return run_id, candidate_id


def _serve_with_held_apply(
    state_dir: str,
    port: int,
    entered: multiprocessing.synchronize.Event,
    release: multiprocessing.synchronize.Event,
    handler_exited: multiprocessing.synchronize.Event,
    executions: multiprocessing.sharedctypes.Synchronized,
) -> None:
    from preflight.server import make_server

    service = RehearsalService(Settings(state_dir=Path(state_dir)), restart=False)

    def held_apply(request):
        # service.call has acquired the real per-run mutation lock before this
        # handler is entered. The event therefore coordinates on the actual lock.
        with executions.get_lock():
            executions.value += 1
        service.store.transition(str(request.run_id), "BASELINED", "MIGRATING")
        entered.set()
        try:
            if not release.wait(10):
                raise PreflightError("LOCAL_HELD_APPLY_TIMEOUT")
            raise PreflightError("LOCAL_HELD_APPLY_RELEASED")
        finally:
            handler_exited.set()

    service.apply_to_clone = held_apply
    make_server(service).run(
        transport="streamable-http", host="127.0.0.1", port=port
    )


def _node_env(port: int, **values: str) -> dict[str, str]:
    return {**os.environ, "N21_ENDPOINT": f"http://127.0.0.1:{port}/mcp", **values}


def test_n21_http_status_remains_typed_and_responsive_while_mutation_lock_is_held(tmp_path):
    run_id, candidate_id = _create_baselined_run(tmp_path)
    port = _unused_port()
    entered = multiprocessing.Event()
    release = multiprocessing.Event()
    handler_exited = multiprocessing.Event()
    executions = multiprocessing.Value("i", 0)
    server = multiprocessing.Process(
        target=_serve_with_held_apply,
        args=(str(tmp_path), port, entered, release, handler_exited, executions),
    )
    server.start()
    mutation = None
    try:
        _wait_for_listener(port)
        mutation_script = """
import { Client } from './integration/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import { StreamableHTTPClientTransport } from './integration/node_modules/@modelcontextprotocol/sdk/dist/esm/client/streamableHttp.js';
const client = new Client({ name: 'n21-held-mutator', version: '1.0.0' });
await client.connect(new StreamableHTTPClientTransport(new URL(process.env.N21_ENDPOINT)));
const result = await client.callTool({
  name: 'apply_to_clone',
  arguments: {
    request_id: process.env.N21_MUTATION_REQUEST,
    run_id: process.env.N21_RUN_ID,
    candidate_id: process.env.N21_CANDIDATE_ID,
  },
});
await client.close();
process.stdout.write(JSON.stringify(result.structuredContent));
"""
        mutation = subprocess.Popen(
            ["node", "--input-type=module", "--eval", mutation_script],
            cwd=ROOT,
            env=_node_env(
                port,
                N21_MUTATION_REQUEST=str(uuid4()),
                N21_RUN_ID=run_id,
                N21_CANDIDATE_ID=candidate_id,
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert entered.wait(5), "controlled apply did not enter while holding the run lock"
        assert executions.value == 1

        # The MCP app does not expose an application health route. This only
        # checks that an unrelated HTTP request remains prompt.
        health_started = time.monotonic()
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
        connection.request("GET", "/health")
        health = connection.getresponse()
        health.read()
        connection.close()
        assert health.status == 404
        assert time.monotonic() - health_started < 1

        status_script = """
import { Client } from './integration/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import { StreamableHTTPClientTransport } from './integration/node_modules/@modelcontextprotocol/sdk/dist/esm/client/streamableHttp.js';
const client = new Client({ name: 'n21-status-observer', version: '1.0.0' });
await client.connect(new StreamableHTTPClientTransport(new URL(process.env.N21_ENDPOINT)));
const pingStarted = performance.now();
const ping = await client.ping();
const pingElapsedMs = performance.now() - pingStarted;
const started = performance.now();
const result = await client.callTool({
  name: 'get_run',
  arguments: { request_id: process.env.N21_STATUS_REQUEST, run_id: process.env.N21_RUN_ID },
});
await client.close();
process.stdout.write(JSON.stringify({
  ping,
  ping_elapsed_ms: pingElapsedMs,
  elapsed_ms: performance.now() - started,
  result,
}));
"""
        observed = subprocess.run(
            ["node", "--input-type=module", "--eval", status_script],
            cwd=ROOT,
            env=_node_env(
                port, N21_STATUS_REQUEST=str(uuid4()), N21_RUN_ID=run_id
            ),
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        assert observed.returncode == 0, observed.stderr or observed.stdout
        decoded = json.loads(observed.stdout)
        assert decoded["ping"] == {}
        assert decoded["ping_elapsed_ms"] < 1_000
        assert decoded["elapsed_ms"] < 1_000
        assert decoded["result"]["isError"] is False
        envelope = decoded["result"]["structuredContent"]
        assert envelope["ok"] is True
        assert envelope["run_id"] == run_id
        assert envelope["state"] == envelope["data"]["phase"] == "MIGRATING"
        assert entered.is_set()
        assert executions.value == 1

        # Cancel only the client delivery. The controlled handler is released
        # once, and no observer call retries the mutation.
        mutation.terminate()
        mutation.wait(timeout=5)
        release.set()
        assert handler_exited.wait(5)
        time.sleep(0.1)
        assert executions.value == 1
    finally:
        release.set()
        if mutation is not None and mutation.poll() is None:
            mutation.terminate()
            mutation.wait(timeout=5)
        server.terminate()
        server.join(timeout=5)

    service = RehearsalService(Settings(state_dir=tmp_path), restart=False)
    try:
        durable = service.store.get_run(run_id)
        assert durable["phase"] == "MIGRATING"
        assert durable["revision"] == 5
        assert executions.value == 1
    finally:
        service.executor.shutdown(wait=True)
