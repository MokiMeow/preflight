"""Credential-free official SDK HTTP interoperability probe."""
import asyncio
import multiprocessing
import time

from mcp import Client
from mcp.server import MCPServer


def serve():
    server = MCPServer("preflight-probe")

    @server.tool()
    def status() -> dict[str, str]:
        return {"status": "probe_only"}

    server.run(transport="streamable-http", host="127.0.0.1", port=18001)


async def probe():
    async with Client("http://127.0.0.1:18001/mcp") as client:
        tools = await client.list_tools()
        result = await client.call_tool("status", {})
        assert result.structured_content == {"status": "probe_only"}
        print({"tools": len(tools.tools), "structured_content": result.structured_content})


if __name__ == "__main__":
    process = multiprocessing.Process(target=serve)
    process.start()
    try:
        time.sleep(2)
        asyncio.run(probe())
    finally:
        process.terminate()
        process.join()
