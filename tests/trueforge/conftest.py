from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
REQUIRED_PACKAGES = (
    ROOT / "integration/node_modules/@truefoundry/trueforge/package.json",
    ROOT / "integration/node_modules/@modelcontextprotocol/sdk/package.json",
    ROOT / "integration/node_modules/openai/package.json",
)


@pytest.fixture(scope="session", autouse=True)
def require_installed_trueforge_dependencies() -> None:
    missing = [path.relative_to(ROOT).as_posix() for path in REQUIRED_PACKAGES if not path.is_file()]
    if missing:
        pytest.fail(
            "required TrueForge integration dependencies are not installed; run "
            "`cd integration && npm ci --ignore-scripts --no-audit --no-fund`. Missing: "
            + ", ".join(missing)
        )
