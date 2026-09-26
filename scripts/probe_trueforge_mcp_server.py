"""Credential-free Python MCP 2.2.0 status server for the TrueForge client probe."""

from __future__ import annotations

import argparse
import importlib.metadata

from mcp.server import MCPServer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18002)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise SystemExit("invalid port")

    server = MCPServer("preflight-trueforge-probe")

    @server.tool()
    def status() -> dict[str, str]:
        return {
            "status": "probe_only",
            "python_mcp_version": importlib.metadata.version("mcp"),
        }

    server.run(transport="streamable-http", host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
