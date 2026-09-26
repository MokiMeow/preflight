"""Doctor inspects only local files and never interprets empty state as AWS absence."""

import sqlite3
from pathlib import Path

from preflight.config import Settings, state_storage_status
from preflight.jobs import JobStore
from preflight.storage import StateStore


def configured(path):
    return Settings(
        state_dir=path, source_instance_id="owned-source", source_allowlist=["owned-source"]
    )


def test_unconfigured_doctor_does_not_create_state(tmp_path):
    assert state_storage_status(Settings(state_dir=tmp_path))["status"] == "NOT_CONFIGURED"
    assert not list(tmp_path.iterdir())


def test_configured_missing_state_warns_without_creating_files(tmp_path):
    result = state_storage_status(configured(tmp_path))
    assert result["warning"] == "CONFIGURED_SOURCE_WITH_MISSING_STATE"
    assert result["cloud_absence_verified"] is False
    assert not list(tmp_path.iterdir())


def test_configured_empty_state_is_not_cloud_absence(tmp_path):
    StateStore(tmp_path / "preflight.sqlite3")
    JobStore(tmp_path / "cloud.sqlite")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    result = state_storage_status(configured(tmp_path))
    assert result["warning"] == "CONFIGURED_SOURCE_WITH_EMPTY_STATE"
    assert result["cloud_absence_verified"] is False
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}


def test_wrong_state_schema_diagnostic_contains_no_private_error(tmp_path):
    private = "PRIVATE_STATE_SENTINEL"
    with sqlite3.connect(tmp_path / "preflight.sqlite3") as db:
        db.execute(f"CREATE TABLE {private} (value TEXT)")
    JobStore(tmp_path / "cloud.sqlite")
    result = state_storage_status(configured(tmp_path))
    assert result["warning"] == "CONFIGURED_SOURCE_STATE_REQUIRES_RECONCILIATION"
    assert private not in str(result)
    assert str(tmp_path) not in str(result)


def test_pending_wal_is_not_silently_ignored_or_modified(tmp_path):
    StateStore(tmp_path / "preflight.sqlite3")
    JobStore(tmp_path / "cloud.sqlite")
    wal = tmp_path / "preflight.sqlite3-wal"
    wal.write_bytes(b"PRIVATE_PENDING_WAL_SENTINEL")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    result = state_storage_status(configured(tmp_path))
    assert result["warning"] == "STATE_COUNTS_REQUIRE_RUNTIME_RECONCILIATION"
    assert result["cloud_absence_verified"] is False
    assert "PRIVATE_PENDING_WAL_SENTINEL" not in str(result)
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}


def test_permission_error_does_not_echo_private_path(monkeypatch, tmp_path):
    def denied(path):
        raise PermissionError("PRIVATE_PERMISSION_SENTINEL")

    monkeypatch.setattr(Path, "is_file", denied)
    result = state_storage_status(configured(tmp_path))
    assert result["status"] == "STATE_UNREADABLE"
    assert "PRIVATE_PERMISSION_SENTINEL" not in str(result)


def test_wal_appearing_during_observation_requires_reconciliation(monkeypatch, tmp_path):
    StateStore(tmp_path / "preflight.sqlite3")
    JobStore(tmp_path / "cloud.sqlite")
    connect = sqlite3.connect

    def concurrent_wal(*args, **kwargs):
        (tmp_path / "preflight.sqlite3-wal").write_bytes(b"PENDING_SYNTHETIC_WRITE")
        return connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", concurrent_wal)
    result = state_storage_status(configured(tmp_path))
    assert result["status"] == "STATE_WAL_PRESENT"
    assert result["cloud_absence_verified"] is False
