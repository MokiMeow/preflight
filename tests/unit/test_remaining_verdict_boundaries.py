"""Remaining P14/V08 local clauses, without connected clients."""

import base64
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest

from preflight.artifacts import sha256
from preflight.config import Settings
from preflight.models import CheckResult, Contract, PreflightError
from preflight.service import RehearsalService
from preflight.sql_policy import inspect_sql, resolve_coverage
from preflight.storage import utc_now
from preflight.verdict import evaluate, invariant_requirements
from tests.cloud.test_rds import cloud as cloud


@pytest.mark.parametrize(
    "weak", [["no_nulls"], ["unique_non_null"], ["no_nulls", "unique_non_null"]]
)
def test_v08_weak_checks_cannot_certify_unprotected_value_intent(weak):
    data = Contract.model_validate_json(
        Path("config/contract.example.json").read_text()
    ).model_dump()
    data["tables"][0]["expected_schema"]["added_columns"] = []
    data["tables"][0]["checks"] = [{"type": "row_count_unchanged"}] + [
        {"type": kind, "column": "notes"} for kind in weak
    ]
    contract = Contract.model_validate(data)
    plan = inspect_sql(b"UPDATE public.customers SET notes='incorrect-value'", contract)
    coverage = resolve_coverage(
        plan, contract, {"public.customers": ["id", "email", "created_at", "notes"]}
    )
    assert len(coverage) == 1 and not coverage[0].complete
    assert coverage[0].reason_code == "COVERAGE_INCOMPLETE"
    requirements = invariant_requirements()
    # Even an otherwise passing manifest cannot override unresolved write intent.
    checks = [CheckResult(id=r.id, category=r.kind, status="pass") for r in requirements]
    assert evaluate(checks, requirements, "committed", coverage) == "WARN"


@pytest.mark.parametrize("mismatch", ["version", "major"])
def test_p14_parser_mismatch_refused_before_parse_or_execution(monkeypatch, mismatch):
    import preflight.sql_policy as policy

    contract = Contract.model_validate_json(Path("config/contract.example.json").read_text())
    if mismatch == "version":
        monkeypatch.setattr(policy.pglast, "__version__", "v8.3")
    else:
        monkeypatch.setattr(policy.pglast, "get_postgresql_version", lambda: (17, 0))
    monkeypatch.setattr(policy, "parse_sql", lambda _: pytest.fail("mismatched parser invoked"))
    with pytest.raises(PreflightError, match="PARSER_MAJOR_MISMATCH"):
        inspect_sql(b"UPDATE public.customers SET email=email", contract)


def test_p04_create_table_statement_is_rejected_without_a_plan():
    contract = Contract.model_validate_json(Path("config/contract.example.json").read_text())
    with pytest.raises(PreflightError, match="SQL_POLICY_REJECTED"):
        inspect_sql(b"CREATE TABLE public.unapproved(id integer)", contract)


@pytest.mark.parametrize("failure", ["missing", "failed", "wrong_source"])
def test_a08_recovery_snapshot_refusal_uses_actual_adapter_without_network(cloud, failure):
    cloud.identity()
    if failure == "missing":
        cloud.rds.add_client_error(
            "describe_db_snapshots",
            "DBSnapshotNotFound",
            expected_params={"DBSnapshotIdentifier": cloud.intent.snapshot_id},
        )
        expected = "AWS_RESOURCE_ABSENT"
    else:
        changes = (
            {"Status": "failed"}
            if failure == "failed"
            else {"DBInstanceIdentifier": "unowned-source"}
        )
        snapshot = cloud.snapshot(**changes)
        cloud.rds.add_response(
            "describe_db_snapshots",
            {"DBSnapshots": [snapshot]},
            {"DBSnapshotIdentifier": cloud.intent.snapshot_id},
        )
        if failure == "failed":
            cloud.tags(snapshot["DBSnapshotArn"], cloud.intent.tags())
        expected = "AWS_RESOURCE_FAILED" if failure == "failed" else "AWS_SNAPSHOT_SOURCE_MISMATCH"
    with pytest.raises(PreflightError, match=expected):
        cloud.adapter.inspect_snapshot(cloud.intent)


def real_local_run(tmp_path):
    service = RehearsalService(Settings(state_dir=tmp_path))
    raw = Path("fixtures/good.sql").read_bytes()
    candidate = service.call(
        "register_candidate",
        {
            "request_id": str(uuid4()),
            "sql_utf8_b64": base64.b64encode(raw).decode(),
            "expected_migration_sha256": sha256(raw),
            "contract": Contract.model_validate_json(
                Path("config/contract.example.json").read_text()
            ).model_dump(mode="json"),
            "operator_id": "unit-operator",
        },
    )
    assert candidate["ok"]
    candidate_id = candidate["data"]["candidate_id"]
    run_id = str(uuid4())
    service.store.create_run(
        {
            "run_id": run_id,
            "candidate_id": candidate_id,
            "source_instance_id": "unit-source",
            "database_name": "preflight_demo",
            "snapshot_id": "unit-snapshot",
            "clone_instance_id": "unit-clone",
            "created_at": utc_now(),
        }
    )
    for old, new in [
        ("REGISTERED", "SNAPSHOTTING"),
        ("SNAPSHOTTING", "RESTORING"),
        ("RESTORING", "READY"),
        ("READY", "BASELINED"),
    ]:
        service.store.transition(run_id, old, new)
    return service, run_id, candidate_id


@pytest.mark.parametrize("tool", ["apply_to_clone", "apply_to_demo_source"])
def test_n21_run_status_remains_responsive_during_long_mutation(tmp_path, monkeypatch, tool):
    service, run_id, candidate_id = real_local_run(tmp_path)
    entered, release = threading.Event(), threading.Event()
    executions = []
    if tool == "apply_to_demo_source":
        for old, new in [
            ("BASELINED", "MIGRATING"),
            ("MIGRATING", "VALIDATING"),
            ("VALIDATING", "PASS"),
            ("PASS", "AWAITING_APPROVAL"),
        ]:
            service.store.transition(run_id, old, new)

    def long_mutation(request):
        executions.append(tool)
        if tool == "apply_to_clone":
            service.store.transition(run_id, "BASELINED", "MIGRATING")
        else:
            service.store.begin_apply(run_id, {"request_id": str(request.request_id)})
        entered.set()
        assert release.wait(5), "bounded mutation fixture was not released"
        raise PreflightError("UNIT_LONG_OPERATION_FINISHED")

    monkeypatch.setattr(service, tool, long_mutation)
    arguments = {"request_id": str(uuid4()), "run_id": run_id, "candidate_id": candidate_id}
    if tool == "apply_to_demo_source":
        arguments.update(
            migration_sha256="0" * 64, report_sha256="1" * 64, source_instance_id="unit-source"
        )
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            mutation = pool.submit(service.call, tool, arguments)
            try:
                assert entered.wait(2)
                status = pool.submit(
                    service.call, "get_run", {"request_id": str(uuid4()), "run_id": run_id}
                )
                observed = status.result(timeout=1)
                assert observed["ok"]
                expected = "MIGRATING" if tool == "apply_to_clone" else "APPLYING"
                assert observed["state"] == observed["data"]["phase"] == expected
                assert not mutation.done()
            finally:
                release.set()
                assert mutation.result(timeout=2)["error_code"] == "UNIT_LONG_OPERATION_FINISHED"
        assert executions == [tool]  # observation never retries the held operation
    finally:
        service.executor.shutdown(wait=True)


def test_n21_run_status_envelope_uses_same_phase_snapshot(tmp_path, monkeypatch):
    service, run_id, _ = real_local_run(tmp_path)
    service.store.transition(run_id, "BASELINED", "MIGRATING")
    original = service.get_run

    def concurrent_completion(request):
        observed = original(request)
        service.store.transition(run_id, "MIGRATING", "VALIDATING")
        return observed

    monkeypatch.setattr(service, "get_run", concurrent_completion)
    try:
        result = service.call("get_run", {"request_id": str(uuid4()), "run_id": run_id})
        assert result["ok"]
        assert result["state"] == result["data"]["phase"] == "MIGRATING"
        assert service.store.get_run(run_id)["phase"] == "VALIDATING"
    finally:
        service.executor.shutdown(wait=True)
