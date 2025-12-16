from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from .core import Sentinel, start_run
from .models import SentinelResponse


def _extract_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result
    if isinstance(result, bytes):
        return result.decode("utf-8", errors="replace")
    if isinstance(result, dict):
        for key in ("text", "content", "output", "message"):
            val = result.get(key)
            if isinstance(val, str):
                return val
        return str(result)
    if hasattr(result, "text") and isinstance(getattr(result, "text"), str):
        return getattr(result, "text")
    if hasattr(result, "content") and isinstance(getattr(result, "content"), str):
        return getattr(result, "content")
    return str(result)


def _call_agent(agent: Any, user_input: str, **kwargs: Any) -> Any:
    if callable(agent):
        try:
            return agent(user_input, **kwargs)
        except TypeError:
            return agent(user_input)

    for method_name in ("invoke", "run", "__call__"):
        if not hasattr(agent, method_name):
            continue
        method = getattr(agent, method_name)
        if not callable(method):
            continue

        if method_name == "invoke":
            try:
                return method({"input": user_input, **kwargs})
            except Exception:
                try:
                    return method(user_input, **kwargs)
                except TypeError:
                    return method(user_input)

        try:
            return method(user_input, **kwargs)
        except TypeError:
            return method(user_input)

    raise TypeError(f"Unsupported agent type: {type(agent)!r}. Expected callable or object with invoke/run.")


@dataclass
class SentinelAgent:
    agent: Any
    sentinel: Sentinel
    conversation: list[dict[str, Any]] = field(default_factory=list)

    def run(self, user_input: str, **kwargs: Any) -> SentinelResponse:
        handle = start_run(self.sentinel)
        try:
            raw = _call_agent(self.agent, user_input, **kwargs)
        finally:
            ctx, duration = handle.finish()

        text = _extract_text(raw)
        self.conversation.append({"role": "user", "content": user_input})
        self.conversation.append({"role": "assistant", "content": text})

        return SentinelResponse(
            text=text,
            raw=raw,
            duration_seconds=duration,
            llm_calls=ctx.llm_calls,
            tool_calls=ctx.tool_calls,
        )
