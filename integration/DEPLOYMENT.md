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

Before reinstalling or upgrading on Windows, stop the owned running service
processes: their executable files can be locked. Restart them after installation.
For the local probe, use `python -m preflight.cli serve` from the locked environment.

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
export PATH=/opt/preflight/node/bin:/usr/local/bin:/usr/bin:/bin
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
They never enter TrueForge instructions or local sandbox code.

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

## Prepare and patch the standalone Linux sandbox

Decision D26 uses TrueForge's installed local Linux fallback. It is automatic in standalone mode
when no row exists at `/api/v1/settings/sandbox-providers`; the settings API itself supports
Daytona, not a synthetic `local` manifest. Install and retain these host dependencies:

- `bubblewrap` (`/usr/bin/bwrap`), `socat` (`/usr/bin/socat`) and `ripgrep`
  (`/usr/local/bin/rg` on the prepared host);
- `/usr/bin/bash` or `/usr/bin/sh`;
- Python 3.12, 3.11 or 3.10 with `venv`; the runtime creates a sandbox-local virtual environment
  and installs `pydantic>=2,<3` through its restricted package-network policy.

The prepared Amazon Linux 2023 host observed `bubblewrap 0.10.0`, `socat 1.7.4.2`, `ripgrep
14.1.1`, `user.max_user_namespaces=15078`, and a successful unprivileged bubblewrap canary. These
are host observations, not portable defaults. Keep `/usr/local/bin` in the TrueForge service PATH
so the startup dependency probe finds `rg`.

Unmodified TrueForge `0.2.1` exposes one process-global Code Mode socket parent to every same-UID
Linux sandbox. Apply the narrow reviewed patch only when the installed files match both exact
baseline hashes. Dry-run first:

```bash
python scripts/patch_trueforge_local_sandbox.py \
  --main-js integration/node_modules/@truefoundry/trueforge/dist/main.js
python scripts/patch_trueforge_local_sandbox.py --apply \
  --main-js integration/node_modules/@truefoundry/trueforge/dist/main.js
```

Expected baseline → patched SHA-256 pairs are:

- `main.js`: `c6902760304c303edec52e2894370be68ca6d679ca20f922a589c6fbc416f9c0`
  → `f1721874969562f995142c5d87a2e3cc75c83d73fbfe061aaa0021d09e922ced`;
- `trueforge-core/dist/core/sandbox/Sandbox.js`:
  `20cbee8c17afc717ca29ef4d1d851833128b05b50856b4164f09947dab41742f`
  → `325b72a1feb6efd7ef0c277320f02b706aefc70fb19160ad86dc98b0bbb80dbe`;
- `trueforge-core/dist/core/sandbox/Sandbox.mjs`:
  `95a9805e69f1176d8189b1bd103b074b6661018653d5a22c6f857db954fc2a4e`
  → `b7c20bc450d66f3cd3b91efaaf235d0877140907e0dfd3e5d2ea93a89530563d`.

Any other input bytes are refused. Restart TrueForge after applying the patch. The journal must say
`Local sandbox fallback is available` with Linux, the expected shell, and Python >=3.10. A prior
host probe selected Python 3.9 and failed on a PEP 604 union in `skill_downloader.py`; that failed
turn is evidence of the compatibility defect, not successful sandbox execution. The patch also
maps a supervisor timeout to the fixed failed-tool result `Local sandbox command timed out`; it
does not infer database rollback or any other business outcome from a process timeout. Public
`sandbox.exec` no longer accepts a caller environment. The native provider admits only its fixed
server-derived Code Mode, trace, skill and Git helper keys; an input such as `BASH_ENV` fails with
`Local sandbox environment key is not permitted` before the host launcher starts.

After restart, require all of the following before saving the product agent:

1. `GET /api/v1/settings/sandbox-providers` returns 404 and
   `GET /api/v1/capabilities` returns `data.sandbox.enabled=true`.
2. A harmless `sandbox` / `exec` turn reports the selected Python and `rg` versions without reading
   environment variables, credentials, other files, processes, network, or MCP tools.
3. Two concurrent sessions prove that each can use its own Code Mode bridge but cannot list, read,
   or connect to the other session's Unix socket. Record only session/tool IDs and pass/fail.
4. Filesystem canaries can write inside the session root but cannot read the Gateway secret or
   write a shared host path. Environment inspection reports variable **names only** and confirms no
   AWS, database, Gateway or Preflight secret names. Never print values.
5. Requests to instance metadata (`169.254.169.254`) and an unallowlisted public host are blocked.
   The allowed PyPI/GitHub domains remain a package/bootstrap capability, not a general egress path.
6. A bounded generated Python call to read-only `get_run` reaches only the current Preflight bridge.
   An attempted Code Mode call to either destructive tool is refused before MCP dispatch. Test each
   direct literal approval separately and leave it pending or have the operator deny it; the coding
   agent never clicks a decision.

Until the two-session test passes under the exact patched hashes, local Code Mode is
`BLOCKED_EXTERNAL`, even when the startup capability says enabled.

## Register the connector and saved agent

1. Create the connector named `preflight` for `http://127.0.0.1:8000/mcp`.
2. Confirm discovery exposes exactly the ten tools in `config/preflight-agent.yaml`.
3. Validate `config/preflight-agent.yaml` against the installed `AgentSpecSchema`. It is JSON and
   therefore valid YAML 1.2; there is no claim that TrueForge imports arbitrary YAML.
4. Validate the configured model/approval policy:

   ```bash
   python scripts/probe_trueforge_config.py config/preflight-agent.yaml
   ```

5. After the patched two-session isolation canary passes, save the agent using the installed UI or API. The observed `0.2.1` create request is
   `{name, description, manifest}`; the template uses only fields present in that schema.
6. Reopen the effective saved configuration. Confirm the enabled list has exactly ten business
   tools and the literal approval list is exactly `apply_to_demo_source` and `cleanup_run`.
7. Test direct gates and Code Mode refusal separately. Stop the deployment if either literal gate
   is lost or generated code can dispatch a destructive tool.

The bootstrap is dry-run by default. `provider-mcp` configures only the exact Gateway alias and
loopback MCP connector. `complete` additionally verifies the absent provider row, sandbox
capability, both patched runtime hashes, ten tools, and the saved agent before it reports success:

```bash
python scripts/configure_trueforge_host.py --stage provider-mcp
python scripts/configure_trueforge_host.py --execute --stage provider-mcp \
  --gateway-secret /var/lib/preflight/gateway.secret.json
python scripts/configure_trueforge_host.py --execute --stage complete \
  --gateway-secret /var/lib/preflight/gateway.secret.json \
  --trueforge-main-js integration/node_modules/@truefoundry/trueforge/dist/main.js
```

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
sandbox run, Preflight business trace, or approval test.

## Native UI connector evidence and resume state

The sanitized local observation is recorded in
[`trueforge-native-connector-evidence.json`](trueforge-native-connector-evidence.json). The native
TrueForge REST API created the `preflight-local-probe` connector in an isolated SQLite database and
discovered exactly the ten Preflight business tools from `http://127.0.0.1:18000/mcp`. Every input
schema was an object with `additionalProperties: false`, every tool exposed an output schema, and
the two literal gate names were present. No MCP tool, agent, model, provider, sandbox, source apply,
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
- real patched local Linux Code Mode execution and two-session bridge isolation;
- Code Mode refusal of both destructive tools and literal source-apply/cleanup pauses through
  separate direct calls;
- denial with no backend apply call, and a separate human-approved request when authorized;
- request logging/cache settings and secret redaction.

Private-host patched sandbox canaries and human approval are connected checks. Keep any unobserved
item `BLOCKED_EXTERNAL`; do not replace it with fixtures or screenshots.
