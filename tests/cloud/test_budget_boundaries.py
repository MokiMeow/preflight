"""Cost admission occurs before provider creates; existing resources stay observable."""

import pytest

from preflight.models import PreflightError
from tests.cloud.test_rds import cloud as cloud


def test_missing_budget_admission_refuses_snapshot_create(cloud):
    cloud.adapter.budget_guard = None
    cloud.source()
    cloud.absent_snapshot()
    cloud.inventory()
    cloud.identity()
    with pytest.raises(PreflightError, match="BUDGET_ADMISSION_REQUIRED"):
        cloud.adapter.ensure_snapshot(cloud.intent)
    assert cloud.store.get(cloud.intent.run_id)["snapshot_reserved"] == 1


def test_failed_budget_admission_refuses_clone_restore(cloud):
    def deny(intent, kind):
        assert intent == cloud.intent and kind == "clone"
        raise PreflightError("BUDGET_COST_UNKNOWN")

    cloud.adapter.budget_guard = deny
    cloud.snap_read()
    cloud.source()
    cloud.absent_clone()
    cloud.inventory()
    cloud.identity()
    with pytest.raises(PreflightError, match="BUDGET_COST_UNKNOWN"):
        cloud.adapter.ensure_clone(cloud.intent)
    assert cloud.store.get(cloud.intent.run_id)["clone_reserved"] == 1


def test_existing_snapshot_is_observed_without_a_new_cost_reservation(cloud):
    cloud.adapter.budget_guard = None
    cloud.source()
    cloud.snap_read()
    assert cloud.adapter.ensure_snapshot(cloud.intent).status == "available"
