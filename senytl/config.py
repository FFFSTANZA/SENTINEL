from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import FallbackMode


@dataclass
class SenytlConfig:
    fallback: FallbackMode = "error"


def load_config(root: Path | None = None) -> SenytlConfig:
    root = root or Path.cwd()

    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return SenytlConfig()

    try:
        import tomllib  # py>=3.11
    except Exception:  # pragma: no cover
        try:
            import tomli as tomllib  # type: ignore
        except Exception:
            return SenytlConfig()

    try:
        payload = tomllib.loads(pyproject.read_text())
    except Exception:
        return SenytlConfig()

    tool_cfg: dict[str, Any] = ((payload.get("tool") or {}).get("senytl") or {})
    fallback = tool_cfg.get("fallback")
    if fallback in {"error", "default", "pass_through"}:
        return SenytlConfig(fallback=fallback)

    return SenytlConfig()
