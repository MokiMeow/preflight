"""Paused deployment composition, with inert AWS clients and no live calls."""

import time
from types import SimpleNamespace
from uuid import UUID

import boto3
import pytest

from preflight.config import Settings
from preflight.jobs import ResourceIntent
from preflight.models import PreflightError
from preflight.runtime import AwsRuntime, build_runtime
from preflight.service import UnconfiguredRuntime


def scoped_settings(tmp_path, **changes):
    values = dict(
        state_dir=tmp_path,
        account_id="123456789012",
        region="ap-south-1",
        source_instance_id="owned-source",
        source_allowlist=["owned-source"],
        db_subnet_group_name="private-subnets",
        clone_security_group_ids=["sg-123abc"],
        sslrootcert=tmp_path / "rds-ca.pem",
        source_read_secret_arn="arn:aws:secretsmanager:ap-south-1:123456789012:secret:read-demo",
        max_run_owned_snapshots=2,
    )
    values.update(changes)
    return Settings(**values)


@pytest.mark.parametrize(
    "missing",
    [
        "defaults",
        "account_id",
        "region",
        "source_instance_id",
        "db_subnet_group_name",
        "clone_security_group_ids",
        "sslrootcert",
        "source_read_secret_arn",
    ],
)
def test_incomplete_paused_configuration_constructs_no_clients(monkeypatch, tmp_path, missing):
    def forbidden_session(**kwargs):
        pytest.fail("incomplete settings must not construct AWS clients")

    monkeypatch.setattr(boto3, "Session", forbidden_session)
    settings = (
        Settings(state_dir=tmp_path)
        if missing == "defaults"
        else scoped_settings(tmp_path, **{missing: [] if missing.endswith("ids") else None})
    )
    assert isinstance(build_runtime(settings), UnconfiguredRuntime)
    assert not (tmp_path / "cloud.sqlite").exists()


@pytest.mark.parametrize(
    "reference",
    [
        "arn:aws:secretsmanager:ap-south-1:999999999999:secret:read-demo",
        "arn:aws:secretsmanager:us-east-1:123456789012:secret:read-demo",
        "arn:aws:secretsmanager:ap-south-1:123456789012:secret:",
    ],
)
def test_unscoped_read_secret_constructs_no_clients(monkeypatch, tmp_path, reference):
    monkeypatch.setattr(boto3, "Session", lambda **kwargs: pytest.fail("unscoped AWS client"))
    assert isinstance(
        build_runtime(scoped_settings(tmp_path, source_read_secret_arn=reference)),
        UnconfiguredRuntime,
    )


@pytest.mark.parametrize("budget", [None, 10.0])
def test_paused_runtime_reads_owned_private_source_without_enabling_writes(
    monkeypatch, tmp_path, budget
):
    calls = []
    source_arn = "arn:aws:rds:ap-south-1:123456789012:db:owned-source"

    class Client:
        meta = SimpleNamespace(region_name="ap-south-1")

        def get_caller_identity(self):
            calls.append("identity")
            return {"Account": "123456789012"}

        def describe_db_instances(self, **kwargs):
            assert kwargs == {"DBInstanceIdentifier": "owned-source"}
            calls.append("describe")
            return {
                "DBInstances": [
                    {
                        "DBInstanceIdentifier": "owned-source",
                        "DBInstanceArn": source_arn,
                        "Engine": "postgres",
                        "EngineVersion": "18.6",
                        "StorageEncrypted": True,
                        "StorageType": "gp3",
                        "PubliclyAccessible": False,
                        "DBSubnetGroup": {"DBSubnetGroupName": "private-subnets"},
                        "VpcSecurityGroups": [{"VpcSecurityGroupId": "sg-123abc"}],
                        "DBInstanceStatus": "available",
                        "Endpoint": {"Address": "owned-source.test.rds.amazonaws.com"},
                    }
                ]
            }

        def list_tags_for_resource(self, **kwargs):
            assert kwargs == {"ResourceName": source_arn}
            calls.append("tags")
            return {
                "TagList": [
                    {"Key": "Project", "Value": "Preflight"},
                    {"Key": "Owner", "Value": "team-operator"},
                    {"Key": "Purpose", "Value": "synthetic-source"},
                ]
            }

        def get_secret_value(self, **kwargs):
            assert kwargs == {"SecretId": settings.source_read_secret_arn}
            calls.append("read-secret")
            return {"SecretString": '{"username":"synthetic_reader","password":"unit-only"}'}

    clients = {}

    class Session:
        def __init__(self, **kwargs):
            assert kwargs == {"region_name": "ap-south-1"}

        def client(self, name, **kwargs):
            assert kwargs["config"].retries["max_attempts"] == 0
            clients[name] = Client()
            return clients[name]

    monkeypatch.setattr(boto3, "Session", Session)
    settings = scoped_settings(tmp_path, approved_budget_ceiling=budget)
    original = settings.model_dump()
    runtime = build_runtime(settings)
    assert isinstance(runtime, AwsRuntime)
    assert runtime.adapter.policy.creation_authorized is False
    assert runtime.adapter.policy.engine_major == settings.postgres_major
    assert runtime.adapter.policy.max_snapshots == 2
    assert runtime.adapter.policy.max_clones == 1
    assert settings.approved_budget_ceiling == budget
    assert settings.model_dump() == original
    assert calls == []

    connection = SimpleNamespace(close=lambda: calls.append("closed"))

    def connect(*args):
        assert args[0:3] == ("owned-source.test.rds.amazonaws.com", 5432, "preflight_demo")
        assert args[-1] == str(settings.sslrootcert)
        calls.append("tls-read")
        return connection

    monkeypatch.setattr("preflight.db.connect_database", connect)
    run = {"source_instance_id": "owned-source", "database_name": "preflight_demo"}
    with runtime.connection(run, "source_read") as observed:
        assert observed is connection
    assert calls == ["identity", "describe", "tags", "read-secret", "tls-read", "closed"]

    intent = ResourceIntent.for_run(UUID(int=1), settings.owner, "2030-01-01T00:00:00Z")
    runtime.jobs.enqueue(
        UUID(int=1), intent, deadline=time.time() + 60, max_clones=1, max_snapshots=2
    )
    for operation in (runtime.adapter.ensure_snapshot, runtime.adapter.ensure_clone):
        with pytest.raises(PreflightError, match="CLOUD_CREATION_NOT_AUTHORIZED"):
            operation(intent)
    with pytest.raises(PreflightError, match="SOURCE_APPLY_DISABLED"):
        with runtime.connection(run, "source_write"):
            pytest.fail("source write must remain disabled")
    assert calls == ["identity", "describe", "tags", "read-secret", "tls-read", "closed"]


def test_local_backend_remains_unconfigured_without_creation(monkeypatch, tmp_path):
    monkeypatch.setattr(boto3, "Session", lambda **kwargs: pytest.fail("test backend AWS client"))
    assert isinstance(
        build_runtime(scoped_settings(tmp_path, evidence_backend="local_postgres_test")),
        UnconfiguredRuntime,
    )


def test_invalid_private_scope_fails_before_client_construction(monkeypatch, tmp_path):
    monkeypatch.setattr(boto3, "Session", lambda **kwargs: pytest.fail("invalid scope AWS client"))
    with pytest.raises(PreflightError, match="CLOUD_POLICY_INVALID"):
        build_runtime(scoped_settings(tmp_path, clone_security_group_ids=["public-group"]))
    assert not (tmp_path / "cloud.sqlite").exists()
