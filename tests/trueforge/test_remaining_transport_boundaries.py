"""Local assertions for the remaining N20/N22/N29 integration boundaries.

These tests use loopback servers and explicit no-AWS/no-PostgreSQL test doubles.
They do not represent a connected Gateway, RDS, Daytona, or human-gate run.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from starlette.testclient import TestClient

from preflight.config import Settings
from preflight.server import make_server, serve
from preflight.service import RehearsalService

ROOT = Path(__file__).parents[2]


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
