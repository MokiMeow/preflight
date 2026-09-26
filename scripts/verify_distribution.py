"""Inspect built artifacts without extracting files or making network requests."""

import hashlib
import json
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
PRD_SHA256 = "5f607b53bd7c439c94e3f97d3826e24e441cb5d007863eca023313347533b6bf"


def main():
    archives = list((ROOT / "dist").glob("preflight_rehearsal-*.tar.gz"))
    wheels = list((ROOT / "dist").glob("preflight_rehearsal-*.whl"))
    if len(archives) != 1 or len(wheels) != 1:
        raise SystemExit("BUILD_EXACTLY_ONE_SOURCE_ARCHIVE_AND_WHEEL")
    with tarfile.open(archives[0]) as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        for member in members:
            original = PurePosixPath(member.name)
            relative = PurePosixPath(*original.parts[1:])
            parts = relative.parts
            if (
                member.issym()
                or member.islnk()
                or original.is_absolute()
                or "\\" in member.name
                or ":" in member.name
                or ".." in parts
                or any(
                    p in {".worktrees", "var", "node_modules", ".venv", ".venv-clean"}
                    for p in parts
                )
                or relative.name.endswith((".local.json", ".pem", ".key", ".log"))
                or ".sqlite" in relative.name
                or (relative.name.startswith(".env") and str(relative) != ".env.example")
            ):
                raise SystemExit("PRIVATE_OR_UNSAFE_SOURCE_ARCHIVE_MEMBER")
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
        modules = [n for n in wheel.namelist() if n.startswith("preflight/") and n.endswith(".py")]
        if len(modules) != 17:
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
