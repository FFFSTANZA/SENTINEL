from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from sentinel import Sentinel, expect
from sentinel.utils import AttrDict


def _install_fake_openai(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    openai = types.ModuleType("openai")
    openai._real_text = "REAL"  # type: ignore[attr-defined]

    class ChatCompletion:  # noqa: D401
        @staticmethod
        def create(*args, **kwargs):
            text = getattr(openai, "_real_text", "REAL")
            message: dict[str, object] = {"role": "assistant", "content": text}
            return AttrDict(
                {
                    "id": "real",
                    "object": "chat.completion",
                    "choices": [
                        AttrDict(
                            {
                                "index": 0,
                                "message": AttrDict(message),
                                "finish_reason": "stop",
                            }
                        )
                    ],
                }
            )

    openai.ChatCompletion = ChatCompletion  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "openai", openai)
    return openai


def _raw_openai_agent(user_input: str) -> str:
    import openai  # type: ignore

    resp = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": user_input}],
    )
    return resp.choices[0].message.content


def test_pytest_fixture_smoke(sentinel):
    sentinel.mock("gpt-4").when(contains="refund").respond("ok")
    resp = sentinel.engine.handle(provider="openai", model="gpt-4", request={"prompt": "refund pls"})
    assert resp.text == "ok"


def test_mock_intercepts_openai_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_fake_openai(monkeypatch)

    s = Sentinel(root=tmp_path)
    s.install()
    s.mock("gpt-4").when(contains="refund").respond(
        "I'll process that refund",
        tools=["create_ticket"],
    )

    agent = s.wrap(_raw_openai_agent)
    response = agent.run("I want a refund")

    expect(response).to_contain("refund").to_have_called("create_ticket")


def test_rule_precedence_last_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_fake_openai(monkeypatch)

    s = Sentinel(root=tmp_path)
    s.install()

    s.mock("gpt-4").when(contains="refund").respond("first")
    s.mock("gpt-4").when(contains="refund").respond("second")

    agent = s.wrap(_raw_openai_agent)
    response = agent.run("refund")
    assert response.text == "second"


def test_stateful_sequence_responses(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_fake_openai(monkeypatch)

    s = Sentinel(root=tmp_path)
    s.install()

    s.mock("gpt-4").when(contains="hello").respond_sequence(["one", "two"])

    agent = s.wrap(_raw_openai_agent)
    assert agent.run("hello").text == "one"
    assert agent.run("hello").text == "two"
    assert agent.run("hello").text == "two"  # repeats last once sequence exhausted


def test_record_and_replay_without_context_manager(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    openai = _install_fake_openai(monkeypatch)

    s = Sentinel(root=tmp_path)
    s.install()

    s.record_session("sess1")
    openai._real_text = "REAL1"  # type: ignore[attr-defined]

    # No mock => pass-through; still recorded.
    real_resp = _raw_openai_agent("ping")
    assert real_resp == "REAL1"

    session_path = tmp_path / ".sentinel" / "sessions" / "sess1.json"
    assert not session_path.exists()

    # Switching to replay should auto-finalize recording and start replay.
    openai._real_text = "REAL2"  # type: ignore[attr-defined]
    s.replay_session("sess1")
    assert session_path.exists()

    replayed_resp = _raw_openai_agent("ping")
    assert replayed_resp == "REAL1"

    s.stop_session()
