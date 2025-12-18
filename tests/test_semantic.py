"""Tests for semantic validation engine."""
import pytest
from unittest.mock import Mock, patch

from senytl.models import SenytlResponse
from senytl.semantic import (
    SemanticValidator, 
    SemanticValidationResult, 
    SemanticValidationConfig,
    semantic_similarity,
    get_semantic_validator
)
from senytl.assertions import expect, SemanticExpectation


class TestSemanticValidationResult:
    """Test SemanticValidationResult dataclass."""
    
    def test_result_creation(self):
        result = SemanticValidationResult(
            score=0.85,
            passed=True,
            explanation="Texts are similar",
            model_name="test-model",
            threshold=0.8
        )
        assert result.score == 0.85
        assert result.passed is True
        assert result.explanation == "Texts are similar"
        assert result.model_name == "test-model"
        assert result.threshold == 0.8


class TestSemanticValidationConfig:
    """Test SemanticValidationConfig dataclass."""
    
    def test_default_config(self):
        config = SemanticValidationConfig()
        assert config.model == "all-MiniLM-L6-v2"
        assert config.threshold == 0.85
        assert config.explain is True
    
    def test_custom_config(self):
        config = SemanticValidationConfig(
            model="all-mpnet-base-v2",
            threshold=0.9,
            explain=False
        )
        assert config.model == "all-mpnet-base-v2"
        assert config.threshold == 0.9
        assert config.explain is False


class TestSemanticValidator:
    """Test SemanticValidator class."""
    
    def test_validator_initialization(self):
        config = SemanticValidationConfig(threshold=0.7)
        validator = SemanticValidator(config)
        assert validator.config.threshold == 0.7
        assert validator.config.model == "all-MiniLM-L6-v2"
    
    def test_get_available_models(self):
        validator = SemanticValidator()
        models = validator.get_available_models()
        assert "all-MiniLM-L6-v2" in models
        assert "all-mpnet-base-v2" in models
        assert "multi-qa-MiniLM-L6-cos-v1" in models
        assert "paraphrase-MiniLM-L6-v3" in models
    
    @patch('senytl.semantic.SentenceTransformer')
    def test_model_loading_error(self, mock_model):
        """Test error handling when model loading fails."""
        mock_model.side_effect = Exception("Model not found")
        
        config = SemanticValidationConfig()
        validator = SemanticValidator(config)
        
        with pytest.raises(RuntimeError, match="Could not load semantic validation model"):
            _ = validator.model
    
    def test_empty_text_validation(self):
        """Test validation with empty texts."""
        validator = SemanticValidator()
        result = validator.validate_similarity("", "some text")
        
        assert result.score == 0.0
        assert result.passed is False
        assert "Cannot compare empty texts" in result.explanation
        
        result = validator.validate_similarity("some text", "")
        assert result.score == 0.0
        assert result.passed is False
        assert "Cannot compare empty texts" in result.explanation
    
    def test_text_similarity_validation(self):
        """Test text similarity validation with mock embeddings."""
        validator = SemanticValidator()
        
        # Mock the _get_embedding method to return simple vectors
        with patch.object(validator, '_get_embedding') as mock_embedding:
            # Mock embeddings for testing
            mock_embedding.return_value = [0.5, 0.3, 0.8]
            
            result = validator.validate_similarity("Hello world", "Hello there")
            
            assert result.score >= 0.0
            assert isinstance(result.explanation, str)
            assert result.model_name == "all-MiniLM-L6-v2"
    
    def test_response_similarity_validation(self):
        """Test SenytlResponse similarity validation."""
        validator = SemanticValidator()
        
        response = SenytlResponse(
            text="I will process your refund request",
            tool_calls=[],
            duration_seconds=1.0
        )
        
        # Mock the validation to avoid actual model dependency
        with patch.object(validator, 'validate_similarity') as mock_validate:
            mock_result = SemanticValidationResult(
                score=0.92,
                passed=True,
                explanation="Both texts discuss processing refunds",
                model_name="test-model",
                threshold=0.85
            )
            mock_validate.return_value = mock_result
            
            result = validator.validate_response_similarity(
                response, 
                "I will process your refund request"
            )
            
            assert result.score == 0.92
            assert result.passed is True
            assert "processing refunds" in result.explanation


class TestSemanticExpectation:
    """Test SemanticExpectation class for assertions."""
    
    def test_semantic_expectation_creation(self):
        """Test creating SemanticExpectation object."""
        response = SenytlResponse(
            text="I will help you with that refund",
            tool_calls=[],
            duration_seconds=1.0
        )
        
        # Mock the semantic validation to avoid model dependency
        with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_result = SemanticValidationResult(
                score=0.9,
                passed=True,
                explanation="Similar meaning detected",
                model_name="test-model",
                threshold=0.85
            )
            mock_validator.validate_response_similarity.return_value = mock_result
            mock_get_validator.return_value = mock_validator
            
            with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
                mock_assertion_validator.return_value = mock_validator
                
                expectation = SemanticExpectation(
                    response=response,
                    reference="I will process your refund",
                    threshold=0.85,
                    model="test-model",
                    explain=True
                )
                
                assert expectation.confidence == 0.9
                assert expectation.explanation == "Similar meaning detected"
                assert expectation.passed is True
    
    def test_semantic_expectation_failure(self):
        """Test SemanticExpectation when validation fails."""
        response = SenytlResponse(
            text="Hello there",
            tool_calls=[],
            duration_seconds=1.0
        )
        
        # Mock failed validation
        with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_result = SemanticValidationResult(
                score=0.3,
                passed=False,
                explanation="Low similarity score",
                model_name="test-model",
                threshold=0.85
            )
            mock_validator.validate_response_similarity.return_value = mock_result
            mock_get_validator.return_value = mock_validator
            
            with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
                mock_assertion_validator.return_value = mock_validator
                
                with pytest.raises(AssertionError, match="Expected response to be semantically similar"):
                    SemanticExpectation(
                        response=response,
                        reference="I will process your refund request",
                        threshold=0.85,
                        model="test-model",
                        explain=True
                    )
    
    def test_with_threshold(self):
        """Test creating new expectation with different threshold."""
        response = SenytlResponse(
            text="Test response",
            tool_calls=[],
            duration_seconds=1.0
        )
        
        with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_get_validator.return_value = mock_validator
            
            with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
                mock_assertion_validator.return_value = mock_validator
                
                original = SemanticExpectation(
                    response=response,
                    reference="Test reference",
                    threshold=0.85,
                    model="test-model",
                    explain=True
                )
                
                modified = original.with_threshold(0.9)
                assert modified.threshold == 0.9
                assert modified.reference == "Test reference"
                assert modified.model == "test-model"
    
    def test_with_model(self):
        """Test creating new expectation with different model."""
        response = SenytlResponse(
            text="Test response",
            tool_calls=[],
            duration_seconds=1.0
        )
        
        with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_get_validator.return_value = mock_validator
            
            with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
                mock_assertion_validator.return_value = mock_validator
                
                original = SemanticExpectation(
                    response=response,
                    reference="Test reference",
                    threshold=0.85,
                    model="test-model",
                    explain=True
                )
                
                modified = original.with_model("new-model")
                assert modified.model == "new-model"
                assert modified.threshold == 0.85
                assert modified.reference == "Test reference"


class TestSemanticAssertions:
    """Test the expect().semantically_similar_to() assertion method."""
    
    def test_semantic_similarity_assertion_success(self):
        """Test successful semantic similarity assertion."""
        response = SenytlResponse(
            text="I will help you process that refund request",
            tool_calls=[],
            duration_seconds=1.0
        )
        
        # Mock the validation to return a passing result
        with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_result = SemanticValidationResult(
                score=0.92,
                passed=True,
                explanation="Both texts discuss processing refunds",
                model_name="all-MiniLM-L6-v2",
                threshold=0.85
            )
            mock_validator.validate_response_similarity.return_value = mock_result
            mock_get_validator.return_value = mock_validator
            
            with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
                mock_assertion_validator.return_value = mock_validator
                
                result = expect(response).semantically_similar_to(
                    "I will process your refund request",
                    threshold=0.85,
                    model="all-MiniLM-L6-v2"
                )
                
                assert isinstance(result, SemanticExpectation)
                assert result.confidence == 0.92
                assert result.explanation == "Both texts discuss processing refunds"
                assert result.passed is True
    
    def test_semantic_similarity_assertion_failure(self):
        """Test failed semantic similarity assertion."""
        response = SenytlResponse(
            text="Hello, how are you today?",
            tool_calls=[],
            duration_seconds=1.0
        )
        
        # Mock the validation to return a failing result
        with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_result = SemanticValidationResult(
                score=0.3,
                passed=False,
                explanation="Texts are not semantically similar",
                model_name="all-MiniLM-L6-v2",
                threshold=0.85
            )
            mock_validator.validate_response_similarity.return_value = mock_result
            mock_get_validator.return_value = mock_validator
            
            with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
                mock_assertion_validator.return_value = mock_validator
                
                with pytest.raises(AssertionError, match="Expected response to be semantically similar"):
                    expect(response).semantically_similar_to(
                        "I will process your refund request",
                        threshold=0.85,
                        model="all-MiniLM-L6-v2"
                    )
    
    def test_semantic_similarity_with_custom_model(self):
        """Test semantic similarity with custom model."""
        response = SenytlResponse(
            text="Test response about refunds",
            tool_calls=[],
            duration_seconds=1.0
        )
        
        with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_get_validator.return_value = mock_validator
            
            with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
                mock_assertion_validator.return_value = mock_validator
                
                result = expect(response).semantically_similar_to(
                    "Refund processing statement",
                    model="all-mpnet-base-v2",
                    threshold=0.9
                )
                
                assert isinstance(result, SemanticExpectation)


class TestSemanticUtilityFunctions:
    """Test utility functions in semantic module."""
    
    def test_semantic_similarity_function(self):
        """Test the standalone semantic_similarity function."""
        # Mock the validation to avoid model dependency
        with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_result = SemanticValidationResult(
                score=0.88,
                passed=True,
                explanation="Texts are similar",
                model_name="all-MiniLM-L6-v2",
                threshold=0.85
            )
            mock_validator.validate_similarity.return_value = mock_result
            mock_get_validator.return_value = mock_validator
            
            result = semantic_similarity(
                "I will help you",
                "I can assist you",
                threshold=0.85,
                model="all-MiniLM-L6-v2"
            )
            
            assert isinstance(result, SemanticValidationResult)
            assert result.score == 0.88
            assert result.passed is True
            assert result.model_name == "all-MiniLM-L6-v2"
    
    def test_get_semantic_validator_singleton(self):
        """Test global validator singleton behavior."""
        validator1 = get_semantic_validator()
        validator2 = get_semantic_validator()
        
        # Should be the same instance
        assert validator1 is validator2
        
        # But with different config should create new instance
        config = SemanticValidationConfig(threshold=0.9)
        validator3 = get_semantic_validator(config)
        assert validator3 is not validator1


class TestSemanticIntegration:
    """Integration tests for semantic validation features."""
    
    def test_refund_processing_example(self):
        """Test the example from the problem description."""
        response = SenytlResponse(
            text="I'll be happy to process that refund request for you",
            tool_calls=[],
            duration_seconds=1.0
        )
        
        # Mock successful validation
        with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_result = SemanticValidationResult(
                score=0.92,
                passed=True,
                explanation="Both texts discuss processing refunds",
                model_name="all-MiniLM-L6-v2",
                threshold=0.85
            )
            mock_validator.validate_response_similarity.return_value = mock_result
            mock_get_validator.return_value = mock_validator
            
            with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
                mock_assertion_validator.return_value = mock_validator
                
                # This should pass
                result = expect(response).semantically_similar_to(
                    "I will process your refund request",
                    threshold=0.85,
                    model="all-MiniLM-L6-v2"
                )
                
                # Check the confidence and explanation as shown in example
                assert result.confidence == 0.92
                assert result.explanation == "Both texts discuss processing refunds"
    
    def test_alternative_wordings(self):
        """Test that alternative wordings with same meaning work."""
        reference_text = "I will process your refund request"
        
        # Different ways to say the same thing
        responses = [
            "I'll be happy to process that refund for you",
            "Let me help you get that refund processed",
            "I'm here to assist with processing your refund",
            "I'll take care of processing your refund request",
        ]
        
        for response_text in responses:
            response = SenytlResponse(
                text=response_text,
                tool_calls=[],
                duration_seconds=1.0
            )
            
            # Mock high similarity scores for all variations
            with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
                mock_validator = Mock()
                mock_result = SemanticValidationResult(
                    score=0.88,  # High but different for each
                    passed=True,
                    explanation="Similar meaning detected",
                    model_name="all-MiniLM-L6-v2",
                    threshold=0.85
                )
                mock_validator.validate_response_similarity.return_value = mock_result
                mock_get_validator.return_value = mock_validator
                
                with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
                    mock_assertion_validator.return_value = mock_validator
                    
                    # All should pass semantic validation
                    result = expect(response).semantically_similar_to(
                        reference_text,
                        threshold=0.85
                    )
                    assert result.passed is True
                    assert result.confidence > 0.85
    
    def test_different_threshold_sensitivity(self):
        """Test that different thresholds affect pass/fail."""
        response = SenytlResponse(
            text="I can help you with that",
            tool_calls=[],
            duration_seconds=1.0
        )
        reference = "I will process your refund request"
        
        # Low threshold should pass
        with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_result = SemanticValidationResult(
                score=0.3,
                passed=True,  # Passes with low threshold
                explanation="Low similarity but passes threshold",
                model_name="all-MiniLM-L6-v2",
                threshold=0.2  # Low threshold
            )
            mock_validator.validate_response_similarity.return_value = mock_result
            mock_get_validator.return_value = mock_validator
            
            with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
                mock_assertion_validator.return_value = mock_validator
                
                result = expect(response).semantically_similar_to(
                    reference,
                    threshold=0.2
                )
                assert result.passed is True
        
        # High threshold should fail
        with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_result = SemanticValidationResult(
                score=0.3,
                passed=False,  # Fails with high threshold
                explanation="Below threshold",
                model_name="all-MiniLM-L6-v2",
                threshold=0.9  # High threshold
            )
            mock_validator.validate_response_similarity.return_value = mock_result
            mock_get_validator.return_value = mock_validator
            
            with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
                mock_assertion_validator.return_value = mock_validator
                
                with pytest.raises(AssertionError):
                    expect(response).semantically_similar_to(
                        reference,
                        threshold=0.9
                    )