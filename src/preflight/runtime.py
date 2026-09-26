"""Real AWS/TLS composition. No credentials/clients are created at import time."""

import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID

from .artifacts import strict_json
from .models import PreflightError


class AwsRuntime:
    def __init__(self, settings, adapter, jobs, secrets):
        self.settings, self.adapter, self.jobs, self.secrets = settings, adapter, jobs, secrets

    def resource_intent(self, run_id):
        from .jobs import ResourceIntent

        expires_at = (datetime.now(UTC) + timedelta(hours=8)).isoformat().replace("+00:00", "Z")
        intent = ResourceIntent.for_run(UUID(run_id), self.settings.owner, expires_at)
        return {
            "snapshot_id": intent.snapshot_id,
            "clone_instance_id": intent.clone_instance_id,
            "resource_expires_at": expires_at,
        }

    def intent(self, run):
        from .jobs import ResourceIntent

        intent = ResourceIntent.for_run(
            UUID(run["run_id"]), self.settings.owner, run["resource_expires_at"]
        )
        if (
            intent.snapshot_id != run["snapshot_id"]
            or intent.clone_instance_id != run["clone_instance_id"]
        ):
            raise PreflightError("RESOURCE_INTENT_MISMATCH")
        if run["source_instance_id"] != self.settings.source_instance_id:
            raise PreflightError("SOURCE_NOT_ALLOWLISTED")
        return intent

    def enqueue(self, run):
        self.jobs.enqueue(
            UUID(run["run_id"]),
            self.intent(run),
            deadline=time.time() + 7200,
            max_clones=self.settings.max_run_owned_clones,
            max_snapshots=self.settings.max_run_owned_snapshots,
        )

    def advance_jobs(self, store):
        from .jobs import tick_job

        # Infrastructure-only restart/reconciliation; no SQL migration callback exists here.
        for run in store.list_runs():
            if run["phase"] not in {"REGISTERED", "SNAPSHOTTING", "RESTORING"}:
                continue
            run_id = run["run_id"]
            try:
                if run["phase"] == "REGISTERED":
                    store.transition(run_id, "REGISTERED", "SNAPSHOTTING")
                while True:
                    job = tick_job(self.jobs, self.adapter, run_id)
                    current = store.get_run(run_id)
                    if job["phase"] == "ERROR":
                        store.transition(
                            run_id, current["phase"], "ERROR", {"last_error": job["error_code"]}
                        )
                        break
                    if (
                        job["phase"] in {"RESTORING", "AVAILABLE"}
                        and current["phase"] == "SNAPSHOTTING"
                    ):
                        store.transition(run_id, "SNAPSHOTTING", "RESTORING")
                    if job["phase"] == "AVAILABLE":
                        self.verify_resources(store.get_run(run_id), require_backup=True)
                        # Actual TLS/authentication/engine proof before declaring application READY.
                        with self.connection(store.get_run(run_id), "clone_read"):
                            pass
                        store.transition(run_id, "RESTORING", "READY")
                        break
                    wait = max(0.2, min(30.0, job["next_poll"] - time.time()))
                    time.sleep(wait)
            except PreflightError as exc:
                current = store.get_run(run_id)
                if current["phase"] in {"REGISTERED", "SNAPSHOTTING", "RESTORING"}:
                    store.transition(run_id, current["phase"], "ERROR", {"last_error": exc.code})

    def verify_resources(self, run, require_backup=False):
        intent = self.intent(run)
        source = self.adapter.inspect_source()
        clone = self.adapter.inspect_clone(intent)
        if source.status != "available" or clone.status != "available":
            raise PreflightError("DATABASE_NOT_AVAILABLE")
        if source.endpoint == clone.endpoint or source.resource_id == clone.resource_id:
            raise PreflightError("SOURCE_CLONE_COLLISION")
        if source.engine_version != clone.engine_version or source.kms_key_id != clone.kms_key_id:
            raise PreflightError("RESTORE_IDENTITY_MISMATCH")
        if require_backup:
            snapshot = self.adapter.inspect_snapshot(intent)
            if snapshot.status != "available":
                raise PreflightError("BACKUP_UNAVAILABLE")

    @contextmanager
    def connection(self, run, mode):
        from .db import connect_database

        if mode not in {"source_read", "source_write", "clone_read", "clone_write"}:
            raise PreflightError("CONNECTION_MODE_INVALID")
        if mode == "source_write" and not self.settings.enable_demo_source_apply:
            raise PreflightError("SOURCE_APPLY_DISABLED")
        if mode.startswith("source"):
            if run["source_instance_id"] != self.settings.source_instance_id:
                raise PreflightError("SOURCE_NOT_ALLOWLISTED")
            observation = self.adapter.inspect_source()
        else:
            observation = self.adapter.inspect_clone(self.intent(run))
        if observation.status != "available" or not observation.endpoint:
            raise PreflightError("DATABASE_NOT_AVAILABLE")
        secret_arn = (
            self.settings.migration_writer_secret_arn
            if mode.endswith("write")
            else self.settings.source_read_secret_arn
        )
        if not secret_arn or not secret_arn.startswith(
            f"arn:aws:secretsmanager:{self.settings.region}:{self.settings.account_id}:secret:"
        ):
            raise PreflightError("SECRET_REFERENCE_NOT_ALLOWLISTED")
        try:
            secret = self.secrets.get_secret_value(SecretId=secret_arn)
            credentials = strict_json(secret["SecretString"].encode("utf-8"), 16384)
        except Exception:
            raise PreflightError("SECRET_ACCESS_FAILED") from None
        if (
            not isinstance(credentials, dict)
            or not isinstance(credentials.get("username"), str)
            or not isinstance(credentials.get("password"), str)
            or credentials.get("dbname", run["database_name"]) != run["database_name"]
            or self.settings.sslrootcert is None
        ):
            raise PreflightError("DATABASE_CREDENTIAL_CONFIGURATION_INVALID")
        connection = connect_database(
            observation.endpoint,
            5432,
            run["database_name"],
            credentials["username"],
            credentials["password"],
            str(self.settings.sslrootcert),
        )
        try:
            yield connection
        finally:
            connection.close()

    def cleanup(self, run, request, source_apply_attempted):
        from .aws_rds import CleanupPolicy

        selection = CleanupPolicy(
            literal_gate_approved=True,
            run_phase=run["phase"],
            reports_retained=True,
            source_apply_attempted=source_apply_attempted,
            preapply_not_after=datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")),
            recovery_backup_snapshot_id=request.recovery_backup_snapshot_id,
            delete_clone=request.delete_clone,
            delete_snapshot=request.delete_snapshot,
            clone_instance_id=request.clone_instance_id or run["clone_instance_id"],
            snapshot_id=request.snapshot_id or run["snapshot_id"],
        )
        actions = self.adapter.cleanup(self.intent(run), selection)
        if request.delete_clone and actions.get("clone") == "DELETING":
            state = "DELETING_CLONE"
        elif request.delete_snapshot and actions.get("snapshot") == "DELETING":
            state = "DELETING_SNAPSHOT"
        elif (
            request.delete_clone
            and request.delete_snapshot
            and all(v == "ABSENT" for v in actions.values())
        ):
            state = "COMPLETE"
        else:
            state = "RETAINED_RECOVERY" if source_apply_attempted else "CLONE_DELETED"
        return {"actions": actions, "cleanup_state": state}

    def observe_cleanup(self, run):
        observed = self.adapter.observe_cleanup(self.intent(run))
        selected = run.get("cleanup_selection", {})
        clone_absent = observed.get("clone") == "ABSENT"
        snapshot_absent = observed.get("snapshot") == "ABSENT"
        if clone_absent and snapshot_absent:
            state = "COMPLETE"
        elif selected.get("delete_clone") and not clone_absent:
            state = "DELETING_CLONE"
        elif selected.get("delete_snapshot") and not snapshot_absent:
            state = "DELETING_SNAPSHOT"
        elif clone_absent:
            state = (
                "RETAINED_RECOVERY"
                if run.get("phase") in {"APPLIED", "APPLY_FAILED", "APPLIED_NEEDS_ATTENTION"}
                else "CLONE_DELETED"
            )
        else:
            state = "NOT_REQUESTED"
        return {"cleanup_state": state, "observed_resources": observed}


def build_runtime(settings):
    from .service import UnconfiguredRuntime

    if not settings.creation_authorized:
        return UnconfiguredRuntime()
    if settings.evidence_backend != "aws_rds":
        raise PreflightError("DEPLOYED_TEST_BACKEND_REFUSED")
    import boto3
    from botocore.config import Config

    from .aws_rds import CloudPolicy, RdsAdapter
    from .jobs import JobStore

    jobs = JobStore(settings.state_dir / "cloud.sqlite")
    policy = CloudPolicy(
        account_id=settings.account_id,
        region=settings.region,
        source_instance_id=settings.source_instance_id,
        owner=settings.owner,
        subnet_group=settings.db_subnet_group_name,
        security_group_ids=tuple(settings.clone_security_group_ids),
        instance_class=settings.instance_class,
        creation_authorized=True,
        max_clones=settings.max_run_owned_clones,
        max_snapshots=settings.max_run_owned_snapshots,
    )
    session = boto3.Session(region_name=settings.region)
    config = Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 0})
    adapter = RdsAdapter(
        session.client("rds", config=config),
        session.client("sts", config=config),
        policy,
        jobs,
        tagging=session.client("resourcegroupstaggingapi", config=config),
    )
    return AwsRuntime(settings, adapter, jobs, session.client("secretsmanager", config=config))
