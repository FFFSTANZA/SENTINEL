from __future__ import annotations

import contextvars
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from .config import SentinelConfig, load_config
from .mock_engine import MatchSpec, MockEngine, MockRule, PassThroughRequest, coerce_mock_response
from .models import LLMCallRecord, MockResponse, ToolCall
from .patching import PatchManager
from .recording import SessionRecorder



def infer_provider(model: str) -> str:
    m = (model or "").lower()
    if "claude" in m or "anthropic" in m:
        return "anthropic"
    if "gemini" in m or "google" in m:
        return "google"
    return "openai"


@dataclass
class RunContext:
    llm_calls: list[LLMCallRecord] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)


class MockModelBuilder:
    def __init__(self, sentinel: "Sentinel", provider: str, model: str) -> None:
        self._sentinel = sentinel
        self._provider = provider
        self._model = model

    def when(
        self,
        *,
        contains: str | list[str] | None = None,
        regex: str | None = None,
        semantic_match: str | None = None,
        semantic_threshold: float = 0.3,
    ) -> "MockRuleBuilder":
        spec = MatchSpec(
            contains=contains,
            regex=regex,
            semantic_match=semantic_match,
            semantic_threshold=semantic_threshold,
        )
        return MockRuleBuilder(self._sentinel, provider=self._provider, model=self._model, match=spec)


class MockRuleBuilder:
    def __init__(self, sentinel: "Sentinel", *, provider: str, model: str, match: MatchSpec) -> None:
        self._sentinel = sentinel
        self._provider = provider
        self._model = model
        self._match = match

    def respond(
        self,
        text: str | None = None,
        *,
        tools: list[str] | None = None,
        reasoning: str | None = None,
        tool_calls: list[dict[str, Any] | ToolCall] | None = None,
    ) -> MockRule:
        response = coerce_mock_response(text, tools=tools, reasoning=reasoning, tool_calls=tool_calls)
        rule = MockRule(provider=self._provider, model=self._model, match=self._match, response=response)
        return self._sentinel.engine.add_rule(rule)

    def respond_sequence(self, responses: Sequence[str | MockResponse]) -> MockRule:
        sequence: list[MockResponse] = []
        for r in responses:
            if isinstance(r, MockResponse):
                sequence.append(r)
            else:
                sequence.append(coerce_mock_response(r))

        if not sequence:
            sequence = [coerce_mock_response("")]

        rule = MockRule(
            provider=self._provider,
            model=self._model,
            match=self._match,
            response=sequence[0],
            response_sequence=sequence,
        )
        return self._sentinel.engine.add_rule(rule)


class Sentinel:
    def __init__(self, config: SentinelConfig | None = None, *, root: Path | None = None) -> None:
        self.root = root or Path.cwd()
        self.config = config or load_config(self.root)
        self.engine = MockEngine(fallback=self.config.fallback)
        self.recorder = SessionRecorder(sessions_dir=self.root / ".sentinel" / "sessions")

        self._run_context: contextvars.ContextVar[RunContext | None] = contextvars.ContextVar(
            "sentinel_run_context", default=None
        )
        self._patch_manager = PatchManager(self._handle_call)
        self._active_session: RecordingContext | None = None

    def install(self) -> None:
        self._patch_manager.install()

    def uninstall(self) -> None:
        self.stop_session()
        self._patch_manager.uninstall()

    def reset(self) -> None:
        self.stop_session()
        self.engine.reset()

    def stop_session(self) -> None:
        ctx = self._active_session
        self._active_session = None
        if ctx is not None:
            ctx.stop()

    def mock(self, model: str, *, provider: str | None = None) -> MockModelBuilder:
        resolved_provider = provider or infer_provider(model)
        return MockModelBuilder(self, resolved_provider, model)

    def wrap(self, agent: Any) -> Any:
        from .adapters import SentinelAgent

        self.install()
        return SentinelAgent(agent, sentinel=self)

    def record_session(self, name: str) -> "RecordingContext":
        self.stop_session()
        ctx = RecordingContext(self, name=name, mode="record", start_immediately=True)
        self._active_session = ctx
        return ctx

    def replay_session(self, name: str) -> "RecordingContext":
        self.stop_session()
        ctx = RecordingContext(self, name=name, mode="replay", start_immediately=True)
        self._active_session = ctx
        return ctx

    def _handle_call(self, *, provider: str, model: str, request: dict[str, Any]) -> MockResponse:
        replay = self.recorder.maybe_replay(provider=provider, model=model, request=request)
        if replay is not None:
            self._trace(provider=provider, model=model, request=request, response=replay)
            return replay

        mocked = True
        try:
            response = self.engine.handle(provider=provider, model=model, request=request)
        except PassThroughRequest:
            mocked = False
            raise

        self.recorder.record(provider=provider, model=model, request=request, response=response, mocked=mocked)
        self._trace(provider=provider, model=model, request=request, response=response)
        return response

    def _trace(self, *, provider: str, model: str, request: dict[str, Any], response: MockResponse) -> None:
        ctx = self._run_context.get()
        if ctx is None:
            return
        record = LLMCallRecord(provider=provider, model=model, request=request, response=response)
        ctx.llm_calls.append(record)
        ctx.tool_calls.extend(response.tool_calls)


class RecordingContext:
    def __init__(
        self,
        sentinel: Sentinel,
        *,
        name: str,
        mode: str,
        start_immediately: bool = False,
    ) -> None:
        self._sentinel = sentinel
        self._name = name
        self._mode = mode
        self._prev_fallback = sentinel.engine.fallback
        self._started = False

        if start_immediately:
            self.__enter__()

    def __enter__(self) -> "RecordingContext":
        if self._started:
            return self

        if self._mode == "record":
            self._sentinel.engine.fallback = "pass_through"
            self._sentinel.recorder.start_recording(self._name)
        else:
            self._sentinel.engine.fallback = "error"
            self._sentinel.recorder.start_replay(self._name)

        self._sentinel.install()
        self._started = True
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if not self._started:
            return
        try:
            if self._mode == "record":
                self._sentinel.recorder.stop_recording()
            else:
                self._sentinel.recorder.stop_replay()
        finally:
            self._sentinel.engine.fallback = self._prev_fallback
            self._started = False

    def stop(self) -> None:
        self.__exit__(None, None, None)


@dataclass
class RunHandle:
    sentinel: Sentinel
    context: RunContext
    started_at: float
    token: contextvars.Token[RunContext | None]

    def finish(self) -> tuple[RunContext, float]:
        duration = time.perf_counter() - self.started_at
        self.sentinel._run_context.reset(self.token)
        return self.context, duration


def start_run(sentinel: Sentinel) -> RunHandle:
    ctx = RunContext()
    token = sentinel._run_context.set(ctx)
    return RunHandle(sentinel=sentinel, context=ctx, started_at=time.perf_counter(), token=token)


_DEFAULT_SENTINEL = Sentinel()


def get_default_sentinel() -> Sentinel:
    return _DEFAULT_SENTINEL
