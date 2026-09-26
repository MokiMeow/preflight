"""Status remains responsive without overwriting another cleanup selection."""

import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import uuid4

from tests.unit.test_remaining_verdict_boundaries import real_local_run


def test_busy_cleanup_returns_snapshot_without_waiting_or_observing(tmp_path):
    service, run_id, _ = real_local_run(tmp_path)
    service.store.begin_cleanup(run_id, {"delete_clone": True, "delete_snapshot": False})
    entered, release = threading.Event(), threading.Event()

    def unexpected_observation(run):
        raise AssertionError("busy cleanup must not be observed")

    service.runtime = SimpleNamespace(observe_cleanup=unexpected_observation)

    def mutation():
        with service.lock(run_id):
            entered.set()
            assert release.wait(5)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            held = pool.submit(mutation)
            try:
                assert entered.wait(2)
                result = pool.submit(
                    service.call, "get_run", {"request_id": str(uuid4()), "run_id": run_id}
                ).result(timeout=1)
                assert result["ok"]
                assert result["data"]["cleanup_state"] == "DELETING_CLONE"
                assert not held.done()
            finally:
                release.set()
                held.result(timeout=2)
    finally:
        service.executor.shutdown(wait=True)


def test_old_cleanup_observation_cannot_overwrite_new_selection(tmp_path):
    service, run_id, _ = real_local_run(tmp_path)
    service.store.begin_cleanup(run_id, {"delete_clone": True, "delete_snapshot": False})
    observing, release, attempted, selected = (threading.Event() for _ in range(4))

    def observation(run):
        assert run["cleanup_selection"] == {"delete_clone": True, "delete_snapshot": False}
        observing.set()
        assert release.wait(5)
        return {"cleanup_state": "CLONE_DELETED"}

    service.runtime = SimpleNamespace(observe_cleanup=observation)

    def new_selection():
        attempted.set()
        with service.lock(run_id):
            service.store.begin_cleanup(run_id, {"delete_clone": False, "delete_snapshot": True})
            selected.set()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            status = pool.submit(
                service.call, "get_run", {"request_id": str(uuid4()), "run_id": run_id}
            )
            mutation = None
            try:
                assert observing.wait(2)
                mutation = pool.submit(new_selection)
                assert attempted.wait(2)
                assert not selected.wait(0.1)
            finally:
                release.set()
                assert status.result(timeout=2)["ok"]
                if mutation is not None:
                    mutation.result(timeout=2)
        final = service.store.get_run(run_id)
        assert final["cleanup_selection"] == {"delete_clone": False, "delete_snapshot": True}
        assert final["cleanup_state"] == "DELETING_SNAPSHOT"
    finally:
        service.executor.shutdown(wait=True)
