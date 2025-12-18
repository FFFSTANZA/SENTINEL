from __future__ import annotations

from typing import Any, Callable, TypeVar

from .assertions import expect
from .core import Senytl
from .models import SenytlResponse, ToolCall
from . import trajectory
from . import snapshot
from . import adversarial
from . import behavior
from . import multi_agent
from . import coverage
from . import generation
from . import ci
from . import semantic

__all__ = [
    "Senytl",
    "senytl",
    "expect",
    "SenytlResponse",
    "ToolCall",
    "trajectory",
    "snapshot",
    "adversarial",
    "behavior",
    "multi_agent",
    "coverage",
    "generation",
    "ci",
    "semantic",
    "agent",
    "mock",
    "wrap",
    "record_session",
    "replay_session",
    "reset",
    "install",
    "uninstall",
    "stop_session",
    "get_default_senytl",
]

from .core import _DEFAULT_SENYTL, get_default_senytl

senytl = _DEFAULT_SENYTL

def install() -> None:
    _DEFAULT_SENYTL.install()


def uninstall() -> None:
    _DEFAULT_SENYTL.uninstall()


def reset() -> None:
    _DEFAULT_SENYTL.reset()


def stop_session() -> None:
    _DEFAULT_SENYTL.stop_session()


def mock(model: str, *, provider: str | None = None):
    return _DEFAULT_SENYTL.mock(model, provider=provider)


def wrap(agent: Any) -> Any:
    return _DEFAULT_SENYTL.wrap(agent)


def record_session(name: str):
    return _DEFAULT_SENYTL.record_session(name)


def replay_session(name: str):
    return _DEFAULT_SENYTL.replay_session(name)


F = TypeVar("F", bound=Callable[..., Any])


def agent(fn: F) -> F:
    """pytest-friendly decorator for agent tests.

    When pytest is present, this becomes a `@pytest.mark.senytl_agent` marker.
    """

    try:
        import pytest  # type: ignore

        return pytest.mark.senytl_agent(fn)  # type: ignore[return-value]
    except Exception:
        return fn
