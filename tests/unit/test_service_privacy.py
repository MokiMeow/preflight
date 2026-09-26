import base64
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from preflight.config import Settings
from preflight.service import RehearsalService

ROOT = Path(__file__).parents[2]


def candidate_arguments(sql: bytes, contract: dict) -> dict:
    return {
        "request_id": str(uuid4()),
        "sql_utf8_b64": base64.b64encode(sql).decode("ascii"),
        "expected_migration_sha256": hashlib.sha256(sql).hexdigest(),
        "contract": contract,
        "operator_id": "unit-operator",
    }


def test_invalid_argument_sentinel_never_echoed(tmp_path):
    service = RehearsalService(Settings(state_dir=tmp_path))
    sentinel = "privacy-sentinel-secret-value"
    result = service.call("get_run", {"request_id": sentinel, "run_id": str(uuid4())})
    assert sentinel not in str(result)
    assert result["request_id"] is None
    request_id = str(uuid4())
    result = service.call("get_run", {"request_id": request_id, "run_id": str(uuid4()),
                                      "password": sentinel})
    assert result["error_code"] == "INVALID_INPUT"
    assert sentinel not in str(result)
    assert result["request_id"] == request_id


def test_absent_cloud_scope_no_start_effects(tmp_path):
    service = RehearsalService(Settings(state_dir=tmp_path))
    result = service.call("start_rehearsal", {"request_id": str(uuid4()), "candidate_id": str(uuid4()),
                          "source_instance_id": "unowned-source", "database_name": "preflight_demo"})
    assert result["error_code"] == "SOURCE_NOT_ALLOWLISTED"
    assert service.store.list_runs() == []


def test_deployed_test_source_adapter_cannot_be_enabled(tmp_path):
    import pytest

    from preflight.models import PreflightError
    with pytest.raises(PreflightError, match="TEST_SOURCE_ADAPTER_REFUSED"):
        RehearsalService(Settings(state_dir=tmp_path), test_source_apply=True)


def test_registration_and_run_status_use_typed_complete_public_outputs(tmp_path):
    service = RehearsalService(Settings(state_dir=tmp_path))
    contract = json.loads((ROOT / "config/contract.example.json").read_text(encoding="utf-8"))
    sql = (ROOT / "fixtures/good.sql").read_bytes()
    registered = service.call("register_candidate", candidate_arguments(sql, contract))
    assert registered["ok"] is True
    assert registered["data"]["coverage_warnings"] == []
    candidate_id = registered["data"]["candidate_id"]

    run_id = str(uuid4())
    service.store.create_run(
        {
            "run_id": run_id,
            "candidate_id": candidate_id,
            "source_instance_id": "preflight-demo-source",
            "database_name": "preflight_demo",
            "account_id": "000000000000",
            "region": "us-east-1",
            "created_at": "2026-09-26T00:00:00Z",
            "snapshot_id": "preflight-snapshot",
            "clone_instance_id": "preflight-clone",
            "resource_expires_at": "2026-09-27T00:00:00Z",
        }
    )
    status = service.call(
        "get_run", {"request_id": str(uuid4()), "run_id": run_id}
    )
    assert status["ok"] is True
    assert status["data"]["migration_sha256"] == registered["data"]["migration_sha256"]
    assert status["data"]["contract_sha256"] == registered["data"]["contract_sha256"]
    assert status["data"]["progress_label"] == "REGISTERED"
    assert status["data"]["elapsed_seconds"] >= 0
    assert status["data"]["last_observed_at"] is None
    assert status["data"]["apply_eligible_now"] is False
    assert status["data"]["eligibility_is_preliminary"] is True
    assert status["data"]["eligibility_reason"] == "PHASE_NOT_AWAITING_APPROVAL"


def test_registration_reports_static_missing_coverage_without_echoing_sql(tmp_path):
    service = RehearsalService(Settings(state_dir=tmp_path))
    contract = json.loads((ROOT / "config/contract.example.json").read_text(encoding="utf-8"))
    contract["tables"][0]["checks"] = [{"type": "row_count_unchanged"}]
    sql = b"ALTER TABLE public.customers ADD COLUMN account_tier text;\n"
    result = service.call("register_candidate", candidate_arguments(sql, contract))
    assert result["ok"] is True
    assert result["data"]["coverage_warnings"] == [
        "COVERAGE_INCOMPLETE:public.customers:account_tier:add_column"
    ]
    assert "ALTER TABLE" not in str(result)
