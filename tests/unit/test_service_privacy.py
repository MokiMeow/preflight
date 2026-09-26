from uuid import uuid4

from preflight.config import Settings
from preflight.service import RehearsalService


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
