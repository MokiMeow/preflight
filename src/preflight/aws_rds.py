"""Allowlisted real RDS operations. No AWS client is constructed at import time.

Only explicit operator policy enables creation. Provider responses are untrusted:
ARN, provenance, privacy, encryption and complete owner tags are checked afresh.
Upstream exception messages are never returned or logged.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from botocore.exceptions import BotoCoreError, ClientError

from preflight.jobs import JobStore, ResourceIntent
from preflight.models import PreflightError


@dataclass(frozen=True)
class CloudPolicy:
    account_id: str
    region: str
    source_instance_id: str
    owner: str
    subnet_group: str
    security_group_ids: tuple[str, ...]
    instance_class: str
    engine_major: int = 18
    max_clones: int = 1
    max_snapshots: int = 3
    creation_authorized: bool = False
    kms_key_id: str | None = None
    storage_type: str = "gp3"

    def __post_init__(self) -> None:
        if (
            not re.fullmatch(r"[0-9]{12}", self.account_id)
            or not re.fullmatch(r"[a-z]{2}(?:-gov)?-[a-z]+-\d", self.region)
            or not valid_id(self.source_instance_id)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", self.owner)
            or not self.subnet_group
            or not self.security_group_ids
            or len(set(self.security_group_ids)) != len(self.security_group_ids)
            or any(not re.fullmatch(r"sg-[0-9a-f]+", s) for s in self.security_group_ids)
            or not re.fullmatch(r"db\.[a-z0-9]+\.[a-z0-9]+", self.instance_class)
            or self.engine_major != 18
            or self.max_clones != 1
            or not 1 <= self.max_snapshots <= 3
            or self.storage_type not in {"gp2", "gp3"}
        ):
            raise PreflightError("CLOUD_POLICY_INVALID")


def valid_id(value: str) -> bool:
    return bool(
        re.fullmatch(r"[a-z][a-z0-9-]{0,62}", value)
        and not value.endswith("-")
        and "--" not in value
    )


@dataclass(frozen=True)
class ResourceObservation:
    resource_id: str
    arn: str
    status: str
    engine_version: str
    endpoint: str | None = None
    created_at: datetime | None = None
    kms_key_id: str | None = None
    storage_type: str | None = None


@dataclass(frozen=True)
class CleanupPolicy:
    """Server-only inputs computed under the lead's exclusive run CAS lock.

    literal_gate_approved must derive from the configured cleanup_run human gate,
    never from a model/tool argument. This is not authenticated production approval.
    """

    literal_gate_approved: bool
    run_phase: str
    reports_retained: bool
    dependent_operation_active: bool = False
    source_apply_attempted: bool = False
    preapply_not_after: datetime | None = None
    recovery_backup_snapshot_id: str | None = None
    delete_clone: bool = False
    delete_snapshot: bool = False
    clone_instance_id: str | None = None
    snapshot_id: str | None = None


class RdsAdapter:
    evidence_backend = "aws_rds"

    def __init__(
        self,
        rds: Any,
        sts: Any,
        policy: CloudPolicy,
        store: JobStore,
        *,
        recovery_attestation: Callable[[str, str, datetime], bool] | None = None,
        tagging: Any | None = None,
        budget_guard: Callable[[ResourceIntent, str], None] | None = None,
    ):
        self.rds, self.sts, self.policy, self.store = rds, sts, policy, store
        self.recovery_attestation = recovery_attestation
        self.tagging = tagging
        self.budget_guard = budget_guard
        if rds.meta.region_name != policy.region or sts.meta.region_name != policy.region:
            raise PreflightError("AWS_REGION_MISMATCH")
        if tagging is not None and tagging.meta.region_name != policy.region:
            raise PreflightError("AWS_REGION_MISMATCH")

    def _resource_registry(self) -> dict[str, tuple[ResourceIntent, str, bool]]:
        registry = {}
        for row in self.store.resource_registry():
            try:
                intent = ResourceIntent(**json.loads(row["intent"]))
                self._intent(intent)
            except (TypeError, ValueError):
                raise PreflightError("CLOUD_REGISTRY_INVALID") from None
            for kind, identifier in (
                ("clone", intent.clone_instance_id),
                ("snapshot", intent.snapshot_id),
            ):
                if identifier in registry:
                    raise PreflightError("CLOUD_REGISTRY_INVALID")
                registry[identifier] = (intent, kind, bool(row[kind + "_reserved"]))
        return registry

    def owned_resource_inventory(self) -> dict:
        """Doctor metadata only: paginated owned tags plus fresh exact-resource reads.

        No account-wide RDS discovery. Tag-index visibility is eventually consistent;
        durable reservations and the shared persisted lease remain primary guards.
        Unknown owned resources are reported but never adopted or deleted.
        """
        if self.tagging is None:
            raise PreflightError("AWS_INVENTORY_CLIENT_REQUIRED")
        self._identity()
        registry = self._resource_registry()
        mappings = []
        seen_arns: set[str] = set()
        seen_tokens: set[str] = set()
        token = None
        for _ in range(10):
            args: dict[str, Any] = {
                "TagFilters": [
                    {"Key": "Project", "Values": ["Preflight"]},
                    {"Key": "Owner", "Values": [self.policy.owner]},
                ],
                "ResourceTypeFilters": ["rds:db", "rds:snapshot"],
                "ResourcesPerPage": 100,
            }
            if token:
                args["PaginationToken"] = token
            page = self._call(self.tagging, "get_resources", **args)
            items = page.get("ResourceTagMappingList")
            if not isinstance(items, list) or len(items) > 100:
                raise PreflightError("AWS_INVENTORY_INCOMPLETE")
            for mapping in items:
                arn = mapping.get("ResourceARN")
                if not isinstance(arn, str) or arn in seen_arns:
                    raise PreflightError("AWS_INVENTORY_INCOMPLETE")
                seen_arns.add(arn)
                pairs = mapping.get("Tags", [])
                tags = {t.get("Key"): t.get("Value") for t in pairs}
                if (
                    len(tags) != len(pairs)
                    or tags.get("Project") != "Preflight"
                    or tags.get("Owner") != self.policy.owner
                ):
                    raise PreflightError("AWS_INVENTORY_TAG_MISMATCH")
                mappings.append((arn, tags))
            token = page.get("PaginationToken")
            if not token:
                break
            if not isinstance(token, str) or token in seen_tokens:
                raise PreflightError("AWS_INVENTORY_INCOMPLETE")
            seen_tokens.add(token)
        else:
            raise PreflightError("AWS_INVENTORY_INCOMPLETE")
        resources = []
        automatic_backups = []
        for arn, _ in mappings:
            parts = arn.split(":", 6)
            if len(parts) != 7 or parts[5] not in {"db", "snapshot"}:
                raise PreflightError("AWS_INVENTORY_RESOURCE_INVALID")
            resource_type, identifier = parts[5], parts[6]
            self._arn(arn, resource_type, identifier)
            if resource_type == "snapshot" and identifier.startswith("rds:"):
                if not re.fullmatch(
                    "rds:"
                    + re.escape(self.policy.source_instance_id)
                    + r"-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}",
                    identifier,
                ):
                    raise PreflightError("AWS_INVENTORY_RESOURCE_INVALID")
                try:
                    value = self._automatic_source_backup(identifier)
                except PreflightError as exc:
                    if exc.code == "AWS_RESOURCE_ABSENT":
                        continue
                    raise
                automatic_backups.append(
                    {
                        "resource_id": identifier,
                        "kind": "source_automatic_backup",
                        "status": value["Status"],
                        "managed_by": "aws_rds",
                    }
                )
                continue
            if not valid_id(identifier):
                raise PreflightError("AWS_INVENTORY_RESOURCE_INVALID")
            if resource_type == "db" and identifier == self.policy.source_instance_id:
                # Never counted as a disposable clone.
                continue
            kind = "clone" if resource_type == "db" else "snapshot"
            try:
                value = (
                    self._instance(identifier) if kind == "clone" else self._snapshot(identifier)
                )
            except PreflightError as exc:
                if exc.code == "AWS_RESOURCE_ABSENT":
                    # The tag index can retain deleted resources. Fresh exact read wins.
                    continue
                raise
            tags = self._tags(arn)
            if tags.get("Project") != "Preflight" or tags.get("Owner") != self.policy.owner:
                raise PreflightError("AWS_INVENTORY_TAG_MISMATCH")
            tracked = identifier in registry
            reserved = False
            if tracked:
                intent, expected_kind, reserved = registry[identifier]
                if (
                    expected_kind != kind
                    or any(tags.get(k) != v for k, v in intent.tags().items())
                    or kind == "clone"
                    and tags.get("SnapshotId") != intent.snapshot_id
                ):
                    raise PreflightError("AWS_INVENTORY_PROVENANCE_MISMATCH")
            status = value.get("DBInstanceStatus" if kind == "clone" else "Status")
            if not isinstance(status, str) or not re.fullmatch(r"[a-z][a-z-]{0,63}", status):
                raise PreflightError("AWS_INVENTORY_RESOURCE_INVALID")
            resources.append(
                {
                    "resource_id": identifier,
                    "kind": kind,
                    "status": status,
                    "tracked": tracked,
                    "reserved": reserved,
                    "storage_type": value["StorageType"],
                }
            )
        resources.sort(key=lambda item: (item["kind"], item["resource_id"]))
        counts = {kind: sum(r["kind"] == kind for r in resources) for kind in ("clone", "snapshot")}
        return {
            "resources": resources,
            "automatic_source_backups": sorted(automatic_backups, key=lambda r: r["resource_id"]),
            "counts": counts,
            "complete": True,
            "visibility": "eventually_consistent_tag_index",
            "unknown_owned_ids": [r["resource_id"] for r in resources if not r["tracked"]],
            "released_present_ids": [
                r["resource_id"] for r in resources if r["tracked"] and not r["reserved"]
            ],
        }

    def _enforce_live_inventory(self, intent: ResourceIntent, kind: str) -> None:
        inventory = self.owned_resource_inventory()
        if inventory["unknown_owned_ids"]:
            raise PreflightError("AWS_OWNED_RESOURCES_UNTRACKED")
        if inventory["released_present_ids"]:
            raise PreflightError("AWS_RESOURCE_RESERVATION_LOST")
        registry = self._resource_registry()
        for resource_kind, cap in (
            ("clone", self.policy.max_clones),
            ("snapshot", self.policy.max_snapshots),
        ):
            live = {r["resource_id"] for r in inventory["resources"] if r["kind"] == resource_kind}
            reserved = {
                identifier
                for identifier, (_, k, active) in registry.items()
                if k == resource_kind and active
            }
            if len(live | reserved) > cap:
                raise PreflightError("RESOURCE_CAP_REACHED")
        intended_id = intent.clone_instance_id if kind == "clone" else intent.snapshot_id
        if any(r["resource_id"] == intended_id for r in inventory["resources"]):
            # An exact read returned absent but the fresh tag inventory found it:
            # reconcile again rather than submit another create request.
            raise PreflightError("AWS_RETRYABLE")

    def _call(self, client: Any, method: str, **kwargs: Any) -> dict:
        try:
            return getattr(client, method)(**kwargs)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {
                "DBInstanceNotFound",
                "DBInstanceNotFoundFault",
                "DBSnapshotNotFound",
                "DBSnapshotNotFoundFault",
            }:
                raise PreflightError("AWS_RESOURCE_ABSENT") from None
            if code in {
                "Throttling",
                "ThrottlingException",
                "RequestLimitExceeded",
                "ServiceUnavailable",
                "InternalFailure",
                "InternalServerError",
                "DBInstanceAlreadyExists",
                "DBInstanceAlreadyExistsFault",
                "DBSnapshotAlreadyExists",
                "DBSnapshotAlreadyExistsFault",
            }:
                raise PreflightError("AWS_RETRYABLE") from None
            raise PreflightError("AWS_REQUEST_DENIED") from None
        except BotoCoreError:
            raise PreflightError("AWS_OUTCOME_UNCERTAIN") from None

    def _identity(self) -> None:
        identity = self._call(self.sts, "get_caller_identity")
        if identity.get("Account") != self.policy.account_id:
            raise PreflightError("AWS_ACCOUNT_MISMATCH")

    def _arn(self, arn: str, kind: str, identifier: str) -> None:
        partition = "aws-us-gov" if self.policy.region.startswith("us-gov-") else "aws"
        expected = (
            f"arn:{partition}:rds:{self.policy.region}:{self.policy.account_id}:{kind}:{identifier}"
        )
        if arn != expected:
            raise PreflightError("AWS_RESOURCE_IDENTITY_MISMATCH")

    def _tags(self, arn: str) -> dict[str, str]:
        response = self._call(self.rds, "list_tags_for_resource", ResourceName=arn)
        pairs = response.get("TagList", [])
        tags = {t.get("Key"): t.get("Value") for t in pairs}
        if len(tags) != len(pairs):
            raise PreflightError("AWS_RESOURCE_TAG_MISMATCH")
        return tags

    def _owned(self, arn: str, intent: ResourceIntent) -> None:
        tags = self._tags(arn)
        if any(tags.get(k) != v for k, v in intent.tags().items()):
            raise PreflightError("AWS_RESOURCE_TAG_MISMATCH")

    def _intent(self, intent: ResourceIntent) -> None:
        try:
            expected = ResourceIntent.for_run(
                UUID(intent.run_id), self.policy.owner, intent.expires_at
            )
            expiry = datetime.fromisoformat(intent.expires_at)
        except (ValueError, TypeError, AttributeError):
            raise PreflightError("RESOURCE_INTENT_INVALID") from None
        if (
            intent != expected
            or expiry.tzinfo is None
            or intent.clone_instance_id == self.policy.source_instance_id
            or not valid_id(intent.snapshot_id)
            or not valid_id(intent.clone_instance_id)
        ):
            raise PreflightError("RESOURCE_INTENT_INVALID")
        self.store.require_reservation(
            intent, max_clones=self.policy.max_clones, max_snapshots=self.policy.max_snapshots
        )

    def _engine_encryption(self, resource: dict, *, snapshot: bool = False) -> None:
        try:
            major = int(resource.get("EngineVersion", "").split(".")[0])
        except (ValueError, AttributeError):
            major = -1
        if resource.get("Engine") != "postgres" or major != self.policy.engine_major:
            raise PreflightError("AWS_ENGINE_MISMATCH")
        encryption_key = "Encrypted" if snapshot else "StorageEncrypted"
        if resource.get(encryption_key) is not True:
            raise PreflightError("AWS_ENCRYPTION_REQUIRED")
        if self.policy.kms_key_id and resource.get("KmsKeyId") != self.policy.kms_key_id:
            raise PreflightError("AWS_KMS_MISMATCH")
        if resource.get("StorageType") not in {"gp2", "gp3"}:
            raise PreflightError("AWS_STORAGE_TYPE_UNSUPPORTED")
        if resource["StorageType"] != self.policy.storage_type:
            raise PreflightError("AWS_STORAGE_POLICY_MISMATCH")

    def _instance(self, identifier: str) -> dict:
        response = self._call(self.rds, "describe_db_instances", DBInstanceIdentifier=identifier)
        resources = response.get("DBInstances", [])
        if len(resources) != 1 or resources[0].get("DBInstanceIdentifier") != identifier:
            raise PreflightError("AWS_RESOURCE_IDENTITY_MISMATCH")
        resource = resources[0]
        self._arn(resource.get("DBInstanceArn", ""), "db", identifier)
        self._engine_encryption(resource)
        if resource.get("PubliclyAccessible") is not False:
            raise PreflightError("AWS_PRIVATE_REQUIRED")
        if resource.get("DBSubnetGroup", {}).get(
            "DBSubnetGroupName"
        ) != self.policy.subnet_group or {
            s.get("VpcSecurityGroupId") for s in resource.get("VpcSecurityGroups", [])
        } != set(self.policy.security_group_ids):
            raise PreflightError("AWS_NETWORK_MISMATCH")
        return resource

    def _observation(self, resource: dict, *, snapshot: bool = False) -> ResourceObservation:
        status = resource.get("Status" if snapshot else "DBInstanceStatus")
        allowed = (
            {"creating", "available", "deleting", "copying"}
            if snapshot
            else {
                "creating",
                "available",
                "deleting",
                "backing-up",
                "modifying",
                "rebooting",
                "storage-optimization",
                "configuring-enhanced-monitoring",
            }
        )
        if status not in allowed:
            raise PreflightError("AWS_RESOURCE_FAILED")
        endpoint = resource.get("Endpoint", {}).get("Address")
        if endpoint is not None:
            suffix = (
                ".rds.amazonaws.com"
                if not self.policy.region.startswith("cn-")
                else ".rds.amazonaws.com.cn"
            )
            if not isinstance(endpoint, str) or not endpoint.endswith(suffix):
                raise PreflightError("AWS_ENDPOINT_INVALID")
        return ResourceObservation(
            resource["DBSnapshotIdentifier" if snapshot else "DBInstanceIdentifier"],
            resource["DBSnapshotArn" if snapshot else "DBInstanceArn"],
            status,
            resource["EngineVersion"],
            endpoint,
            resource.get("SnapshotCreateTime"),
            resource.get("KmsKeyId"),
            resource["StorageType"],
        )

    def inspect_source(self) -> ResourceObservation:
        self._identity()
        try:
            resource = self._instance(self.policy.source_instance_id)
        except PreflightError as exc:
            if exc.code == "AWS_RESOURCE_ABSENT":
                raise PreflightError("AWS_SOURCE_ABSENT") from None
            raise
        tags = self._tags(resource["DBInstanceArn"])
        if (
            tags.get("Project") != "Preflight"
            or tags.get("Owner") != self.policy.owner
            or tags.get("Purpose") != "synthetic-source"
        ):
            raise PreflightError("SOURCE_NOT_OWNED_SYNTHETIC")
        return self._observation(resource)

    def _automatic_source_backup(self, identifier: str) -> dict:
        """Observe only AWS-managed backups of the exact source, never run resources.

        Fresh Describe TagList verifies ownership without widening ListTags grants.
        This does not establish run provenance or eligibility for deletion/recovery.
        """
        response = self._call(
            self.rds,
            "describe_db_snapshots",
            DBSnapshotIdentifier=identifier,
            SnapshotType="automated",
        )
        values = response.get("DBSnapshots", [])
        if len(values) != 1 or values[0].get("DBSnapshotIdentifier") != identifier:
            raise PreflightError("AWS_RESOURCE_IDENTITY_MISMATCH")
        value = values[0]
        self._arn(value.get("DBSnapshotArn", ""), "snapshot", identifier)
        self._engine_encryption(value, snapshot=True)
        if value.get("DBInstanceIdentifier") != self.policy.source_instance_id:
            raise PreflightError("AWS_SNAPSHOT_SOURCE_MISMATCH")
        if value.get("SnapshotType") != "automated":
            raise PreflightError("AWS_SNAPSHOT_TYPE_MISMATCH")
        pairs = value.get("TagList", [])
        if not isinstance(pairs, list) or any(
            not isinstance(t, dict)
            or not isinstance(t.get("Key"), str)
            or not isinstance(t.get("Value"), str)
            for t in pairs
        ):
            raise PreflightError("AWS_INVENTORY_TAG_MISMATCH")
        tags = {t.get("Key"): t.get("Value") for t in pairs}
        if (
            len(tags) != len(pairs)
            or tags.get("Project") != "Preflight"
            or tags.get("Owner") != self.policy.owner
            or any(k in tags for k in ("RunId", "SnapshotId"))
        ):
            raise PreflightError("AWS_INVENTORY_TAG_MISMATCH")
        status = value.get("Status")
        if not isinstance(status, str) or not re.fullmatch(r"[a-z][a-z-]{0,63}", status):
            raise PreflightError("AWS_INVENTORY_RESOURCE_INVALID")
        return value

    def _snapshot(self, identifier: str) -> dict:
        response = self._call(self.rds, "describe_db_snapshots", DBSnapshotIdentifier=identifier)
        resources = response.get("DBSnapshots", [])
        if len(resources) != 1 or resources[0].get("DBSnapshotIdentifier") != identifier:
            raise PreflightError("AWS_RESOURCE_IDENTITY_MISMATCH")
        resource = resources[0]
        self._arn(resource.get("DBSnapshotArn", ""), "snapshot", identifier)
        self._engine_encryption(resource, snapshot=True)
        if resource.get("DBInstanceIdentifier") != self.policy.source_instance_id:
            raise PreflightError("AWS_SNAPSHOT_SOURCE_MISMATCH")
        if resource.get("SnapshotType") != "manual":
            raise PreflightError("AWS_SNAPSHOT_TYPE_MISMATCH")
        return resource

    def inspect_snapshot(self, intent: ResourceIntent) -> ResourceObservation:
        self._intent(intent)
        self._identity()
        resource = self._snapshot(intent.snapshot_id)
        self._owned(resource["DBSnapshotArn"], intent)
        return self._observation(resource, snapshot=True)

    def inspect_clone(self, intent: ResourceIntent) -> ResourceObservation:
        self._intent(intent)
        self._identity()
        resource = self._instance(intent.clone_instance_id)
        self._owned(resource["DBInstanceArn"], intent)
        # DBInstance does not expose snapshot provenance. Intent ownership tags bind
        # the exact snapshot; restore request is journaled before submission.
        tags = self._tags(resource["DBInstanceArn"])
        if tags.get("SnapshotId") != intent.snapshot_id:
            raise PreflightError("AWS_CLONE_PROVENANCE_MISMATCH")
        if (
            resource.get("DBInstanceClass") != self.policy.instance_class
            or resource.get("DeletionProtection") is not False
        ):
            raise PreflightError("AWS_CLONE_CONFIGURATION_MISMATCH")
        observation = self._observation(resource)
        if observation.status == "available" and observation.endpoint is None:
            raise PreflightError("AWS_ENDPOINT_INVALID")
        source = self.inspect_source()
        if observation.endpoint and observation.endpoint == source.endpoint:
            raise PreflightError("AWS_SOURCE_CLONE_ENDPOINT_EQUAL")
        if (
            observation.engine_version != source.engine_version
            or observation.kms_key_id != source.kms_key_id
            or observation.storage_type != source.storage_type
        ):
            raise PreflightError("AWS_SOURCE_CLONE_CONFIGURATION_MISMATCH")
        return observation

    def _creation(self, intent: ResourceIntent, kind: str) -> None:
        self._intent(intent)
        if not self.policy.creation_authorized:
            raise PreflightError("CLOUD_CREATION_NOT_AUTHORIZED")
        if not self.store.get(intent.run_id)[kind + "_reserved"]:
            raise PreflightError("RESOURCE_NOT_RESERVED")

    def _reserve_budget(self, intent: ResourceIntent, kind: str) -> None:
        if self.budget_guard is None:
            raise PreflightError("BUDGET_ADMISSION_REQUIRED")
        self.budget_guard(intent, kind)

    def ensure_snapshot(self, intent: ResourceIntent) -> ResourceObservation:
        self._creation(intent, "snapshot")
        with self.store.mutation_lease(intent.run_id):
            source = self.inspect_source()
            try:
                observation = self.inspect_snapshot(intent)
            except PreflightError as exc:
                if exc.code != "AWS_RESOURCE_ABSENT":
                    raise
                self._enforce_live_inventory(intent, "snapshot")
                self._identity()
                self._reserve_budget(intent, "snapshot")
                self._call(
                    self.rds,
                    "create_db_snapshot",
                    DBInstanceIdentifier=self.policy.source_instance_id,
                    DBSnapshotIdentifier=intent.snapshot_id,
                    Tags=[{"Key": k, "Value": v} for k, v in intent.tags().items()],
                )
                # Creation response is not ownership/provenance evidence; fresh read.
                observation = self.inspect_snapshot(intent)
            if (
                observation.engine_version != source.engine_version
                or observation.kms_key_id != source.kms_key_id
                or observation.storage_type != source.storage_type
            ):
                raise PreflightError("AWS_SNAPSHOT_CONFIGURATION_MISMATCH")
            return observation

    def ensure_clone(self, intent: ResourceIntent) -> ResourceObservation:
        self._creation(intent, "clone")
        with self.store.mutation_lease(intent.run_id):
            snapshot = self.inspect_snapshot(intent)
            if snapshot.status != "available":
                raise PreflightError("AWS_RETRYABLE")
            source = self.inspect_source()
            if (
                snapshot.engine_version != source.engine_version
                or snapshot.kms_key_id != source.kms_key_id
                or snapshot.storage_type != source.storage_type
            ):
                raise PreflightError("AWS_SNAPSHOT_CONFIGURATION_MISMATCH")
            try:
                return self.inspect_clone(intent)
            except PreflightError as exc:
                if exc.code != "AWS_RESOURCE_ABSENT":
                    raise
            self._enforce_live_inventory(intent, "clone")
            self._identity()
            tags = intent.tags() | {"SnapshotId": intent.snapshot_id}
            self._reserve_budget(intent, "clone")
            self._call(
                self.rds,
                "restore_db_instance_from_db_snapshot",
                DBInstanceIdentifier=intent.clone_instance_id,
                DBSnapshotIdentifier=intent.snapshot_id,
                DBInstanceClass=self.policy.instance_class,
                DBSubnetGroupName=self.policy.subnet_group,
                VpcSecurityGroupIds=list(self.policy.security_group_ids),
                PubliclyAccessible=False,
                DeletionProtection=False,
                MultiAZ=False,
                AutoMinorVersionUpgrade=False,
                CopyTagsToSnapshot=True,
                StorageType=self.policy.storage_type,
                Tags=[{"Key": k, "Value": v} for k, v in tags.items()],
            )
            observation = self.inspect_clone(intent)
            if observation.engine_version != source.engine_version:
                raise PreflightError("AWS_ENGINE_VERSION_MISMATCH")
            return observation

    def verify_recovery_snapshot(
        self, snapshot_id: str, expected_source: str, before_created_at: datetime
    ) -> ResourceObservation:
        if (
            not valid_id(snapshot_id)
            or expected_source != self.policy.source_instance_id
            or before_created_at.tzinfo is None
            or self.recovery_attestation is None
            or not self.recovery_attestation(snapshot_id, expected_source, before_created_at)
        ):
            raise PreflightError("RECOVERY_BACKUP_INVALID")
        self._identity()
        resource = self._snapshot(snapshot_id)
        tags = self._tags(resource["DBSnapshotArn"])
        created = resource.get("SnapshotCreateTime")
        # A provider timestamp alone cannot prove equivalent data. The injected
        # callback above requires independent trusted persisted pre-apply evidence.
        if (
            tags.get("Project") != "Preflight"
            or tags.get("Owner") != self.policy.owner
            or resource.get("Status") != "available"
            or not isinstance(created, datetime)
            or created.tzinfo is None
            or created.astimezone(UTC) > before_created_at.astimezone(UTC)
        ):
            raise PreflightError("RECOVERY_BACKUP_INVALID")
        return self._observation(resource, snapshot=True)

    def cleanup(self, intent: ResourceIntent, selection: CleanupPolicy) -> dict[str, str]:
        self._intent(intent)
        if not selection.literal_gate_approved:
            raise PreflightError("CLEANUP_APPROVAL_REQUIRED")
        if not selection.delete_clone and not selection.delete_snapshot:
            raise PreflightError("CLEANUP_SELECTION_REQUIRED")
        if not selection.reports_retained:
            raise PreflightError("CLEANUP_REPORT_RETENTION_REQUIRED")
        allowed_phases = {
            "READY",
            "BASELINED",
            "PASS",
            "WARN",
            "BLOCKED",
            "BLOCK",
            "AWAITING_APPROVAL",
            "APPLIED",
            "APPLY_FAILED",
            "APPLIED_NEEDS_ATTENTION",
            "STALE",
            "ERROR",
        }
        if selection.run_phase not in allowed_phases or selection.dependent_operation_active:
            raise PreflightError("CLEANUP_MUTATION_STATE_BLOCKED")
        if (
            selection.clone_instance_id not in {None, intent.clone_instance_id}
            or selection.snapshot_id not in {None, intent.snapshot_id}
            or selection.clone_instance_id == self.policy.source_instance_id
            or selection.snapshot_id == self.policy.source_instance_id
        ):
            raise PreflightError("CLEANUP_RESOURCE_MISMATCH")
        if (selection.delete_clone and selection.clone_instance_id != intent.clone_instance_id) or (
            selection.delete_snapshot and selection.snapshot_id != intent.snapshot_id
        ):
            raise PreflightError("CLEANUP_EXACT_SELECTION_REQUIRED")
        with self.store.mutation_lease(intent.run_id):
            self.inspect_source()
            if selection.delete_snapshot and selection.source_apply_attempted:
                backup = selection.recovery_backup_snapshot_id
                if (
                    not backup
                    or backup == intent.snapshot_id
                    or selection.preapply_not_after is None
                ):
                    raise PreflightError("RECOVERY_BACKUP_REQUIRED")
                self.verify_recovery_snapshot(
                    backup, self.policy.source_instance_id, selection.preapply_not_after
                )
            # Preflight every selected resource before any deletion.
            observed: dict[str, ResourceObservation | None] = {}
            for kind, selected, inspect in (
                ("clone", selection.delete_clone, self.inspect_clone),
                ("snapshot", selection.delete_snapshot, self.inspect_snapshot),
            ):
                if selected:
                    try:
                        observed[kind] = inspect(intent)
                    except PreflightError as exc:
                        if exc.code != "AWS_RESOURCE_ABSENT":
                            raise
                        observed[kind] = None
            if any(r and r.status not in {"available", "deleting"} for r in observed.values()):
                raise PreflightError("CLEANUP_RESOURCE_BUSY")
            result = {}
            for kind, resource in observed.items():
                if resource is None:
                    result[kind] = "ABSENT"
                    continue
                if resource.status == "deleting":
                    result[kind] = "DELETING"
                    continue
                if resource.status != "available":
                    raise PreflightError("CLEANUP_RESOURCE_BUSY")
                self._identity()
                if kind == "clone":
                    self._call(
                        self.rds,
                        "delete_db_instance",
                        DBInstanceIdentifier=intent.clone_instance_id,
                        SkipFinalSnapshot=True,
                        DeleteAutomatedBackups=True,
                    )
                else:
                    self._call(
                        self.rds, "delete_db_snapshot", DBSnapshotIdentifier=intent.snapshot_id
                    )
                result[kind] = "DELETING"
            self.store.release_reservation(
                intent,
                clone_absent=result.get("clone") == "ABSENT",
                snapshot_absent=result.get("snapshot") == "ABSENT",
            )
            return result

    def observe_cleanup(self, intent: ResourceIntent) -> dict[str, str]:
        """Read-only AWS reconciliation; never issues another deletion request.

        Keep DELETING distinct from ABSENT. Present resources still need exact
        account/ARN/provenance/tag checks; source absence is never clone absence.
        """
        self._intent(intent)
        with self.store.mutation_lease(intent.run_id):
            self.inspect_source()
            result = {}
            for kind, inspect in (
                ("clone", self.inspect_clone),
                ("snapshot", self.inspect_snapshot),
            ):
                try:
                    observation = inspect(intent)
                    result[kind] = observation.status.upper()
                except PreflightError as exc:
                    if exc.code != "AWS_RESOURCE_ABSENT":
                        raise
                    result[kind] = "ABSENT"
            self.store.release_reservation(
                intent,
                clone_absent=result["clone"] == "ABSENT",
                snapshot_absent=result["snapshot"] == "ABSENT",
            )
            return result
