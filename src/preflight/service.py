"""Use cases and guards. Only the approved source use case can request a writer."""

import base64
import binascii
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from importlib.metadata import version
from typing import Any
from uuid import UUID, uuid4

from pydantic import ValidationError

from .artifacts import ArtifactStore, canonical_json, sha256, strict_json
from .config import Settings
from .models import (
    TOOL_INPUTS,
    TOOL_OUTPUTS,
    Candidate,
    CheckResult,
    Contract,
    PreflightError,
    ReportPayload,
    Requirement,
    ToolEnvelope,
    TxOutcome,
)
from .storage import StateStore, utc_now
from .verdict import evaluate, invariant_requirements


class UnconfiguredRuntime:
    """Missing connected access is a refusal, never a synthetic cloud success."""

    def __getattr__(self, name):
        raise PreflightError("CONNECTED_RUNTIME_NOT_CONFIGURED")


class RehearsalService:
    def __init__(
        self,
        settings: Settings,
        runtime=None,
        *,
        restart: bool = True,
        test_source_apply: bool = False,
    ):
        if test_source_apply and (
            settings.evidence_backend != "local_postgres_test"
            or runtime is None
            or not getattr(runtime, "local_test_only", False)
        ):
            raise PreflightError("TEST_SOURCE_ADAPTER_REFUSED")
        self._test_source_apply = test_source_apply
        self.settings = settings
        self.runtime = runtime or UnconfiguredRuntime()
        self.store = StateStore(settings.state_dir / "preflight.sqlite3")
        self.artifacts = ArtifactStore(settings.state_dir)
        self.baselines: dict[str, Any] = {}
        self._locks: dict[str, threading.RLock] = {}
        self._lock_guard = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="preflight-job")
        if restart:
            self.store.reconcile_restart()

    def lock(self, run_id: str):
        with self._lock_guard:
            return self._locks.setdefault(run_id, threading.RLock())

    def call(self, tool: str, arguments: dict) -> dict:
        request_id = arguments.get("request_id")
        output_model = TOOL_OUTPUTS.get(tool)
        envelope_model: Any = ToolEnvelope[output_model] if output_model else ToolEnvelope  # type: ignore[valid-type]
        try:
            model = TOOL_INPUTS[tool].model_validate(arguments)
            if output_model is None:
                raise KeyError(tool)
        except (ValidationError, KeyError):
            # Neither exception text nor the invalid input is returned/logged.
            try:
                safe_request_id = str(UUID(request_id)) if isinstance(request_id, str) else None
            except ValueError:
                safe_request_id = None
            return {
                "ok": False,
                "request_id": safe_request_id,
                "run_id": None,
                "state": None,
                "data": {"message": "INVALID_INPUT"},
                "error_code": "INVALID_INPUT",
                "retryable": False,
            }
        run_id = str(getattr(model, "run_id", "") or "")
        mutating = tool in {
            "register_candidate",
            "start_rehearsal",
            "capture_baseline",
            "apply_to_clone",
            "validate_rehearsal",
            "cleanup_run",
        }
        claimed = False
        try:
            if mutating:
                digest = sha256(canonical_json(model.model_dump(mode="json")))
                replay = self.store.claim_request(tool, str(model.request_id), digest)
                if replay is not None:
                    return replay
                claimed = True
            with self.lock(run_id or tool):
                data = getattr(self, tool)(model)
            validated_data = output_model.model_validate(data)
            result_id = run_id or data.get("run_id")
            state = self.store.get_run(result_id)["phase"] if result_id else None
            result = envelope_model(
                ok=True,
                request_id=model.request_id,
                run_id=UUID(result_id) if result_id else None,
                state=state,
                data=validated_data,
            )
        except PreflightError as exc:
            result = envelope_model(
                ok=False,
                request_id=model.request_id,
                run_id=UUID(run_id) if run_id else None,
                data={"message": exc.code},
                error_code=exc.code,
            )
        except Exception:
            result = envelope_model(
                ok=False,
                request_id=model.request_id,
                run_id=UUID(run_id) if run_id else None,
                data={"message": "INTERNAL_ERROR"},
                error_code="INTERNAL_ERROR",
            )
        encoded = result.model_dump(mode="json")
        if claimed:
            self.store.finish_request(tool, str(model.request_id), encoded)
        return encoded

    def candidate(self, candidate_id: str) -> tuple[Candidate, bytes]:
        record = Candidate.model_validate(self.store.get("candidate", candidate_id))
        sql = self.artifacts.read(
            f"artifacts/{candidate_id}/migration.sql", record.migration_sha256, 65536
        )
        contract_bytes = self.artifacts.read(
            f"artifacts/{candidate_id}/contract.canonical.json", record.contract_sha256
        )
        if canonical_json(record.contract.model_dump(mode="json")) != contract_bytes:
            raise PreflightError("CONTRACT_INTEGRITY_ERROR")
        return record, sql

    def register_candidate(self, request):
        from .sql_policy import inspect_sql

        try:
            raw = (
                base64.b64decode(request.sql_utf8_b64, validate=True)
                if request.sql_utf8_b64 is not None
                else request.sql_text.encode("utf-8")
            )
            raw.decode("utf-8")
        except (binascii.Error, UnicodeError):
            raise PreflightError("INVALID_SQL_ENCODING") from None
        if not raw or len(raw) > 65536 or b"\x00" in raw:
            raise PreflightError("SQL_SIZE_OR_NUL")
        if sha256(raw) != request.expected_migration_sha256:
            raise PreflightError("MIGRATION_HASH_MISMATCH")
        if not {t.name for t in request.contract.tables} <= set(self.settings.table_allowlist):
            raise PreflightError("TABLE_NOT_ALLOWLISTED")
        plan = inspect_sql(raw, request.contract)
        contract_bytes = canonical_json(request.contract.model_dump(mode="json"))
        run = None
        if request.run_id:
            run = self.store.get_run(str(request.run_id))
            if run["candidate_id"] != str(request.parent_candidate_id):
                raise PreflightError("STALE_CANDIDATE")
            parent, _ = self.candidate(run["candidate_id"])
            if sha256(contract_bytes) != parent.contract_sha256:
                raise PreflightError("CONTRACT_CHANGE_REQUIRES_NEW_RUN")
            if (
                run["phase"] != "BLOCKED"
                or run.get("clone_outcome") != "rolled_back"
                or str(request.run_id) not in self.baselines
                or self.store.has_apply(str(request.run_id))
            ):
                raise PreflightError("FRESH_REHEARSAL_REQUIRED")
            from .evidence import baseline_matches, capture_evidence

            with self.runtime.connection(run, "clone_read") as con:
                fresh = capture_evidence(con, request.contract)
            if not baseline_matches(self.baselines[str(request.run_id)], fresh):
                raise PreflightError("FRESH_REHEARSAL_REQUIRED")
        candidate_id = str(uuid4())
        record = Candidate(
            candidate_id=candidate_id,
            parent_candidate_id=request.parent_candidate_id,
            operator_id=request.operator_id,
            migration_sha256=sha256(raw),
            contract_sha256=sha256(contract_bytes),
            byte_size=len(raw),
            created_at=utc_now(),
            contract=request.contract,
        )
        self.artifacts.write_once(f"artifacts/{candidate_id}/migration.sql", raw)
        self.artifacts.write_once(
            f"artifacts/{candidate_id}/contract.canonical.json", contract_bytes
        )
        self.store.publish_candidate(record.model_dump(mode="json"), run)
        tables = {table.name: table for table in request.contract.tables}
        coverage_warnings = []
        for write in plan.writes:
            table = tables[write.table]
            checks = {
                (check.type, getattr(check, "column", None)) for check in table.checks
            }
            expected = {
                column.name: column
                for column in (
                    table.expected_schema.added_columns if table.expected_schema else []
                )
            }
            complete = False
            if write.operation == "update":
                complete = (
                    write.column in table.preserve_columns
                    or ("all_equal", write.column) in checks
                )
            elif write.operation == "add_column":
                complete = (
                    write.column in expected and ("all_equal", write.column) in checks
                )
            elif write.operation == "set_not_null":
                complete = (
                    write.column in expected
                    and not expected[write.column].nullable
                    and ("column_not_null", write.column) in checks
                    and ("no_nulls", write.column) in checks
                )
            if not complete:
                coverage_warnings.append(
                    f"COVERAGE_INCOMPLETE:{write.table}:{write.column}:{write.operation}"
                )
        return {
            "candidate_id": candidate_id,
            "parent_candidate_id": str(request.parent_candidate_id)
            if request.parent_candidate_id
            else None,
            "migration_sha256": record.migration_sha256,
            "contract_sha256": record.contract_sha256,
            "byte_size": len(raw),
            "policy_version": plan.policy_version,
            "declared_tables": plan.tables,
            "coverage_warnings": sorted(set(coverage_warnings)),
            "attached": bool(run),
        }

    def start_rehearsal(self, request):
        self._source_guard(request.source_instance_id, request.database_name)
        if not self.settings.creation_authorized:
            raise PreflightError("CLOUD_CREATION_NOT_AUTHORIZED")
        candidate, _ = self.candidate(str(request.candidate_id))
        if candidate.contract.database != request.database_name:
            raise PreflightError("DATABASE_CONTRACT_MISMATCH")
        run_id = str(uuid4())
        resources = self.runtime.resource_intent(run_id)
        run = {
            "run_id": run_id,
            "candidate_id": str(request.candidate_id),
            "source_instance_id": request.source_instance_id,
            "database_name": request.database_name,
            "account_id": self.settings.account_id,
            "region": self.settings.region,
            "created_at": utc_now(),
            **resources,
        }
        self.store.create_run(run)
        self.runtime.enqueue(run)
        self.executor.submit(self.runtime.advance_jobs, self.store)
        return {"run_id": run_id, "phase": "REGISTERED", **resources, "poll_after_seconds": 5}

    def _source_guard(self, source_id: str, database: str):
        if (
            source_id != self.settings.source_instance_id
            or source_id not in self.settings.source_allowlist
            or database != self.settings.database_name
        ):
            raise PreflightError("SOURCE_NOT_ALLOWLISTED")

    def get_run(self, request):
        run = self.store.get_run(str(request.run_id))
        if run["cleanup_state"] in {"DELETING_CLONE", "DELETING_SNAPSHOT"}:
            try:
                observation = self.runtime.observe_cleanup(run)
                state = observation["cleanup_state"]
                if state != run["cleanup_state"]:
                    self.store.set_cleanup(run["run_id"], state)
                    run = self.store.get_run(run["run_id"])
            except PreflightError:
                pass  # A failed read is not evidence of absence.
        result = {
            key: value
            for key, value in run.items()
            if key
            in {
                "run_id",
                "candidate_id",
                "phase",
                "revision",
                "source_instance_id",
                "snapshot_id",
                "clone_instance_id",
                "created_at",
                "updated_at",
                "cleanup_state",
                "clone_outcome",
                "report_sha256",
                "verdict",
                "last_error",
                "last_resource_status",
            }
        }
        candidate, _ = self.candidate(run["candidate_id"])
        result["migration_sha256"] = candidate.migration_sha256
        result["contract_sha256"] = candidate.contract_sha256
        result["progress_label"] = run["phase"]
        start = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
        terminal = {
            "APPLIED",
            "APPLY_FAILED",
            "APPLIED_NEEDS_ATTENTION",
            "APPLY_OUTCOME_UNKNOWN",
            "STALE",
            "ERROR",
            "BLOCKED",
            "WARN",
        }
        end_value = run.get("updated_at") if run["phase"] in terminal else None
        end = (
            datetime.fromisoformat(end_value.replace("Z", "+00:00"))
            if end_value
            else datetime.now(timezone.utc)
        )
        result["elapsed_seconds"] = max(0, int((end - start).total_seconds()))
        result["last_observed_at"] = run.get("last_observed_at")
        eligible = (
            run["phase"] == "AWAITING_APPROVAL"
            and run["cleanup_state"] == "NOT_REQUESTED"
            and str(request.run_id) in self.baselines
            and self.settings.enable_demo_source_apply
            and not self.store.has_apply(str(request.run_id))
        )
        result["apply_eligible_now"] = eligible
        result["eligibility_is_preliminary"] = True
        if eligible:
            reason = "PRELIMINARY_ELIGIBLE"
        elif run["phase"] != "AWAITING_APPROVAL":
            reason = "PHASE_NOT_AWAITING_APPROVAL"
        elif run["cleanup_state"] != "NOT_REQUESTED":
            reason = "CLEANUP_ACTIVE"
        elif str(request.run_id) not in self.baselines:
            reason = "BASELINE_UNAVAILABLE"
        elif not self.settings.enable_demo_source_apply:
            reason = "SOURCE_APPLY_DISABLED"
        else:
            reason = "SOURCE_APPLY_ALREADY_ATTEMPTED"
        result["eligibility_reason"] = reason
        return result

    def get_source_status(self, request):
        from .evidence import capture_evidence
        from .models import RowCountCheck, TableContract

        self._source_guard(request.source_instance_id, request.database_name)
        if not set(request.table_names) <= set(self.settings.table_allowlist):
            raise PreflightError("TABLE_NOT_ALLOWLISTED")
        if request.run_id:
            run = self.store.get_run(str(request.run_id))
            if run["source_instance_id"] != request.source_instance_id:
                raise PreflightError("SOURCE_NOT_ALLOWLISTED")
            candidate, _ = self.candidate(run["candidate_id"])
            requested = set(request.table_names)
            contract = Contract.model_validate(
                {
                    **candidate.contract.model_dump(mode="json"),
                    "tables": [
                        table.model_dump(mode="json")
                        for table in candidate.contract.tables
                        if table.name in requested
                    ],
                }
            )
            if not set(request.table_names) <= {t.name for t in contract.tables}:
                raise PreflightError("TABLE_NOT_DECLARED")
        else:
            if request.table_names != ["public.customers"]:
                raise PreflightError("STATUS_CONTRACT_REQUIRED")
            contract = Contract(
                schema_version="1.1",
                database=self.settings.database_name,
                tables=[
                    TableContract(
                        name="public.customers",
                        primary_key=["id"],
                        preserve_columns=["id", "email", "created_at"],
                        checks=[RowCountCheck(type="row_count_unchanged")],
                    )
                ],
                max_migration_seconds=60,
                max_rows_per_table=10000,
                max_bytes_per_table=10485760,
            )
            run = {
                "source_instance_id": request.source_instance_id,
                "database_name": request.database_name,
            }
        with self.runtime.connection(run, "source_read") as con:
            evidence = capture_evidence(con, contract)
        comparison_status = "NOT_REQUESTED"
        if request.run_id:
            baseline = self.baselines.get(str(request.run_id))
            if baseline is None:
                comparison_status = "BASELINE_UNAVAILABLE"
            else:
                baseline_tables = {
                    table.name: table.model_dump(mode="json")
                    for table in baseline.public.tables
                    if table.name in set(request.table_names)
                }
                observed_tables = {
                    table.name: table.model_dump(mode="json") for table in evidence.public.tables
                }
                comparison_status = (
                    "MATCH" if baseline_tables == observed_tables else "DIFFERENT"
                )
        return {
            "evidence": evidence.public.model_dump(mode="json"),
            "comparison_status": comparison_status,
        }

    def capture_baseline(self, request):
        from .evidence import baseline_matches, capture_evidence, resolve_coverage
        from .sql_policy import inspect_sql

        run_id = str(request.run_id)
        run = self.store.get_run(run_id)
        if run["phase"] == "BASELINED" and run_id in self.baselines:
            baseline = self.baselines[run_id]
            candidate, raw = self.candidate(run["candidate_id"])
            coverage = resolve_coverage(
                inspect_sql(raw, candidate.contract),
                candidate.contract,
                baseline.existing_columns,
            )
            return {
                "baseline_id": sha256(canonical_json(baseline.public.model_dump(mode="json"))),
                "baseline": baseline.public.model_dump(mode="json"),
                "coverage": [item.model_dump(mode="json") for item in coverage],
            }
        if run["phase"] != "READY":
            raise PreflightError("RUN_NOT_READY")
        self.runtime.verify_resources(run, require_backup=True)
        if run["clone_instance_id"] == run["source_instance_id"]:
            raise PreflightError("SOURCE_CLONE_COLLISION")
        candidate, raw = self.candidate(run["candidate_id"])
        plan = inspect_sql(raw, candidate.contract)
        with self.runtime.connection(run, "clone_read") as con:
            baseline = capture_evidence(con, candidate.contract)
        with self.runtime.connection(run, "source_read") as con:
            source = capture_evidence(con, candidate.contract)
        if not baseline_matches(baseline, source):
            self.store.transition(run_id, "READY", "ERROR", code="SOURCE_BASELINE_MISMATCH")
            raise PreflightError("SOURCE_BASELINE_MISMATCH")
        columns = baseline.existing_columns
        coverage = resolve_coverage(plan, candidate.contract, columns)
        self.baselines[run_id] = baseline
        self.store.transition(
            run_id,
            "READY",
            "BASELINED",
            {
                "baseline": baseline.public.model_dump(mode="json"),
                "coverage": [item.model_dump(mode="json") for item in coverage],
            },
        )
        return {
            "baseline_id": sha256(canonical_json(baseline.public.model_dump(mode="json"))),
            "baseline": baseline.public.model_dump(mode="json"),
            "coverage": [item.model_dump(mode="json") for item in coverage],
        }

    def apply_to_clone(self, request):
        from .db import execute_migration
        from .evidence import baseline_matches, capture_evidence
        from .sql_policy import inspect_sql

        run_id = str(request.run_id)
        run = self.store.get_run(run_id)
        if run["phase"] != "BASELINED" or run["candidate_id"] != str(request.candidate_id):
            raise PreflightError("CLONE_REPLAY_OR_STATE_REJECTED")
        if run_id not in self.baselines:
            raise PreflightError("BASELINE_MEMORY_LOST")
        self.runtime.verify_resources(run, require_backup=True)
        candidate, raw = self.candidate(run["candidate_id"])
        plan = inspect_sql(raw, candidate.contract)
        self.store.transition(run_id, "BASELINED", "MIGRATING")
        try:
            with self.runtime.connection(run, "clone_write") as con:
                outcome = execute_migration(con, raw, plan, candidate.contract)
        except Exception:
            outcome = TxOutcome(outcome="unknown", elapsed_ms=0, reason_code="CONNECTION_LOST")
        state = {
            "committed": "VALIDATING",
            "rolled_back": "BLOCKED",
            "unknown": "CLONE_OUTCOME_UNKNOWN",
        }[outcome.outcome]
        unchanged = None
        if outcome.outcome == "rolled_back":
            try:
                with self.runtime.connection(run, "clone_read") as con:
                    fresh = capture_evidence(con, candidate.contract)
                unchanged = baseline_matches(self.baselines[run_id], fresh)
            except Exception:
                unchanged = False
        self.store.transition(
            run_id,
            "MIGRATING",
            state,
            {
                "clone_outcome": outcome.outcome,
                "migration": outcome.model_dump(mode="json"),
                "rollback_baseline_unchanged": unchanged,
            },
        )
        return {
            "transaction": outcome.model_dump(mode="json"),
            "baseline_unchanged": unchanged,
            "next_permitted_operation": (
                "manual_resolution" if outcome.outcome == "unknown" else "validate_rehearsal"
            ),
        }

    def _complete_checks(self, checkset, outcome):
        requirements = list(checkset.requirements)
        checks = list(checkset.checks)
        existing = {req.id for req in requirements}
        for req in invariant_requirements():
            if req.id not in existing:
                requirements.append(req)
                evidence_kinds = {
                    "pk_set_unchanged",
                    "preserved_values_unchanged",
                    "schema_expected",
                    "coverage_complete",
                    "within_budgets",
                    "declared_checks_complete",
                }
                status = (
                    "pass"
                    if outcome == "committed" and req.kind not in evidence_kinds
                    else "not_run"
                )
                checks.append(
                    CheckResult(
                        id=req.id,
                        category=req.kind,
                        status=status,
                        reason_code=None if status == "pass" else "MIGRATION_FAILED",
                    )
                )
        return checks, requirements

    def validate_rehearsal(self, request):
        from .evidence import capture_evidence, compare_evidence
        from .models import CheckSet
        from .report import seal_report
        from .sql_policy import inspect_sql

        run_id = str(request.run_id)
        run = self.store.get_run(run_id)
        candidate, raw = self.candidate(run["candidate_id"])
        key = f"{run_id}:{run['candidate_id']}"
        try:
            existing = self.store.get("report_pending", key)
            return self._publish_report(run, ReportPayload.model_validate(existing))
        except PreflightError as exc:
            if exc.code != "NOT_FOUND":
                raise
        if run["phase"] not in ("VALIDATING", "BLOCKED"):
            raise PreflightError("VALIDATION_NOT_READY")
        self.runtime.verify_resources(run, require_backup=True)
        before = self.baselines.get(run_id)
        after = None
        if run["clone_outcome"] == "committed" and before is not None:
            with self.runtime.connection(run, "clone_read") as con:
                after = capture_evidence(
                    con, candidate.contract, existing_columns=before.existing_columns
                )
            checkset = compare_evidence(
                before, after, candidate.contract, inspect_sql(raw, candidate.contract)
            )
        else:
            requirements = []
            checks = []
            for table in candidate.contract.tables:
                for index, check in enumerate(table.checks):
                    req_id = f"declared:{table.name}:{index}:{check.type}"
                    requirements.append(
                        Requirement(
                            id=req_id,
                            kind=check.type,
                            table=table.name,
                            column=getattr(check, "column", None),
                            policy_role="declared",
                        )
                    )
                    checks.append(
                        CheckResult(
                            id=req_id,
                            category=check.type,
                            status="not_run",
                            reason_code="MIGRATION_FAILED"
                            if run["clone_outcome"] == "rolled_back"
                            else "BASELINE_MEMORY_LOST",
                        )
                    )
            checkset = CheckSet(checks=checks, requirements=requirements)
        checks, requirements = self._complete_checks(checkset, run["clone_outcome"])
        verdict = evaluate(checks, requirements, run["clone_outcome"], checkset.coverage)
        payload = ReportPayload(
            evidence_backend=self.settings.evidence_backend,
            run_id=run_id,
            candidate_id=run["candidate_id"],
            operator_id=candidate.operator_id,
            created_at=utc_now(),
            source_instance_id=run["source_instance_id"],
            snapshot_id=run["snapshot_id"],
            clone_instance_id=run["clone_instance_id"],
            engine_major=18,
            dependency_versions={
                name: version(name) for name in ["mcp", "pglast", "psycopg", "boto3"]
            },
            migration_sha256=candidate.migration_sha256,
            contract_sha256=candidate.contract_sha256,
            before=before.public if before else None,
            after=after.public if after else None,
            checks=checks,
            validation_requirements=requirements,
            impact_summary=checkset.coverage,
            migration=TxOutcome.model_validate(run["migration"]),
            backup_available=True,
            verdict=verdict,
            apply_eligible_at_report_time=verdict == "PASS",
            untested_risks=[
                "Production traffic, application compatibility and downtime untested",
                "Historical clone proof; current source guards still required",
            ],
        )
        report = seal_report(payload)
        self.store.put_once("report_pending", key, report.payload.model_dump(mode="json"))
        return self._publish_report(run, report.payload)

    def _publish_report(self, run, payload):
        """Resume a durable sealed publication without remeasuring or changing timestamps."""
        from .report import render_report, seal_report

        run_id = run["run_id"]
        key = f"{run_id}:{run['candidate_id']}"
        report = seal_report(payload)
        if str(payload.run_id) != run_id or str(payload.candidate_id) != run["candidate_id"]:
            raise PreflightError("REPORT_CANDIDATE_MISMATCH")
        relative = f"reports/{run_id}/{run['candidate_id']}"
        self.artifacts.write_once(
            relative + ".json", canonical_json(report.model_dump(mode="json"))
        )
        markdown = render_report(payload).encode("utf-8")
        markdown_digest = self.artifacts.write_once(relative + ".md", markdown)
        self.store.put_once("report", key, report.model_dump(mode="json"))
        self.store.put_once(
            "report_artifact", key, {"path": relative, "markdown_sha256": markdown_digest}
        )
        if run["phase"] == "VALIDATING":
            self.store.complete_validation(run_id, payload.verdict, report.report_sha256)
        return {
            "verdict": payload.verdict,
            "report_sha256": report.report_sha256,
            "report_reference": relative + ".json",
            "apply_eligible_at_report_time": payload.apply_eligible_at_report_time,
            "checks": [check.model_dump(mode="json") for check in payload.checks],
        }

    def get_report(self, request):
        from .models import SealedReport

        run_id = str(request.run_id)
        run = self.store.get_run(run_id)
        candidate_id = str(request.candidate_id or run["candidate_id"])
        key = f"{run_id}:{candidate_id}"
        try:
            record = self.store.get("report", key)
            artifact = self.store.get("report_artifact", key)
        except PreflightError:
            raise PreflightError("REPORT_NOT_READY") from None
        report = SealedReport.model_validate(
            strict_json(self.artifacts.read(artifact["path"] + ".json"))
        )
        if report.model_dump(mode="json") != record:
            raise PreflightError("REPORT_INTEGRITY_ERROR")
        if sha256(canonical_json(report.payload.model_dump(mode="json"))) != report.report_sha256:
            raise PreflightError("REPORT_INTEGRITY_ERROR")
        markdown = self.artifacts.read(
            artifact["path"] + ".md", artifact["markdown_sha256"]
        ).decode("utf-8")
        return {
            **report.model_dump(mode="json"),
            "markdown": markdown,
            "current_state": self.get_run(request),
        }

    def apply_to_demo_source(self, request):
        from psycopg import sql

        from .db import execute_migration
        from .evidence import baseline_matches, capture_evidence, compare_evidence
        from .models import GetReport
        from .sql_policy import inspect_sql

        run_id = str(request.run_id)
        run = self.store.get_run(run_id)
        if self.store.has_apply(run_id):
            raise PreflightError("SOURCE_APPLY_REPLAY_REJECTED")
        if not (self.settings.enable_demo_source_apply or self._test_source_apply):
            raise PreflightError("SOURCE_APPLY_DISABLED")
        if self.settings.evidence_backend != "aws_rds" and not self._test_source_apply:
            raise PreflightError("TEST_BACKEND_SOURCE_APPLY_REFUSED")
        self._source_guard(request.source_instance_id, run["database_name"])
        if (
            run["phase"] != "AWAITING_APPROVAL"
            or run["cleanup_state"] != "NOT_REQUESTED"
            or run["candidate_id"] != str(request.candidate_id)
            or run_id not in self.baselines
        ):
            raise PreflightError("SOURCE_NOT_ELIGIBLE")
        candidate, raw = self.candidate(run["candidate_id"])
        report = self.get_report(GetReport(request_id=request.request_id, run_id=request.run_id))
        if (
            candidate.migration_sha256 != request.migration_sha256
            or report["report_sha256"] != request.report_sha256
            or report["payload"]["contract_sha256"] != candidate.contract_sha256
            or report["payload"]["verdict"] != "PASS"
        ):
            raise PreflightError("APPROVED_ARTIFACT_MISMATCH")
        self.runtime.verify_resources(run, require_backup=True)
        plan = inspect_sql(raw, candidate.contract)
        baseline = self.baselines[run_id]
        columns = baseline.existing_columns
        precheck_status = "NOT_RUN"

        def precheck(con):
            nonlocal precheck_status
            for table in sorted(t.name for t in candidate.contract.tables):
                schema, name = table.split(".")
                con.execute(
                    sql.SQL("LOCK TABLE {} IN ACCESS EXCLUSIVE MODE").format(
                        sql.Identifier(schema, name)
                    )
                )
            fresh = capture_evidence(
                con, candidate.contract, existing_columns=columns, in_transaction=True
            )
            if not baseline_matches(baseline, fresh):
                precheck_status = "DRIFT"
                raise PreflightError("SOURCE_DRIFT")
            precheck_status = "MATCH"

        def postcheck(con):
            after = capture_evidence(
                con, candidate.contract, existing_columns=columns, in_transaction=True
            )
            checkset = compare_evidence(baseline, after, candidate.contract, plan)
            checks, requirements = self._complete_checks(checkset, "committed")
            if evaluate(checks, requirements, "committed", checkset.coverage) != "PASS":
                raise PreflightError("SOURCE_POSTCONDITION_FAILED")
            return True

        self.store.begin_apply(run_id, request.model_dump(mode="json"))
        try:
            with self.runtime.connection(run, "source_write") as con:
                outcome = execute_migration(
                    con,
                    raw,
                    plan,
                    candidate.contract,
                    checks_before_commit=postcheck,
                    precheck=precheck,
                )
        except Exception:
            outcome = TxOutcome(outcome="unknown", elapsed_ms=0, reason_code="CONNECTION_LOST")
        confirmation = False
        if outcome.outcome == "committed":
            try:
                with self.runtime.connection(run, "source_read") as con:
                    after = capture_evidence(con, candidate.contract, existing_columns=columns)
                checkset = compare_evidence(baseline, after, candidate.contract, plan)
                checks, requirements = self._complete_checks(checkset, "committed")
                confirmation = (
                    evaluate(checks, requirements, "committed", checkset.coverage) == "PASS"
                )
            except Exception:
                confirmation = False
        state = (
            ("APPLIED" if confirmation else "APPLIED_NEEDS_ATTENTION")
            if outcome.outcome == "committed"
            else ("STALE" if outcome.reason_code == "SOURCE_DRIFT" else "APPLY_FAILED")
            if outcome.outcome == "rolled_back"
            else "APPLY_OUTCOME_UNKNOWN"
        )
        receipt = {
            "receipt_id": str(uuid4()),
            "run_id": run_id,
            "report_sha256": request.report_sha256,
            "migration_sha256": request.migration_sha256,
            "source_instance_id": request.source_instance_id,
            "transaction": outcome.model_dump(mode="json"),
            "confirmation": confirmation,
            "state": state,
            "created_at": utc_now(),
            "precheck_status": precheck_status,
        }
        self.store.put_once("receipt", receipt["receipt_id"], receipt)
        self.artifacts.write_once(
            f"reports/{run_id}/{receipt['receipt_id']}.receipt.json", canonical_json(receipt)
        )
        self.store.finish_apply(run_id, receipt)
        self.store.transition(run_id, "APPLYING", state)
        return receipt

    def cleanup_run(self, request):
        run_id = str(request.run_id)
        run = self.store.get_run(run_id)
        if run["phase"] in {
            "MIGRATING",
            "APPLYING",
            "APPLY_OUTCOME_UNKNOWN",
            "CLONE_OUTCOME_UNKNOWN",
            "SNAPSHOTTING",
            "RESTORING",
            "VALIDATING",
        }:
            raise PreflightError("CLEANUP_UNSAFE_STATE")
        for supplied, field in [
            (request.clone_instance_id, "clone_instance_id"),
            (request.snapshot_id, "snapshot_id"),
        ]:
            if supplied and (supplied != run[field] or supplied == run["source_instance_id"]):
                raise PreflightError("CLEANUP_RESOURCE_MISMATCH")
        # Preserve every sealed report and receipt before requesting external deletion.
        for report in self.store.list_records("report"):
            if report["payload"]["run_id"] == run_id:
                from .models import GetReport

                self.get_report(
                    GetReport(
                        request_id=request.request_id,
                        run_id=run_id,
                        candidate_id=report["payload"]["candidate_id"],
                    )
                )
        self.store.begin_cleanup(run_id, request.model_dump(mode="json"))
        try:
            result = self.runtime.cleanup(run, request, self.store.has_apply(run_id))
        except Exception:
            self.store.set_cleanup(run_id, "CLEANUP_ERROR")
            raise
        self.store.set_cleanup(run_id, result["cleanup_state"])
        receipt = {
            "receipt_id": str(uuid4()),
            "run_id": run_id,
            "kind": "cleanup",
            "created_at": utc_now(),
            **result,
        }
        self.store.put_once("receipt", receipt["receipt_id"], receipt)
        self.artifacts.write_once(
            f"reports/{run_id}/{receipt['receipt_id']}.receipt.json", canonical_json(receipt)
        )
        return receipt
