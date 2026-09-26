# Private TrueForge deployment

These instructions describe the installed `@truefoundry/trueforge@0.2.1` package that was
probed for this repository. They do not authorize cloud spend, source writes, cleanup, or either
human approval decision.

## Verified package boundary

- Node requirement: `>=22.14.0` (locally probed with Node `v24.11.1`).
- Registry integrity: `sha512-yrCLD0QOKB/iHcHA6/WHVHEpVZfrSasYjIkZLZ4hiIbi4TXEZFFwVCueYVxzVWNq2OcusG4+BdjZg1mA/1I0iA==`.
- CLI: `trueforge --port <n>`; the installed CLI has no host-address flag.
- The observed standalone listener was loopback-only (`localhost`, IPv6 `::1` on the Windows
  probe host). `127.0.0.1` did not reach that Windows listener. Use `localhost` for the UI tunnel
  and verify the actual listener on the deployment host.
- Standalone mode uses SQLite, disables browser login, and is explicitly described by the package
  as local-only. It must remain behind an SSH tunnel; never publish its port.
- The installed OpenAPI schema is at `/api/v1/openapi.json`; interactive docs are at
  `/api/v1/docs`.

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
npx trueforge --port 8790
```

Keep the process on the private host and access it through a tunnel:

```bash
ssh -L 8790:localhost:8790 operator@PRIVATE_HOST
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
