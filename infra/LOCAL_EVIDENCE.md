# T04/T12/T13/T17 local cloud evidence

Assigned checkout: `.worktrees/cloud`, branch `preflight/cloud`.
Base commit: `5790a6a4f2cbeb2ef86c6918b08abdcae8568240`.
Effective own session `turn_context`: model `gpt-6-sol`, effort `high`.
Only that thread's matching session file was inspected; no credentials or full
session messages were emitted.

Backend: Boto3/Botocore Stubber and pure unit job fixtures only. Actual AWS identity,
pricing, source/host creation, snapshot restore, TLS readiness, human cleanup,
live deletion, Linux systemd startup and source mutation have NOT_RUN.
No operator-inputs.local.json, AWS resource identifiers or creation/spend scope
were supplied. T04 connected authorization is BLOCKED_EXTERNAL.

Commands from this checkout, using the existing lead Python 3.12 venv:

```
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& '../../.venv/Scripts/python.exe' -m pytest tests/cloud -q
& '../../.venv/Scripts/python.exe' -m ruff check src/preflight/aws_rds.py src/preflight/jobs.py infra tests/cloud
& '../../.venv/Scripts/python.exe' -m ruff format --check src/preflight/aws_rds.py src/preflight/jobs.py infra tests/cloud
```

The cloud suite covers exact private/encrypted restore construction, account,
source/network/engine/tag checks, deterministic collision refusal, resource caps,
separate mutation lease, restart/poll/deadline behavior, preserved uncertainty IDs,
provider error sanitization, lost-create reconciliation, literal cleanup gate,
source/unknown-outcome/report-retention refusal, independent recovery attestation,
exact deletion and absence observation. Bootstrap source/host request shapes use
Stubber; admin runtime policy, absent scopes and mismatched plan digests refuse.

Observed first cloud run: `47 passed in 6.42s`. Inventory/storage hardening run:
`64 passed in 31.55s`. Ruff check passed. Mypy
`--follow-imports=silent --ignore-missing-imports` passed for both cloud source
modules. `git diff --check` passed. These are local results, not live proof.

T12/T13/T17 are LOCAL_VERIFIED. No independent
cloud boundary review is claimed. Lead integration must hold application run CAS
through cleanup/source apply, supply trusted recovery evidence, promote AWS
availability to READY only after TLS/role/object checks, and expose only real
production clients under approved CloudPolicy. Both runtime and bootstrap share
the same durable `cloud.sqlite` and mutation lease. Never free reservations just
because a job expired or a deletion request returned.

Hardening adds paginated ownership-filtered Tagging API inventory, exact fresh
resource reads, empty/wrong-state refusal for untracked owned resources, stale
tag-index handling, released-but-present refusal, no-create reconciliation after
inconsistent provider reads, and retained snapshot accounting across a new run.
Storage source/clone/snapshot checks reject `standard` and unapproved modes;
restores explicitly pass the policy mode and safe observations record it.

Bootstrap prerequisite hardening run: `78 passed in 11.25s`. Owned-path Ruff check,
format check, both-cloud-module Mypy and final `git diff --check` passed. A mixed
line-ending formatting/diff issue was normalized before commit; no checks were
disabled. Bootstrap tests now exercise actual Stubber metadata reads for a valid
private network/runtime profile and public 8000/8790 rule refusal. Pure negative
guards reject public DB routing, DB egress, unrelated SG/VPC, unrelated/source
delete targets, broad Secrets Manager/KMS/IAM actions and external role trust.
