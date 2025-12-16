from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import MockResponse, SentinelError, ToolCall
from .utils import stable_hash, stable_json_dumps


class RecordingNotFoundError(SentinelError):
    pass


def _default_sessions_dir(root: Path | None = None) -> Path:
    base = root or Path.cwd()
    return base / ".sentinel" / "sessions"


def _normalize_request(provider: str, model: str, request: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "provider": provider,
        "model": model,
        "request": request,
    }
    return json.loads(stable_json_dumps(normalized))


def _normalize_response(response: MockResponse) -> dict[str, Any]:
    return {
        "text": response.text,
        "reasoning": response.reasoning,
        "tools": list(response.tools),
        "tool_calls": [asdict(tc) for tc in response.tool_calls],
    }


def _response_from_payload(payload: dict[str, Any]) -> MockResponse:
    return MockResponse(
        text=str(payload.get("text") or ""),
        reasoning=payload.get("reasoning"),
        tools=list(payload.get("tools") or []),
        tool_calls=[ToolCall(**tc) for tc in (payload.get("tool_calls") or [])],
    )


class SessionRecorder:
    def __init__(self, *, sessions_dir: Path | None = None) -> None:
        self.sessions_dir = sessions_dir or _default_sessions_dir()
        self._mode: str | None = None
        self._name: str | None = None
        self._calls: list[dict[str, Any]] = []
        self._replay_index: dict[str, MockResponse] = {}

    @property
    def mode(self) -> str | None:
        return self._mode

    @property
    def name(self) -> str | None:
        return self._name

    def start_recording(self, name: str) -> None:
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._mode = "record"
        self._name = name
        self._calls = []
        self._replay_index = {}

    def stop_recording(self) -> Path | None:
        if self._mode != "record" or not self._name:
            return None
        path = self.sessions_dir / f"{self._name}.json"
        path.write_text(json.dumps({"calls": self._calls}, indent=2, ensure_ascii=False) + "\n")
        self._mode = None
        self._name = None
        self._calls = []
        self._replay_index = {}
        return path

    def start_replay(self, name: str) -> None:
        path = self.sessions_dir / f"{name}.json"
        if not path.exists():
            raise RecordingNotFoundError(f"Recording session not found: {path}")
        payload = json.loads(path.read_text())
        calls = list(payload.get("calls") or [])
        index: dict[str, MockResponse] = {}
        for call in calls:
            key = call.get("key")
            resp = call.get("response")
            if key and isinstance(resp, dict):
                index[str(key)] = _response_from_payload(resp)
        self._mode = "replay"
        self._name = name
        self._calls = calls
        self._replay_index = index

    def stop_replay(self) -> None:
        if self._mode != "replay":
            return
        self._mode = None
        self._name = None
        self._calls = []
        self._replay_index = {}

    def _key(self, provider: str, model: str, request: dict[str, Any]) -> str:
        normalized = _normalize_request(provider, model, request)
        return stable_hash(normalized)

    def maybe_replay(self, *, provider: str, model: str, request: dict[str, Any]) -> MockResponse | None:
        if self._mode != "replay":
            return None
        key = self._key(provider, model, request)
        return self._replay_index.get(key)

    def record(
        self,
        *,
        provider: str,
        model: str,
        request: dict[str, Any],
        response: MockResponse,
        mocked: bool,
    ) -> None:
        if self._mode != "record":
            return
        key = self._key(provider, model, request)
        self._calls.append(
            {
                "key": key,
                "provider": provider,
                "model": model,
                "request": _normalize_request(provider, model, request)["request"],
                "response": _normalize_response(response),
                "mocked": bool(mocked),
            }
        )
