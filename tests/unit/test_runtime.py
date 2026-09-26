"""Deployment composition test with inert clients, no network or credentials."""

from types import SimpleNamespace

from preflight.config import Settings
from preflight.runtime import build_runtime


def test_cloud_runtime_wires_tag_inventory_client(monkeypatch, tmp_path):
    import boto3

    clients = {}

    class Session:
        def __init__(self, **kwargs):
            assert kwargs == {"region_name": "ap-south-1"}

        def client(self, name, **kwargs):
            assert kwargs["config"].retries["max_attempts"] == 0
            clients[name] = SimpleNamespace(meta=SimpleNamespace(region_name="ap-south-1"))
            return clients[name]

    monkeypatch.setattr(boto3, "Session", Session)
    runtime = build_runtime(
        Settings(
            state_dir=tmp_path,
            creation_authorized=True,
            approved_budget_ceiling=10,
            account_id="123456789012",
            region="ap-south-1",
            source_instance_id="owned-source",
            source_allowlist=["owned-source"],
            db_subnet_group_name="private-subnets",
            clone_security_group_ids=["sg-123abc"],
        )
    )
    assert runtime.adapter.tagging is clients["resourcegroupstaggingapi"]
    assert set(clients) == {"rds", "sts", "resourcegroupstaggingapi", "secretsmanager"}


def test_explicit_bounded_ceiling_can_exceed_previous_operator_limit():
    import pytest
    from pydantic import ValidationError

    assert Settings(approved_budget_ceiling=1000).approved_budget_ceiling == 1000
    assert Settings().approved_budget_ceiling is None
    for value in (0, -1, float("inf"), float("nan")):
        with pytest.raises(ValidationError):
            Settings(approved_budget_ceiling=value)


def _runtime_settings(tmp_path, **changes):
    values = dict(
        state_dir=tmp_path,
        creation_authorized=True,
        account_id="123456789012",
        region="ap-south-1",
        source_instance_id="owned-source",
        source_allowlist=["owned-source"],
        db_subnet_group_name="private-subnets",
        clone_security_group_ids=["sg-123abc"],
    )
    values.update(changes)
    return Settings(**values)


def _inert_clients(monkeypatch):
    import boto3

    class Session:
        def __init__(self, **kwargs):
            pass

        def client(self, name, **kwargs):
            return SimpleNamespace(meta=SimpleNamespace(region_name="ap-south-1"))

    monkeypatch.setattr(boto3, "Session", Session)


def test_explicit_unlimited_authorization_bypasses_only_budget_admission(monkeypatch, tmp_path):
    from uuid import UUID

    import pytest

    from preflight.jobs import ResourceIntent
    from preflight.models import PreflightError

    _inert_clients(monkeypatch)
    monkeypatch.setattr(
        "preflight.budget.BudgetLedger",
        lambda *args: pytest.fail(
            "unlimited must not manufacture cost facts or open bounded ledger"
        ),
    )
    settings = _runtime_settings(tmp_path, unlimited_budget_authorized=True)
    runtime = build_runtime(settings)
    intent = ResourceIntent.for_run(UUID(int=1), settings.owner, "2030-01-01T00:00:00Z")
    for kind in ("snapshot", "clone"):
        assert runtime.adapter.budget_guard(intent, kind) is None
    assert not (tmp_path / "budget.sqlite").exists()
    assert runtime.adapter.policy.creation_authorized is True
    assert runtime.adapter.policy.source_instance_id == "owned-source"
    assert runtime.adapter.policy.max_clones == 1
    assert runtime.adapter.policy.max_snapshots == settings.max_run_owned_snapshots
    assert runtime.adapter.policy.subnet_group == "private-subnets"
    assert runtime.adapter.policy.security_group_ids == ("sg-123abc",)
    with pytest.raises(PreflightError, match="SOURCE_APPLY_DISABLED"):
        with runtime.connection({"source_instance_id": "owned-source"}, "source_write"):
            pytest.fail("budget authorization is not source apply authorization")


def test_default_bounded_runtime_still_refuses_unknown_costs(monkeypatch, tmp_path):
    from uuid import UUID

    import pytest

    from preflight.jobs import ResourceIntent
    from preflight.models import PreflightError

    _inert_clients(monkeypatch)
    settings = _runtime_settings(tmp_path, approved_budget_ceiling=100)
    assert settings.unlimited_budget_authorized is False
    runtime = build_runtime(settings)
    intent = ResourceIntent.for_run(UUID(int=1), settings.owner, "2030-01-01T00:00:00Z")
    with pytest.raises(PreflightError, match="BUDGET_OBSERVATION_UNKNOWN"):
        runtime.adapter.budget_guard(intent, "snapshot")


def test_unlimited_does_not_authorize_creation_or_default_clients(monkeypatch, tmp_path):
    import boto3

    from preflight.service import UnconfiguredRuntime

    monkeypatch.setattr(
        boto3,
        "Session",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("default clients forbidden")),
    )
    settings = Settings(state_dir=tmp_path, unlimited_budget_authorized=True)
    assert settings.creation_authorized is False
    assert settings.enable_demo_source_apply is False
    assert isinstance(build_runtime(settings), UnconfiguredRuntime)
    assert not (tmp_path / "budget.sqlite").exists()


def test_unlimited_requires_actual_boolean_and_scoped_creation(tmp_path):
    import pytest
    from pydantic import ValidationError

    for value in ("true", "false", 1, 0, None):
        with pytest.raises(ValidationError):
            Settings(unlimited_budget_authorized=value)
    with pytest.raises(ValidationError):
        Settings(creation_authorized=True, unlimited_budget_authorized=True)
    with pytest.raises(ValidationError):
        _runtime_settings(tmp_path, unlimited_budget_authorized=True, source_allowlist=[])


def test_unlimited_preserves_existing_bounded_ledger(monkeypatch, tmp_path):
    from preflight.budget import BudgetLedger

    _inert_clients(monkeypatch)
    ledger = BudgetLedger(tmp_path / "budget.sqlite")
    before = ledger.path.read_bytes()
    runtime = build_runtime(
        _runtime_settings(tmp_path, unlimited_budget_authorized=True, approved_budget_ceiling=10)
    )
    assert runtime.adapter.budget_guard(None, "clone") is None
    assert ledger.path.read_bytes() == before
    assert ledger.ceiling == 100


def test_unlimited_paused_scoped_runtime_keeps_creation_gate(monkeypatch, tmp_path):
    from uuid import UUID

    import pytest

    from preflight.jobs import ResourceIntent
    from preflight.models import PreflightError

    _inert_clients(monkeypatch)
    settings = _runtime_settings(
        tmp_path,
        unlimited_budget_authorized=True,
        creation_authorized=False,
        sslrootcert=tmp_path / "ca.pem",
        source_read_secret_arn="arn:aws:secretsmanager:ap-south-1:123456789012:secret:read-demo",
    )
    runtime = build_runtime(settings)
    intent = ResourceIntent.for_run(UUID(int=1), settings.owner, "2030-01-01T00:00:00Z")
    runtime.jobs.enqueue(UUID(int=1), intent, deadline=4102444800, max_clones=1, max_snapshots=3)
    for operation in (runtime.adapter.ensure_snapshot, runtime.adapter.ensure_clone):
        with pytest.raises(PreflightError, match="CLOUD_CREATION_NOT_AUTHORIZED"):
            operation(intent)
    assert not (tmp_path / "budget.sqlite").exists()
