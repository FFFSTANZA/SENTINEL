from __future__ import annotations

from typing import Any

import pytest

from . import get_default_senytl


def pytest_configure(config: Any) -> None:
    config.addinivalue_line("markers", "senytl_agent: enable Senytl agent helpers")
    config.addinivalue_line("markers", "senytl_mock: enable Senytl mock engine")
    config.addinivalue_line("markers", "senytl_adversarial: adversarial test case")


def pytest_runtest_setup(item: Any) -> None:
    if item.get_closest_marker("senytl_agent") or item.get_closest_marker("senytl_mock"):
        if "senytl" not in item.fixturenames:
            item.fixturenames.append("senytl")


@pytest.fixture
def senytl() -> Any:
    s = get_default_senytl()
    s.reset()
    s.install()
    yield s
    s.reset()
    s.uninstall()


@pytest.fixture
def senytl_agent(senytl: Any):
    def _wrap(agent: Any) -> Any:
        return senytl.wrap(agent)

    return _wrap
