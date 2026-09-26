"""Durable CAS state, immutable records and conservative restart reconciliation."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .artifacts import canonical_json, strict_json
from .models import Phase, PreflightError, TRANSITIONS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class StateStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.transaction() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS records (
              kind TEXT NOT NULL, id TEXT NOT NULL, value BLOB NOT NULL,
              PRIMARY KEY(kind,id));
            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY, phase TEXT NOT NULL, revision INTEGER NOT NULL,
              value BLOB NOT NULL, cleanup_state TEXT NOT NULL DEFAULT 'NOT_REQUESTED');
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, timestamp TEXT NOT NULL,
              before_phase TEXT, after_phase TEXT, code TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS idempotency (
              tool TEXT NOT NULL, request_id TEXT NOT NULL, digest TEXT NOT NULL,
              result BLOB, PRIMARY KEY(tool,request_id));
            CREATE TABLE IF NOT EXISTS apply_attempts (
              run_id TEXT PRIMARY KEY, intent BLOB NOT NULL, result BLOB);
            """)

    @contextmanager
    def transaction(self):
        con = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA busy_timeout=5000")
        con.execute("BEGIN IMMEDIATE")
        try:
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    def put_once(self, kind: str, record_id: str, value: Any):
        encoded = canonical_json(value)
        with self.transaction() as con:
            row = con.execute("SELECT value FROM records WHERE kind=? AND id=?",
                              (kind, record_id)).fetchone()
            if row:
                if bytes(row[0]) != encoded:
                    raise PreflightError("RECORD_IMMUTABLE")
                return
            con.execute("INSERT INTO records VALUES (?,?,?)", (kind, record_id, encoded))

    def get(self, kind: str, record_id: str) -> dict:
        with self.transaction() as con:
            row = con.execute("SELECT value FROM records WHERE kind=? AND id=?",
                              (kind, record_id)).fetchone()
        if not row:
            raise PreflightError("NOT_FOUND")
        return strict_json(bytes(row[0]))

    def list_records(self, kind: str) -> list[dict]:
        with self.transaction() as con:
            rows = con.execute("SELECT value FROM records WHERE kind=? ORDER BY id", (kind,)).fetchall()
        return [strict_json(bytes(row[0])) for row in rows]

    def create_run(self, value: dict):
        with self.transaction() as con:
            if con.execute("SELECT 1 FROM runs WHERE cleanup_state != 'COMPLETE' LIMIT 1").fetchone():
                raise PreflightError("ACTIVE_RUN_LIMIT")
            con.execute("INSERT INTO runs(id,phase,revision,value) VALUES(?,?,0,?)",
                        (value["run_id"], "REGISTERED", canonical_json(value)))
            con.execute("INSERT INTO events(run_id,timestamp,after_phase,code) VALUES(?,?,?,?)",
                        (value["run_id"], utc_now(), "REGISTERED", "RUN_CREATED"))

    def get_run(self, run_id: str) -> dict:
        with self.transaction() as con:
            row = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row:
            raise PreflightError("RUN_NOT_FOUND")
        data = strict_json(bytes(row["value"]))
        data.update(phase=row["phase"], revision=row["revision"], cleanup_state=row["cleanup_state"])
        return data

    def list_runs(self) -> list[dict]:
        with self.transaction() as con:
            ids = [row[0] for row in con.execute("SELECT id FROM runs ORDER BY id")]
        return [self.get_run(run_id) for run_id in ids]

    def transition(self, run_id: str, expected: str, new: str, updates: dict | None = None,
                   code: str = "STATE_TRANSITION") -> dict:
        if Phase(new) not in TRANSITIONS.get(Phase(expected), frozenset()):
            raise PreflightError("ILLEGAL_TRANSITION")
        with self.transaction() as con:
            row = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not row or row["phase"] != expected:
                raise PreflightError("STATE_CONFLICT")
            value = strict_json(bytes(row["value"]))
            value.update(updates or {})
            value["updated_at"] = utc_now()
            con.execute("UPDATE runs SET phase=?,revision=revision+1,value=? WHERE id=? AND revision=?",
                        (new, canonical_json(value), run_id, row["revision"]))
            con.execute("INSERT INTO events(run_id,timestamp,before_phase,after_phase,code) VALUES(?,?,?,?,?)",
                        (run_id, utc_now(), expected, new, code))
        return self.get_run(run_id)

    def patch_run(self, run_id: str, expected_revision: int, updates: dict):
        with self.transaction() as con:
            row = con.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not row or row["revision"] != expected_revision:
                raise PreflightError("STATE_CONFLICT")
            value = strict_json(bytes(row["value"]))
            value.update(updates)
            con.execute("UPDATE runs SET revision=revision+1,value=? WHERE id=?",
                        (canonical_json(value), run_id))

    def set_cleanup(self, run_id: str, state: str):
        with self.transaction() as con:
            if not con.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone():
                raise PreflightError("RUN_NOT_FOUND")
            con.execute("UPDATE runs SET cleanup_state=?,revision=revision+1 WHERE id=?", (state, run_id))

    def claim_request(self, tool: str, request_id: str, digest: str) -> dict | None:
        with self.transaction() as con:
            row = con.execute("SELECT * FROM idempotency WHERE tool=? AND request_id=?",
                              (tool, request_id)).fetchone()
            if row:
                if row["digest"] != digest:
                    raise PreflightError("IDEMPOTENCY_CONFLICT")
                if row["result"] is None:
                    raise PreflightError("REQUEST_IN_PROGRESS")
                return strict_json(bytes(row["result"]))
            con.execute("INSERT INTO idempotency VALUES(?,?,?,NULL)", (tool, request_id, digest))
        return None

    def finish_request(self, tool: str, request_id: str, result: dict):
        with self.transaction() as con:
            con.execute("UPDATE idempotency SET result=? WHERE tool=? AND request_id=?",
                        (canonical_json(result), tool, request_id))

    def begin_apply(self, run_id: str, intent: dict):
        with self.transaction() as con:
            row = con.execute("SELECT phase FROM runs WHERE id=?", (run_id,)).fetchone()
            if con.execute("SELECT 1 FROM apply_attempts WHERE run_id=?", (run_id,)).fetchone():
                raise PreflightError("SOURCE_APPLY_REPLAY_REJECTED")
            if not row or row[0] != "AWAITING_APPROVAL":
                raise PreflightError("SOURCE_NOT_ELIGIBLE")
            con.execute("INSERT INTO apply_attempts VALUES(?,?,NULL)", (run_id, canonical_json(intent)))
            con.execute("UPDATE runs SET phase='APPLYING',revision=revision+1 WHERE id=?", (run_id,))
            con.execute("INSERT INTO events(run_id,timestamp,before_phase,after_phase,code) VALUES(?,?,?,?,?)",
                        (run_id, utc_now(), "AWAITING_APPROVAL", "APPLYING", "APPLY_INTENT"))

    def has_apply(self, run_id: str) -> bool:
        with self.transaction() as con:
            return bool(con.execute("SELECT 1 FROM apply_attempts WHERE run_id=?", (run_id,)).fetchone())

    def finish_apply(self, run_id: str, result: dict):
        with self.transaction() as con:
            con.execute("UPDATE apply_attempts SET result=? WHERE run_id=? AND result IS NULL",
                        (canonical_json(result), run_id))

    def reconcile_restart(self):
        for run in self.list_runs():
            phase = run["phase"]
            if phase == "APPLYING":
                self.transition(run["run_id"], phase, "APPLY_OUTCOME_UNKNOWN", code="RESTART_UNKNOWN")
            elif phase == "MIGRATING":
                self.transition(run["run_id"], phase, "CLONE_OUTCOME_UNKNOWN", code="RESTART_UNKNOWN")
            elif phase in ("BASELINED", "VALIDATING"):
                self.transition(run["run_id"], phase, "ERROR", code="BASELINE_MEMORY_LOST")
