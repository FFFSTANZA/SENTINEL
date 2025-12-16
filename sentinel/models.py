from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


FallbackMode = Literal["error", "default", "pass_through"]


class SentinelError(Exception):
    pass


class NoMockMatchError(SentinelError):
    def __init__(self, *, provider: str, model: str, prompt: str) -> None:
        super().__init__(
            f"No mock matched provider={provider!r} model={model!r}. Prompt snippet: {prompt[:200]!r}"
        )
        self.provider = provider
        self.model = model
        self.prompt = prompt


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class MockResponse:
    text: str = ""
    reasoning: str | None = None
    tools: list[str] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class LLMCallRecord:
    provider: str
    model: str
    request: dict[str, Any]
    response: MockResponse


@dataclass
class SentinelResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None
    duration_seconds: float | None = None
    llm_calls: list[LLMCallRecord] = field(default_factory=list)

    def called_tool(self, name: str) -> bool:
        return any(tc.name == name for tc in self.tool_calls)
