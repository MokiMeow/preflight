from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from preflight.artifacts import ArtifactStore, sha256
from preflight.models import PreflightError
from preflight.storage import StateStore


def make_run(store):
    run_id = str(uuid4())
    store.create_run({"run_id": run_id, "candidate_id": str(uuid4())})
    return run_id


def test_cas_and_illegal_transition(tmp_path):
    store = StateStore(tmp_path / "state.db")
    run_id = make_run(store)

    def advance():
        try:
            store.transition(run_id, "REGISTERED", "SNAPSHOTTING")
            return True
        except PreflightError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(lambda _: advance(), range(2))) == 1
    with pytest.raises(PreflightError):
        store.transition(run_id, "SNAPSHOTTING", "APPLIED")


def test_single_active_and_idempotency(tmp_path):
    store = StateStore(tmp_path / "state.db")
    make_run(store)
    with pytest.raises(PreflightError):
        make_run(store)
    digest = sha256(b"same")
    assert store.claim_request("register", "id", digest) is None
    with pytest.raises(PreflightError, match="REQUEST_IN_PROGRESS"):
        store.claim_request("register", "id", digest)
    store.finish_request("register", "id", {"candidate_id": "one"})
    assert store.claim_request("register", "id", digest)["candidate_id"] == "one"
    with pytest.raises(PreflightError, match="IDEMPOTENCY_CONFLICT"):
        store.claim_request("register", "id", sha256(b"different"))


def test_restart_unknown_and_never_replay(tmp_path):
    store = StateStore(tmp_path / "state.db")
    run_id = make_run(store)
    for old, new in [
        ("REGISTERED", "SNAPSHOTTING"),
        ("SNAPSHOTTING", "RESTORING"),
        ("RESTORING", "READY"),
        ("READY", "BASELINED"),
        ("BASELINED", "MIGRATING"),
        ("MIGRATING", "VALIDATING"),
        ("VALIDATING", "PASS"),
        ("PASS", "AWAITING_APPROVAL"),
    ]:
        store.transition(run_id, old, new)
    store.begin_apply(run_id, {"hash": sha256(b"sql")})
    store.reconcile_restart()
    assert store.get_run(run_id)["phase"] == "APPLY_OUTCOME_UNKNOWN"
    with pytest.raises(PreflightError, match="SOURCE_APPLY_REPLAY_REJECTED"):
        store.begin_apply(run_id, {})


def test_exact_bytes_immutable_and_traversal(tmp_path):
    artifacts = ArtifactStore(tmp_path)
    raw = b"-- unicode \xe2\x98\x83\r\nUPDATE public.customers SET email='x';\r\n"
    digest = artifacts.write_once("safe/migration.sql", raw)
    assert artifacts.read("safe/migration.sql", digest) == raw
    with pytest.raises(PreflightError):
        artifacts.write_once("safe/migration.sql", raw.replace(b"\r", b""))
    with pytest.raises(PreflightError):
        artifacts.write_once("../outside", b"bad")
