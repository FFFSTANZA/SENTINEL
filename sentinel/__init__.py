from __future__ import annotations

from typing import Any, Callable, TypeVar

from .assertions import expect
from .core import Sentinel
from .models import SentinelResponse, ToolCall

__all__ = [
    "Sentinel",
    "expect",
    "SentinelResponse",
    "ToolCall",
    "agent",
    "mock",
    "wrap",
    "record_session",
    "replay_session",
    "reset",
    "install",
    "uninstall",
    "get_default_sentinel",
]

_DEFAULT_SENTINEL = Sentinel()


def get_default_sentinel() -> Sentinel:
    return _DEFAULT_SENTINEL


def install() -> None:
    _DEFAULT_SENTINEL.install()


def uninstall() -> None:
    _DEFAULT_SENTINEL.uninstall()


def reset() -> None:
    _DEFAULT_SENTINEL.reset()


def mock(model: str, *, provider: str | None = None):
    return _DEFAULT_SENTINEL.mock(model, provider=provider)


def wrap(agent: Any) -> Any:
    return _DEFAULT_SENTINEL.wrap(agent)


def record_session(name: str):
    return _DEFAULT_SENTINEL.record_session(name)


def replay_session(name: str):
    return _DEFAULT_SENTINEL.replay_session(name)


F = TypeVar("F", bound=Callable[..., Any])


def agent(fn: F) -> F:
    """pytest-friendly decorator for agent tests.

    When pytest is present, this becomes a `@pytest.mark.sentinel_agent` marker.
    """

    try:
        import pytest  # type: ignore

        return pytest.mark.sentinel_agent(fn)  # type: ignore[return-value]
    except Exception:
        return fn
