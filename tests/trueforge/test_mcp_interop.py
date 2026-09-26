import json
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parents[2]


def unused_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def wait_for_listener(port: int) -> None:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise AssertionError("Python MCP probe did not start")


def test_trueforge_bundled_js_client_calls_python_mcp_2_2_0():
    port = unused_port()
    server = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "scripts/probe_trueforge_mcp_server.py"),
            "--port",
            str(port),
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_listener(port)
        result = subprocess.run(
            [
                "node",
                str(ROOT / "scripts/probe_trueforge_mcp_client.mjs"),
                f"http://127.0.0.1:{port}/mcp",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        observed = json.loads(result.stdout)
        assert observed["ok"] is True
        assert observed["js_mcp_version"] == "1.30.1"
        assert observed["python_mcp_version"] == "2.2.0"
        assert observed["tools"] == ["status"]
        assert observed["structured_content"] == {
            "status": "probe_only",
            "python_mcp_version": "2.2.0",
        }
    finally:
        server.terminate()
        server.wait(timeout=10)
