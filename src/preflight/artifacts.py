"""Bounded strict JSON and immutable exact-byte artifact storage."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import PreflightError


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def strict_json(data: bytes, ceiling: int = 2097152) -> Any:
    if len(data) > ceiling:
        raise PreflightError("INPUT_TOO_LARGE")

    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise PreflightError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    def invalid_constant(_):
        raise PreflightError("INVALID_JSON_NUMBER")

    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=invalid_constant
        )

        def depth(obj, level=0):
            if level > 32:
                raise PreflightError("JSON_TOO_DEEP")
            if isinstance(obj, dict):
                for item in obj.values():
                    depth(item, level + 1)
            elif isinstance(obj, list):
                for item in obj:
                    depth(item, level + 1)

        depth(value)
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise PreflightError("INVALID_JSON") from None


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def path(self, relative: str) -> Path:
        target = (self.root / relative).resolve()
        if not target.is_relative_to(self.root) or target == self.root:
            raise PreflightError("INVALID_ARTIFACT_PATH")
        return target

    def write_once(self, relative: str, data: bytes) -> str:
        target = self.path(relative)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = target.parent / f".preflight-{uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                # A hard link publishes a complete file exclusively; it never replaces a target.
                os.link(temporary, target)
            except FileExistsError:
                if target.read_bytes() != data:
                    raise PreflightError("ARTIFACT_IMMUTABLE") from None
            if os.name != "nt":
                directory = os.open(target.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)
        return sha256(data)

    def read(
        self, relative: str, expected_digest: str | None = None, ceiling: int = 2097152
    ) -> bytes:
        with self.path(relative).open("rb") as handle:
            data = handle.read(ceiling + 1)
        if len(data) > ceiling:
            raise PreflightError("ARTIFACT_TOO_LARGE")
        if expected_digest is not None and sha256(data) != expected_digest:
            raise PreflightError("ARTIFACT_INTEGRITY_ERROR")
        return data
