"""Pure fail-closed validation of operator-selected existing cloud prerequisites."""

from __future__ import annotations

from ipaddress import ip_network

try:
    from bootstrap import PlanError
except ImportError:
    from infra.bootstrap import PlanError


def validate_runtime_documents(documents: list[dict], inputs: dict, deployment: dict) -> None:
    prefix = f"arn:aws:rds:{inputs['region']}:{inputs['account_id']}:"
    source = prefix + "db:" + inputs["source_instance_id"]
    clone = prefix + "db:preflight-*"
    snapshot = prefix + "snapshot:preflight-*"
    scopes = {
        "rds:DescribeDBInstances": {"*", source, clone},
        "rds:DescribeDBSnapshots": {"*", snapshot},
        "rds:CreateDBSnapshot": {source, snapshot},
        "rds:RestoreDBInstanceFromDBSnapshot": {clone, snapshot},
        "rds:ListTagsForResource": {source, clone, snapshot},
        "rds:AddTagsToResource": {clone, snapshot},
        "rds:DeleteDBInstance": {clone},
        "rds:DeleteDBSnapshot": {snapshot},
        "secretsmanager:GetSecretValue": {
            deployment["read_secret_arn"],
            deployment["writer_secret_arn"],
        },
        "sts:GetCallerIdentity": {"*"},
        "tag:GetResources": {"*"},
    }
    if deployment["kms_key_arn"]:
        for action in ("kms:Decrypt", "kms:DescribeKey", "kms:CreateGrant", "kms:GenerateDataKey"):
            scopes[action] = {deployment["kms_key_arn"]}
    if not documents:
        raise PlanError("BOOTSTRAP_RUNTIME_POLICY_INVALID")
    for document in documents:
        if not isinstance(document, dict):
            raise PlanError("BOOTSTRAP_RUNTIME_POLICY_INVALID")
        statements = document.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]
        if not isinstance(statements, list) or not statements:
            raise PlanError("BOOTSTRAP_RUNTIME_POLICY_INVALID")
        for statement in statements:
            if not isinstance(statement, dict):
                raise PlanError("BOOTSTRAP_RUNTIME_POLICY_INVALID")
            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            resources = statement.get("Resource", [])
            if isinstance(resources, str):
                resources = [resources]
            if (
                statement.get("Effect") != "Allow"
                or "NotAction" in statement
                or "NotResource" in statement
                or not isinstance(actions, list)
                or not actions
                or not isinstance(resources, list)
                or not resources
                or any(not isinstance(action, str) or action not in scopes for action in actions)
                or any(not isinstance(resource, str) for resource in resources)
            ):
                raise PlanError("BOOTSTRAP_RUNTIME_POLICY_TOO_BROAD")
            for action in actions:
                if set(resources) - scopes[action]:
                    raise PlanError("BOOTSTRAP_RUNTIME_POLICY_TARGET_TOO_BROAD")
                if action == "kms:CreateGrant":
                    condition = statement.get("Condition", {}).get("Bool", {})
                    if condition.get("kms:GrantIsForAWSResource") not in {"true", True}:
                        raise PlanError("BOOTSTRAP_RUNTIME_KMS_GRANT_TOO_BROAD")


def validate_role_trust(document: dict, role_arn: str, account_id: str) -> None:
    if not isinstance(role_arn, str) or not role_arn.startswith(f"arn:aws:iam::{account_id}:role/"):
        raise PlanError("BOOTSTRAP_RUNTIME_ROLE_IDENTITY_INVALID")
    statements = document.get("Statement", []) if isinstance(document, dict) else []
    if isinstance(statements, dict):
        statements = [statements]
    if not isinstance(statements, list) or not statements:
        raise PlanError("BOOTSTRAP_RUNTIME_TRUST_INVALID")
    for statement in statements:
        if (
            not isinstance(statement, dict)
            or statement.get("Effect") != "Allow"
            or statement.get("Action") not in ("sts:AssumeRole", ["sts:AssumeRole"])
            or statement.get("Principal")
            not in ({"Service": "ec2.amazonaws.com"}, {"Service": ["ec2.amazonaws.com"]})
        ):
            raise PlanError("BOOTSTRAP_RUNTIME_TRUST_TOO_BROAD")


def validate_security_groups(groups: list[dict], inputs: dict, deployment: dict, vpc: str) -> None:
    db_ids, host_ids = set(inputs["security_group_ids"]), set(deployment["host_security_group_ids"])
    if db_ids & host_ids:
        raise PlanError("BOOTSTRAP_SEPARATE_SECURITY_GROUPS_REQUIRED")
    if (
        {g.get("GroupId") for g in groups} != db_ids | host_ids
        or len(groups) != len(db_ids | host_ids)
        or any(g.get("VpcId") != vpc for g in groups)
    ):
        raise PlanError("BOOTSTRAP_SECURITY_GROUP_MISMATCH")
    try:
        ssh_origin = ip_network(inputs["ssh_cidr"], strict=True)
    except ValueError:
        raise PlanError("BOOTSTRAP_SSH_ORIGIN_INVALID") from None
    if ssh_origin.version != 4 or ssh_origin.prefixlen < 24:
        raise PlanError("BOOTSTRAP_SSH_ORIGIN_TOO_BROAD")
    saw_db_rule = False
    for group in groups:
        is_db = group["GroupId"] in db_ids
        if is_db and group.get("IpPermissionsEgress"):
            raise PlanError("BOOTSTRAP_DB_EGRESS_FORBIDDEN")
        for rule in group.get("IpPermissions", []):
            if is_db:
                if (
                    rule.get("IpProtocol") != "tcp"
                    or rule.get("FromPort") != 5432
                    or rule.get("ToPort") != 5432
                    or rule.get("IpRanges")
                    or rule.get("Ipv6Ranges")
                    or rule.get("PrefixListIds")
                    or not rule.get("UserIdGroupPairs")
                    or any(
                        p.get("GroupId") not in host_ids
                        or p.get("UserId") not in {None, inputs["account_id"]}
                        for p in rule.get("UserIdGroupPairs", [])
                    )
                ):
                    raise PlanError("BOOTSTRAP_PRIVATE_DB_RULE_REQUIRED")
                saw_db_rule = True
            elif (
                rule.get("IpProtocol") != "tcp"
                or rule.get("FromPort") != 22
                or rule.get("ToPort") != 22
                or rule.get("Ipv6Ranges")
                or rule.get("PrefixListIds")
                or rule.get("UserIdGroupPairs")
                or not rule.get("IpRanges")
                or any(p.get("CidrIp") != inputs["ssh_cidr"] for p in rule.get("IpRanges", []))
            ):
                raise PlanError("BOOTSTRAP_PRIVATE_HOST_RULE_REQUIRED")
    if not saw_db_rule:
        raise PlanError("BOOTSTRAP_DATABASE_ROUTE_REQUIRED")
