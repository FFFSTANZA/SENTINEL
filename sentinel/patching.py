from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .mock_engine import PassThroughRequest
from .models import MockResponse, ToolCall
from .utils import AttrDict


@dataclass
class Patch:
    target: Any
    attr: str
    original: Any


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _parse_openai_response(resp: Any) -> MockResponse:
    choices = _safe_get(resp, "choices") or []
    first = choices[0] if choices else None
    message = _safe_get(first, "message") or {}
    text = _safe_get(message, "content") or ""

    tool_calls: list[ToolCall] = []
    for tc in _safe_get(message, "tool_calls") or []:
        fn = _safe_get(tc, "function") or {}
        name = _safe_get(fn, "name")
        args = _safe_get(fn, "arguments")
        if name:
            tool_calls.append(ToolCall(name=str(name), args=dict(args or {})))

    return MockResponse(text=str(text or ""), tool_calls=tool_calls)


def _parse_anthropic_response(resp: Any) -> MockResponse:
    blocks = _safe_get(resp, "content") or []
    parts: list[str] = []
    for b in blocks:
        t = _safe_get(b, "text")
        if isinstance(t, str):
            parts.append(t)
    return MockResponse(text="".join(parts))


def _parse_google_response(resp: Any) -> MockResponse:
    text = _safe_get(resp, "text") or ""
    return MockResponse(text=str(text or ""))


class PatchManager:
    def __init__(self, handler: Callable[..., Any]) -> None:
        self._handler = handler
        self._sentinel = getattr(handler, "__self__", None)
        self._patches: list[Patch] = []

    def installed(self) -> bool:
        return bool(self._patches)

    def install(self) -> None:
        if self.installed():
            return
        self._patch_openai()
        self._patch_anthropic()
        self._patch_google()

    def uninstall(self) -> None:
        while self._patches:
            patch = self._patches.pop()
            setattr(patch.target, patch.attr, patch.original)

    def _apply(self, target: Any, attr: str, replacement: Any) -> None:
        original = getattr(target, attr)
        setattr(target, attr, replacement)
        self._patches.append(Patch(target=target, attr=attr, original=original))

    def _maybe_record_passthrough(
        self,
        *,
        provider: str,
        model: str,
        request: dict[str, Any],
        raw_response: Any,
        parser: Callable[[Any], MockResponse],
    ) -> None:
        if self._sentinel is None:
            return
        recorder = getattr(self._sentinel, "recorder", None)
        if recorder is None or getattr(recorder, "mode", None) != "record":
            return

        response = parser(raw_response)
        recorder.record(provider=provider, model=model, request=request, response=response, mocked=False)

        trace = getattr(self._sentinel, "_trace", None)
        if callable(trace):
            trace(provider=provider, model=model, request=request, response=response)

    def _patch_openai(self) -> None:
        try:
            import openai  # type: ignore
        except Exception:
            return

        def _make_chat_completion_response(*, text: str, tool_calls: list[dict[str, Any]]) -> Any:
            message: dict[str, Any] = {"role": "assistant", "content": text}
            if tool_calls:
                message["tool_calls"] = tool_calls
            return AttrDict(
                {
                    "id": "sentinel-mock",
                    "object": "chat.completion",
                    "choices": [AttrDict({"index": 0, "message": AttrDict(message), "finish_reason": "stop"})],
                }
            )

        def _wrap_tool_calls(call_list: Any) -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []
            for idx, tc in enumerate(call_list or []):
                args = tc.args if hasattr(tc, "args") else {}
                result.append(
                    {
                        "id": f"sentinel-toolcall-{idx}",
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": AttrDict(args),
                        },
                    }
                )
            return result

        if hasattr(openai, "ChatCompletion") and hasattr(openai.ChatCompletion, "create"):
            original_create = openai.ChatCompletion.create

            def chatcompletion_create(*args: Any, **kwargs: Any) -> Any:
                model = kwargs.get("model") or ""
                request = {"messages": kwargs.get("messages"), **kwargs}
                try:
                    mock = self._handler(provider="openai", model=model, request=request)
                except PassThroughRequest:
                    raw = original_create(*args, **kwargs)
                    self._maybe_record_passthrough(
                        provider="openai",
                        model=str(model),
                        request=request,
                        raw_response=raw,
                        parser=_parse_openai_response,
                    )
                    return raw

                return _make_chat_completion_response(
                    text=mock.text,
                    tool_calls=_wrap_tool_calls(mock.tool_calls),
                )

            self._apply(openai.ChatCompletion, "create", chatcompletion_create)

        # Best-effort patch for the v1 client
        try:
            from openai.resources.chat.completions import Completions  # type: ignore
        except Exception:
            Completions = None

        if Completions is not None and hasattr(Completions, "create"):
            original_create = Completions.create

            def completions_create(self_obj: Any, *args: Any, **kwargs: Any) -> Any:
                model = kwargs.get("model") or ""
                request = {"messages": kwargs.get("messages"), **kwargs}
                try:
                    mock = self._handler(provider="openai", model=model, request=request)
                except PassThroughRequest:
                    raw = original_create(self_obj, *args, **kwargs)
                    self._maybe_record_passthrough(
                        provider="openai",
                        model=str(model),
                        request=request,
                        raw_response=raw,
                        parser=_parse_openai_response,
                    )
                    return raw

                return _make_chat_completion_response(
                    text=mock.text,
                    tool_calls=_wrap_tool_calls(mock.tool_calls),
                )

            self._apply(Completions, "create", completions_create)

    def _patch_anthropic(self) -> None:
        try:
            import anthropic  # type: ignore
        except Exception:
            return

        def _make_messages_response(*, text: str) -> Any:
            return AttrDict(
                {
                    "id": "sentinel-mock",
                    "type": "message",
                    "role": "assistant",
                    "content": [AttrDict({"type": "text", "text": text})],
                    "stop_reason": "end_turn",
                }
            )

        try:
            from anthropic.resources.messages import Messages  # type: ignore
        except Exception:
            Messages = None

        if Messages is not None and hasattr(Messages, "create"):
            original_create = Messages.create

            def messages_create(self_obj: Any, *args: Any, **kwargs: Any) -> Any:
                model = kwargs.get("model") or ""
                request = {"messages": kwargs.get("messages"), **kwargs}
                try:
                    mock = self._handler(provider="anthropic", model=model, request=request)
                except PassThroughRequest:
                    raw = original_create(self_obj, *args, **kwargs)
                    self._maybe_record_passthrough(
                        provider="anthropic",
                        model=str(model),
                        request=request,
                        raw_response=raw,
                        parser=_parse_anthropic_response,
                    )
                    return raw

                return _make_messages_response(text=mock.text)

            self._apply(Messages, "create", messages_create)

        if hasattr(anthropic, "messages") and hasattr(anthropic.messages, "create"):
            original_create = anthropic.messages.create

            def legacy_messages_create(*args: Any, **kwargs: Any) -> Any:
                model = kwargs.get("model") or ""
                request = {"messages": kwargs.get("messages"), **kwargs}
                try:
                    mock = self._handler(provider="anthropic", model=model, request=request)
                except PassThroughRequest:
                    raw = original_create(*args, **kwargs)
                    self._maybe_record_passthrough(
                        provider="anthropic",
                        model=str(model),
                        request=request,
                        raw_response=raw,
                        parser=_parse_anthropic_response,
                    )
                    return raw

                return _make_messages_response(text=mock.text)

            self._apply(anthropic.messages, "create", legacy_messages_create)

    def _patch_google(self) -> None:
        try:
            import google.generativeai as genai  # type: ignore
        except Exception:
            return

        model_cls = getattr(genai, "GenerativeModel", None)
        if model_cls is None or not hasattr(model_cls, "generate_content"):
            return

        original_generate_content = model_cls.generate_content

        def generate_content(self_obj: Any, *args: Any, **kwargs: Any) -> Any:
            model = getattr(self_obj, "model_name", None) or getattr(self_obj, "model", None) or ""
            prompt = args[0] if args else kwargs.get("contents")
            request = {"prompt": prompt, **kwargs}
            try:
                mock = self._handler(provider="google", model=model, request=request)
            except PassThroughRequest:
                raw = original_generate_content(self_obj, *args, **kwargs)
                self._maybe_record_passthrough(
                    provider="google",
                    model=str(model),
                    request=request,
                    raw_response=raw,
                    parser=_parse_google_response,
                )
                return raw

            return AttrDict({"text": mock.text})

        self._apply(model_cls, "generate_content", generate_content)
