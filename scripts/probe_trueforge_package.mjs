import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const root = new URL("../integration/", import.meta.url);
const lock = JSON.parse(await readFile(new URL("package-lock.json", root), "utf8"));
const installed = JSON.parse(
  await readFile(new URL("node_modules/@truefoundry/trueforge/package.json", root), "utf8"),
);
const client = JSON.parse(
  await readFile(new URL("node_modules/@modelcontextprotocol/sdk/package.json", root), "utf8"),
);
const locked = lock.packages["node_modules/@truefoundry/trueforge"];

assert.equal(installed.version, "0.2.1");
assert.equal(locked.version, "0.2.1");
assert.equal(
  locked.integrity,
  "sha512-yrCLD0QOKB/iHcHA6/WHVHEpVZfrSasYjIkZLZ4hiIbi4TXEZFFwVCueYVxzVWNq2OcusG4+BdjZg1mA/1I0iA==",
);
assert.match(installed.engines.node, />=22\.14\.0/);

process.stdout.write(
  `${JSON.stringify({
    ok: true,
    trueforge_version: installed.version,
    node_requirement: installed.engines.node,
    package_integrity: locked.integrity,
    bundled_js_mcp_version: client.version,
  })}\n`,
);
