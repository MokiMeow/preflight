# 04 — Cloud, credentials and deployment runbook

This is the executable build procedure to implement, not evidence that resources already exist. Use only the team's explicitly authorized AWS account and synthetic database. Defaults/examples are not authorization to spend. Current AWS/PostgreSQL references are in [08](08_RESEARCH.md).

## 1. Minimum prerequisites and discovery

The cloud lane reads `config/operator-inputs.local.json`, the existing authenticated AWS context and nonsecret environment. Ask once for genuinely unavailable items; do not ask the user to manually supply an ID that an authorized describe call can discover.

Required decisions are account/region, source identifier or create permission, database name, resource ceilings, budget authorization, operator identity label, SSH access policy, and whether source apply may later be enabled. Network/subnet/SG/secret IDs may initially be unknown and become bootstrap outputs. Never paste credentials into the task ledger. The approved operator JSON is authoritative for account/source/resource policy. Bootstrap may populate its discovered identifiers and singleton source allowlist only from the approved plan and verified AWS results. Empty environment values are treated as unset; a nonempty environment value that conflicts with that policy is an error, not a silent override. This avoids asking the operator to type the same source/account twice.

Read-only discovery commands that can run once the AWS CLI is actually configured include:

```bash
aws sts get-caller-identity
aws configure get region
aws rds describe-db-instances --db-instance-identifier "$PREFLIGHT_SOURCE_INSTANCE_ID"
aws rds describe-db-engine-versions --engine postgres
aws rds describe-orderable-db-instance-options --engine postgres --engine-version "$PREFLIGHT_POSTGRES_ENGINE_VERSION"
```

These are examples with **operator/discovery-provided values**, not fabricated account settings. Use the approved region explicitly in the implementation. Verify caller account against the configured allowlist before every destructive path; do not assume the current shell profile is the intended account.

Select PostgreSQL 18/pglast 8.4 for a supported new source, or PostgreSQL 17/pglast 7.18 for an existing supported source. Use the actual returned minor version and compatible instance options. Keep test PostgreSQL on the same major. No latest-engine upgrade or source conversion is authorized by this plan.

## 2. Bounded resource plan

Prefer reusing existing safe demo infrastructure. For new infrastructure, the agent's `infra/bootstrap.py` must have **plan** and **apply** modes, explicit account/region verification, a saved plan digest and operator confirmation before billable creation. It creates infrastructure during the event, not as part of this startup archive.

| Resource | Purpose / proposed sizing policy | Boundary |
|---|---|---|
| One Linux EC2 host | x86-64 instance with enough memory for TrueForge + Python; propose a modest supported 4 GiB class and verify current cost | A proposal, not a performance guarantee or a fixed required SKU |
| One owned RDS PostgreSQL source | Small supported instance class, encrypted storage, one synthetic DB with 1,000 rows | No third-party production or account-wide database discovery |
| Run-owned clone instances | Normally one active clone; second only within explicitly approved cap for separate testing | Never unlimited clones per retry |
| Run-owned snapshots | Per-run recovery/provenance; retain pre-apply snapshot after source mutation | Tags do not grant automatic deletion |
| VPC/subnets/security groups | Host-to-private-RDS path; reuse where safe | No broad shared-network modification |
| Named Secrets Manager entries | Source-read and migration-role secrets | Only named ARNs are exposed to the runtime IAM policy |
| Persistent host storage | Separate TrueForge and Preflight state/report directories | Not an ephemeral container filesystem |

Record selected class/storage/region, observed current pricing source or estimate status, approved spend ceiling, count caps and resource owner. Budget alarms are useful but are **not** an immediate hard stop on cloud charges. The service's count limits and explicit cleanup decisions prevent uncontrolled provisioning. Do not promise sponsor credits, a free tier or a fixed total bill.

## 3. Network layout

A straightforward controlled-demo setup is an EC2 host in a subnet with outbound HTTPS and a restricted SSH entry point, with RDS source and clone in private DB subnets in the same VPC. A DB subnet group must satisfy the actual RDS availability-zone requirements. Do not put the RDS endpoint on the public internet to accommodate Daytona; Daytona calls through the harness, not through database networking.

| Security group | Inbound | Outbound / notes |
|---|---|---|
| EC2 service host | SSH 22 from the operator's verified current IP/CIDR only; no 8000/8790 rule | Required HTTPS to model/sandbox/AWS/package services; DB 5432 to the source/clone groups; necessary DNS through the VPC resolver |
| RDS source | PostgreSQL 5432 from the EC2 service SG only | Restrict application/external integration routes; no traffic from a public CIDR |
| RDS clone | PostgreSQL 5432 from the EC2 service SG only | No outbound application-integration access; no inbound application servers |

Use SG references where supported instead of private IPs that may change. Inspect existing permissive rules rather than merely adding a restrictive rule beside `0.0.0.0/0`. Venue Wi-Fi/hotspot changes may change the operator IP; update the narrow SSH rule deliberately. Do not temporarily expose the app/MCP publicly “for the demo.” A team-operated SSM path is an alternative only when already configured and documented; it is not required by this kit.

From the operator machine, the normal UI path is a local forward:

```bash
ssh -i <operator-private-key-path> -L 8790:127.0.0.1:8790 <os-user>@<approved-ec2-address>
```

Replace placeholders from actual setup; never commit the private key. Forward 8000 only for an explicitly authorized local diagnostic when needed, not to make a public MCP endpoint. Keep the running service bound to `127.0.0.1`.

## 4. Bootstrap identity versus runtime identity

Bootstrap can create the approved host/network/source/secrets and DB roles. Those privileges are **not** inherited by the agent or runtime service. Use an EC2 instance profile for runtime AWS calls, not a copied developer AWS access key. Configure short-lived operator access where available.

The runtime policy is generated for the actual account, region, source ARN, run naming/tagging scope and named secret ARNs. Use AWS's service-authorization reference to verify the resource/condition support of each action; do not invent an IAM condition that AWS ignores. Avoid account-wide administrator/RDS full access. Document any describe/list action that AWS requires on `*` rather than disguising that as tightly resource-scoped.

| Runtime capability | Intended AWS actions | Required guard |
|---|---|---|
| Inspect source/clone | RDS DescribeDBInstances, relevant snapshot describes | Service-level account/source/run allowlist in addition to IAM |
| Create recovery snapshot | CreateDBSnapshot, AddTagsToResource where needed | Known source, predetermined name, request/run owner tags, count cap |
| Restore separate clone | RestoreDBInstanceFromDBSnapshot | Known run snapshot, new instance only, explicit subnet/SG/private settings |
| Verify ownership | ListTagsForResource and describe calls | Full run UUID, project and owner tags plus exact stored ID/ARN |
| Delete owned clone/snapshot | DeleteDBInstance, DeleteDBSnapshot | Scoped ARNs/tag conditions where supported; service refuses source and unowned resources |
| Fetch DB credentials | Secrets Manager GetSecretValue | Exact read/writer secret ARNs only; no secret enumeration capability |
| Encrypted resources | Necessary KMS permissions only if customer-managed keys require them | Actual key ARNs and documented service grants; no blanket `kms:*` |

Creating service-linked roles or attaching IAM policies is bootstrap work, not a runtime permission. Verify actual IAM policy behavior using safe reads, permitted creation on the synthetic source and negative service tests. IAM simulation alone does not establish that the full AWS operation will succeed. If a restore fails for KMS/role/subnet reasons, inspect the real error; do not add `AdministratorAccess` as a repair.

## 5. Database roles and synthetic seed

Bootstrap owns the synthetic setup. Create a non-superuser migration role that owns only the demo tables and can perform the permitted ALTER/UPDATE operations. Create a separate source-read login with schema USAGE and SELECT only on the declared fixture tables. Provision these logins and their real named secrets during host/source bootstrap so connection-only deployment checks can run before table seeding. Grant table-specific privileges when the fixture tables are later created; do not require a missing fixture table for a connection-only readiness probe. The migration role and data are included in the snapshot, so the writer can operate on the clone without receiving a broader master credential.

Store read and migration credentials in separate named Secrets Manager entries. The Preflight process can retrieve the writer for clone work, but a source-writer connection factory is reachable only through the gated apply use case. The model, Daytona, report renderer and read-only source tool never receive these secrets. Remove bootstrap/master credentials from runtime environment and working directories once setup is complete.

Seed exactly 1,000 reproducible synthetic customers, with a fixed random seed where randomness is used. Use a fixed UTC timestamp range, predictable integer IDs and unmistakably synthetic email addresses under an example domain. Do not generate real names/addresses or ingest customer dumps. Setup/reset must be explicit, logged and separated from runtime rehearsal; a hidden reset would invalidate a “source unchanged” demonstration.

Do not grant rds_superuser, extension creation, FDW access or general schema ownership to the runtime role. Check for triggers, RLS, rules, partitions/inheritance and external references rather than assuming a restored instance is inert. The v1 supported object policy is in [02](02_CONTRACTS_AND_SAFETY.md).

## 6. PostgreSQL TLS

Use the current AWS RDS CA bundle obtained from the official trust store, stored at a configured host path. Verify the endpoint certificate and hostname (`sslmode=verify-full`), not merely encrypted-but-unverified transport. Connect using the actual RDS DNS endpoint, not an invented alias whose certificate cannot validate. Do not disable validation when a connection fails; check CA, host and clock.

The local disposable PostgreSQL harness may use explicitly labeled local credentials and local TLS/test settings. Those settings must not be selected for RDS mode. Tests must reject RDS mode with `sslmode=disable`, source/clone endpoint equality or an arbitrary model-provided host.

## 7. Snapshot and restore operation

Persist intent first. Generate deterministic names such as `preflight-<run-short-id>-snap` and `preflight-<run-short-id>-clone`, validating RDS identifier length/character rules. Full UUID, project, owner and expiry metadata live in tags. A short-name collision is verified against full tags and fails closed if unrelated.

Snapshot the **entire RDS instance**, not just the database. The owned source must contain synthetic data only. CreateDBSnapshot then describe until `available`. Save snapshot ARN/ID/source association/creation time and safe request IDs.

RestoreDBInstanceFromDBSnapshot must be given the new identifier and recorded snapshot, compatible approved instance class, explicit DB subnet group, explicit VPC SG IDs, `PubliclyAccessible=False` and ownership tags. Set clone deletion protection deliberately for the cleanup policy; never modify the source's deletion protection as a side effect. Retain encryption/KMS compatibility. Do not assume all network/parameter choices from the source are automatically the intended clone configuration.

After AWS reports `available`, verify the actual engine/version, instance/snapshot provenance, tags, private setting and endpoint. Then verify TLS connection and semantic DB-role/object policy. Warm-up/read effects may influence observed migration time; report actual measured clone timing and known limitations, not a production estimate. An available AWS control-plane status is not sufficient database readiness.

On throttling, describe failures or a lost create response, reconcile the exact intended resource before retrying. Do not create a new snapshot/clone name for each retry. Deadline expiry produces ERROR plus retained resource IDs for inspection; it is not permission to delete uncertain resources automatically.

## 8. Install and operate the host

Create dedicated private directories, for example `/opt/preflight` for code and `/var/lib/preflight` for artifacts/state, and a separate TrueForge state directory. They are proposed deployment paths, not existing resources. Run under a dedicated OS user. Keep code read-only where practical and writable state explicitly scoped. Use restrictive environment-file permissions and log rotation.

Install the tested Python/Node/uv/pnpm versions and locked dependencies; deploy the implementation created during the event. The agent must document actual setup commands, generate systemd units and verify the units under the actual OS. Do not provide an untested `ExecStart` path or assume a shell's PATH exists under systemd.

Start Preflight on loopback port 8000 and TrueForge on its verified loopback UI port (8790 is the PRD example; inspect the installed configuration). Configure the connector through TrueForge Settings → Connectors. Keep provider keys in TrueForge's credential configuration, not inside the saved-agent instruction text. The Python service uses its own named DB secrets and instance profile.

Set graceful shutdown, bounded job polling, process lock and persistent volume mount checks. A service restart reconciles infrastructure; it never auto-replays source SQL. Doctor must confirm the intended state directory and warn when started against a new empty SQLite file on the same live resources.

## 9. Troubleshooting without weakening the design

| Symptom | Inspect first | Never do |
|---|---|---|
| TrueForge does not list tools | SDK/protocol initialization, actual connector URL/transport, ten schemas, loopback route | Substitute hand-built JSON as a successful MCP call |
| Daytona cannot call MCP | Harness bridge configuration and real tool output schema | Expose RDS/MCP publicly or give sandbox DB passwords |
| Sandbox provisioning fails | Daytona permissions, quota, snapshot setup, actual error | Claim local Python ran in Daytona |
| RDS restore fails | Source snapshot status, compatible engine/class, subnet/KMS/role constraints | Repeatedly create new unrelated resources or grant admin |
| DB connect fails | SG reference, route, endpoint, role and CA/hostname | Disable TLS or make DB public |
| Preserved data/source drift | Correct baseline, exact candidate, full source fingerprints | Rebaseline a mutated clone or force PASS |
| Agent/tool times out | Persisted run/attempt phase and known transaction outcome | Rerun source SQL blindly |
| Approval did not appear | Saved manifest literal names, connector/tool name matching, installed version behavior | Add an `approved:true` argument and call it equivalent |

## 10. Cleanup and resource handoff

Keep the staged judging clone while it is needed; record that retention honestly. After explicit approval, `cleanup_run` may delete only its exact run-owned clone and optionally the snapshot subject to recovery rules. Describe until deletion finishes. `SkipFinalSnapshot` may be used for a disposable clone only under the selected cleanup policy; it is not a source-delete shortcut. Keep immutable reports and receipts before any deletion.

The pre-apply snapshot remains after source mutation unless another verified same-source pre-apply recovery snapshot exists. If source outcome is unknown, neither automated migration retry nor cleanup is allowed. A retained backup has an owner and reason, not a claim that costs stopped.

Source, EC2 host, shared network, secrets and IAM teardown are **outside** the runtime cleanup tool. The operator can separately authorize their teardown after evidence/recovery needs are resolved. The final handoff lists each retained resource/region/owner/reason and each observed deletion. Do not describe “all cleaned up” while snapshots or instances still exist.


## 11. Current restore and storage checks

Current AWS restore documentation includes lazy loading and a change effective **1 July 2026** disallowing magnetic storage for snapshot restores. For this new synthetic fixture prefer an approved compatible `gp3` configuration. Verify engine/class/storage/KMS support in the actual region; do not change the source's storage just to satisfy a template. Never assume a restore can shrink allocated storage.

Treat `available`, network/TLS readiness and storage initialization as distinct observations. If the API exposes storage operation/progress metadata, show the actual values; otherwise show state and elapsed time without a made-up percentage. Record whether evidence scans warmed the clone before timing a migration. Do not compare its cold/warm duration to live production performance.

The source is owned and synthetic. Refuse unexpected shared/cross-account snapshots; the special copy requirements of a shared encrypted snapshot are not silently added to this demo. A restored instance can carry roles/functions/settings, so run the declared object policy and restrict outbound integrations before SQL execution.

TLS negative tests must cover wrong CA and wrong hostname, not only `sslmode=disable`. PostgreSQL `rds.force_ssl` requiring encryption does not replace client certificate/hostname verification. Do not bypass TLS when a corporate proxy, stale CA file or renamed host causes errors.

## 12. Provider access, secrets and resource economics

The build uses the operator's coding subscription; the running product uses a separate Gateway/OpenAI route; AWS and Daytona have their own account permissions/limits. Do not treat generous Codex usage as unlimited API/cloud spend. Discover the authorized account and inspect quotas before creating resources; obtain a bounded resource/budget decision once rather than asking on every permitted poll.

Use a team/application-scoped Gateway credential where supported, copied into the approved provider settings, and confirm the model is enabled for that credential. Copy the exact base URL and model identifier from the actual Playground example. Never put a guessed provider prefix or secret in the model instruction. Do not change organization-wide access policies to work around a denied request.

Log/account dashboards may contain prompt text. Review Gateway, OpenAI, Daytona and SDK telemetry settings and retained payloads; keep only the synthetic SQL/check metadata needed, no rows or credentials. Prefix caching may be used; semantic cached action responses must not replace fresh stateful decisions. Record observed usage if accessible, not invented cost estimates.

Restore costs can continue after the UI is closed. The retained-resource handoff includes snapshots as well as instances, region, owner and next authorized action. Expiry tags flag review; they are not automatic permission to delete a recovery backup or a resource with unknown transaction outcome.

## 13. Dependency and release hygiene

At T01 retrieve actual package metadata and record the selected stable version; at T30 freeze integrity/locks only after compatibility tests. Do not update TrueForge's internal Daytona/AI SDK dependencies independently because another SDK has a newer release. Do not use a development documentation version as a stable package pin.

Create a small dependency/license inventory in the implemented repository. The pglast package metadata identifies GPL-3.0-or-later; do not label all bundled dependencies MIT or remove notices. Decide the project's distribution/license with the operator and preserve required attribution. This is an inventory/control requirement, not a claim that a particular distribution has been legally cleared.


## V3 observation-budget clarification

A short **agent Code Mode polling-batch deadline** returns the existing job as still pending; it is not the service's longer persisted **cloud job deadline**. The service may mark its job ERROR after its configured whole-job deadline while retaining exact resource IDs for inspection. Neither deadline authorizes an extra snapshot/restore, SQL replay or cleanup. Keep these deadlines and states distinct in code, configuration, tests and presentation.

Coding-model admission is governed by `config/model-policy.json`: Sol High for ordinary cloud work, no Astra escalation for a normal pending restore or known IAM/quota error. Provider usage and AWS resource costs are separate observations. Apply the same private network, TLS, identity, lifecycle and recovery requirements regardless of which Sol model wrote a module.
