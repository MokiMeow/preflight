import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]
LOCK = ROOT / "integration/package-lock.json"
INTEGRITY = (
    "sha512-yrCLD0QOKB/iHcHA6/WHVHEpVZfrSasYjIkZLZ4hiIbi4TXEZFFwVCueYVxzVWNq2OcusG4+"
    "BdjZg1mA/1I0iA=="
)


def test_trueforge_lock_is_exact_and_integrity_pinned():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    package = lock["packages"]["node_modules/@truefoundry/trueforge"]
    assert package["version"] == "0.2.1"
    assert package["integrity"] == INTEGRITY
    assert lock["packages"][""]["dependencies"] == {"@truefoundry/trueforge": "0.2.1"}


def test_local_package_probe_reports_resolved_versions():
    result = subprocess.run(
        ["node", str(ROOT / "scripts/probe_trueforge_package.mjs")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    observed = json.loads(result.stdout)
    assert observed["ok"] is True
    assert observed["trueforge_version"] == "0.2.1"
    assert observed["bundled_js_mcp_version"] == "1.30.1"
    assert observed["package_integrity"] == INTEGRITY
