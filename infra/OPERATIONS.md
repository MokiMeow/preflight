# Cloud lane operational handoff

Runtime construction must inject a region-bound `resourcegroupstaggingapi`
client as `RdsAdapter(..., tagging=client)`. Before any new snapshot/clone request,
the adapter queries `GetResources` with both exact Project and Owner tag filters,
RDS instance/snapshot type filters, and complete bounded pagination. It then makes
fresh exact-ID RDS reads for owned resources only. A present owned ID absent from
the durable registry, or present after its reservation was released, blocks all
creation and requires operator reconciliation. Doctor's
`owned_resource_inventory()` exposes safe IDs, status, observed storage mode and
counts only. It never adopts or deletes discovered resources.

The tagging index is eventually consistent and may list previously tagged/deleted
resources. Fresh exact RDS absence discards a stale index entry; conflicting reads
of the intended ID cause reconciliation, never an additional create request.
Completed pagination is not proof of immediate global inventory visibility.
Durable reservations, one shared persistent lease, one service owner and the
intended state directory remain mandatory. Refuse startup against an unexpected
state directory and retain original state across deployment/restarts.

The read-only `tag:GetResources` permission requires `Resource: "*"`; unlike
mutation permissions this API has no resource-level IAM scope. The service applies
exact ownership filters and ARN validation. This is an explicitly documented
read-only prerequisite, never automatic permission broadening. AWS API semantics:
[GetResources](https://docs.aws.amazon.com/resourcegroupstagging/latest/APIReference/API_GetResources.html)
and [Tagging API authorization](https://docs.aws.amazon.com/service-authorization/latest/reference/list_resourcegroupstaggingapi.html).

Storage mode defaults to reviewed `gp3`; an existing supported `gp2` source needs
an explicit matching policy. The adapter never converts source storage. Source,
snapshot and clone must match that mode and every restore passes it explicitly.
Magnetic `standard` is refused under the current
[AWS restore/storage rule](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Storage.html).

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

Bootstrap prerequisite verification reads the exact existing instance profile,
its role trust, all attached/inline policy documents, exact named secret metadata,
DB subnet group, host subnet, exact SGs and (for creation) selected AMI. Runtime
trust admits only the EC2 service principal in the approved account; administrator,
IAM mutation/PassRole permissions, unrelated/cross-account mutation ARNs, broad
secret access and unscoped KMS grants are refused. Policy documents are normalized
and sorted before their independently reviewed digest is compared. Describe and
ownership-filtered Tagging metadata permissions may require wildcard resources;
write resources remain the exact source or predefined run ARN scope. Source
deletion is also refused unconditionally by the service. This verifier attaches
no policies and never treats a provider denial as permission to broaden them.

Require two distinct named reader/writer secret ARNs and a same-account/region
key ARN if a customer KMS key is selected. Reader/writer database role privileges
still require the separate DB readiness probe. Require separate DB/host SGs in
the approved VPC and at least one DB ingress rule consisting solely of TCP 5432
from the approved host SG. DB outbound application routes are refused. Host
ingress may contain only TCP 22 from the recorded narrow IPv4 operator origin
(prefix /24 or narrower); rules for 8000/8790, public DB CIDRs and unrelated SGs
are refused even beside restrictive rules. No network rule is changed to repair
a failure. An IPv6 or SSM alternative requires an explicitly implemented,
reviewed policy rather than an implicit bypass.

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
