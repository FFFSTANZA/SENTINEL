from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from .models import SenytlResponse
from .utils import jaccard_similarity
from .semantic import get_semantic_validator, semantic_similarity, SemanticValidationResult


@dataclass
class SemanticExpectation:
    """Extended expectation for semantic validation with detailed results."""
    
    response: SenytlResponse
    reference: str
    threshold: float
    model: str
    explain: bool
    
    def __post_init__(self):
        """Perform semantic validation on initialization."""
        from .semantic import SemanticValidationConfig
        config = SemanticValidationConfig(
            model=self.model,
            threshold=self.threshold,
            explain=self.explain
        )
        self.validator = get_semantic_validator(config)
        self.result = self.validator.validate_response_similarity(
            self.response, self.reference
        )
        
        if not self.result.passed:
            raise AssertionError(
                f"Expected response to be semantically similar to {self.reference!r} "
                f"(threshold={self.threshold}, model={self.model!r}). "
                f"Score={self.result.score:.3f}. Got: {self.response.text!r}\n"
                f"Explanation: {self.result.explanation}"
            )
    
    @property
    def confidence(self) -> float:
        """Get the similarity confidence score."""
        return self.result.score
    
    @property
    def explanation(self) -> str:
        """Get the explanation for why validation passed/failed."""
        return self.result.explanation
    
    @property
    def passed(self) -> bool:
        """Whether the semantic validation passed."""
        return self.result.passed
    
    def with_threshold(self, new_threshold: float) -> "SemanticExpectation":
        """Create new expectation with different threshold."""
        return SemanticExpectation(
            self.response, self.reference, new_threshold, self.model, self.explain
        )
    
    def with_model(self, new_model: str) -> "SemanticExpectation":
        """Create new expectation with different model."""
        return SemanticExpectation(
            self.response, self.reference, self.threshold, new_model, self.explain
        )


@dataclass
class Expectation:
    response: SenytlResponse

    def to_contain(self, text: str) -> "Expectation":
        if text not in (self.response.text or ""):
            raise AssertionError(f"Expected response to contain {text!r}. Got: {self.response.text!r}")
        return self

    def to_match(self, pattern: str, *, flags: int = re.IGNORECASE) -> "Expectation":
        if re.search(pattern, self.response.text or "", flags=flags) is None:
            raise AssertionError(
                f"Expected response to match /{pattern}/. Got: {self.response.text!r}"
            )
        return self

    def to_contain_intent(self, intent: str, *, threshold: float = 0.3) -> "Expectation":
        score = jaccard_similarity(self.response.text or "", intent)
        if score < threshold:
            raise AssertionError(
                f"Expected response to semantically match {intent!r} (threshold={threshold}). "
                f"Score={score:.3f}. Got: {self.response.text!r}"
            )
        return self

    def semantically_similar_to(self, reference: str, *, 
                                threshold: float = 0.85, 
                                model: str = "all-MiniLM-L6-v2",
                                explain: bool = True) -> "SemanticExpectation":
        """Check semantic similarity using embedding-based validation.
        
        This method provides true semantic matching rather than basic keyword matching.
        
        Args:
            reference: Reference text to compare against
            threshold: Similarity threshold (0.0 to 1.0)
            model: Sentence transformer model to use
            explain: Whether to generate explanation for validation result
            
        Returns:
            SemanticExpectation with additional methods like .confidence and .explanation
            
        Raises:
            AssertionError: If similarity score is below threshold
            
        Example:
            result = expect(response).semantically_similar_to(
                "I will process your refund request",
                threshold=0.85,
                model="all-MiniLM-L6-v2"
            )
            print(result.confidence)  # 0.92
            print(result.explanation)  # "Both texts discuss processing refunds"
        """
        return SemanticExpectation(
            self.response, reference, threshold, model, explain
        )

    def to_be_polite(self) -> "Expectation":
        text = (self.response.text or "").lower()
        polite = any(w in text for w in ("please", "thank", "thanks", "happy to", "glad to"))
        rude = any(w in text for w in ("idiot", "stupid", "shut up", "hate"))
        if rude or not polite:
            raise AssertionError(f"Expected a polite response. Got: {self.response.text!r}")
        return self

    def not_to_contain_pii(self) -> "Expectation":
        text = self.response.text or ""
        patterns = {
            "email": r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
            "phone": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        }
        for label, pat in patterns.items():
            if re.search(pat, text, flags=re.IGNORECASE) is not None:
                raise AssertionError(f"Expected no PII ({label}) in response. Got: {text!r}")
        return self

    def to_have_called(self, tool_name: str) -> "Expectation":
        if not any(tc.name == tool_name for tc in self.response.tool_calls):
            raise AssertionError(
                f"Expected tool {tool_name!r} to be called. Calls: {self.response.tool_calls!r}"
            )
        return self

    def not_to_have_called(self, tool_name: str) -> "Expectation":
        if any(tc.name == tool_name for tc in self.response.tool_calls):
            raise AssertionError(
                f"Expected tool {tool_name!r} to NOT be called. Calls: {self.response.tool_calls!r}"
            )
        return self

    def to_have_called_with(self, tool_name: str, /, **expected_args: Any) -> "Expectation":
        matching = [tc for tc in self.response.tool_calls if tc.name == tool_name]
        if not matching:
            raise AssertionError(
                f"Expected tool {tool_name!r} to be called. Calls: {self.response.tool_calls!r}"
            )
        for call in matching:
            if _args_contain(call.args, expected_args):
                return self
        raise AssertionError(
            f"Expected tool {tool_name!r} to be called with {expected_args!r}. Calls: {matching!r}"
        )

    def to_have_response_time_under(self, *, seconds: float) -> "Expectation":
        duration = self.response.duration_seconds
        if duration is None:
            raise AssertionError("Response did not include duration_seconds")
        if duration > seconds:
            raise AssertionError(f"Expected response under {seconds}s, got {duration:.6f}s")
        return self


def _args_contain(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    for k, v in expected.items():
        if k not in actual:
            return False
        if actual[k] != v:
            return False
    return True


def expect(response: SenytlResponse) -> Expectation:
    return Expectation(response)
