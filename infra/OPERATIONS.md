# Cloud lane operational handoff

This checkout has performed no AWS calls or cloud mutations. The adapter uses real
Boto3 clients only when injected with approved policy; unit Stubber results are
LOCAL_VERIFIED, never connected RDS evidence.

`bootstrap.py plan --inputs <private-operator-plan-inputs.json> --out <private-plan.json>`
persists a canonical SHA-256 plan. Every required field comes from the operator;
the script invents no account, network, source, SSH policy or budget. Costs remain
NOT_OBSERVED. `apply --plan <private-plan.json> --approval <private-approval.json>`
checks an exact separately approved digest/account/region/operator/spend match,
requires a complete explicit deployment block: pinned engine minor version,
database name, existing subnet/SG identifiers, named reader/writer secret ARNs,
existing instance profile and reviewed runtime-policy digest, SSH key name,
approved image/owner, optional approved KMS key and exact host identifier for
reuse. It reuses those prerequisites and creates only the plan-selected source
and/or one host. It never modifies IAM or network rules, fetches secrets, resets
source data or seeds database roles. Creation is private/encrypted and reconciles
exact source ID plus a stable host ClientToken after ambiguous outcomes. Current
region costs and operator scope remain prerequisites, never inferred credits.
Database role/fixture/TLS setup is a separate integration gate. No connected
bootstrap acceptance is claimed.

Runtime and bootstrap identities remain separate. No IAM policy is attached or
broadened. Runtime needs only named source/snapshot/clone operations and named
secret ARNs, with documented AWS-required describe wildcards. Source has exact
Project=Preflight, Owner=<approved owner>, Purpose=synthetic-source tags; a tag is
an ownership guard, not proof of data contents. Database baseline/object checks
must establish the synthetic fixture separately.

JobStore uses a separate persistent SQLite database and file lock. Restrict its
directory to the dedicated service OS user (0700 on Linux), database files to 0600,
and use durable local storage. One owner and one mutation lease cover all run
resources. A restart reconciles exact names and tags. Resource reservations stay
held after errors/expiry/deletion requests. `observe_cleanup(intent)` makes only
fresh exact-ID AWS reads under the lease and frees each reservation separately
only after confirmed ABSENT, preserving counts for DELETING or present resources.
Operator inventory reconciliation is required for unresolved resources. No TTL
sweeper or reset script is provided. AWS AVAILABLE does not mean SQL READY.

The lead must hold its exclusive application run lock across cleanup and any
source transaction. CleanupPolicy is computed by server code from durable state
after the actual literal cleanup_run TrueForge human gate; never accept its
approval or state fields from the model. Preserve report/receipt files first.
Unknown apply/clone outcomes block cleanup. Deletion requests remain DELETING
until fresh exact-resource reads confirm absence. After any source apply attempt,
snapshot deletion requires an independent available same-source preapply recovery
snapshot plus a trusted persisted equivalence attestation callback. A timestamp,
tag, arbitrary string or post-apply snapshot alone does not establish equivalence.

Host deployment is BLOCKED_EXTERNAL. Verify the actual Linux OS, Python/Node
paths, installed entry points, state mounts, private network origin and loopback
ports before enabling a unit. Generate ExecStart from the tested installed CLI;
do not run placeholder paths. Use a dedicated OS user, `UMask=0077`,
`Restart=on-failure`, `TimeoutStopSec=30`, `NoNewPrivileges=true`,
`ProtectSystem=strict`, `ProtectHome=true`, and explicitly writable state paths.
Persist separate TrueForge and Preflight state. Do not put secrets in unit text.
Use root-readable environment/credential files and an instance profile.

Verify units with `systemd-analyze verify` on the actual host before enabling;
that check has NOT_RUN on this Windows build machine. Check a restart preserves
SQLite identity and never replays source SQL. Configure journald with bounded
`SystemMaxUse` and `MaxRetentionSec` under the operator's host policy (suggested
proposal: 100 MiB and 7 days). Emit only fixed error codes/resource IDs/status and
safe request IDs; do not log SQL, raw rows, provider exception text, credentials
or connection strings. Retain sealed reports and receipts separately from logs.

`preflight.service.in` is the deployment template for the lead's actual
`preflight serve` entry point (loopback is enforced by application code). Paths
are proposed deployment locations and have NOT_RUN on Linux. Before installation,
verify `/usr/bin/test`, the venv executable and the intended mounted state path,
install private environment file `/etc/preflight/preflight.env` with
`PREFLIGHT_SETTINGS` pointing to operator settings under `/var/lib/preflight`,
and validate with `systemd-analyze verify infra/preflight.service.in` on the host.
The systemd template cannot prove DB readiness or authorize source apply/cleanup.
`journald-preflight.conf.in` is a bounded host-policy proposal; approve its global
impact before installing as a journald drop-in. TrueForge unit generation must
wait for its verified installed start command and separate state paths.
