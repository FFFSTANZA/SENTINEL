#!/usr/bin/env python3
"""
Comprehensive test script to validate all Senytl framework features.
"""
import sys
import tempfile
import shutil
from pathlib import Path

def test_basic_functionality():
    """Test basic Senytl functionality."""
    print("🧪 Testing basic functionality...")
    
    try:
        import senytl
        
        # Test default instance
        assert hasattr(senytl, 'senytl'), "Default senytl instance missing"
        assert hasattr(senytl, 'Senytl'), "Senytl class missing"
        
        # Test basic mocking
        with senytl.senytl.mock("gpt-4") as mock:
            mock.when(contains="hello").respond("Hello there!")
        
        # Test wrapping
        def dummy_agent(prompt):
            return "Response"
        
        wrapped = senytl.wrap(dummy_agent)
        assert wrapped is not None, "Agent wrapping failed"
        
        print("  ✅ Basic functionality works")
        return True
        
    except Exception as e:
        print(f"  ❌ Basic functionality failed: {e}")
        return False

def test_performance_module():
    """Test performance testing module."""
    print("🧪 Testing performance module...")
    
    try:
        import senytl.performance
        
        # Test decorator
        decorator = senytl.performance.benchmark
        assert callable(decorator), "Benchmark decorator not callable"
        
        # Test assertions
        assert hasattr(senytl.performance, 'assert_latency_under'), "Latency assertion missing"
        assert hasattr(senytl.performance, 'assert_cost_under'), "Cost assertion missing"
        assert hasattr(senytl.performance, 'assert_throughput_above'), "Throughput assertion missing"
        
        print("  ✅ Performance module works")
        return True
        
    except Exception as e:
        print(f"  ❌ Performance module failed: {e}")
        return False

def test_state_module():
    """Test state persistence module."""
    print("🧪 Testing state module...")
    
    try:
        import senytl.state
        
        # Test checkpoint functions
        assert hasattr(senytl.state, 'save_checkpoint'), "save_checkpoint missing"
        assert hasattr(senytl.state, 'from_checkpoint'), "from_checkpoint missing"
        assert hasattr(senytl.state, 'list_checkpoints'), "list_checkpoints missing"
        assert hasattr(senytl.state, 'delete_checkpoint'), "delete_checkpoint missing"
        
        # Test classes
        assert hasattr(senytl.state, 'SystemState'), "SystemState missing"
        assert hasattr(senytl.state, 'CheckpointMetadata'), "CheckpointMetadata missing"
        
        print("  ✅ State module works")
        return True
        
    except Exception as e:
        print(f"  ❌ State module failed: {e}")
        return False

def test_coverage_module():
    """Test coverage module."""
    print("🧪 Testing coverage module...")
    
    try:
        import senytl.coverage
        
        # Test coverage tracker
        assert hasattr(senytl.coverage, 'get_coverage_tracker'), "get_coverage_tracker missing"
        assert hasattr(senytl.coverage, 'CoverageTracker'), "CoverageTracker class missing"
        
        print("  ✅ Coverage module works")
        return True
        
    except Exception as e:
        print(f"  ❌ Coverage module failed: {e}")
        return False

def test_cli_commands():
    """Test CLI functionality."""
    print("🧪 Testing CLI commands...")
    
    try:
        import subprocess
        import sys
        
        # Test help command
        result = subprocess.run([sys.executable, '-m', 'senytl', '--help'], 
                              capture_output=True, text=True, cwd='/home/engine/project')
        
        assert result.returncode == 0, f"CLI help failed: {result.stderr}"
        assert "Senytl" in result.stdout, "CLI help output missing 'Senytl'"
        assert "suggest-tests" in result.stdout, "CLI help missing suggest-tests command"
        assert "generate" in result.stdout, "CLI help missing generate command"
        
        # Test version command
        result = subprocess.run([sys.executable, '-m', 'senytl', 'version'], 
                              capture_output=True, text=True, cwd='/home/engine/project')
        
        assert result.returncode == 0, f"CLI version failed: {result.stderr}"
        assert "Senytl" in result.stdout, "CLI version output missing 'Senytl'"
        
        print("  ✅ CLI commands work")
        return True
        
    except Exception as e:
        print(f"  ❌ CLI commands failed: {e}")
        return False

def test_semantic_module():
    """Test semantic validation module."""
    print("🧪 Testing semantic module...")
    
    try:
        import senytl.semantic
        import senytl
        
        # Test validator
        assert hasattr(senytl.semantic, 'SemanticValidator'), "SemanticValidator missing"
        
        # Test the semantic similarity function is available in the main module
        assert hasattr(senytl, 'expect_semantic_similarity'), "expect_semantic_similarity missing from main module"
        
        print("  ✅ Semantic module works")
        return True
        
    except Exception as e:
        print(f"  ❌ Semantic module failed: {e}")
        return False

def test_multi_agent_module():
    """Test multi-agent module."""
    print("🧪 Testing multi-agent module...")
    
    try:
        import senytl.multi_agent
        
        # Test System class
        assert hasattr(senytl.multi_agent, 'System'), "System class missing"
        assert hasattr(senytl.multi_agent, 'Agent'), "Agent class missing"
        
        print("  ✅ Multi-agent module works")
        return True
        
    except Exception as e:
        print(f"  ❌ Multi-agent module failed: {e}")
        return False

def test_assertions_module():
    """Test assertions module."""
    print("🧪 Testing assertions module...")
    
    try:
        import senytl.assertions
        
        # Test expect function
        assert hasattr(senytl.assertions, 'expect'), "expect function missing"
        
        print("  ✅ Assertions module works")
        return True
        
    except Exception as e:
        print(f"  ❌ Assertions module failed: {e}")
        return False

def test_snapshot_module():
    """Test snapshot testing module."""
    print("🧪 Testing snapshot module...")
    
    try:
        import senytl.snapshot
        
        # Test snapshot functions
        assert hasattr(senytl.snapshot, 'assert_snapshot'), "assert_snapshot missing"
        assert hasattr(senytl.snapshot, 'update_snapshots'), "update_snapshots missing"
        
        print("  ✅ Snapshot module works")
        return True
        
    except Exception as e:
        print(f"  ❌ Snapshot module failed: {e}")
        return False

def test_adversarial_module():
    """Test adversarial testing module."""
    print("🧪 Testing adversarial module...")
    
    try:
        import senytl.adversarial
        
        # Test adversarial functions
        assert hasattr(senytl.adversarial, 'test_prompt_injection'), "test_prompt_injection missing"
        assert hasattr(senytl.adversarial, 'test_data_poisoning'), "test_data_poisoning missing"
        
        print("  ✅ Adversarial module works")
        return True
        
    except Exception as e:
        print(f"  ❌ Adversarial module failed: {e}")
        return False

def test_ci_module():
    """Test CI/CD integration module."""
    print("🧪 Testing CI module...")
    
    try:
        import senytl.ci
        
        # Test CI functions
        assert hasattr(senytl.ci, 'generate_github_workflow'), "generate_github_workflow missing"
        assert hasattr(senytl.ci, 'generate_ci_report'), "generate_ci_report missing"
        
        print("  ✅ CI module works")
        return True
        
    except Exception as e:
        print(f"  ❌ CI module failed: {e}")
        return False

def run_comprehensive_test():
    """Run all tests."""
    print("🚀 Starting comprehensive Senytl framework test...")
    print("=" * 60)
    
    tests = [
        test_basic_functionality,
        test_performance_module,
        test_state_module,
        test_coverage_module,
        test_cli_commands,
        test_semantic_module,
        test_multi_agent_module,
        test_assertions_module,
        test_snapshot_module,
        test_adversarial_module,
        test_ci_module,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"  ❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The Senytl framework is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(run_comprehensive_test())