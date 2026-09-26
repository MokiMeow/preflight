"""Label each acceptance lane without silently skipping unavailable backends."""

import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        lane = item.path.parent.name
        if lane in {"unit", "postgres", "mcp", "cloud", "trueforge"}:
            item.add_marker(getattr(pytest.mark, lane))
