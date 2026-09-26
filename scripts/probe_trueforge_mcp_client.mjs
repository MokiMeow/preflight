import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import { Client } from "../integration/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js";
import { StreamableHTTPClientTransport } from "../integration/node_modules/@modelcontextprotocol/sdk/dist/esm/client/streamableHttp.js";

const endpoint = process.argv[2] ?? "http://127.0.0.1:18002/mcp";
const packagePath = new URL(
  "../integration/node_modules/@modelcontextprotocol/sdk/package.json",
  import.meta.url,
);
const sdkPackage = JSON.parse(await readFile(packagePath, "utf8"));
const client = new Client({ name: "preflight-trueforge-probe", version: "1.0.0" });
const transport = new StreamableHTTPClientTransport(new URL(endpoint));

try {
  await client.connect(transport);
  const listed = await client.listTools();
  assert.deepEqual(listed.tools.map((tool) => tool.name), ["status"]);
  const called = await client.callTool({ name: "status", arguments: {} });
  assert.deepEqual(called.structuredContent, {
    status: "probe_only",
    python_mcp_version: "2.2.0",
  });
  process.stdout.write(
    `${JSON.stringify({
      ok: true,
      transport: "streamable-http",
      endpoint_scope: "loopback",
      js_mcp_version: sdkPackage.version,
      python_mcp_version: called.structuredContent.python_mcp_version,
      tools: listed.tools.map((tool) => tool.name),
      structured_content: called.structuredContent,
    })}\n`,
  );
} finally {
  await client.close();
}
