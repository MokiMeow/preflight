"""Missing local DB/service clauses; disposable loopback PG, no approval proof."""

import base64
import json
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from preflight.artifacts import sha256
from preflight.evidence import baseline_matches, capture_evidence
from preflight.models import Contract
from preflight.service import RehearsalService
from tests.postgres.test_service import call, pass_rehearsal, ready_run, register, source_request
from tests.postgres.test_service import service_pair as service_pair


def revision_request(run_id, candidate, contract):
    raw = Path("fixtures/good.sql").read_bytes()
    return dict(
        request_id=str(uuid4()),
        run_id=run_id,
        parent_candidate_id=candidate["candidate_id"],
        sql_utf8_b64=base64.b64encode(raw).decode(),
        expected_migration_sha256=sha256(raw),
        contract=contract.model_dump(mode="json"),
        operator_id="test-operator",
    )


def failed_rehearsal(service, contract):
    bad = register(service, "fixtures/bad.sql", contract)
    run_id = ready_run(service, bad)
    call(service, "capture_baseline", run_id=run_id)
    result = call(service, "apply_to_clone", run_id=run_id, candidate_id=bad["candidate_id"])
    assert result["transaction"]["outcome"] == "rolled_back"
    assert result["baseline_unchanged"] is True
    assert call(service, "validate_rehearsal", run_id=run_id)["verdict"] == "BLOCK"
    return run_id, bad


def test_d05_real_physical_row_order_changes_without_changing_roots(db, contract):
    db.execute("CREATE UNIQUE INDEX fixture_reverse ON public.customers(id DESC)")
    before = capture_evidence(db, contract)
    initial = db.execute("SELECT id FROM public.customers ORDER BY ctid LIMIT 1").fetchone()[0]
    db.execute("CLUSTER public.customers USING fixture_reverse")
    reordered = db.execute("SELECT id FROM public.customers ORDER BY ctid LIMIT 1").fetchone()[0]
    assert initial != reordered
    assert baseline_matches(before, capture_evidence(db, contract))


def test_d18_independent_table_and_index_oids_do_not_change_normalized_roots(
    service_pair, contract
):
    service, runtime = service_pair
    candidate = register(service, "fixtures/good.sql", contract)
    run_id = ready_run(service, candidate)
    run = service.store.get_run(run_id)
    with (
        runtime.connection(run, "source_read") as source,
        runtime.connection(run, "clone_read") as clone,
    ):
        clone.execute("DROP TABLE public.customers")
        clone.execute(
            "CREATE TABLE public.customers(id integer PRIMARY KEY,email text NOT NULL,created_at timestamptz NOT NULL)"
        )
        clone.execute(
            "INSERT INTO public.customers SELECT i,'customer-'||i::text||'@example.invalid',timestamptz '2026-01-01 00:00:00+00'+i*interval '1 second' FROM generate_series(1,1000) i"
        )
        source_oid = source.execute("SELECT 'public.customers'::regclass::oid").fetchone()[0]
        clone_oid = clone.execute("SELECT 'public.customers'::regclass::oid").fetchone()[0]
        assert source_oid != clone_oid
        assert (
            source.execute("SELECT 'public.customers_pkey'::regclass::oid").fetchone()[0]
            != clone.execute("SELECT 'public.customers_pkey'::regclass::oid").fetchone()[0]
        )
        assert baseline_matches(
            capture_evidence(source, contract), capture_evidence(clone, contract)
        )


@pytest.mark.parametrize("loss", ["ram", "nonpreserved_drift"])
def test_d19_d20_revision_requires_private_maps_and_full_unchanged_baseline(
    service_pair, contract, loss
):
    service, runtime = service_pair
    if loss == "nonpreserved_drift":
        candidate = register(service, "fixtures/bad.sql", contract)
        run_id = ready_run(service, candidate)
        run = service.store.get_run(run_id)
        for mode in ["source_read", "clone_read"]:
            with runtime.connection(run, mode) as con:
                con.execute("ALTER TABLE public.customers ADD COLUMN notes text")
        call(service, "capture_baseline", run_id=run_id)
        call(service, "apply_to_clone", run_id=run_id, candidate_id=candidate["candidate_id"])
        call(service, "validate_rehearsal", run_id=run_id)
        with runtime.connection(run, "clone_read") as con:
            con.execute("UPDATE public.customers SET notes='unprotected-drift' WHERE id=1")
            fresh = capture_evidence(con, contract)
        original = service.baselines[run_id]
        assert original.public.tables[0].preserved_sha256 == fresh.public.tables[0].preserved_sha256
        assert original.public.tables[0].full_sha256 != fresh.public.tables[0].full_sha256
    else:
        run_id, candidate = failed_rehearsal(service, contract)
        service.baselines.clear()
    before_candidate = service.store.get_run(run_id)["candidate_id"]
    refused = service.call("register_candidate", revision_request(run_id, candidate, contract))
    assert refused["error_code"] == "FRESH_REHEARSAL_REQUIRED"
    assert service.store.get_run(run_id)["candidate_id"] == before_candidate


@pytest.mark.parametrize("drift", ["schema", "nonpreserved"])
def test_a05_a07_source_drift_stales_before_migration(service_pair, contract, drift):
    service, runtime = service_pair
    service._test_source_apply = True
    if drift == "nonpreserved":
        candidate = register(service, "fixtures/good.sql", contract)
        run_id = ready_run(service, candidate)
        for mode in ["source_read", "clone_read"]:
            with runtime.connection(service.store.get_run(run_id), mode) as con:
                con.execute("ALTER TABLE public.customers ADD COLUMN notes text")
        call(service, "capture_baseline", run_id=run_id)
        call(service, "apply_to_clone", run_id=run_id, candidate_id=candidate["candidate_id"])
        report = call(service, "validate_rehearsal", run_id=run_id)
        assert report["verdict"] == "PASS"
    else:
        run_id, candidate, report = pass_rehearsal(service, contract)
    run = service.store.get_run(run_id)
    with runtime.connection(run, "source_read") as con:
        con.execute(
            "CREATE UNIQUE INDEX fixture_drift ON public.customers(email DESC)"
            if drift == "schema"
            else "UPDATE public.customers SET notes='unprotected-drift' WHERE id=1"
        )
        fresh = capture_evidence(con, contract)
        baseline = service.baselines[run_id]
        if drift == "nonpreserved":
            assert (
                baseline.public.tables[0].preserved_sha256
                == fresh.public.tables[0].preserved_sha256
            )
            assert baseline.public.tables[0].full_sha256 != fresh.public.tables[0].full_sha256
    result = service.call("apply_to_demo_source", source_request(run_id, candidate, report))
    assert result["ok"] and result["data"]["state"] == "STALE"
    assert result["data"]["transaction"]["outcome"] == "rolled_back"
    with runtime.connection(run, "source_read") as con:
        assert (
            "account_tier"
            not in capture_evidence(con, contract).existing_columns["public.customers"]
        )


def test_a11_same_and_new_request_ids_cannot_reexecute_committed_source(service_pair, contract):
    service, runtime = service_pair
    service._test_source_apply = True
    run_id, candidate, report = pass_rehearsal(service, contract)
    request = source_request(run_id, candidate, report)
    first = service.call("apply_to_demo_source", request)
    assert first["ok"] and first["data"]["state"] == "APPLIED"
    for retry in [request, {**request, "request_id": str(uuid4())}]:
        assert (
            service.call("apply_to_demo_source", retry)["error_code"]
            == "SOURCE_APPLY_REPLAY_REJECTED"
        )
    assert runtime.writer_count == 1


def test_a15_a16_restart_after_durable_intent_without_sql_never_replays(service_pair, contract):
    service, runtime = service_pair
    run_id, candidate, report = pass_rehearsal(service, contract)
    request = source_request(run_id, candidate, report)
    service.store.begin_apply(run_id, request)
    assert service.store.get_run(run_id)["phase"] == "APPLYING"
    restarted = RehearsalService(service.settings, runtime, test_source_apply=True)
    try:
        assert restarted.store.get_run(run_id)["phase"] == "APPLY_OUTCOME_UNKNOWN"
        for retry in [request, {**request, "request_id": str(uuid4())}]:
            assert (
                restarted.call("apply_to_demo_source", retry)["error_code"]
                == "SOURCE_APPLY_REPLAY_REJECTED"
            )
        assert runtime.writer_count == 0
        with runtime.connection(service.store.get_run(run_id), "source_read") as con:
            assert (
                "account_tier"
                not in capture_evidence(con, contract).existing_columns["public.customers"]
            )
    finally:
        restarted.executor.shutdown(wait=True)


def test_d15_private_database_error_value_absent_from_tool_logs_and_reports(
    service_pair, contract, caplog
):
    service, runtime = service_pair
    private = "private-password-like-db-error-sentinel"
    raw = f"UPDATE public.customers SET email='{private}' WHERE id=1; UPDATE public.customers SET created_at=NULL WHERE id=1".encode()
    candidate = call(
        service,
        "register_candidate",
        sql_utf8_b64=base64.b64encode(raw).decode(),
        expected_migration_sha256=sha256(raw),
        contract=contract.model_dump(mode="json"),
        operator_id="test-operator",
    )
    run_id = ready_run(service, candidate)
    baseline = call(service, "capture_baseline", run_id=run_id)
    with runtime.connection(service.store.get_run(run_id), "clone_read") as con:
        con.execute("BEGIN")
        try:
            with pytest.raises(psycopg.errors.NotNullViolation) as actual:
                con.execute(raw.decode(), prepare=False)
            assert private in str(actual.value)
        finally:
            con.execute("ROLLBACK")
    outcome = call(service, "apply_to_clone", run_id=run_id, candidate_id=candidate["candidate_id"])
    assert outcome["transaction"]["outcome"] == "rolled_back"
    assert outcome["transaction"]["sqlstate"] == "23502"
    assert call(service, "validate_rehearsal", run_id=run_id)["verdict"] == "BLOCK"
    report = call(service, "get_report", run_id=run_id)
    assert private not in str([baseline, outcome, report])
    assert private not in caplog.text


@pytest.mark.parametrize("scope", ["source", "database", "collision"])
def test_a02_source_scope_refusal_precedes_writer(service_pair, contract, scope):
    service, runtime = service_pair
    service._test_source_apply = True
    run_id, candidate, report = pass_rehearsal(service, contract)
    request = source_request(run_id, candidate, report)
    if scope == "source":
        request["source_instance_id"] = "unowned-source"
    elif scope == "database":
        service.settings = service.settings.model_copy(
            update={"database_name": "different_database"}
        )
    else:
        # Corrupt local resource identity as an adversarial persisted input.
        with service.store.transaction() as con:
            row = con.execute("SELECT value FROM runs WHERE id=?", (run_id,)).fetchone()
            value = json.loads(bytes(row[0]))
            value["clone_instance_id"] = value["source_instance_id"]
            con.execute("UPDATE runs SET value=? WHERE id=?", (json.dumps(value).encode(), run_id))
    response = service.call("apply_to_demo_source", request)
    assert response["error_code"] == (
        "SOURCE_CLONE_COLLISION" if scope == "collision" else "SOURCE_NOT_ALLOWLISTED"
    )
    assert runtime.writer_count == 0 and not service.store.has_apply(run_id)


@pytest.mark.parametrize(
    "changed", ["migration_hash", "report_hash", "contract_file", "contract_record", "report_file"]
)
def test_a03_approved_artifact_changes_refused_without_writer(service_pair, contract, changed):
    service, runtime = service_pair
    service._test_source_apply = True
    run_id, candidate, report = pass_rehearsal(service, contract)
    request = source_request(run_id, candidate, report)
    if changed.endswith("hash"):
        request["migration_sha256" if changed == "migration_hash" else "report_sha256"] = "0" * 64
    elif changed == "contract_file":
        path = service.artifacts.path(
            f"artifacts/{candidate['candidate_id']}/contract.canonical.json"
        )
        path.write_bytes(path.read_bytes() + b" ")
    elif changed == "contract_record":
        with service.store.transaction() as con:
            row = con.execute(
                "SELECT value FROM records WHERE kind='candidate' AND id=?",
                (candidate["candidate_id"],),
            ).fetchone()
            value = json.loads(bytes(row[0]))
            value["contract"]["max_migration_seconds"] = 59
            con.execute(
                "UPDATE records SET value=? WHERE kind='candidate' AND id=?",
                (json.dumps(value).encode(), candidate["candidate_id"]),
            )
    else:
        path = service.artifacts.path(f"reports/{run_id}/{candidate['candidate_id']}.json")
        value = json.loads(path.read_bytes())
        value["payload"]["verdict"] = "BLOCK"
        path.write_text(json.dumps(value), encoding="utf8")
    response = service.call("apply_to_demo_source", request)
    expected = {
        "migration_hash": "APPROVED_ARTIFACT_MISMATCH",
        "report_hash": "APPROVED_ARTIFACT_MISMATCH",
        "contract_file": "ARTIFACT_INTEGRITY_ERROR",
        "contract_record": "CONTRACT_INTEGRITY_ERROR",
        "report_file": "REPORT_INTEGRITY_ERROR",
    }
    assert response["error_code"] == expected[changed]
    assert runtime.writer_count == 0 and not service.store.has_apply(run_id)


@pytest.mark.parametrize("eligibility", ["noncurrent", "missing_baseline", "blocked"])
def test_a04_ineligible_run_refused_without_writer(service_pair, contract, eligibility):
    service, runtime = service_pair
    service._test_source_apply = True
    if eligibility == "blocked":
        run_id, candidate = failed_rehearsal(service, contract)
        report = call(service, "get_report", run_id=run_id)
    else:
        run_id, candidate, report = pass_rehearsal(service, contract)
    request = source_request(run_id, candidate, report)
    if eligibility == "noncurrent":
        request["candidate_id"] = register(service, "fixtures/good.sql", contract)["candidate_id"]
    elif eligibility == "missing_baseline":
        service.baselines.clear()
    response = service.call("apply_to_demo_source", request)
    assert response["error_code"] == "SOURCE_NOT_ELIGIBLE"
    assert runtime.writer_count == 0 and not service.store.has_apply(run_id)


@pytest.mark.parametrize(
    "checks", [["no_nulls"], ["unique_non_null"], ["no_nulls", "unique_non_null"]]
)
def test_a04_warn_with_passing_weak_checks_refuses_source_writer(service_pair, contract, checks):
    service, runtime = service_pair
    service._test_source_apply = True
    data = contract.model_dump()
    data["tables"][0]["expected_schema"]["added_columns"] = []
    data["tables"][0]["checks"] = [{"type": "row_count_unchanged"}] + [
        {"type": kind, "column": "notes"} for kind in checks
    ]
    weak = Contract.model_validate(data)
    raw = b"UPDATE public.customers SET notes=email"
    candidate = call(
        service,
        "register_candidate",
        sql_utf8_b64=base64.b64encode(raw).decode(),
        expected_migration_sha256=sha256(raw),
        contract=weak.model_dump(mode="json"),
        operator_id="test-operator",
    )
    run_id = ready_run(service, candidate)
    for mode in ["source_read", "clone_read"]:
        with runtime.connection(service.store.get_run(run_id), mode) as con:
            con.execute("ALTER TABLE public.customers ADD COLUMN notes text")
    call(service, "capture_baseline", run_id=run_id)
    assert (
        call(service, "apply_to_clone", run_id=run_id, candidate_id=candidate["candidate_id"])[
            "transaction"
        ]["outcome"]
        == "committed"
    )
    report = call(service, "validate_rehearsal", run_id=run_id)
    assert report["verdict"] == "WARN"
    public = call(service, "get_report", run_id=run_id)["payload"]
    assert all(
        c["status"] == "pass"
        for c in public["checks"]
        if c["category"] in {"row_count_unchanged", *checks}
    )
    refused = service.call("apply_to_demo_source", source_request(run_id, candidate, report))
    assert refused["error_code"] == "SOURCE_NOT_ELIGIBLE"
    assert runtime.writer_count == 0 and not service.store.has_apply(run_id)
