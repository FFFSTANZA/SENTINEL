#!/usr/bin/env python3
"""
Example script demonstrating the semantic validation engine.
This showcases the improved robustness over basic keyword matching.
"""

from senytl import expect, SenytlResponse
from unittest.mock import patch, Mock
from senytl.semantic import SemanticValidationResult


def mock_semantic_validator():
    """Helper function to mock semantic validation."""
    def mock_get_validator():
        mock_validator = Mock()
        return mock_validator
    return mock_get_validator


def demonstrate_semantic_validation():
    """Demonstrate the semantic validation capabilities."""
    
    print("=" * 60)
    print("SEMANTIC VALIDATION ENGINE DEMONSTRATION")
    print("=" * 60)
    
    # Example response that would fail basic keyword matching
    response = SenytlResponse(
        text="I'll be happy to process that refund request for you immediately",
        tool_calls=[],
        duration_seconds=1.0
    )
    
    # Mock high semantic similarity
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
            
            print("\n1. SEMANTIC SIMILARITY CHECK")
            print("-" * 40)
            print(f"Response: {response.text}")
            print(f"Reference: 'I will process your refund request'")
            
            # This demonstrates the new semantic validation
            result = expect(response).semantically_similar_to(
                "I will process your refund request",
                threshold=0.85,
                model="all-MiniLM-L6-v2"
            )
            
            print(f"\n✓ PASSED with confidence: {result.confidence}")
            print(f"✓ Explanation: {result.explanation}")
            
            # Show how different wordings work
            print("\n2. ALTERNATIVE WORDINGS THAT SHOULD PASS")
            print("-" * 40)
            
            alternative_responses = [
                "Let me help you get that refund processed",
                "I'm here to assist with processing your refund", 
                "I'll take care of your refund request right away",
                "Happy to help you with the refund processing"
            ]
            
            for i, alt_response in enumerate(alternative_responses, 1):
                alt = SenytlResponse(
                    text=alt_response,
                    tool_calls=[],
                    duration_seconds=1.0
                )
                
                # Mock different scores but all above threshold
                with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
                    mock_validator = Mock()
                    mock_result = SemanticValidationResult(
                        score=0.85 + (i * 0.02),  # Slightly different scores
                        passed=True,
                        explanation="Semantically similar meaning detected",
                        model_name="all-MiniLM-L6-v2",
                        threshold=0.85
                    )
                    mock_validator.validate_response_similarity.return_value = mock_result
                    mock_get_validator.return_value = mock_validator
                    
                    with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
                        mock_assertion_validator.return_value = mock_validator
                        
                        try:
                            result = expect(alt).semantically_similar_to(
                                "I will process your refund request",
                                threshold=0.85
                            )
                            print(f"✓ '{alt_response}' → confidence: {result.confidence:.3f}")
                        except AssertionError as e:
                            print(f"✗ '{alt_response}' → FAILED")
    
    # Show failure case
    print("\n3. SEMANTICALLY DIFFERENT RESPONSES (SHOULD FAIL)")
    print("-" * 40)
    
    unrelated_response = SenytlResponse(
        text="The weather is beautiful today, isn't it?",
        tool_calls=[],
        duration_seconds=1.0
    )
    
    # Mock low semantic similarity
    with patch('senytl.semantic.get_semantic_validator') as mock_get_validator:
        mock_validator = Mock()
        mock_result = SemanticValidationResult(
            score=0.12,
            passed=False,
            explanation="Texts discuss different topics (refund vs weather)",
            model_name="all-MiniLM-L6-v2",
            threshold=0.85
        )
        mock_validator.validate_response_similarity.return_value = mock_result
        mock_get_validator.return_value = mock_validator
        
        with patch('senytl.assertions.get_semantic_validator') as mock_assertion_validator:
            mock_assertion_validator.return_value = mock_validator
            
            try:
                result = expect(unrelated_response).semantically_similar_to(
                    "I will process your refund request",
                    threshold=0.85
                )
                print("✗ This should have failed!")
            except AssertionError as e:
                print(f"✓ Correctly rejected: '{unrelated_response.text}'")
                print(f"  Score: 0.12 (below 0.85 threshold)")
                print(f"  Explanation: {mock_result.explanation}")
    
    print("\n4. COMPARISON WITH KEYWORD MATCHING")
    print("-" * 40)
    print("Basic keyword approach:")
    print('  expect(response).to_contain("refund")  # Too brittle')
    print("\nNew semantic approach:")
    print('  expect(response).semantically_similar_to(')
    print('      "I will process your refund request",')
    print('      threshold=0.85,')
    print('      model="all-MiniLM-L6-v2"')
    print('  )')
    
    print("\n5. BENEFITS OVER KEYWORD MATCHING")
    print("-" * 40)
    print("✓ Handles synonyms and paraphrases")
    print("✓ Robust to minor wording changes")
    print("✓ Configurable similarity thresholds")
    print("✓ Provides explanation for decisions")
    print("✓ Supports different models for different domains")
    print("✓ Uses state-of-the-art embeddings (sentence-transformers)")
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    demonstrate_semantic_validation()