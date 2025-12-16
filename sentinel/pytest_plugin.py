from __future__ import annotations

from typing import Any

import pytest

from . import get_default_sentinel


def pytest_configure(config: Any) -> None:
    config.addinivalue_line("markers", "sentinel_agent: enable Sentinel agent helpers")
    config.addinivalue_line("markers", "sentinel_mock: enable Sentinel mock engine")
    config.addinivalue_line("markers", "sentinel_adversarial: adversarial test case")


def pytest_runtest_setup(item: Any) -> None:
    if item.get_closest_marker("sentinel_agent") or item.get_closest_marker("sentinel_mock"):
        if "sentinel" not in item.fixturenames:
            item.fixturenames.append("sentinel")


@pytest.fixture
def sentinel() -> Any:
    s = get_default_sentinel()
    s.reset()
    s.install()
    yield s
    s.reset()
    s.uninstall()


@pytest.fixture
def sentinel_agent(sentinel: Any):
    def _wrap(agent: Any) -> Any:
        return sentinel.wrap(agent)

    return _wrap
