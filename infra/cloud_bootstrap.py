"""Scoped EC2/RDS bootstrap, reusing approved network and runtime IAM identity.

Never creates/modifies IAM, networking, secrets, database roles or source data.
All new billable resources need the separately digest-bound operator approval.
Existing identifiers come from explicit deployment inputs, not discovery guesses.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from preflight.jobs import JobStore

try:
    from bootstrap import PlanError, verify_apply_scope
except ImportError:
    from infra.bootstrap import PlanError, verify_apply_scope

try:
    from prerequisites import (
        validate_role_trust,
        validate_runtime_documents,
        validate_security_groups,
    )
except ImportError:
    from infra.prerequisites import (
        validate_role_trust,
        validate_runtime_documents,
        validate_security_groups,
    )


DEPLOYMENT_FIELDS = {
    "database_name",
    "host_instance_id",
    "host_subnet_id",
    "host_security_group_ids",
    "host_image_id",
    "host_image_owner",
    "instance_profile_name",
    "instance_profile_arn",
    "ssh_key_name",
    "kms_key_arn",
    "read_secret_arn",
    "writer_secret_arn",
    "engine_version",
    "runtime_role_policy_sha256",
}


class BootstrapDriver:
    def __init__(self, envelope: dict, approval: dict, clients: dict[str, Any], state_dir: str):
        self.plan = verify_apply_scope(envelope, approval)
        self.inputs = self.plan["operator_inputs"]
        self.digest = envelope["plan_sha256"]
        self.deployment = self.inputs.get("deployment", {})
        if (
            set(self.deployment) != DEPLOYMENT_FIELDS
            or any(
                not isinstance(v, str) or not v
                for k, v in self.deployment.items()
                if k not in {"host_security_group_ids", "host_instance_id", "kms_key_arn"}
            )
            or not isinstance(self.deployment["host_security_group_ids"], list)
            or not self.deployment["host_security_group_ids"]
            or not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", self.deployment["database_name"])
            or self.inputs["host_mode"] == "reuse"
            and not self.deployment["host_instance_id"]
        ):
            raise PlanError("BOOTSTRAP_DEPLOYMENT_SCOPE_REQUIRED")
        self.clients = clients
        self.state_dir = Path(state_dir).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.store = JobStore(self.state_dir / "cloud.sqlite")
        self.journal = self.state_dir / "bootstrap.sqlite"
        with self._db() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS bootstrap(plan_digest TEXT PRIMARY KEY, "
                "source_id TEXT NOT NULL, host_id TEXT, stage TEXT NOT NULL)"
            )

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.journal)
        try:
            with db:
                yield db
        finally:
            db.close()

    def call(self, service: str, method: str, **kwargs) -> dict:
        try:
            return getattr(self.clients[service], method)(**kwargs)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {"DBInstanceNotFound", "DBInstanceNotFoundFault"}:
                raise PlanError("BOOTSTRAP_SOURCE_ABSENT") from None
            raise PlanError("BOOTSTRAP_PROVIDER_DENIED") from None
        except BotoCoreError:
            raise PlanError("BOOTSTRAP_OUTCOME_UNCERTAIN_RECONCILE") from None

    def identity(self):
        if self.call("sts", "get_caller_identity").get("Account") != self.inputs["account_id"]:
            raise PlanError("BOOTSTRAP_ACCOUNT_MISMATCH")
        if any(
            c.meta.region_name != self.inputs["region"]
            for name, c in self.clients.items()
            if name != "iam"
        ):
            raise PlanError("BOOTSTRAP_REGION_MISMATCH")

    def validate_prerequisites(self):
        d, i = self.deployment, self.inputs
        if d["read_secret_arn"] == d["writer_secret_arn"]:
            raise PlanError("BOOTSTRAP_SEPARATE_DATABASE_SECRETS_REQUIRED")
        if d["kms_key_arn"] and not d["kms_key_arn"].startswith(
            f"arn:aws:kms:{i['region']}:{i['account_id']}:key/"
        ):
            raise PlanError("BOOTSTRAP_KMS_KEY_SCOPE_INVALID")
        # Existing runtime role only; this driver cannot broaden/attach policies.
        profile = self.call(
            "iam", "get_instance_profile", InstanceProfileName=d["instance_profile_name"]
        )
        profile = profile.get("InstanceProfile", {})
        if (
            profile.get("Arn") != d["instance_profile_arn"]
            or len(profile.get("Roles", [])) != 1
            or not d["instance_profile_arn"].startswith(
                f"arn:aws:iam::{i['account_id']}:instance-profile/"
            )
        ):
            raise PlanError("BOOTSTRAP_RUNTIME_IDENTITY_MISMATCH")
        role = profile["Roles"][0]["RoleName"]
        documents = []
        inline = self.call("iam", "list_role_policies", RoleName=role)
        attached = self.call("iam", "list_attached_role_policies", RoleName=role)
        if inline.get("IsTruncated") or attached.get("IsTruncated"):
            raise PlanError("BOOTSTRAP_RUNTIME_POLICY_SCAN_INCOMPLETE")
        for name in inline.get("PolicyNames", []):
            documents.append(
                self.call("iam", "get_role_policy", RoleName=role, PolicyName=name)[
                    "PolicyDocument"
                ]
            )
        for attached_policy in attached.get("AttachedPolicies", []):
            arn = attached_policy["PolicyArn"]
            policy = self.call("iam", "get_policy", PolicyArn=arn)["Policy"]
            documents.append(
                self.call(
                    "iam", "get_policy_version", PolicyArn=arn, VersionId=policy["DefaultVersionId"]
                )["PolicyVersion"]["Document"]
            )
        documents = [json.loads(unquote(doc)) if isinstance(doc, str) else doc for doc in documents]
        validate_runtime_documents(documents, i, d)
        documents.sort(key=lambda doc: json.dumps(doc, sort_keys=True, separators=(",", ":")))
        role = profile["Roles"][0]
        trust = role.get("AssumeRolePolicyDocument", {})
        trust = json.loads(unquote(trust)) if isinstance(trust, str) else trust
        validate_role_trust(trust, role.get("Arn"), i["account_id"])
        policy_digest = hashlib.sha256(
            json.dumps(documents, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if not documents or policy_digest != d["runtime_role_policy_sha256"]:
            raise PlanError("BOOTSTRAP_RUNTIME_POLICY_REVIEW_REQUIRED")
        # Only named Secrets Manager metadata. Never enumerate or print secrets.
        for key in ("read_secret_arn", "writer_secret_arn"):
            if not d[key].startswith(
                f"arn:aws:secretsmanager:{i['region']}:{i['account_id']}:secret:"
            ):
                raise PlanError("BOOTSTRAP_SECRET_SCOPE_MISMATCH")
            secret = self.call("secretsmanager", "describe_secret", SecretId=d[key])
            if secret.get("ARN") != d[key] or secret.get("DeletedDate"):
                raise PlanError("BOOTSTRAP_SECRET_SCOPE_MISMATCH")
        group = self.call("rds", "describe_db_subnet_groups", DBSubnetGroupName=i["subnet_group"])
        groups = group.get("DBSubnetGroups", [])
        if (
            len(groups) != 1
            or groups[0].get("SubnetGroupStatus") != "Complete"
            or len(
                {
                    s.get("SubnetAvailabilityZone", {}).get("Name")
                    for s in groups[0].get("Subnets", [])
                }
            )
            < 2
        ):
            raise PlanError("BOOTSTRAP_SUBNET_SCOPE_INVALID")
        vpc = groups[0].get("VpcId")
        subnet = self.call("ec2", "describe_subnets", SubnetIds=[d["host_subnet_id"]]).get(
            "Subnets", []
        )
        if len(subnet) != 1 or subnet[0].get("VpcId") != vpc:
            raise PlanError("BOOTSTRAP_VPC_MISMATCH")
        sg_ids = sorted(set(i["security_group_ids"] + d["host_security_group_ids"]))
        groups = self.call("ec2", "describe_security_groups", GroupIds=sg_ids).get(
            "SecurityGroups", []
        )
        validate_security_groups(groups, i, d, vpc)
        if self.inputs["host_mode"] == "create":
            self.approved_root_device = self.inspect_host_image()

    def inspect_host_image(self):
        d = self.deployment
        images = self.call("ec2", "describe_images", ImageIds=[d["host_image_id"]]).get("Images", [])
        if (
            len(images) != 1
            or images[0].get("ImageId") != d["host_image_id"]
            or images[0].get("OwnerId") != d["host_image_owner"]
            or images[0].get("State") != "available"
            or images[0].get("Architecture") != "x86_64"
            or images[0].get("RootDeviceType") != "ebs"
            or not images[0].get("RootDeviceName")
        ):
            raise PlanError("BOOTSTRAP_HOST_IMAGE_INVALID")
        return images[0]["RootDeviceName"]

    def tags(self, source=False):
        values = {
            "Project": "Preflight",
            "Owner": self.inputs["operator_label"],
            "PlanDigest": self.digest,
        }
        if source:
            values["Purpose"] = "synthetic-source"
        return [{"Key": k, "Value": v} for k, v in values.items()]

    def source(self):
        i, d = self.inputs, self.deployment
        source_id = i["source_instance_id"]
        try:
            response = self.call("rds", "describe_db_instances", DBInstanceIdentifier=source_id)
        except PlanError as exc:
            if str(exc) != "BOOTSTRAP_SOURCE_ABSENT" or i["source_mode"] != "create":
                raise
            version = d["engine_version"]
            versions = self.call(
                "rds", "describe_db_engine_versions", Engine="postgres", EngineVersion=version
            ).get("DBEngineVersions", [])
            if not any(
                v.get("EngineVersion") == version
                and version.startswith("18.")
                and v.get("Status") == "available"
                for v in versions
            ):
                raise PlanError("BOOTSTRAP_ENGINE_UNAVAILABLE")
            options = self.call(
                "rds",
                "describe_orderable_db_instance_options",
                Engine="postgres",
                EngineVersion=version,
                DBInstanceClass=i["instance_class"],
                Vpc=True,
            )
            if not any(
                o.get("StorageType") == "gp3" and o.get("SupportsStorageEncryption") is True
                for o in options.get("OrderableDBInstanceOptions", [])
            ):
                raise PlanError("BOOTSTRAP_CLASS_UNAVAILABLE")
            self.identity()
            args = {
                "DBInstanceIdentifier": source_id,
                "DBName": d["database_name"],
                "Engine": "postgres",
                "EngineVersion": version,
                "DBInstanceClass": i["instance_class"],
                "AllocatedStorage": i["allocated_storage_gib"],
                "StorageType": "gp3",
                "StorageEncrypted": True,
                "PubliclyAccessible": False,
                "DBSubnetGroupName": i["subnet_group"],
                "VpcSecurityGroupIds": i["security_group_ids"],
                "MasterUsername": "preflight_bootstrap",
                "ManageMasterUserPassword": True,
                "BackupRetentionPeriod": 7,
                "DeletionProtection": True,
                "MultiAZ": False,
                "AutoMinorVersionUpgrade": False,
                "CopyTagsToSnapshot": True,
                "Tags": self.tags(True),
            }
            if d["kms_key_arn"]:
                args["KmsKeyId"] = d["kms_key_arn"]
            # Durable exact intent exists before this request; restart describes same ID.
            self.call("rds", "create_db_instance", **args)
            response = self.call("rds", "describe_db_instances", DBInstanceIdentifier=source_id)
        instances = response.get("DBInstances", [])
        if len(instances) != 1:
            raise PlanError("BOOTSTRAP_SOURCE_IDENTITY_MISMATCH")
        source = instances[0]
        arn = f"arn:aws:rds:{i['region']}:{i['account_id']}:db:{source_id}"
        tags = self.call("rds", "list_tags_for_resource", ResourceName=arn).get("TagList", [])
        tags = {t.get("Key"): t.get("Value") for t in tags}
        if (
            source.get("DBInstanceIdentifier") != source_id
            or source.get("DBInstanceArn") != arn
            or source.get("Engine") != "postgres"
            or not source.get("EngineVersion", "").startswith("18.")
            or source.get("EngineVersion") != d["engine_version"]
            or source.get("DBInstanceClass") != i["instance_class"]
            or source.get("DBName") != d["database_name"]
            or source.get("PubliclyAccessible") is not False
            or source.get("StorageEncrypted") is not True
            or source.get("StorageType") != "gp3"
            or source.get("AllocatedStorage") != i["allocated_storage_gib"]
            or source.get("DBSubnetGroup", {}).get("DBSubnetGroupName") != i["subnet_group"]
            or {g.get("VpcSecurityGroupId") for g in source.get("VpcSecurityGroups", [])}
            != set(i["security_group_ids"])
            or tags.get("Project") != "Preflight"
            or tags.get("Owner") != i["operator_label"]
            or tags.get("Purpose") != "synthetic-source"
            or i["source_mode"] == "create"
            and tags.get("PlanDigest") != self.digest
        ):
            raise PlanError("BOOTSTRAP_SOURCE_POLICY_MISMATCH")
        if d["kms_key_arn"] and source.get("KmsKeyId") != d["kms_key_arn"]:
            raise PlanError("BOOTSTRAP_SOURCE_KMS_MISMATCH")
        return source_id, source.get("DBInstanceStatus", "unknown")

    def host(self):
        i, d = self.inputs, self.deployment
        if i["host_mode"] == "reuse":
            response = self.call("ec2", "describe_instances", InstanceIds=[d["host_instance_id"]])
        else:
            response = self.call(
                "ec2",
                "describe_instances",
                Filters=[{"Name": "client-token", "Values": [self.digest]}],
            )
        hosts = [v for r in response.get("Reservations", []) for v in r.get("Instances", [])]
        if not hosts and i["host_mode"] == "create":
            root_device = getattr(self, "approved_root_device", None) or self.inspect_host_image()
            self.identity()
            self.call(
                "ec2",
                "run_instances",
                ImageId=d["host_image_id"],
                InstanceType=i["host_instance_type"],
                MinCount=1,
                MaxCount=1,
                ClientToken=self.digest,
                SubnetId=d["host_subnet_id"],
                SecurityGroupIds=d["host_security_group_ids"],
                KeyName=d["ssh_key_name"],
                IamInstanceProfile={"Arn": d["instance_profile_arn"]},
                MetadataOptions={"HttpTokens": "required", "HttpEndpoint": "enabled"},
                BlockDeviceMappings=[
                    {
                        "DeviceName": root_device,
                        "Ebs": {
                            "Encrypted": True,
                            "VolumeType": "gp3",
                            "VolumeSize": 30,
                            "DeleteOnTermination": False,
                        },
                    }
                ],
                TagSpecifications=[
                    {"ResourceType": "instance", "Tags": self.tags()},
                    {"ResourceType": "volume", "Tags": self.tags()},
                ],
            )
            response = self.call(
                "ec2",
                "describe_instances",
                Filters=[{"Name": "client-token", "Values": [self.digest]}],
            )
            hosts = [v for r in response.get("Reservations", []) for v in r.get("Instances", [])]
        if len(hosts) != 1:
            raise PlanError("BOOTSTRAP_HOST_IDENTITY_MISMATCH")
        host = hosts[0]
        tags = {t.get("Key"): t.get("Value") for t in host.get("Tags", [])}
        if (
            not host.get("InstanceId")
            or i["host_mode"] == "reuse"
            and host.get("InstanceId") != d["host_instance_id"]
            or host.get("SubnetId") != d["host_subnet_id"]
            or host.get("IamInstanceProfile", {}).get("Arn") != d["instance_profile_arn"]
            or {s.get("GroupId") for s in host.get("SecurityGroups", [])}
            != set(d["host_security_group_ids"])
            or host.get("InstanceType") != i["host_instance_type"]
            or host.get("MetadataOptions", {}).get("HttpTokens") != "required"
            or tags.get("Project") != "Preflight"
            or tags.get("Owner") != i["operator_label"]
            or i["host_mode"] == "create"
            and (host.get("ClientToken") != self.digest or tags.get("PlanDigest") != self.digest)
        ):
            raise PlanError("BOOTSTRAP_HOST_POLICY_MISMATCH")
        mappings = host.get("BlockDeviceMappings", [])
        root = [m for m in mappings if m.get("DeviceName") == host.get("RootDeviceName")]
        if (
            host.get("RootDeviceType") != "ebs"
            or not host.get("RootDeviceName")
            or len(root) != 1
            or root[0].get("Ebs", {}).get("DeleteOnTermination") is not False
            or any(not m.get("Ebs", {}).get("VolumeId") for m in mappings)
        ):
            raise PlanError("BOOTSTRAP_PERSISTENT_HOST_STORAGE_REQUIRED")
        volume_ids = sorted(m["Ebs"]["VolumeId"] for m in mappings)
        if len(volume_ids) != len(set(volume_ids)):
            raise PlanError("BOOTSTRAP_HOST_STORAGE_IDENTITY_MISMATCH")
        volumes = self.call("ec2", "describe_volumes", VolumeIds=volume_ids).get("Volumes", [])
        if (
            len(volumes) != len(volume_ids)
            or {v.get("VolumeId") for v in volumes} != set(volume_ids)
            or any(
                v.get("Encrypted") is not True
                or v.get("VolumeType") != "gp3"
                or not any(a.get("InstanceId") == host["InstanceId"] for a in v.get("Attachments", []))
                for v in volumes
            )
        ):
            raise PlanError("BOOTSTRAP_ENCRYPTED_HOST_STORAGE_REQUIRED")
        return host["InstanceId"], host.get("State", {}).get("Name", "unknown")

    def run(self) -> dict:
        with self.store.mutation_lease("bootstrap-" + self.digest):
            self.identity()
            self.validate_prerequisites()
            with self._db() as db:
                prior = db.execute("SELECT plan_digest, source_id FROM bootstrap").fetchall()
                if any(row[1] != self.inputs["source_instance_id"] for row in prior):
                    raise PlanError("BOOTSTRAP_SINGLE_SOURCE_CAP")
                if self.inputs["host_mode"] == "create" and any(
                    row[0] != self.digest for row in prior
                ):
                    raise PlanError("BOOTSTRAP_SINGLE_HOST_CAP_RECONCILE")
                db.execute(
                    "INSERT OR IGNORE INTO bootstrap(plan_digest,source_id,stage) VALUES(?,?,?)",
                    (self.digest, self.inputs["source_instance_id"], "INTENT"),
                )
            source_id, source_status = self.source()
            host_id, host_status = self.host()
            with self._db() as db:
                db.execute(
                    "UPDATE bootstrap SET host_id=?,stage='OBSERVED' WHERE plan_digest=?",
                    (host_id, self.digest),
                )
            return {
                "source_id": source_id,
                "source_status": source_status,
                "host_id": host_id,
                "host_status": host_status,
                "database_readiness": "NOT_RUN",
                "state_dir": str(self.state_dir),
            }


def execute_bootstrap(envelope: dict, approval: dict, state_dir: str, *, clients=None) -> dict:
    # Validate recorded scope before constructing clients/consulting credentials.
    plan = verify_apply_scope(envelope, approval)
    if not plan["operator_inputs"].get("deployment"):
        raise PlanError("BOOTSTRAP_DEPLOYMENT_SCOPE_REQUIRED")
    if clients is None:
        session = boto3.Session(region_name=plan["operator_inputs"]["region"])
        clients = {
            name: session.client(name) for name in ("sts", "iam", "rds", "ec2", "secretsmanager")
        }
    return BootstrapDriver(envelope, approval, clients, state_dir).run()
