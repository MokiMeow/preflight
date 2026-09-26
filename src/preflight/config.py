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
    approved_budget_ceiling: float | None = Field(default=None, gt=0)
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
        if self.creation_authorized and not (self.approved_budget_ceiling and self.account_id
                                             and self.region and self.source_instance_id):
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
    cloud = bool(settings.creation_authorized and settings.account_id and settings.region
                 and settings.source_instance_id and settings.db_subnet_group_name
                 and settings.clone_security_group_ids)
    return {"local_ready": True, "cloud_config_ready": cloud,
            "cloud_connected_verified": False,
            "source_apply_enabled": settings.enable_demo_source_apply,
            "source_apply_ready": False,
            "gateway_configured": bool(os.environ.get("PREFLIGHT_GATEWAY_CONFIGURED")),
            "daytona_configured": bool(os.environ.get("PREFLIGHT_DAYTONA_CONFIGURED")),
            "provider_roundtrip_verified": False,
            "human_approval_verified": False}
