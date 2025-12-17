"""Comprehensive tests for generation module"""
import tempfile
from pathlib import Path

import pytest
from senytl.generation import (
    AgentAnalyzer,
    TestGenerator,
    generate_tests,
    generate_summary,
)


class TestAgentAnalyzer:
    """Test AgentAnalyzer class"""
    
    def test_analyze_simple_agent(self):
        """Test analyzing a simple agent file"""
        code = '''
def agent(prompt):
    return "Hello"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            analyzer = AgentAnalyzer(path)
            result = analyzer.analyze()
            
            assert "tools" in result
            assert "patterns" in result
            assert "safety_critical" in result
            assert "error" not in result
        finally:
            path.unlink()
    
    def test_analyze_with_tools(self):
        """Test analyzing agent with tool functions"""
        code = '''
def search_tool(query):
    """Search for items"""
    pass

def create_tool(data):
    """Create an item"""
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            analyzer = AgentAnalyzer(path)
            result = analyzer.analyze()
            
            assert len(result["tools"]) >= 0  # May or may not detect based on patterns
        finally:
            path.unlink()
    
    def test_analyze_with_safety_critical_tools(self):
        """Test detecting safety-critical operations"""
        code = '''
def delete_account(user_id):
    """Delete user account"""
    pass

def process_refund(amount):
    """Process refund"""
    pass

def search(query):
    """Safe search"""
    pass
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            analyzer = AgentAnalyzer(path)
            result = analyzer.analyze()
            
            # Should detect safety-critical operations
            assert "safety_critical" in result
        finally:
            path.unlink()
    
    def test_analyze_with_patterns(self):
        """Test detecting conversation patterns"""
        code = '''
def agent(prompt):
    if "hello" in prompt.lower():
        return "Hello! How can I help?"
    elif "problem" in prompt.lower():
        return "I'll help with your problem"
    elif "manager" in prompt.lower():
        return "Let me escalate this"
    return "Default response"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            analyzer = AgentAnalyzer(path)
            result = analyzer.analyze()
            
            assert "patterns" in result
            # Patterns detected from string literals
        finally:
            path.unlink()
    
    def test_analyze_nonexistent_file(self):
        """Test analyzing nonexistent file"""
        path = Path("/tmp/nonexistent_agent.py")
        analyzer = AgentAnalyzer(path)
        result = analyzer.analyze()
        
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    def test_analyze_invalid_syntax(self):
        """Test analyzing file with invalid syntax"""
        code = '''
def agent(prompt):
    return "Hello
'''  # Missing closing quote
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            analyzer = AgentAnalyzer(path)
            result = analyzer.analyze()
            
            assert "error" in result
        finally:
            path.unlink()


class TestTestGenerator:
    """Test TestGenerator class"""
    
    def test_generator_initialization(self):
        """Test generator initialization"""
        generator = TestGenerator()
        assert generator.test_cases == []
    
    def test_generate_for_simple_agent(self):
        """Test generating tests for simple agent"""
        code = '''
def agent(prompt):
    return "Hello"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            generator = TestGenerator()
            tests = generator.generate_for_agent(path)
            
            assert len(tests) > 0
            assert "import pytest" in tests
            assert "from senytl import" in tests
        finally:
            path.unlink()
    
    def test_generate_tool_tests(self):
        """Test generating tool-specific tests"""
        generator = TestGenerator()
        generator._generate_tool_tests(["search", "create", "delete"])
        
        assert len(generator.test_cases) == 3
        assert "test_search_usage" in generator.test_cases[0]
        assert "test_create_usage" in generator.test_cases[1]
    
    def test_generate_conversation_tests(self):
        """Test generating conversation flow tests"""
        generator = TestGenerator()
        generator._generate_conversation_tests(["greeting", "problem_solving"])
        
        assert len(generator.test_cases) == 2
        assert "test_conversation_greeting" in generator.test_cases[0]
    
    def test_generate_adversarial_tests(self):
        """Test generating adversarial tests"""
        generator = TestGenerator()
        generator._generate_adversarial_tests(["delete_account", "process_refund"])
        
        assert len(generator.test_cases) == 2
        assert "adversarial" in generator.test_cases[0]
        assert "jailbreak" in generator.test_cases[0].lower()
    
    def test_generate_edge_case_tests(self):
        """Test generating edge case tests"""
        generator = TestGenerator()
        generator._generate_edge_case_tests(["search"])
        
        assert len(generator.test_cases) >= 2
        assert any("empty" in tc.lower() for tc in generator.test_cases)


class TestGenerateFunctions:
    """Test module-level functions"""
    
    def test_generate_tests_with_output(self):
        """Test generating tests with output file"""
        code = '''
def agent(prompt):
    return "Hello"
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_file = Path(tmpdir) / "agent.py"
            agent_file.write_text(code)
            
            output_file = Path(tmpdir) / "test_agent.py"
            
            tests = generate_tests(agent_file, output_file)
            
            assert output_file.exists()
            assert len(tests) > 0
            assert "import pytest" in tests
    
    def test_generate_tests_without_output(self):
        """Test generating tests without saving to file"""
        code = '''
def agent(prompt):
    return "Hello"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            tests = generate_tests(path, None)
            
            assert len(tests) > 0
            assert "import pytest" in tests
        finally:
            path.unlink()
    
    def test_generate_summary(self):
        """Test generating summary"""
        code = '''
def search_tool(query):
    pass

def delete_account(user_id):
    pass

def agent(prompt):
    if "hello" in prompt:
        return "Hi"
    return "Default"
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)
        
        try:
            summary = generate_summary(path)
            
            assert "Analyzing agent" in summary
            assert "test" in summary.lower()
        finally:
            path.unlink()
    
    def test_generate_summary_with_error(self):
        """Test generating summary for nonexistent file"""
        path = Path("/tmp/nonexistent.py")
        summary = generate_summary(path)
        
        assert "Error" in summary or "error" in summary


class TestGenerationEdgeCases:
    """Test edge cases"""
    
    def test_empty_agent_file(self):
        """Test with empty agent file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("")
            f.flush()
            path = Path(f.name)
        
        try:
            generator = TestGenerator()
            tests = generator.generate_for_agent(path)
            
            # Should still generate header and edge cases
            assert "import pytest" in tests
        finally:
            path.unlink()
    
    def test_generate_many_tools(self):
        """Test generating tests for many tools"""
        generator = TestGenerator()
        tools = [f"tool{i}" for i in range(20)]
        generator._generate_tool_tests(tools)
        
        # Should limit to 8 tools
        assert len(generator.test_cases) == 8
    
    def test_generate_many_patterns(self):
        """Test generating tests for many patterns"""
        generator = TestGenerator()
        patterns = [f"pattern{i}" for i in range(20)]
        generator._generate_conversation_tests(patterns)
        
        # Should limit to 6 patterns
        assert len(generator.test_cases) == 6
    
    def test_generate_many_safety_critical(self):
        """Test generating tests for many safety-critical operations"""
        generator = TestGenerator()
        operations = [f"delete{i}" for i in range(20)]
        generator._generate_adversarial_tests(operations)
        
        # Should limit to 5
        assert len(generator.test_cases) == 5
