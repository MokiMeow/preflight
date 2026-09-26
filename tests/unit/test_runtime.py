"""Deployment composition test with inert clients, no network or credentials."""

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
            clients[name] = object()
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
