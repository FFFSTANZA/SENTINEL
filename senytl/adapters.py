from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .core import start_run
from .models import SenytlResponse

try:
    from .coverage import get_coverage_tracker
    _HAS_COVERAGE = True
except ImportError:
    _HAS_COVERAGE = False


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
class SenytlAgent:
    agent: Any
    senytl: Any
    conversation: list[dict[str, Any]] = field(default_factory=list)

    def run(self, user_input: str, **kwargs: Any) -> SenytlResponse:
        handle = start_run(self.senytl)
        try:
            raw = _call_agent(self.agent, user_input, **kwargs)
        finally:
            ctx, duration = handle.finish()

        text = _extract_text(raw)
        self.conversation.append({"role": "user", "content": user_input})
        self.conversation.append({"role": "assistant", "content": text})

        response = SenytlResponse(
            text=text,
            raw=raw,
            duration_seconds=duration,
            llm_calls=ctx.llm_calls,
            tool_calls=ctx.tool_calls,
        )
        
        if _HAS_COVERAGE:
            tracker = get_coverage_tracker()
            tracker.record_input(user_input)
            for tool_call in response.tool_calls:
                tracker.record_tool_call(tool_call)
        
        return response

    def __call__(self, user_input: str, **kwargs: Any) -> SenytlResponse:
        """Make the agent callable by delegating to run method."""
        return self.run(user_input, **kwargs)
