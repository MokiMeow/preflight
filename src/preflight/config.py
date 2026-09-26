"""Nonsecret policy settings; cloud and source writes are disabled by default."""

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .artifacts import strict_json
from .models import Identifier, ResourceId, StrictModel, TableName


class Settings(StrictModel):
    state_dir: Path = Path("var")
    evidence_backend: Literal["aws_rds", "local_postgres_test"] = "aws_rds"
    source_instance_id: ResourceId | None = None
    database_name: Identifier = "preflight_demo"
    account_id: str | None = Field(default=None, pattern=r"^\d{12}$")
    region: str | None = Field(default=None, pattern=r"^[a-z]{2}-[a-z]+-\d$")
    owner: str = Field(default="team-operator", pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    source_allowlist: list[ResourceId] = Field(default_factory=list)
    table_allowlist: list[TableName] = Field(default_factory=lambda: ["public.customers"])
    creation_authorized: bool = False
    approved_budget_ceiling: float | None = Field(default=None, gt=0, le=100)
    enable_demo_source_apply: bool = False
    max_active_runs: Literal[1] = 1
    max_run_owned_clones: Literal[1] = 1
    max_run_owned_snapshots: int = Field(default=3, ge=1, le=3)
    db_subnet_group_name: str | None = None
    clone_security_group_ids: list[str] = Field(default_factory=list)
    instance_class: str = "db.t4g.micro"
    postgres_major: Literal[18] = 18
    sslrootcert: Path | None = None
    source_read_secret_arn: str | None = None
    migration_writer_secret_arn: str | None = None
    lock_timeout_ms: int = Field(default=3000, ge=100, le=3000)
    service_port: int = Field(default=8000, ge=1024, le=65535)

    @model_validator(mode="after")
    def authorization_dependencies(self):
        if self.evidence_backend != "aws_rds" and self.enable_demo_source_apply:
            raise ValueError("deployed source apply requires aws_rds")
        if self.creation_authorized and not (
            self.approved_budget_ceiling
            and self.account_id
            and self.region
            and self.source_instance_id
        ):
            raise ValueError("creation authorization requires bounded account scope")
        if self.source_instance_id and self.source_instance_id not in self.source_allowlist:
            raise ValueError("configured source must be allowlisted")
        return self


def load_settings(path: Path | None = None) -> Settings:
    settings_path = path or Path(os.environ.get("PREFLIGHT_SETTINGS", "config/settings.local.json"))
    if not settings_path.exists():
        return Settings()
    return Settings.model_validate(strict_json(settings_path.read_bytes(), 65536))


def readiness(settings: Settings) -> dict:
    cloud = bool(
        settings.creation_authorized
        and settings.account_id
        and settings.region
        and settings.source_instance_id
        and settings.db_subnet_group_name
        and settings.clone_security_group_ids
    )
    return {
        "local_ready": True,
        "cloud_config_ready": cloud,
        "cloud_connected_verified": False,
        "source_apply_enabled": settings.enable_demo_source_apply,
        "source_apply_ready": False,
        "gateway_configured": bool(os.environ.get("PREFLIGHT_GATEWAY_CONFIGURED")),
        "local_sandbox_configured": bool(os.environ.get("PREFLIGHT_LOCAL_SANDBOX_CONFIGURED")),
        "provider_roundtrip_verified": False,
        "human_approval_verified": False,
    }


def state_storage_status(settings: Settings) -> dict:
    """Read-only local diagnostics; empty state is never proof of no AWS resources."""
    import sqlite3
    from contextlib import closing

    if settings.source_instance_id is None:
        return {"status": "NOT_CONFIGURED", "warning": None, "cloud_absence_verified": False}
    counts = {}
    for filename, table in (("preflight.sqlite3", "runs"), ("cloud.sqlite", "jobs")):
        path = settings.state_dir / filename
        try:
            if not path.is_file():
                return {
                    "status": "STATE_FILES_MISSING",
                    "warning": "CONFIGURED_SOURCE_WITH_MISSING_STATE",
                    "cloud_absence_verified": False,
                }
            wal = path.with_name(path.name + "-wal")
            if wal.is_file() and wal.stat().st_size:
                return {
                    "status": "STATE_WAL_PRESENT",
                    "warning": "STATE_COUNTS_REQUIRE_RUNTIME_RECONCILIATION",
                    "cloud_absence_verified": False,
                }
            with closing(
                sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
            ) as database:
                # Inspect a static main-file snapshot without creating WAL/SHM.
                # A pending WAL above must be reconciled by the running service.
                # Both table names are fixed internal literals, never configuration input.
                counts[table] = database.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except (sqlite3.Error, OSError):
            return {
                "status": "STATE_UNREADABLE",
                "warning": "CONFIGURED_SOURCE_STATE_REQUIRES_RECONCILIATION",
                "cloud_absence_verified": False,
            }
    try:
        for filename in ("preflight.sqlite3-wal", "cloud.sqlite-wal"):
            wal = settings.state_dir / filename
            if wal.is_file() and wal.stat().st_size:
                return {
                    "status": "STATE_WAL_PRESENT",
                    "warning": "STATE_COUNTS_REQUIRE_RUNTIME_RECONCILIATION",
                    "cloud_absence_verified": False,
                }
    except OSError:
        return {
            "status": "STATE_UNREADABLE",
            "warning": "CONFIGURED_SOURCE_STATE_REQUIRES_RECONCILIATION",
            "cloud_absence_verified": False,
        }
    empty = counts["runs"] == 0 and counts["jobs"] == 0
    return {
        "status": "EMPTY_CONFIGURED_STATE" if empty else "STATE_RECORDS_PRESENT",
        "warning": "CONFIGURED_SOURCE_WITH_EMPTY_STATE" if empty else None,
        "cloud_absence_verified": False,
    }
