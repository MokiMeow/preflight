import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

import OpenAI from "../integration/node_modules/openai/index.mjs";
import { FinalTextState, ProbeProtocolError, ToolCallState } from "./responses_stream_state.mjs";

const EXPECTED_KEYS = new Set([
  "adapter",
  "api_family",
  "base_url",
  "model",
  "reasoning_effort",
  "api_key_env",
  "timeout_seconds",
]);

class SafeProbeError extends Error {
  constructor(code, exitCode = 2) {
    super(code);
    this.code = code;
    this.exitCode = exitCode;
  }
}

function fail(code, exitCode = 2) {
  throw new SafeProbeError(code, exitCode);
}

function validateConfig(value) {
  if (!value || Array.isArray(value) || typeof value !== "object") fail("ROUTE_CONFIG_INVALID");
  const keys = Object.keys(value);
  if (keys.length !== EXPECTED_KEYS.size || keys.some((key) => !EXPECTED_KEYS.has(key))) {
    fail("ROUTE_CONFIG_INVALID");
  }
  if (value.adapter !== "openai" || value.api_family !== "responses") {
    fail("ROUTE_NOT_RESPONSES");
  }
  if (value.reasoning_effort !== "high") fail("ROUTE_EFFORT_NOT_HIGH");
  if (
    typeof value.model !== "string" ||
    !value.model.toLowerCase().includes("sol") ||
    value.model.toLowerCase().includes("astra") ||
    value.model.startsWith("REPLACE_")
  ) {
    fail("ROUTE_MODEL_INVALID");
  }
  let endpoint;
  try {
    endpoint = new URL(value.base_url);
  } catch {
    fail("ROUTE_ENDPOINT_INVALID");
  }
  if (
    endpoint.protocol !== "https:" ||
    endpoint.username ||
    endpoint.password ||
    endpoint.search ||
    endpoint.hash ||
    value.base_url.startsWith("REPLACE_")
  ) {
    fail("ROUTE_ENDPOINT_INVALID");
  }
  if (
    typeof value.api_key_env !== "string" ||
    !/^PREFLIGHT_[A-Z0-9_]{1,63}$/.test(value.api_key_env)
  ) {
    fail("ROUTE_CREDENTIAL_ENV_INVALID");
  }
  if (!Number.isInteger(value.timeout_seconds) || value.timeout_seconds < 5 || value.timeout_seconds > 60) {
    fail("ROUTE_TIMEOUT_INVALID");
  }
  return value;
}

async function loadConfig(path) {
  let raw;
  try {
    raw = await readFile(path, "utf8");
  } catch (error) {
    if (error?.code === "ENOENT") fail("ROUTE_CONFIG_MISSING", 4);
    fail("ROUTE_CONFIG_UNAVAILABLE", 4);
  }
  if (Buffer.byteLength(raw, "utf8") > 16_384) fail("ROUTE_CONFIG_TOO_LARGE");
  try {
    return validateConfig(JSON.parse(raw));
  } catch (error) {
    if (error instanceof SafeProbeError) throw error;
    fail("ROUTE_CONFIG_INVALID");
  }
}

async function consume(stream, state) {
  for await (const event of stream) state.accept(event);
  return state.finish();
}

function providerFailure(error) {
  if (error instanceof ProbeProtocolError) return new SafeProbeError(error.code, 5);
  if (error?.status === 401 || error?.status === 403) {
    return new SafeProbeError("PROVIDER_AUTH_REFUSED", 6);
  }
  if (error?.status === 429) return new SafeProbeError("PROVIDER_RATE_LIMITED", 7);
  if (typeof error?.status === "number" && error.status >= 500) {
    return new SafeProbeError("PROVIDER_UNAVAILABLE", 8);
  }
  return new SafeProbeError("PROVIDER_REQUEST_FAILED", 8);
}

async function execute(config) {
  const apiKey = process.env[config.api_key_env];
  if (typeof apiKey !== "string" || apiKey.length === 0) fail("PROVIDER_CREDENTIAL_MISSING", 4);
  const client = new OpenAI({
    apiKey,
    baseURL: config.base_url,
    timeout: config.timeout_seconds * 1000,
    maxRetries: 0,
  });
  try {
    const initial = await client.responses.create({
      model: config.model,
      reasoning: { effort: "high" },
      input: "Call status exactly once, then summarize the returned status in one sentence.",
      tools: [
        {
          type: "function",
          name: "status",
          description: "Return the fixed harmless compatibility-probe status.",
          parameters: { type: "object", properties: {}, additionalProperties: false },
          strict: true,
        },
      ],
      tool_choice: { type: "function", name: "status" },
      stream: true,
    });
    const tool = await consume(initial, new ToolCallState());
    const continued = await client.responses.create({
      model: config.model,
      reasoning: { effort: "high" },
      previous_response_id: tool.responseId,
      input: [
        {
          type: "function_call_output",
          call_id: tool.callId,
          output: JSON.stringify({ status: "probe_only" }),
        },
      ],
      stream: true,
    });
    const final = await consume(continued, new FinalTextState());
    return {
      ok: true,
      state: "CONNECTED_VERIFIED",
      api_family: "responses",
      adapter: "openai",
      model: config.model,
      reasoning_effort: "high",
      initial_response_id: tool.responseId,
      tool_call_id: tool.callId,
      continued_response_id: final.responseId,
      tool_call_linked: true,
      final_text_present: true,
      final_text_sha256: createHash("sha256").update(final.text, "utf8").digest("hex"),
    };
  } catch (error) {
    throw providerFailure(error);
  }
}

async function main() {
  const args = process.argv.slice(2);
  const executeRequested = args.includes("--execute");
  const configArg = args.find((value) => value.startsWith("--config="));
  const configPath = configArg?.slice("--config=".length) ?? "config/runtime-route.local.json";
  try {
    const config = await loadConfig(configPath);
    if (!executeRequested) {
      process.stdout.write(
        `${JSON.stringify({
          ok: false,
          state: "NOT_RUN",
          error_code: "EXPLICIT_EXECUTE_REQUIRED",
          api_family: "responses",
          adapter: "openai",
          model: config.model,
          reasoning_effort: "high",
        })}\n`,
      );
      process.exitCode = 4;
      return;
    }
    process.stdout.write(`${JSON.stringify(await execute(config))}\n`);
  } catch (error) {
    const safe =
      error instanceof SafeProbeError ? error : new SafeProbeError("PROBE_INTERNAL_ERROR", 9);
    process.stdout.write(
      `${JSON.stringify({ ok: false, state: "BLOCKED_EXTERNAL", error_code: safe.code })}\n`,
    );
    process.exitCode = safe.exitCode;
  }
}

await main();
