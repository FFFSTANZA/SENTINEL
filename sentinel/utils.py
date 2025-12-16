from __future__ import annotations

import hashlib
import json
import re
from dataclasses import is_dataclass, asdict
from typing import Any, Iterable


class AttrDict(dict):
    """A tiny helper to mimic SDK response objects with attribute access."""

    def __getattr__(self, item: str) -> Any:  # noqa: D401
        try:
            value = self[item]
        except KeyError as e:  # pragma: no cover
            raise AttributeError(item) from e
        return value

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


def _json_default(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, set):
        return sorted(obj)
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def stable_json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=_json_default)


def stable_hash(value: Any) -> str:
    payload = stable_json_dumps(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


_WORD_RE = re.compile(r"[A-Za-z0-9_']+")


def tokenize(text: str) -> set[str]:
    return {m.group(0).lower() for m in _WORD_RE.finditer(text or "")}


def jaccard_similarity(a: str, b: str) -> float:
    a_tokens = tokenize(a)
    b_tokens = tokenize(b)
    if not a_tokens and not b_tokens:
        return 1.0
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def flatten_messages(messages: Any) -> str:
    if messages is None:
        return ""
    if isinstance(messages, str):
        return messages
    if isinstance(messages, list):
        parts: list[str] = []
        for m in messages:
            if isinstance(m, str):
                parts.append(m)
                continue
            if isinstance(m, dict):
                if "content" in m and isinstance(m["content"], str):
                    parts.append(m["content"])
                    continue
                # common: {role, content}
                content = m.get("content")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and isinstance(block.get("text"), str):
                            parts.append(block["text"])
                elif content is not None:
                    parts.append(str(content))
                continue
            parts.append(str(m))
        return "\n".join(parts)
    return str(messages)


def any_match(patterns: Iterable[str], text: str) -> bool:
    text_l = (text or "").lower()
    return any(p.lower() in text_l for p in patterns)
