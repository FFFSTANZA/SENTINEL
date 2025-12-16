from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .models import FallbackMode, MockResponse, NoMockMatchError, ToolCall
from .utils import flatten_messages, jaccard_similarity


@dataclass
class MatchSpec:
    contains: str | list[str] | None = None
    regex: str | None = None
    semantic_match: str | None = None
    semantic_threshold: float = 0.3

    def matches(self, prompt: str) -> bool:
        text = prompt or ""
        if self.contains is not None:
            haystack = text.lower()
            needles = [self.contains] if isinstance(self.contains, str) else list(self.contains)
            if not any(n.lower() in haystack for n in needles):
                return False
        if self.regex is not None and re.search(self.regex, text, flags=re.IGNORECASE) is None:
            return False
        if self.semantic_match is not None:
            score = jaccard_similarity(text, self.semantic_match)
            if score < self.semantic_threshold:
                return False
        return True


@dataclass
class MockRule:
    provider: str
    model: str
    match: MatchSpec
    response: MockResponse
    state: dict[str, Any] = field(default_factory=dict)

    def record_turn(self, *, prompt: str, response: MockResponse) -> None:
        history = self.state.setdefault("history", [])
        history.append({"prompt": prompt, "response": response})


class PassThroughRequest(Exception):
    def __init__(self, *, provider: str, model: str, request: dict[str, Any]) -> None:
        super().__init__("pass-through")
        self.provider = provider
        self.model = model
        self.request = request


class MockEngine:
    def __init__(self, *, fallback: FallbackMode = "error") -> None:
        self.fallback: FallbackMode = fallback
        self._rules: list[MockRule] = []

    def reset(self) -> None:
        self._rules.clear()

    def add_rule(self, rule: MockRule) -> MockRule:
        self._rules.append(rule)
        return rule

    def handle(self, *, provider: str, model: str, request: dict[str, Any]) -> MockResponse:
        prompt = self._extract_prompt(request)
        for rule in reversed(self._rules):
            if rule.provider != provider:
                continue
            if rule.model != model:
                continue
            if rule.match.matches(prompt):
                rule.record_turn(prompt=prompt, response=rule.response)
                return rule.response

        if self.fallback == "pass_through":
            raise PassThroughRequest(provider=provider, model=model, request=request)
        if self.fallback == "default":
            return MockResponse(text="")
        raise NoMockMatchError(provider=provider, model=model, prompt=prompt)

    @staticmethod
    def _extract_prompt(request: dict[str, Any]) -> str:
        if "prompt" in request and isinstance(request["prompt"], str):
            return request["prompt"]
        if "messages" in request:
            return flatten_messages(request.get("messages"))
        if "input" in request and isinstance(request["input"], str):
            return request["input"]
        return str(request)


def coerce_mock_response(
    text: str | None = None,
    *,
    tools: list[str] | None = None,
    reasoning: str | None = None,
    tool_calls: list[dict[str, Any] | ToolCall] | None = None,
) -> MockResponse:
    resolved_calls: list[ToolCall] = []
    if tools:
        resolved_calls.extend(ToolCall(name=t) for t in tools)

    if tool_calls:
        for tc in tool_calls:
            if isinstance(tc, ToolCall):
                resolved_calls.append(tc)
            elif isinstance(tc, dict):
                resolved_calls.append(ToolCall(name=str(tc.get("name")), args=dict(tc.get("args") or {})))
            else:
                resolved_calls.append(ToolCall(name=str(tc)))

    return MockResponse(
        text=text or "",
        tools=list(tools or []),
        reasoning=reasoning,
        tool_calls=resolved_calls,
    )
