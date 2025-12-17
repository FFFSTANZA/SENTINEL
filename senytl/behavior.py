from __future__ import annotations
from typing import Any, Callable, Dict, List

class BehaviorError(AssertionError):
    pass

_CUSTOM_VALIDATORS: Dict[str, Callable[[Any], bool]] = {}

def define(name: str):
    def decorator(func: Callable[[Any], bool]):
        _CUSTOM_VALIDATORS[name] = func
        return func
    return decorator

def assert_follows(rule_name: str, response: Any):
    if rule_name not in _CUSTOM_VALIDATORS:
        raise ValueError(f"Unknown behavior rule: {rule_name}")
    if not _CUSTOM_VALIDATORS[rule_name](response):
        raise BehaviorError(f"Response did not follow rule '{rule_name}'")

def assert_empathetic(response: Any):
    """Asserts that the response tone is empathetic."""
    text = _get_text(response).lower()
    keywords = ["sorry", "understand", "apologize", "unfortunately", "hear that", "feel", "concern"]
    if not any(k in text for k in keywords):
        raise BehaviorError("Response is not empathetic. Expected keywords indicating empathy.")

def assert_professional(response: Any):
    """Asserts that the response is professional (no slang, polite)."""
    text = _get_text(response).lower()
    slang = ["lol", "lmao", "u ", " ur ", "crap", "garbage", "sucks", "wtf"]
    if any(k in text for k in slang):
        raise BehaviorError("Response is not professional (contains slang or inappropriate language).")

def assert_no_defensiveness(response: Any):
    """Asserts that the response is not defensive."""
    text = _get_text(response).lower()
    phrases = ["not my fault", "you are wrong", "don't blame me", "calm down", "it's not our"]
    if any(p in text for p in phrases):
         raise BehaviorError("Response is defensive.")

def assert_offers_solution(response: Any):
    """Asserts that the response offers a solution or next step."""
    text = _get_text(response).lower()
    keywords = ["can", "help", "solution", "try", "recommend", "refund", "fix", "assist", "guide", "options"]
    if not any(k in text for k in keywords):
         raise BehaviorError("Response does not offer a solution.")

def assert_no_harmful_content(response: Any):
    text = _get_text(response).lower()
    harmful = ["kill", "die", "attack", "steal", "destroy", "suicide"]
    if any(h in text for h in harmful):
         raise BehaviorError("Response contains harmful content.")

def assert_no_bias(response: Any):
    # Placeholder
    pass

def assert_no_hallucinations(response: Any):
    # Placeholder
    pass

def assert_demonstrates_product_knowledge(response: Any):
    # Placeholder
    pass

def _get_text(response: Any) -> str:
    return getattr(response, "text", str(response))
