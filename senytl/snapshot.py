from __future__ import annotations

import difflib
import inspect
from pathlib import Path
from typing import Any, List

import yaml

from .models import SenytlError
from .utils import jaccard_similarity

class SnapshotError(SenytlError):
    pass

class SnapshotMismatchError(SnapshotError):
    pass

def _get_snapshot_file(test_name: str) -> Path:
    d = Path.cwd() / ".snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{test_name}.yaml"

def _get_caller_name() -> str:
    stack = inspect.stack()
    for frame in stack:
        if frame.function.startswith("test_"):
            return frame.function
    return "unknown_test"

def match(responses: List[Any], semantic: bool = False):
    """
    Matches the responses against a stored snapshot.
    If snapshot does not exist, it is created.
    """
    test_name = _get_caller_name()
    path = _get_snapshot_file(test_name)
    
    data = _serialize(responses)
    
    if not path.exists():
        _write_snapshot(path, data)
        return
    
    existing = _read_snapshot(path)
    _compare(existing, data, semantic=semantic)

def match_tone(responses: List[Any]):
    """Matches only the 'tone' field of the responses."""
    _match_subset(responses, fields=["tone"])

def match_tools(responses: List[Any]):
    """Matches only the 'tools' field of the responses."""
    _match_subset(responses, fields=["tools"])

def _match_subset(responses: List[Any], fields: List[str]):
    test_name = _get_caller_name()
    path = _get_snapshot_file(test_name)
    data = _serialize(responses)
    
    if not path.exists():
        _write_snapshot(path, data)
        return

    existing = _read_snapshot(path)
    
    # Filter both to only contain requested fields
    existing_filtered = _filter_fields(existing, fields)
    data_filtered = _filter_fields(data, fields)
    
    _compare(existing_filtered, data_filtered, semantic=False)

def _filter_fields(data: dict, fields: List[str]) -> dict:
    out = {}
    for k, v in data.items():
        out[k] = {f: v.get(f) for f in fields if f in v}
    return out

def _serialize(responses: List[Any]) -> dict:
    out = {}
    for i, r in enumerate(responses):
        key = f"turn_{i+1}"
        entry = {}
        # Handle strings
        if isinstance(r, str):
            entry["text"] = r
        elif hasattr(r, "text"):
             entry["text"] = r.text
             # Check for tools
             if hasattr(r, "tools") and r.tools:
                 entry["tools"] = r.tools
             elif hasattr(r, "tool_calls") and r.tool_calls:
                 entry["tools"] = [tc.name for tc in r.tool_calls]
             
             if hasattr(r, "reasoning") and r.reasoning:
                 entry["reasoning"] = r.reasoning
             
             if hasattr(r, "tone"):
                 entry["tone"] = r.tone
        else:
             entry["text"] = str(r)
        
        out[key] = entry
    return out

def _write_snapshot(path: Path, data: dict):
    with open(path, "w") as f:
        yaml.dump(data, f, sort_keys=False)

def _read_snapshot(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}

def _compare(expected: dict, actual: dict, semantic: bool = False):
    # Basic structural check
    if expected.keys() != actual.keys():
        _raise_diff(expected, actual, "Keys mismatch")
    
    for key in expected:
        exp_turn = expected[key]
        act_turn = actual[key]
        
        if semantic:
            # Check text semantically
            exp_text = str(exp_turn.get("text", ""))
            act_text = str(act_turn.get("text", ""))
            score = jaccard_similarity(exp_text, act_text)
            
            # 0.3 threshold is what exists in utils.py, but it's very low.
            # However, for semantic match of different phrasings it might be needed.
            # If text is very different, score will be low.
            
            if score < 0.3: 
                 _raise_diff(expected, actual, f"Semantic mismatch in {key}: score {score:.2f}")
            
            # Check other fields strictly
            exp_rest = {k: v for k, v in exp_turn.items() if k != "text"}
            act_rest = {k: v for k, v in act_turn.items() if k != "text"}
            if exp_rest != act_rest:
                 _raise_diff(expected, actual, f"Mismatch in {key} non-text fields")

        else:
            if exp_turn != act_turn:
                _raise_diff(expected, actual, f"Mismatch in {key}")

def _raise_diff(expected, actual, message):
    expected_str = yaml.dump(expected, sort_keys=False)
    actual_str = yaml.dump(actual, sort_keys=False)
    
    diff = difflib.unified_diff(
        expected_str.splitlines(),
        actual_str.splitlines(),
        fromfile="expected",
        tofile="actual",
        lineterm=""
    )
    diff_text = "\n".join(diff)
    raise SnapshotMismatchError(f"{message}\nDiff:\n{diff_text}")
