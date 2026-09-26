import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "bootstrap", Path(__file__).parents[2] / "infra/bootstrap.py"
)
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def inputs():
    return {
        "account_id": "123456789012",
        "region": "us-east-1",
        "operator_label": "unit-owner",
        "source_instance_id": "synthetic-source",
        "source_mode": "reuse",
        "host_mode": "reuse",
        "instance_class": "db.t4g.micro",
        "allocated_storage_gib": 20,
        "host_instance_type": "t3.medium",
        "subnet_group": "private-subnets",
        "security_group_ids": ["sg-0123456789abcdef0"],
        "max_clones": 1,
        "max_snapshots": 3,
        "approved_spend_ceiling": 10,
        "currency": "USD",
        "retention_owner": "unit-owner",
        "ssh_cidr": "192.0.2.1/32",
    }


def approval(plan):
    supplied = plan["plan"]["operator_inputs"]
    return {
        "plan_sha256": plan["plan_sha256"],
        "account_id": supplied["account_id"],
        "region": supplied["region"],
        "operator_label": supplied["operator_label"],
        "approved_spend_ceiling": supplied["approved_spend_ceiling"],
        "creation_authorized": True,
    }


def test_saved_plan_is_exact_and_does_not_infer_observations():
    plan = bootstrap.make_plan(inputs())
    assert plan["plan"]["pricing_status"] == "NOT_OBSERVED"
    assert plan["plan"]["aws_identity_status"] == "NOT_RUN"
    assert bootstrap.verify_apply_scope(plan, approval(plan)) == plan["plan"]
    changed = approval(plan) | {"region": "us-west-2"}
    with pytest.raises(bootstrap.PlanError, match="OPERATOR_SCOPE_MISMATCH"):
        bootstrap.verify_apply_scope(plan, changed)
    plan["plan"]["operator_inputs"]["max_clones"] = 2
    with pytest.raises(bootstrap.PlanError, match="PLAN_DIGEST_MISMATCH"):
        bootstrap.verify_apply_scope(plan, approval(plan))


@pytest.mark.parametrize(
    "extra",
    [{"aws_secret_access_key": "never-print"}, {"max_clones": 100}, {"approved_spend_ceiling": 0}],
)
def test_unknown_or_unsafe_plan_fields_rejected(extra):
    with pytest.raises(bootstrap.PlanError):
        bootstrap.make_plan(inputs() | extra)


def test_duplicate_input_keys_rejected(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"region":"a","region":"b"}')
    with pytest.raises(bootstrap.PlanError, match="DUPLICATE_JSON_KEY"):
        bootstrap.read_json(str(path))
