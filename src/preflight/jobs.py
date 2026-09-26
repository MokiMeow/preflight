"""Durable infrastructure intent and a single cloud mutation lease.

This worker does no SQL. AWS availability and database readiness are separate.
The application owns its run CAS/lock and must hold it when invoking cleanup.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from filelock import FileLock, Timeout

from preflight.models import PreflightError

if TYPE_CHECKING:
    from preflight.aws_rds import RdsAdapter


@dataclass(frozen=True)
class ResourceIntent:
    run_id: str
    owner: str
    expires_at: str
    snapshot_id: str
    clone_instance_id: str

    @classmethod
    def for_run(cls, run_id: UUID, owner: str, expires_at: str) -> ResourceIntent:
        # Use the full UUID, avoiding short-name collision adoption.
        prefix = f"preflight-{run_id.hex}"
        return cls(str(run_id), owner, expires_at, f"{prefix}-snap", f"{prefix}-clone")

    def tags(self) -> dict[str, str]:
        return {
            "Project": "Preflight",
            "Owner": self.owner,
            "RunId": self.run_id,
            "ExpiresAt": self.expires_at,
        }


class JobStore:
    """Separate private SQLite database. Resource reservations survive job errors.

    Reservations are not automatically freed at expiry or after deletion requests.
    An operator must reconcile retained resources before another reservation.
    """

    def __init__(self, path: str | Path):
        self.path = str(Path(path).resolve())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(self.path + ".cloud-mutation.lock")
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                    run_id TEXT PRIMARY KEY, request_id TEXT UNIQUE NOT NULL,
                    intent TEXT NOT NULL, deadline REAL NOT NULL,
                    phase TEXT NOT NULL, next_poll REAL NOT NULL DEFAULT 0,
                    polls INTEGER NOT NULL DEFAULT 0, error_code TEXT,
                    aws_status TEXT, updated_at REAL NOT NULL,
                    snapshot_reserved INTEGER NOT NULL DEFAULT 1,
                    clone_reserved INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS cloud_lease (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1), run_id TEXT,
                    acquired_at REAL
                );
                INSERT OR IGNORE INTO cloud_lease(singleton) VALUES(1);
            """)

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def enqueue(
        self,
        request_id: UUID,
        intent: ResourceIntent,
        *,
        deadline: float,
        max_clones: int,
        max_snapshots: int,
    ) -> dict:
        if deadline <= time.time() or max_clones != 1 or not 1 <= max_snapshots <= 3:
            raise PreflightError("CLOUD_PLAN_INVALID")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT * FROM jobs WHERE request_id=?", (str(request_id),)
            ).fetchone()
            if existing:
                if json.loads(existing["intent"]) != asdict(intent):
                    raise PreflightError("REQUEST_ID_CONFLICT")
                return dict(existing)
            counts = db.execute(
                "SELECT COALESCE(SUM(clone_reserved),0), "
                "COALESCE(SUM(snapshot_reserved),0) FROM jobs"
            ).fetchone()
            active = db.execute(
                "SELECT 1 FROM jobs WHERE phase NOT IN ('AVAILABLE','ERROR')"
            ).fetchone()
            if active:
                raise PreflightError("REHEARSAL_ACTIVE")
            if counts[0] >= max_clones or counts[1] >= max_snapshots:
                raise PreflightError("RESOURCE_CAP_REACHED")
            try:
                db.execute(
                    "INSERT INTO jobs(run_id,request_id,intent,deadline,phase,updated_at) "
                    "VALUES(?,?,?,?,?,?)",
                    (
                        intent.run_id,
                        str(request_id),
                        json.dumps(asdict(intent), sort_keys=True),
                        deadline,
                        "SNAPSHOTTING",
                        time.time(),
                    ),
                )
            except sqlite3.IntegrityError:
                raise PreflightError("RUN_ID_CONFLICT") from None
        return self.get(intent.run_id)

    def get(self, run_id: str) -> dict:
        with self._db() as db:
            row = db.execute("SELECT * FROM jobs WHERE run_id=?", (run_id,)).fetchone()
            if row is None:
                raise PreflightError("JOB_NOT_FOUND")
            return dict(row)

    def resource_registry(self) -> list[dict]:
        """All exact persisted intent IDs, including retained and released resources."""
        with self._db() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT intent, clone_reserved, snapshot_reserved FROM jobs ORDER BY run_id"
                )
            ]

    def require_reservation(
        self, intent: ResourceIntent, *, max_clones: int, max_snapshots: int
    ) -> None:
        row = self.get(intent.run_id)
        if json.loads(row["intent"]) != asdict(intent):
            raise PreflightError("RESOURCE_INTENT_MISMATCH")
        with self._db() as db:
            counts = db.execute(
                "SELECT SUM(clone_reserved), SUM(snapshot_reserved) FROM jobs"
            ).fetchone()
        if counts[0] > max_clones or counts[1] > max_snapshots:
            raise PreflightError("RESOURCE_CAP_REACHED")

    def release_reservation(
        self, intent: ResourceIntent, *, clone_absent: bool = False, snapshot_absent: bool = False
    ) -> None:
        """Adapter-only: called after fresh exact-ID provider absence observation.

        Absence flags are server evidence, never model/tool parameters. Releasing
        counts does not change a run outcome or authorize a resource deletion.
        """
        row = self.get(intent.run_id)
        if json.loads(row["intent"]) != asdict(intent):
            raise PreflightError("RESOURCE_INTENT_MISMATCH")
        with self._db() as db:
            db.execute(
                "UPDATE jobs SET clone_reserved=CASE WHEN ? THEN 0 ELSE clone_reserved END, "
                "snapshot_reserved=CASE WHEN ? THEN 0 ELSE snapshot_reserved END WHERE run_id=?",
                (clone_absent is True, snapshot_absent is True, intent.run_id),
            )

    @contextmanager
    def mutation_lease(self, run_id: str) -> Iterator[None]:
        try:
            self.lock.acquire(timeout=0)
        except Timeout:
            raise PreflightError("CLOUD_MUTATION_BUSY") from None
        try:
            with self._db() as db:
                db.execute(
                    "UPDATE cloud_lease SET run_id=?,acquired_at=? WHERE singleton=1",
                    (run_id, time.time()),
                )
            yield
        finally:
            with self._db() as db:
                db.execute("UPDATE cloud_lease SET run_id=NULL,acquired_at=NULL WHERE singleton=1")
            self.lock.release()

    def update(
        self,
        run_id: str,
        *,
        phase: str,
        aws_status: str | None,
        error_code: str | None = None,
        now: float | None = None,
    ) -> dict:
        now = time.time() if now is None else now
        row = self.get(run_id)
        polls = row["polls"] + 1
        # Bounded exponential backoff; polling is a caller-controlled tick, not a sleep.
        with self._db() as db:
            db.execute(
                "UPDATE jobs SET phase=?,aws_status=?,error_code=?,polls=?,"
                "next_poll=?,updated_at=? WHERE run_id=?",
                (
                    phase,
                    aws_status,
                    error_code,
                    polls,
                    now + min(60, 2 ** min(polls, 6)),
                    now,
                    run_id,
                ),
            )
        return self.get(run_id)


def tick_job(
    store: JobStore, adapter: RdsAdapter, run_id: str, *, now: float | None = None
) -> dict:
    """One bounded observation/creation step. Never execute or replay SQL.

    AVAILABLE means control-plane availability only; lead must verify TLS/role/
    object policy before promoting the application run to READY.
    """
    with store.mutation_lease(run_id):
        return _tick_job(store, adapter, run_id, now=now)


def _tick_job(store: JobStore, adapter: RdsAdapter, run_id: str, *, now: float | None) -> dict:
    now = time.time() if now is None else now
    row = store.get(run_id)
    if row["phase"] in {"ERROR", "AVAILABLE"} or now < row["next_poll"]:
        return row
    if now >= row["deadline"]:
        return store.update(
            run_id,
            phase="ERROR",
            aws_status=row["aws_status"],
            error_code="CLOUD_DEADLINE_EXCEEDED",
            now=now,
        )
    intent = ResourceIntent(**json.loads(row["intent"]))
    try:
        if row["phase"] == "SNAPSHOTTING":
            resource = adapter.ensure_snapshot(intent)
            phase = "RESTORING" if resource.status == "available" else "SNAPSHOTTING"
        else:
            resource = adapter.ensure_clone(intent)
            phase = "AVAILABLE" if resource.status == "available" else "RESTORING"
        return store.update(run_id, phase=phase, aws_status=resource.status, now=now)
    except PreflightError as exc:
        retryable = exc.code in {"AWS_RETRYABLE", "AWS_OUTCOME_UNCERTAIN"}
        return store.update(
            run_id,
            phase=row["phase"] if retryable else "ERROR",
            aws_status=row["aws_status"],
            error_code=exc.code,
            now=now,
        )
