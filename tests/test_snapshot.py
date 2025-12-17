import pytest
from senytl import snapshot
from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class MockResponse:
    text: str
    tools: Optional[List[str]] = None
    tone: Optional[str] = None
    tool_calls: Optional[List[Any]] = None

def test_snapshot_match(tmp_path):
    original_get = snapshot._get_snapshot_file
    snapshot._get_snapshot_file = lambda name: tmp_path / f"{name}.yaml"
    
    try:
        responses = [
            MockResponse(text="Hello", tools=[], tone="friendly"),
            MockResponse(text="World", tools=["search"], tone="neutral")
        ]
        
        # First run: should create file
        snapshot.match(responses)
        
        assert (tmp_path / "test_snapshot_match.yaml").exists()
        
        # Second run: should pass
        snapshot.match(responses)
        
        # Mismatch text
        mismatched = [
            MockResponse(text="Goodbye", tools=[], tone="friendly"),
            MockResponse(text="World", tools=["search"], tone="neutral")
        ]
        
        with pytest.raises(snapshot.SnapshotMismatchError):
            snapshot.match(mismatched)
            
    finally:
        snapshot._get_snapshot_file = original_get

def test_snapshot_semantic(tmp_path):
    original_get = snapshot._get_snapshot_file
    snapshot._get_snapshot_file = lambda name: tmp_path / f"{name}.yaml"
    
    try:
        responses_sem = [MockResponse(text="I have a problem")]
        snapshot.match(responses_sem) # Create snapshot
        
        # Token overlap: i, have (2). Union: i, have, a, problem, an, issue (6). 2/6 = 0.33. > 0.3.
        mismatched_sem = [MockResponse(text="I have an issue")]
        snapshot.match(mismatched_sem, semantic=True)
        
        # Very different
        diff = [MockResponse(text="Everything is fine")]
        with pytest.raises(snapshot.SnapshotMismatchError):
             snapshot.match(diff, semantic=True)
             
    finally:
        snapshot._get_snapshot_file = original_get

def test_snapshot_selective(tmp_path):
    original_get = snapshot._get_snapshot_file
    snapshot._get_snapshot_file = lambda name: tmp_path / f"{name}.yaml"
    
    try:
        responses_tone = [MockResponse(text="Foo", tone="friendly")]
        snapshot.match_tone(responses_tone) # Create
        
        mismatched_text_same_tone = [MockResponse(text="Bar", tone="friendly")]
        snapshot.match_tone(mismatched_text_same_tone) # Should pass
        
        mismatched_tone = [MockResponse(text="Foo", tone="angry")]
        with pytest.raises(snapshot.SnapshotMismatchError):
            snapshot.match_tone(mismatched_tone)
            
    finally:
        snapshot._get_snapshot_file = original_get
