"""Generate a deterministic inventory from the exact installed Python and npm packages."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def python_direct_names(root: Path) -> set[str]:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    requirements = list(project["project"]["dependencies"])
    for values in project.get("dependency-groups", {}).values():
        requirements.extend(values)
    return {canonicalize_name(Requirement(value).name) for value in requirements}


def python_components(root: Path) -> list[dict[str, object]]:
    direct = python_direct_names(root)
    components = []
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get("Name")
        if not name:
            continue
        canonical = canonicalize_name(name)
        expression = distribution.metadata.get("License-Expression")
        legacy = distribution.metadata.get("License")
        classifiers = sorted(
            item
            for item in distribution.metadata.get_all("Classifier", [])
            if item.startswith("License ::")
        )
        if canonical == "preflight-rehearsal":
            declared = "UNDECIDED"
            source = "PROJECT_POLICY"
        elif expression:
            declared = expression
            source = "License-Expression"
        elif legacy:
            declared = " ".join(legacy.split())
            source = "License"
        elif classifiers:
            declared = None
            source = "Classifier"
        else:
            declared = None
            source = "NOT_DECLARED_IN_INSTALLED_METADATA"
        components.append(
            {
                "ecosystem": "pypi",
                "name": name,
                "normalized_name": canonical,
                "version": distribution.version,
                "direct": canonical in direct or canonical == "preflight-rehearsal",
                "license_declared": declared,
                "license_source": source,
                "license_classifiers": classifiers,
                "purl": f"pkg:pypi/{canonical}@{distribution.version}",
            }
        )
    return components


def npm_components(root: Path) -> list[dict[str, object]]:
    npm_root = root / "integration"
    lock = json.loads((npm_root / "package-lock.json").read_text(encoding="utf-8"))
    direct = set(lock["packages"][""]["dependencies"])
    components = []
    for install_path, locked in lock["packages"].items():
        if not install_path:
            continue
        package_path = npm_root / install_path / "package.json"
        if not package_path.is_file():
            continue
        package = json.loads(package_path.read_text(encoding="utf-8"))
        name = package.get("name")
        version = package.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            continue
        components.append(
            {
                "ecosystem": "npm",
                "name": name,
                "version": version,
                "direct": name in direct and install_path == f"node_modules/{name}",
                "license_declared": package.get("license"),
                "license_source": "package.json" if "license" in package else "NOT_DECLARED",
                "integrity": locked.get("integrity"),
                "install_path": install_path.replace("\\", "/"),
                "purl": f"pkg:npm/{name.replace('@', '%40')}@{version}",
            }
        )
    return components


def inventory(root: Path) -> dict[str, object]:
    node_version = subprocess.run(
        ["node", "--version"], capture_output=True, check=True, text=True
    ).stdout.strip()
    components = python_components(root) + npm_components(root)
    components.sort(
        key=lambda item: (
            str(item["ecosystem"]),
            str(item["name"]).casefold(),
            str(item["version"]),
            str(item.get("install_path", "")),
        )
    )
    return {
        "schema_version": "preflight-installed-dependency-inventory-1",
        "scope": "Exact packages installed by uv sync --locked and npm ci in the probe checkout",
        "environment": {
            "os": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "node": node_version,
        },
        "locks": {
            "uv.lock_sha256": file_sha256(root / "uv.lock"),
            "integration/package-lock.json_sha256": file_sha256(
                root / "integration/package-lock.json"
            ),
        },
        "project_license": "UNDECIDED",
        "component_count": len(components),
        "components": components,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("integration/dependency-inventory.json"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    encoded = json.dumps(inventory(root), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    output = (root / args.output).resolve()
    if not output.is_relative_to(root) or output == root:
        parser.error("output must stay inside the checkout")
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != encoded:
            print("DEPENDENCY_INVENTORY_STALE")
            return 2
        print("DEPENDENCY_INVENTORY_CURRENT")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded, encoding="utf-8", newline="\n")
    print("DEPENDENCY_INVENTORY_WRITTEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
