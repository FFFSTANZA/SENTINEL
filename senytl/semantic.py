from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from .models import SenytlResponse


logger = logging.getLogger(__name__)


@dataclass
class SemanticValidationResult:
    """Result of semantic validation with explanation."""
    score: float
    passed: bool
    explanation: str
    model_name: str
    threshold: float


@dataclass 
class SemanticValidationConfig:
    """Configuration for semantic validation."""
    model: str = "all-MiniLM-L6-v2"
    threshold: float = 0.85
    explain: bool = True


class EmbeddingCache:
    """Simple LRU cache for embeddings to improve performance."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_order: list[str] = []
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.max_size:
            # Remove least recently used
            oldest = self.access_order.pop(0)
            del self.cache[oldest]
        
        self.cache[key] = value
        self.access_order.append(key)
    
    def clear(self) -> None:
        self.cache.clear()
        self.access_order.clear()


class SemanticValidator:
    """Embedding-based semantic validation engine."""
    
    def __init__(self, config: Optional[SemanticValidationConfig] = None):
        self.config = config or SemanticValidationConfig()
        self._model = None
        self._cache = EmbeddingCache()
        self._default_model = "all-MiniLM-L6-v2"
        
    @property
    def model(self) -> Optional[SentenceTransformer]:
        """Lazy-load the sentence transformer model."""
        if self._model is None:
            if SentenceTransformer is None:
                raise ImportError(
                    "sentence-transformers is required for semantic validation. "
                    "Install with: pip install 'senytl[semantic]'"
                )
            try:
                model_name = self.config.model
                logger.info(f"Loading semantic validation model: {model_name}")
                self._model = SentenceTransformer(model_name)
            except Exception as e:
                logger.error(f"Failed to load model {self.config.model}: {e}")
                raise RuntimeError(f"Could not load semantic validation model: {e}")
        return self._model
    
    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text to use as cache key."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _get_embedding(self, text: str) -> Optional[Any]:
        """Get embedding for text with caching."""
        text_hash = self._get_text_hash(text)
        cached = self._cache.get(text_hash)
        if cached is not None:
            return cached
        
        try:
            embedding = self.model.encode(text.strip())
            self._cache.put(text_hash, embedding)
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            return None
    
    def _cosine_similarity(self, embedding1: Any, embedding2: Any) -> float:
        """Calculate cosine similarity between two embeddings."""
        try:
            import torch
            if torch.is_tensor(embedding1) and torch.is_tensor(embedding2):
                cos_sim = torch.nn.functional.cosine_similarity(
                    embedding1.unsqueeze(0), embedding2.unsqueeze(0)
                )
                return float(cos_sim.item())
        except ImportError:
            pass
        
        # Fallback to numpy if torch not available
        try:
            import numpy as np
            embedding1 = embedding1.reshape(1, -1)
            embedding2 = embedding2.reshape(1, -1)
            cos_sim = np.dot(embedding1, embedding2.T) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )
            return float(cos_sim.item())
        except Exception:
            pass
        
        # If all else fails, use basic similarity
        return 0.0
    
    def _generate_explanation(self, text1: str, text2: str, score: float) -> str:
        """Generate explanation for why validation passed/failed."""
        # Extract key concepts from both texts
        words1 = set(word.lower().strip('.,!?;:"') for word in text1.split())
        words2 = set(word.lower().strip('.,!?;:"') for word in text2.split())
        
        common_words = words1 & words2
        unique_words1 = words1 - words2
        unique_words2 = words2 - words1
        
        if score >= self.config.threshold:
            if common_words:
                return (
                    f"Texts are semantically similar (score: {score:.3f}). "
                    f"Common concepts: {', '.join(sorted(common_words)[:5])}"
                )
            else:
                return (
                    f"Texts convey similar meaning despite different wording "
                    f"(score: {score:.3f})."
                )
        else:
            return (
                f"Texts lack semantic similarity (score: {score:.3f} < {self.config.threshold}). "
                f"Text 1 focuses on: {', '.join(sorted(list(unique_words1)[:3]))}. "
                f"Text 2 focuses on: {', '.join(sorted(list(unique_words2)[:3]))}."
            )
    
    def validate_similarity(self, text1: str, text2: str, 
                          threshold: Optional[float] = None) -> SemanticValidationResult:
        """
        Validate semantic similarity between two texts.
        
        Args:
            text1: First text to compare
            text2: Second text to compare  
            threshold: Optional override for similarity threshold
            
        Returns:
            SemanticValidationResult with score, pass/fail, and explanation
        """
        if not text1 or not text2:
            return SemanticValidationResult(
                score=0.0,
                passed=False,
                explanation="Cannot compare empty texts",
                model_name=self.config.model,
                threshold=threshold or self.config.threshold
            )
        
        # Generate embeddings
        embedding1 = self._get_embedding(text1)
        embedding2 = self._get_embedding(text2)
        
        if embedding1 is None or embedding2 is None:
            return SemanticValidationResult(
                score=0.0,
                passed=False,
                explanation="Failed to generate text embeddings",
                model_name=self.config.model,
                threshold=threshold or self.config.threshold
            )
        
        # Calculate similarity
        score = self._cosine_similarity(embedding1, embedding2)
        final_threshold = threshold or self.config.threshold
        passed = score >= final_threshold
        
        # Generate explanation
        if self.config.explain:
            explanation = self._generate_explanation(text1, text2, score)
        else:
            explanation = f"Semantic similarity score: {score:.3f}"
        
        return SemanticValidationResult(
            score=score,
            passed=passed,
            explanation=explanation,
            model_name=self.config.model,
            threshold=final_threshold
        )
    
    def validate_response_similarity(self, response: SenytlResponse, reference: str,
                                   threshold: Optional[float] = None) -> SemanticValidationResult:
        """
        Validate semantic similarity between a SenytlResponse and reference text.
        
        Args:
            response: SenytlResponse to validate
            reference: Reference text to compare against
            threshold: Optional threshold override
            
        Returns:
            SemanticValidationResult
        """
        response_text = response.text or ""
        return self.validate_similarity(response_text, reference, threshold)
    
    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
    
    def get_available_models(self) -> list[str]:
        """Get list of available sentence transformer models."""
        return [
            "all-MiniLM-L6-v2",      # Fast, good general purpose
            "all-mpnet-base-v2",     # Higher quality, slower
            "multi-qa-MiniLM-L6-cos-v1",  # Optimized for Q&A
            "paraphrase-MiniLM-L6-v3",    # Optimized for paraphrase detection
        ]


# Global validator instance
_global_validator: Optional[SemanticValidator] = None


def get_semantic_validator(config: Optional[SemanticValidationConfig] = None) -> SemanticValidator:
    """Get global semantic validator instance."""
    global _global_validator
    if _global_validator is None:
        _global_validator = SemanticValidator(config)
    elif config is not None:
        _global_validator = SemanticValidator(config)
    return _global_validator


def semantic_similarity(text1: str, text2: str, 
                       threshold: float = 0.85,
                       model: str = "all-MiniLM-L6-v2") -> SemanticValidationResult:
    """
    Utility function for quick semantic similarity checks.
    
    Args:
        text1: First text
        text2: Second text  
        threshold: Similarity threshold (0.0 to 1.0)
        model: Sentence transformer model to use
        
    Returns:
        SemanticValidationResult
    """
    config = SemanticValidationConfig(
        model=model,
        threshold=threshold,
        explain=True
    )
    validator = get_semantic_validator(config)
    return validator.validate_similarity(text1, text2)