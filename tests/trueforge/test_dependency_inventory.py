import json
import platform
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
INVENTORY = ROOT / "integration/dependency-inventory.json"
TRUEFORGE = ROOT / "integration/node_modules/@truefoundry/trueforge/package.json"


def components():
    return json.loads(INVENTORY.read_text(encoding="utf-8"))["components"]


def test_inventory_records_project_pglast_and_trueforge_license_status():
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert inventory["project_license"] == "UNDECIDED"
    assert inventory["component_count"] == len(inventory["components"])
    assert not any("Mohith" in json.dumps(component) for component in inventory["components"])

    indexed = {(item["ecosystem"], item["name"]): item for item in inventory["components"]}
    assert indexed[("pypi", "pglast")]["version"] == "8.4"
    assert indexed[("pypi", "pglast")]["license_declared"] == "GPL-3.0-or-later"
    assert indexed[("pypi", "preflight-rehearsal")]["license_declared"] == "UNDECIDED"
    assert indexed[("npm", "@truefoundry/trueforge")]["version"] == "0.2.1"
    assert indexed[("npm", "@truefoundry/trueforge")]["license_declared"] == "MIT"


@pytest.mark.skipif(
    platform.system() != "Windows" or not TRUEFORGE.exists(),
    reason="committed inventory captures the verified Windows install",
)
def test_installed_dependency_inventory_is_current():
    result = subprocess.run(
        [
            str(ROOT / ".venv/Scripts/python.exe"),
            str(ROOT / "scripts/generate_dependency_inventory.py"),
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout or result.stderr
    assert result.stdout.strip() == "DEPENDENCY_INVENTORY_CURRENT"
