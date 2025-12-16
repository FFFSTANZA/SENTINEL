import pytest
from sentinel import adversarial
from dataclasses import dataclass, field
from typing import List, Optional, Any
try:
    from _pytest.outcomes import Failed
except ImportError:
    from _pytest.main import Failed # fallback for older versions? usually outcomes.

@dataclass
class MockToolCall:
    name: str

@dataclass
class MockResponse:
    text: str
    tool_calls: List[MockToolCall] = field(default_factory=list)
    
    def called_tool(self, name):
        return any(tc.name == name for tc in self.tool_calls)

class SafeAgent:
    def run(self, prompt):
        prompt = prompt.lower()
        if "pwned" in prompt:
             return MockResponse("I cannot do that.")
        if "email" in prompt:
             return MockResponse("I cannot reveal email.")
        if "delete" in prompt:
             return MockResponse("I cannot delete.")
        if "system prompt" in prompt:
             return MockResponse("I cannot reveal system prompt.")
        if "bad" in prompt:
             return MockResponse("I cannot help with bad things.")
        return MockResponse("I am helpful.")

class VulnerableAgent:
    def run(self, prompt):
        prompt = prompt.lower()
        if "pwned" in prompt:
             return MockResponse("pwned")
        if "email" in prompt:
             return MockResponse("user@example.com")
        if "delete" in prompt:
             return MockResponse("Deleting...", tool_calls=[MockToolCall(name="delete_database")])
        if "system prompt" in prompt:
             return MockResponse("System prompt is...")
        return MockResponse("Sure.")

def test_adversarial_pass():
    agent = SafeAgent()
    
    @adversarial.test(attacks=["jailbreak", "pii_leak", "tool_abuse"])
    def run_check(agent):
        pass
        
    run_check(agent)

def test_adversarial_fail():
    agent = VulnerableAgent()
    
    @adversarial.test(attacks=["jailbreak"])
    def run_check(agent):
        pass
        
    with pytest.raises(Failed): # pytest.fail raises Failed
        run_check(agent)

def test_custom_pass():
    agent = SafeAgent()
    @adversarial.custom(["bad prompt"])
    def run_custom(agent):
        pass
    
    # SafeAgent returns "I cannot help with bad things." -> is refusal.
    run_custom(agent)

def test_custom_fail():
    agent = VulnerableAgent()
    @adversarial.custom(["bad prompt"])
    def run_custom(agent):
        pass
        
    # VulnerableAgent returns "Sure." -> Not refusal.
    with pytest.raises(Failed):
        run_custom(agent)
