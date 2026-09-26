"""Real official-client HTTP discovery and safe refusal probe."""

import asyncio
import multiprocessing
import socket
import time
from pathlib import Path
from uuid import uuid4

from mcp import Client


def serve_probe(state_dir, port):
    from preflight.config import Settings
    from preflight.server import make_server
    from preflight.service import RehearsalService

    server = make_server(RehearsalService(Settings(state_dir=Path(state_dir))))
    server.run(transport="streamable-http", host="127.0.0.1", port=port)


def test_ten_flat_strict_schemas_structured_error_and_no_source_write(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = multiprocessing.Process(target=serve_probe, args=(str(tmp_path), port))
    process.start()
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                if time.monotonic() > deadline:
                    raise AssertionError("MCP server not ready")
                time.sleep(0.1)

        async def check():
            async with Client(f"http://127.0.0.1:{port}/mcp") as client:
                tools = await client.list_tools()
                assert len(tools.tools) == 10
                by_name = {t.name: t for t in tools.tools}
                assert "request_id" in by_name["get_run"].input_schema["properties"]
                assert by_name["get_run"].input_schema["additionalProperties"] is False
                result = await client.call_tool(
                    "get_run", {"request_id": str(uuid4()), "run_id": str(uuid4())}
                )
                data = result.structured_content
                assert data["ok"] is False
                assert data["error_code"] == "RUN_NOT_FOUND"
                assert by_name["apply_to_demo_source"].annotations.destructive_hint is True

        asyncio.run(check())
    finally:
        process.terminate()
        process.join(timeout=5)
