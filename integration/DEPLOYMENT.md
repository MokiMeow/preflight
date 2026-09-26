# Private TrueForge deployment

These instructions describe the installed `@truefoundry/trueforge@0.2.1` package that was
probed for this repository. They do not authorize cloud spend, source writes, cleanup, or either
human approval decision.

## Install and validate Preflight

From the exact integrated commit:

```bash
uv sync --locked
cd integration
npm ci --ignore-scripts --no-audit --no-fund
cd ..
```

Copy `config/settings.example.json` to the ignored `config/settings.local.json`. Populate only
authorized nonsecret policy values and Secrets Manager ARN references. Keep source apply disabled
until its demonstration is authorized, then run:

```bash
uv run preflight doctor --json
uv run preflight serve
```

The service binds `127.0.0.1` on the configured port (default 8000). A successful process start is
not connected cloud proof; preserve the doctor's `NOT_RUN` and `NOT_OBSERVED` fields.

## Verified package boundary

- Node requirement: `>=22.14.0` (locally probed with Node `v24.11.1`).
- Registry integrity: `sha512-yrCLD0QOKB/iHcHA6/WHVHEpVZfrSasYjIkZLZ4hiIbi4TXEZFFwVCueYVxzVWNq2OcusG4+BdjZg1mA/1I0iA==`.
- CLI: `trueforge --port <n>`; the installed CLI has no host-address flag.
- The default `HOST=localhost` probe bound IPv6 `::1` on Windows. The successful isolated native
  connector proof explicitly set `HOST=127.0.0.1`; verify the actual listener on deployment.
- Standalone mode uses SQLite, disables browser login, and is explicitly described by the package
  as local-only. It must remain behind an SSH tunnel; never publish its port.
- The installed OpenAPI schema is at `/api/v1/openapi.json`; interactive docs are at
  `/api/v1/docs`.
- On the first Windows start after the locked install, the CLI was silent while it awaited the
  bundled `main.js` dependency graph: the isolated SQLite file appeared 63 seconds after process
  creation. A separate cold reproduction took 52 seconds to create SQLite and 54 seconds to answer
  HTTP; a warmed start took 2 seconds. The shipped `better-sqlite3@13.0.3` `win32-x64` prebuild
  loaded successfully with SQLite `3.53.4`, so the missing banner was not a missing native addon.
  Use a bounded readiness check against `/api/v1/openapi.json` before diagnosing the first silent
  minute as a permanent hang. The lower-level Windows filesystem/security-scanner contribution was
  not isolated and must not be stated as the cause.

Install exactly the lockfile and rerun the package probe:

```bash
cd integration
npm ci --ignore-scripts --no-audit --no-fund
cd ..
node scripts/probe_trueforge_package.mjs
```

The install intentionally disables package lifecycle scripts. Do not replace the exact version
with `latest` for the demonstration.

## Start the private demo UI

On the private host, with the repository checkout and runtime settings already present:

```bash
cd integration
export HOST=127.0.0.1
export OUTBOUND_URL_ALLOWED_HOSTS='["127.0.0.1"]'
npx trueforge --port 8790
```

TrueForge `0.2.1` enables its outbound URL guard by default and blocks `127.0.0.0/8` unless the
exact connector host is allowlisted. Without the line above, creating the documented
`http://127.0.0.1:8000/mcp` connector returns `400 Outbound URL blocked`. Keep
`NETWORK_POLICY_ENABLED` at its default `true`; do not disable the guard or add a broad host range.
Set the allowlist only in the private TrueForge process environment, not in a global or personal
profile.

Keep the process on the private host and access it through a tunnel:

```bash
ssh -L 8790:127.0.0.1:8790 operator@PRIVATE_HOST
```

Open `http://localhost:8790` locally. Before relying on the tunnel, inspect the deployment host's
listener and confirm it is loopback-only. A firewall is additional containment; it is not a reason
to bind an unauthenticated standalone UI publicly.

The Preflight service runs separately on the same host and exposes its Streamable HTTP connector
at `http://127.0.0.1:8000/mcp`. Its database and AWS credentials remain in the service process.
They never enter TrueForge instructions or Daytona.

## Configure the model route

The installed `0.2.1` OpenAPI schema confirms these relevant provider fields:

- provider type `openai`: `auth`, `models`, and optional `base_url` (the core adapter uses the
  Responses API);
- provider type `truefoundry`: `models` and required `base_url` (the compatible-provider path is
  distinct from the OpenAI Responses adapter);
- agent model: `name` plus optional `params`, including `reasoning_effort`.

Use Settings in the private UI. Copy the team-scoped Gateway base URL and upstream model ID from
the real Gateway Playground snippet; do not construct an endpoint path. Select a Sol model that
actually completes the Responses tool-call probe with `reasoning_effort: high`. The intended
starting route is GPT-6 Sol/high, with GPT-5.6 Sol/high only after its own successful probe. Runtime
Astra is disabled. Do not add `temperature`, `top_p`, or guessed provider fields.

No provider credential or funded route was available in the local probe. A registry install or a
catalog entry is not evidence of a working model response. Record the actual adapter, API family,
resolved model, effort, tool-call ID, request ID when exposed, and the final tool-result roundtrip
only after the authorized route succeeds.

The standalone credential-safe probe uses an ignored route file and never prints the endpoint or
credential. Copy `config/runtime-route.example.json` to `config/runtime-route.local.json`, replace
the placeholders only with the authorized Gateway Playground base URL and exact Sol model ID, and
leave effort at `high`. Put the key in the environment variable named by that local file.

Validation alone makes no provider request and exits `NOT_RUN`:

```bash
node scripts/probe_gateway_responses.mjs
```

When provider credit/access is confirmed, explicitly authorize the harmless paid probe invocation:

```bash
node scripts/probe_gateway_responses.mjs --execute
```

It requires the model to stream one `status` function call, validates its complete JSON arguments and
stable call ID, submits one fixed `function_call_output` linked by that ID, then requires a continued
final response. Output contains IDs and a final-text digest, never prompts, provider bodies, headers,
endpoint, key, or final model prose. HTTP/auth/rate/stream errors collapse to fixed safe codes. Do not
use a Chat Completions `none` fallback unless the operator separately chooses and records that route;
it is outside this Sol/high Responses probe.

## Configure Daytona

Configure Daytona through TrueForge's supported sandbox-provider settings. The local Windows
startup probe reported that TrueForge's local sandbox fallback supports macOS and Linux only; it
did not prove Daytona access. Do not add a separate Daytona SDK or put AWS/database credentials in
the sandbox.

Before the connected gate can pass, record a real Daytona execution ID and a meaningful bounded
program that calls typed Preflight tools through the harness bridge. Read-only observation may poll
`get_run` with a monotonic deadline and bounded backoff. It must never call
`apply_to_demo_source` or `cleanup_run` from an automatic loop.

## Register the connector and saved agent

1. Create the connector named `preflight` for `http://127.0.0.1:8000/mcp`.
2. Confirm discovery exposes exactly the ten tools in `config/trueforge-agent.example.json`.
3. Copy the example config and replace only the model placeholder with the verified TrueForge
   model resource name.
4. Validate the configured copy without `--template`:

   ```bash
   python scripts/probe_trueforge_config.py /path/to/configured-agent.json
   ```

5. Save/import the agent using the installed UI or API. The observed `0.2.1` create request is
   `{name, description, manifest}`; the template uses only fields present in that schema.
6. Reopen the effective saved configuration. Confirm the enabled list has exactly ten business
   tools and the literal approval list is exactly `apply_to_demo_source` and `cleanup_run`.
7. Test direct and Code Mode calls separately. Stop the deployment if either literal gate is lost.

The coding agent must never click Allow or Deny for the operator. Source apply and cleanup are two
separate human decisions. The service still rechecks hashes, state, backup, target, and drift after
the UI pause.

## Local MCP interoperability probe

The credential-free probe starts one Python MCP `2.2.0` status tool and calls it with the actual
JavaScript MCP client bundled under TrueForge (`1.30.1`):

```bash
python scripts/probe_trueforge_mcp_server.py --port 18002
node scripts/probe_trueforge_mcp_client.mjs http://127.0.0.1:18002/mcp
```

The expected output identifies `probe_only`, both observed SDK versions, Streamable HTTP, and the
single `status` tool. This proves local wire interoperability only. It is not a Gateway response,
Daytona run, Preflight business trace, or approval test.

## Native UI connector evidence and resume state

The sanitized local observation is recorded in
[`trueforge-native-connector-evidence.json`](trueforge-native-connector-evidence.json). The native
TrueForge REST API created the `preflight-local-probe` connector in an isolated SQLite database and
discovered exactly the ten Preflight business tools from `http://127.0.0.1:18000/mcp`. Every input
schema was an object with `additionalProperties: false`, every tool exposed an output schema, and
the two literal gate names were present. No MCP tool, agent, model, provider, Daytona, source apply,
cleanup, or human decision ran during this observation.

To resume this local proof without touching personal TrueForge state:

1. Start Preflight with the ignored `config/ui-probe.local.json` and its isolated
   `var/ui-probe-service` state. Require source `NONE`, cloud/apply disabled, and no credential
   values.
2. Start TrueForge on `127.0.0.1:18790` with `SQLITE_PATH` pointing to the isolated
   `var/trueforge-probe.sqlite`, `APP_DATA_DIR_SUFFIX=preflight-probe`, and the exact loopback
   allowlist above. Do not export these variables through a global or personal profile.
3. Wait up to 90 seconds for `GET http://127.0.0.1:18790/api/v1/openapi.json` to return 200 on a
   cold Windows start. A missing early banner is not readiness evidence.
4. Open Connectors in the native UI and inspect `preflight-local-probe`, or call read-only
   `GET /api/v1/mcp-servers/preflight-local-probe/tools`. Do not invoke either literal gate.
5. Stop only the processes whose command, port, and isolated paths match this probe. TrueForge
   `0.2.1` exposes no connector-delete route in the observed OpenAPI schema; remove the isolated
   SQLite files only after stopping TrueForge when the local evidence is no longer needed.

The actual Windows resume commands use process-scoped environment variables. Run each server in
its own repository-root PowerShell; do not copy these variables into a profile:

```powershell
# Shell 1: isolated, fail-closed Preflight service on port 18000.
if (-not (Test-Path 'config/ui-probe.local.json')) {
  Copy-Item 'config/ui-probe.example.json' 'config/ui-probe.local.json'
}
$env:PREFLIGHT_SETTINGS = (Resolve-Path 'config/ui-probe.local.json').Path
uv run --locked preflight doctor --json
uv run --locked preflight serve
```

```powershell
# Shell 2: isolated native TrueForge UI/API on port 18790.
$env:HOST = '127.0.0.1'
$env:SQLITE_PATH = (Join-Path (Get-Location) 'var/trueforge-probe.sqlite')
$env:APP_DATA_DIR_SUFFIX = 'preflight-probe'
$env:OUTBOUND_URL_ALLOWED_HOSTS = '["127.0.0.1"]'
$env:NODE_ENV = 'production'
node integration/node_modules/@truefoundry/trueforge/dist/cli.js --port 18790
```

In a third shell, perform only the readiness and schema observations:

```powershell
Invoke-WebRequest 'http://127.0.0.1:18790/api/v1/openapi.json' -UseBasicParsing -TimeoutSec 10
Invoke-WebRequest 'http://127.0.0.1:18790/api/v1/mcp-servers/preflight-local-probe/tools' -UseBasicParsing -TimeoutSec 20
```

## Connected acceptance still required

The deployment is connected-verified only after all of these are observed and sanitized:

- streamed Responses arguments, stable tool-call ID, structured tool result, and final answer;
- exact effective Sol model and effort on the authorized Gateway route;
- actual private Preflight connector schemas and result shape;
- real Daytona Code Mode execution;
- literal source-apply and cleanup pauses through direct and Code Mode calls;
- denial with no backend apply call, and a separate human-approved request when authorized;
- request logging/cache settings and secret redaction.

Provider credits/access, Daytona credentials/quota, private host deployment, and human approval were
not available to this local task. Those checks remain `BLOCKED_EXTERNAL`; do not replace them with
fixtures or screenshots.
