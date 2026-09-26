"""Inspect built artifacts without extracting files or making network requests."""

import hashlib
import json
import stat
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PRD_SHA256 = "5f607b53bd7c439c94e3f97d3826e24e441cb5d007863eca023313347533b6bf"


def member_path(name, roots, allow_env_example=False):
    original = PurePosixPath(name)
    if (
        not original.parts
        or original.is_absolute()
        or ".." in original.parts
        or "\\" in name
        or ":" in name
        or original.parts[0] not in roots
    ):
        raise SystemExit("PRIVATE_OR_UNSAFE_ARCHIVE_MEMBER")
    relative = PurePosixPath(*original.parts[1:])
    if (
        any(
            p in {".worktrees", "var", "node_modules", ".venv", ".venv-clean", ".aws"}
            for p in relative.parts
        )
        or relative.name.endswith(
            (".local.json", ".pem", ".key", ".p12", ".log", ".har", ".auth-state.json")
        )
        or ".sqlite" in relative.name
        or (
            relative.name.startswith(".env")
            and not (allow_env_example and str(relative) == ".env.example")
        )
    ):
        raise SystemExit("PRIVATE_OR_UNSAFE_ARCHIVE_MEMBER")
    return str(original)


def inspect_source_members(archive, root):
    seen = set()
    for member in archive.getmembers():
        normalized = member_path(member.name, {root}, allow_env_example=True)
        if normalized in seen or not (member.isfile() or member.isdir()):
            raise SystemExit("DUPLICATE_OR_SPECIAL_ARCHIVE_MEMBER")
        seen.add(normalized)


def inspect_wheel_members(wheel, metadata_root):
    seen = set()
    for member in wheel.infolist():
        normalized = member_path(member.filename, {"preflight", metadata_root})
        mode = member.external_attr >> 16
        if normalized in seen or stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}:
            raise SystemExit("DUPLICATE_OR_SPECIAL_ARCHIVE_MEMBER")
        seen.add(normalized)


def main():
    archives = list((ROOT / "dist").glob("preflight_rehearsal-*.tar.gz"))
    wheels = list((ROOT / "dist").glob("preflight_rehearsal-*.whl"))
    if len(archives) != 1 or len(wheels) != 1:
        raise SystemExit("BUILD_EXACTLY_ONE_SOURCE_ARCHIVE_AND_WHEEL")
    with tarfile.open(archives[0]) as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        inspect_source_members(archive, archives[0].name.removesuffix(".tar.gz"))
        prd = next(n for n in names if n.endswith("/reference/Preflight-PRD.md"))
        if hashlib.sha256(archive.extractfile(prd).read()).hexdigest() != PRD_SHA256:
            raise SystemExit("ORIGINAL_PRD_HASH_MISMATCH")
        for suffix in [
            "fixtures/seed_demo.py",
            "uv.lock",
            "integration/package-lock.json",
            "evidence/local/verification.json",
        ]:
            if not any(n.endswith("/" + suffix) for n in names):
                raise SystemExit("REQUIRED_SOURCE_ARCHIVE_MEMBER_MISSING")
    with zipfile.ZipFile(wheels[0]) as wheel:
        metadata_root = "-".join(wheels[0].name.split("-")[:2]) + ".dist-info"
        inspect_wheel_members(wheel, metadata_root)
        modules = [n for n in wheel.namelist() if n.startswith("preflight/") and n.endswith(".py")]
        if len(modules) != 18:
            raise SystemExit("WHEEL_MODULES_INCOMPLETE")
    print(
        json.dumps(
            {
                "source_archive_members": len(names),
                "private_artifacts": 0,
                "original_prd_hash_match": True,
                "wheel_python_modules": len(modules),
            }
        )
    )


if __name__ == "__main__":
    main()
