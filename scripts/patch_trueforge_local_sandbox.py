#!/usr/bin/env python3
"""Apply the reviewed TrueForge 0.2.1 Linux Code Mode isolation patch.

The patch is refused unless both installed JavaScript files have their exact
published-lock installation hashes. It narrows Linux sandbox read access from
the process-global Code Mode socket parent to the current transport's socket
and prevents an agent-supplied exec environment from choosing that socket.

Dry-run is the default. Pass ``--apply`` during the reviewed host deployment,
then restart TrueForge and run the documented two-session isolation canary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

MAIN_BASELINE_SHA256 = "c6902760304c303edec52e2894370be68ca6d679ca20f922a589c6fbc416f9c0"
CORE_BASELINE_SHA256 = "20cbee8c17afc717ca29ef4d1d851833128b05b50856b4164f09947dab41742f"
MAIN_PATCHED_SHA256 = "61deb0b09fc65610afa13b8d356d7225ae9b93c1322bdd90d5414045d85fcd40"
CORE_PATCHED_SHA256 = "dc08e4e0f1bb6ce08b66882911e08de74c5995be0ee0f0353da29d3e79b993f8"
DEFAULT_MAIN_JS = Path("integration/node_modules/@truefoundry/trueforge/dist/main.js")


class PatchError(Exception):
    """A stable patch refusal without file contents."""


@dataclass(frozen=True)
class Target:
    name: str
    path: Path
    baseline_sha256: str
    patched_sha256: str
    replacements: tuple[tuple[bytes, bytes], ...]


MAIN_REPLACEMENTS = (
    (
        b'import { realpathSync as realpathSync2 } from "fs";',
        b'import { lstatSync, realpathSync as realpathSync2 } from "fs";',
    ),
    (
        b'''function codeModeSocketParentAllow() {
  return codeModeSocketParentPath === void 0 ? [] : [codeModeSocketParentPath];
}''',
        b'''function codeModeSocketAllow(socketPath) {
  if (socketPath === void 0) {
    return [];
  }
  if (
    codeModeSocketParentPath === void 0 ||
    !isAbsolute2(socketPath) ||
    dirname2(socketPath) !== codeModeSocketParentPath ||
    realpathSync2(socketPath) !== socketPath ||
    !lstatSync(socketPath).isSocket()
  ) {
    throw new Error("TFY_MCP_SOCK must be the current canonical Code Mode Unix socket");
  }
  return [socketPath];
}''',
    ),
    (
        b'''      params.sandboxRootPath,
      ...codeModeSocketParentAllow(),
      ...linuxNetworkSocketAllow(params.platform),''',
        b'''      params.sandboxRootPath,
      ...codeModeSocketAllow(params.codeModeSocketPath),
      ...linuxNetworkSocketAllow(params.platform),''',
    ),
    (
        b'''    allowRead: [...platformAllowRead(platform), ...codeModeSocketParentAllow()]''',
        b'''    allowRead: [...platformAllowRead(platform)]''',
    ),
    (
        b'''      filesystem: filesystemPolicy({ sandboxRootPath, platform }),''',
        b'''      filesystem: filesystemPolicy({
        sandboxRootPath,
        platform,
        codeModeSocketPath: env?.TFY_MCP_SOCK
      }),''',
    ),
    (
        b'''    PYTHON_CANDIDATES = ["python3", "python"];''',
        b'''    PYTHON_CANDIDATES = ["python3.12", "python3.11", "python3.10", "python3", "python"];''',
    ),
    (
        b'''                "import sys; raise SystemExit(0 if sys.version_info[0] == 3 else 1)"''',
        b'''                "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"''',
    ),
    (
        b'''                summary: "No usable Python 3 interpreter in sandbox (python3 or python via command -v)",''',
        b'''                summary: "No usable Python >=3.10 interpreter in sandbox (python3.12/3.11/3.10/python3/python via command -v)",''',
    ),
    (
        b'''          if (session.protocolError !== void 0) {
            return { success: false, error: session.protocolError };
          }
          const result = session.stdoutText + (session.stderrText ? session.stderrText : "");''',
        b'''          if (session.protocolError !== void 0) {
            return { success: false, error: session.protocolError };
          }
          if (session.timedOut) {
            return { success: false, error: "Local sandbox command timed out" };
          }
          const result = session.stdoutText + (session.stderrText ? session.stderrText : "");''',
    ),
)

CORE_REPLACEMENTS = (
    (
        b'''function injectMCPClientEnv(params) {
  const codeModeEnv = params.codeModeEnv ?? {};''',
        b'''function injectMCPClientEnv(params) {
  const inputEnv = { ...params.env ?? {} };
  delete inputEnv.TFY_MCP_SOCK;
  const codeModeEnv = params.codeModeEnv ?? {};''',
    ),
    (
        b'''    ...params.env ?? {},
    ...layout !== void 0 && {''',
        b'''    ...inputEnv,
    ...layout !== void 0 && {''',
    ),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _core_path(main_js: Path) -> Path:
    try:
        scope = main_js.parent.parent.parent
    except IndexError as error:
        raise PatchError("MAIN_PATH_INVALID") from error
    return scope / "trueforge-core/dist/core/sandbox/Sandbox.js"


def _targets(main_js: Path) -> tuple[Target, Target]:
    return (
        Target(
            "trueforge_main",
            main_js,
            MAIN_BASELINE_SHA256,
            MAIN_PATCHED_SHA256,
            MAIN_REPLACEMENTS,
        ),
        Target(
            "trueforge_core_sandbox",
            _core_path(main_js),
            CORE_BASELINE_SHA256,
            CORE_PATCHED_SHA256,
            CORE_REPLACEMENTS,
        ),
    )


def _transform(target: Target, data: bytes) -> bytes:
    result = data
    for before, after in target.replacements:
        count = result.count(before)
        if count != 1:
            raise PatchError(f"{target.name.upper()}_PATCH_SHAPE_MISMATCH")
        result = result.replace(before, after, 1)
    return result


def _read_regular_file(path: Path, label: str) -> bytes:
    try:
        info = path.lstat()
    except OSError as error:
        raise PatchError(f"{label.upper()}_UNAVAILABLE") from error
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise PatchError(f"{label.upper()}_NOT_REGULAR")
    try:
        return path.read_bytes()
    except OSError as error:
        raise PatchError(f"{label.upper()}_UNAVAILABLE") from error


def _prepare(target: Target) -> tuple[bytes, str, str, str]:
    original = _read_regular_file(target.path, target.name)
    original_sha = _sha256(original)
    if original_sha == target.baseline_sha256:
        patched = _transform(target, original)
        patched_sha = _sha256(patched)
        if patched_sha != target.patched_sha256:
            raise PatchError(f"{target.name.upper()}_EXPECTED_HASH_MISMATCH")
        return patched, original_sha, patched_sha, "pending"
    if original_sha == target.patched_sha256:
        return original, target.baseline_sha256, original_sha, "already_patched"

    # A non-baseline/non-patched input cannot define its own accepted result.
    raise PatchError(f"{target.name.upper()}_HASH_MISMATCH")


def _write_atomic(path: Path, data: bytes) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    temporary = path.with_name(f".{path.name}.preflight-patch-{os.getpid()}")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def run(main_js: Path, *, apply: bool) -> dict[str, object]:
    targets = _targets(main_js)
    prepared = [(target, *_prepare(target)) for target in targets]
    if apply:
        for target, patched, _before, expected_after, _state in prepared:
            _write_atomic(target.path, patched)
            actual_after = _sha256(_read_regular_file(target.path, target.name))
            if actual_after != expected_after:
                raise PatchError(f"{target.name.upper()}_POSTWRITE_HASH_MISMATCH")
    return {
        "ok": True,
        "state": "PATCHED_RESTART_REQUIRED" if apply else "NOT_RUN",
        "applied": apply,
        "targets": [
            {
                "name": target.name,
                "baseline_sha256": before,
                "patched_sha256": after,
            }
            for target, _patched, before, after, _state in prepared
        ],
        "scope": "linux_code_mode_socket_isolation_and_python_compatibility",
        "approval_logic_changed": False,
        "network_policy_changed": False,
        "next_step": (
            "restart_trueforge_then_run_two_session_bridge_isolation_canary"
            if apply
            else "review_then_rerun_with_apply"
        ),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--main-js", type=Path, default=DEFAULT_MAIN_JS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
        result = run(args.main_js.resolve(), apply=args.apply)
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except PatchError as error:
        print(
            json.dumps(
                {"ok": False, "state": "REFUSED", "error_code": str(error)},
                separators=(",", ":"),
            )
        )
        return 5
    except Exception:
        print(
            json.dumps(
                {"ok": False, "state": "REFUSED", "error_code": "PATCH_INTERNAL_ERROR"},
                separators=(",", ":"),
            )
        )
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
